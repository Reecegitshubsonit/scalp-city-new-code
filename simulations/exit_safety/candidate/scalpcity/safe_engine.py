"""Candidate production-engine integration. Broker I/O runs outside the engine lock.
Only adapters with explicit PAPER capability are accepted. See release_gate.json.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import hashlib
import fcntl
import json
import math
import os
import uuid

from .engine import Engine
from .bot import Position, State
from .contracts import atm_strike, next_trading_day, occ_symbol
from .types import Bar, Fill, OrderIntent, ET

TERMINAL = {'FILLED', 'CANCELLED', 'REJECTED', 'EXPIRED', 'FAILED'}
UNKNOWN_GRACE_S = 30
ACTIVE = {'PREPARED','SUBMITTED','PARTIALLY_FILLED','CANCEL_PENDING','UNKNOWN'}

class SafeEngine(Engine):
    def __init__(self, settings, log, adapter, quotes, state_path, now_fn=None, fee_per_contract=0.0, **kwargs):
        if getattr(adapter, 'capability', None) != 'PAPER':
            raise ValueError('paper adapter required')
        super().__init__(settings, log, adapter, quotes, **kwargs)
        self.now_fn = now_fn or (lambda: datetime.now(ET))
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True,exist_ok=True)
        self._state_lock = self.state_path.with_suffix('.lock').open('a')
        try:fcntl.flock(self._state_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except Exception:
            self._state_lock.close()
            raise RuntimeError('candidate state already in use')
        self.pool = ThreadPoolExecutor(max_workers=12, thread_name_prefix='paper-order')
        self.orders = {}
        self.futures = {}
        self.telemetry = []
        self.reconciled = False
        self.halted = True
        self.fee_per_contract = fee_per_contract
        self.config_hash = hashlib.sha256(json.dumps({'settings':asdict(settings),'fee_per_contract':fee_per_contract},default=str,sort_keys=True).encode()).hexdigest()
        self.stopping = False

    def _record(self, kind, **data):
        self.telemetry.append(dict(kind=kind, observed_at=self.now_fn().isoformat(), **data))

    def _save(self):
        payload = {'version':1,'config_hash':self.config_hash,'day':str(self.day),
                   'orders':self.orders,'telemetry':self.telemetry[-2000:], 'bots':{}}
        for b in self.bots:
            payload['bots'][b.bot_id] = dict(position=asdict(b.position) if b.position else None,
                pending=b.pending,exit_reason=b.exit_reason,pnl_day=b.pnl_day,trades=b.trades,
                cooldown_until=b.cooldown_until.isoformat() if b.cooldown_until else None,
                paused=b.paused,locked=b.locked)
        self.state_path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.state_path.with_suffix('.tmp')
        try:
            with tmp.open('w') as f:
                json.dump(payload,f,default=str,allow_nan=False,sort_keys=True)
                f.flush();os.fsync(f.fileno())
            os.replace(tmp,self.state_path)
            fd=os.open(self.state_path.parent,os.O_RDONLY)
            try:os.fsync(fd)
            finally:os.close(fd)
        except Exception:
            self.halted=True;self.reconciled=False
            raise

    def load_state(self):
        with self.lock:
            data=json.loads(self.state_path.read_text())
            if data['version']!=1 or data['config_hash']!=self.config_hash or data['day']!=str(self.day):
                raise ValueError('state version, settings, or session mismatch')
            self.orders=data['orders'];self.telemetry=data['telemetry']
            for bid,x in data['bots'].items():
                b=self.by_id[bid];p=x.pop('position')
                if p and p['opened_at']:p['opened_at']=datetime.fromisoformat(p['opened_at'])
                b.position=Position(**p) if p else None
                x['cooldown_until']=datetime.fromisoformat(x['cooldown_until']) if x['cooldown_until'] else None
                for key,value in x.items():setattr(b,key,value)
                b.state=State.EXITING if b.exit_reason else State.MANAGING if b.position else State.IDLE
            self.reconciled=False;self.halted=True

    def _owned(self):
        result={}
        for b in self.bots:
            p=b.position
            if p and p.entry_price is not None:
                result[p.contract]=result.get(p.contract,0)+p.qty
        return {k:v for k,v in result.items() if v}

    def reconcile(self, snapshot):
        """Authoritative paper-account snapshot, including statuses of tracked orders.
        Called with collection complete; never performs network I/O under the lock.
        """
        with self.lock:
            stamp=datetime.fromisoformat(snapshot['observed_at'])
            if not 0 <= (self.now_fn()-stamp).total_seconds() <= 5:
                self.reconciled=False;self.halted=True;return False
            self.reconciled=False;self.halted=True
            for update in snapshot['orders']:
                if update['client_order_id'] in self.orders:
                    self._apply(update)
            self._fail_unseen_unknown(stamp, {u['client_order_id'] for u in snapshot['orders']})
            expected={oid for oid,o in self.orders.items() if o['status'] not in TERMINAL}
            actual={o['client_order_id'] for o in snapshot['orders'] if o['status'] not in TERMINAL}
            positions={k:int(v) for k,v in snapshot['positions'].items() if v}
            # Unknown/prepared orders must be resolved with broker detail before any submission.
            uncertain=any(o['status'] in {'UNKNOWN','PREPARED'} for o in self.orders.values())
            self.reconciled=expected==actual and positions==self._owned() and not uncertain
            self.halted=not self.reconciled
            self._record('reconciliation',ok=self.reconciled)
            self._save()
            return self.reconciled

    def _fail_unseen_unknown(self, stamp, seen):
        """An UNKNOWN order the broker snapshot, taken UNKNOWN_GRACE_S after the failure, still does not list was never accepted.
        Only unfilled orders qualify; a filled one missing from the broker stays unresolved for manual review."""
        for oid,o in self.orders.items():
            if o['status']!='UNKNOWN' or oid in seen or o['filled']:continue
            since=o.get('unknown_at')
            if since is None or (stamp-datetime.fromisoformat(since)).total_seconds()<UNKNOWN_GRACE_S:continue
            o['status']='FAILED'
            b=self.by_id[o['bot']];b.pending=None
            if o['kind']=='BUY_OPEN' and b.position and b.position.entry_price is None:
                b.on_order_failed('BUY_OPEN','NOT_ACCEPTED')
            self._record('unknown_resolved_not_accepted',order_id=oid,bot=o['bot'])

    def _active_for(self, bid):
        return [(oid,o) for oid,o in self.orders.items() if o['bot']==bid and o['status'] not in TERMINAL]

    def _quote(self, contract, now):
        q=self.quotes.get(contract,now)  # adapter MUST supply an in-memory quote cache
        if q is None or q.symbol != contract:return None
        if not all(math.isfinite(v) for v in (q.bid,q.ask)) or q.bid<=0 or q.ask<q.bid:return None
        if not 0 <= (now-q.ts).total_seconds() <= 2:return None
        return q

    def _execute(self, bot, intent, bar, ind):
        now=self.now_fn()
        if self.stopping or not self.reconciled or self._active_for(bot.bot_id):
            if not self._active_for(bot.bot_id):
                if intent.kind=='BUY_OPEN':bot.on_order_failed(intent.kind,'RECONCILIATION_REQUIRED')
                else:bot.pending=None
            return
        contract=occ_symbol(intent.ticker,next_trading_day(bar.ts.date()),intent.right,atm_strike(bar.close)) if intent.kind=='BUY_OPEN' else intent.contract
        q=self._quote(contract,now)
        if q is None:
            bot.on_order_failed(intent.kind,'NO_FRESH_QUOTE');self._save();return
        if intent.kind=='BUY_OPEN':
            ok,why=self.risk.check(intent,q,self.stale,self.halted)
            if not ok:bot.on_order_failed(intent.kind,why);self._save();return
        elif not bot.position or intent.qty>bot.position.qty:
            raise ValueError('exit exceeds owned position')
        oid=uuid.uuid4().hex
        o=dict(client_order_id=oid,bot=bot.bot_id,contract=contract,kind=intent.kind,
               qty=intent.qty,status='PREPARED',filled=0,notional=0.0,fees=0.0,
               limit=q.ask if intent.kind=='BUY_OPEN' else q.bid,
               quote_bid=q.bid,quote_ask=q.ask,quote_at=q.ts.isoformat(),
               decision_at=bar.end.isoformat(),submitted_at=now.isoformat(),reason=intent.reason,
               cancel_requested=False)
        self.orders[oid]=o
        self._record('order_prepared',order_id=oid,bot=bot.bot_id,decision_at=o['decision_at'],quote_at=o['quote_at'])
        self._save()  # journal stable id before crossing the broker boundary
        self.futures[oid]=(self.pool.submit(self.broker.submit,dict(o)),'submit')

    def _apply(self, u):
        oid=u['client_order_id'];o=self.orders[oid];b=self.by_id[o['bot']]
        status=u['status'];n=u['filled_qty'];avg=u.get('avg_price')
        if u.get('contract',o['contract'])!=o['contract'] or u.get('qty',o['qty'])!=o['qty']:
            raise ValueError('broker order identity/quantity mismatch')
        expected_side='BUY' if o['kind']=='BUY_OPEN' else 'SELL'
        if u.get('side',expected_side)!=expected_side:raise ValueError('broker side mismatch')
        if status not in TERMINAL|ACTIVE:raise ValueError('unknown broker status')
        if not isinstance(n,int) or not o['filled']<=n<=o['qty']:raise ValueError('invalid cumulative fill')
        if o['status'] in TERMINAL and (status!=o['status'] or n!=o['filled']):raise ValueError('terminal status regression')
        if status=='FILLED' and n!=o['qty']:raise ValueError('inconsistent FILLED quantity')
        if n and (avg is None or not math.isfinite(avg) or avg<=0):raise ValueError('missing fill price')
        total=round(n*(avg or 0)*100,6)
        fees=float(u.get('fees',n*self.fee_per_contract))
        if not math.isfinite(fees) or fees<o['fees']:raise ValueError('invalid cumulative fees')
        delta=n-o['filled'];delta_fee=fees-o['fees']
        if o['status'] in TERMINAL and delta==0 and abs(total-o['notional'])<1e-5 and delta_fee==0:return
        if delta==0 and (abs(total-o['notional'])>1e-5 or delta_fee):raise ValueError('fill correction requires manual reconciliation')
        events=[]
        if delta:
            px=(total-o['notional'])/(100*delta)
            if not math.isfinite(px) or px<=0:raise ValueError('invalid incremental fill price')
            fill_time=datetime.fromisoformat(u['fill_time'])
            if fill_time.tzinfo is None or fill_time>self.now_fn():raise ValueError('invalid broker fill time')
            fill=Fill(b.bot_id,o['kind'],o['contract'],delta,px,getattr(self.broker,'fill_source','paper_adapter'),fill_time,o['quote_bid'],o['quote_ask'])
            events=b.on_fill(fill,terminal=status in TERMINAL,fee=delta_fee)
        o.update(status=status,filled=n,notional=total,fees=fees)
        if status in TERMINAL and b.position:
            b.pending=None
            if o['kind']=='BUY_OPEN' and n==0:
                b.on_order_failed('BUY_OPEN',status)
        self._record('order_update',order_id=oid,status=status,cumulative_filled=n,broker_fill_at=u.get('fill_time'))
        self._save()  # authoritative snapshot before best-effort UI event projection
        if events:self._write(self.now_fn(),b,events)

    def service(self):
        """Drain completed broker tasks and queue polls/cancels; never wait on I/O."""
        with self.lock:
            for oid,(future,op) in list(self.futures.items()):
                if not future.done():continue
                del self.futures[oid]
                try:self._apply(future.result())
                except Exception as e:
                    if self.orders[oid]['status'] not in TERMINAL:
                        self.orders[oid]['status']='UNKNOWN'
                        self.orders[oid].setdefault('unknown_at',self.now_fn().isoformat())
                    self.halted=True;self.reconciled=False
                    self._record('broker_uncertainty',order_id=oid,operation=op,error_type=type(e).__name__)
                    self._save()
            for oid,o in self.orders.items():
                if self.stopping:continue
                if o['status'] in TERMINAL or oid in self.futures:continue
                age=(self.now_fn()-datetime.fromisoformat(o['submitted_at'])).total_seconds()
                if (age>=15 or o['cancel_requested']) and not o.get('cancel_sent') and o['status']!='UNKNOWN':
                    o['cancel_sent']=True;o['status']='CANCEL_PENDING';self._save()
                    self.futures[oid]=(self.pool.submit(self.broker.cancel,oid),'cancel')
                else:self.futures[oid]=(self.pool.submit(self.broker.poll,oid),'poll')

    def monitor(self, ticker, price, observed_at):
        """Fresh underlying tick path, separate from completed-bar entry signals."""
        with self.lock:
            now=self.now_fn()
            fresh=price is not None and math.isfinite(price) and price>0 and 0 <= (now-observed_at).total_seconds()<=2
            for b in self.bots:
                p=b.position
                if b.ticker!=ticker or not p or p.entry_price is None:continue
                sign=1 if p.right=='CALL' else -1
                why='TIME' if now.time()>=self.s.flat_by else 'STOP' if fresh and sign*(price-p.stop_und)<=0 else 'TARGET' if fresh and sign*(price-p.target_und)>=0 else None
                if why and not b.exit_reason:
                    b.exit_reason=why
                    self._record('exit_latched',bot=b.bot_id,reason=why,market_at=observed_at.isoformat())
                    self._save()
                if not b.exit_reason:continue
                active=self._active_for(b.bot_id)
                if active:
                    for oid,o in active:
                        if o['kind']=='BUY_OPEN':o['cancel_requested']=True
                    self._save();continue
                b.pending='exit'
                intent=OrderIntent(b.bot_id,ticker,'SELL_CLOSE',p.right,p.qty,b.exit_reason,price or p.entry_und,p.contract)
                bar=Bar(ticker,now,price or p.entry_und,0,0,price or p.entry_und,0)
                # Decision timestamp is actual monitor time, not a fabricated bar end.
                from datetime import timedelta
                bar=Bar(ticker,now-timedelta(minutes=1),bar.open,bar.high,bar.low,bar.close,0)
                self._execute(b,intent,bar,self.ind[ticker])

    def check_stale(self, now, last_bar_wall, open_quote_wall=None):
        # Do not invoke the legacy synchronous liquidation path.
        with self.lock:
            for ticker in self.ind:
                seen=last_bar_wall.get(ticker)
                if seen is None or (now-seen).total_seconds()>self.s.stale_idle_s:self.stale.add(ticker)
                else:self.stale.discard(ticker)
            for b in self.bots:
                p=b.position
                if not p or p.entry_price is None:continue
                seen=(open_quote_wall or {}).get(b.bot_id) or p.opened_at
                if seen and (now-seen).total_seconds()>self.s.flatten_after_stale_s:
                    b.exit_reason=b.exit_reason or 'STALE'
            self._save()
        for ticker in self.ind:self.monitor(ticker,None,now)

    def set_paused(self,bot_id,paused,time):
        super().set_paused(bot_id,paused,time)
        with self.lock:self._save()

    def recover(self,events):
        raise RuntimeError('SafeEngine requires its durable state and broker reconciliation; legacy log recovery is unsafe')

    def close(self):
        self.stopping=True
        self.pool.shutdown(wait=True,cancel_futures=False)
        self.service()
        fcntl.flock(self._state_lock,fcntl.LOCK_UN)
        self._state_lock.close()
