"""Disconnected ticker-direction ownership prototype; no broker APIs."""
from threading import RLock
import json

class DirectionBook:
    def __init__(self):
        self.lock=RLock(); self.entries={}; self.exit_fills={}; self.reconciled=True

    def reserve(self,order_id,ticker,side,qty):
        if side not in ('CALL','PUT') or qty<=0:raise ValueError('invalid entry')
        with self.lock:
            if not self.reconciled:return False
            if order_id in self.entries:raise ValueError('duplicate reservation')
            if any(x['ticker']==ticker and x['side']!=side and (x['pending'] or x['held']) for x in self.entries.values()):return False
            self.entries[order_id]=dict(ticker=ticker,side=side,requested=qty,cumulative=0,pending=qty,held=0,status='PENDING')
            return True

    def update_entry(self,order_id,cumulative,status):
        with self.lock:
            x=self.entries[order_id]
            if not x['cumulative']<=cumulative<=x['requested']:raise ValueError('invalid cumulative fill')
            if status not in ('PENDING','PARTIAL','UNKNOWN','FILLED','CANCELLED','REJECTED'):raise ValueError('invalid status')
            if status=='FILLED' and cumulative!=x['requested']:raise ValueError('incomplete full fill')
            if x['status'] in ('FILLED','CANCELLED','REJECTED') and cumulative==x['cumulative']:
                return  # ignore duplicated/stale entry status without resurrecting pending quantity
            was_terminal=x['status'] in ('FILLED','CANCELLED','REJECTED')
            x['held']+=cumulative-x['cumulative'];x['cumulative']=cumulative
            x['pending']=0 if status in ('FILLED','CANCELLED','REJECTED') else x['requested']-cumulative
            x['status']=status
            if was_terminal or not self.invariant():self.reconciled=False

    def reduce(self,order_id,quantity,fill_id=None):
        with self.lock:
            if fill_id in self.exit_fills:
                if self.exit_fills[fill_id]!=[order_id,quantity]:raise ValueError('conflicting duplicate exit')
                return
            x=self.entries[order_id]
            if quantity<=0 or quantity>x['held']:raise ValueError('exit exceeds holdings')
            x['held']-=quantity
            if fill_id is not None:self.exit_fills[fill_id]=[order_id,quantity]

    def invariant(self):
        with self.lock:
            tickers={x['ticker'] for x in self.entries.values()}
            return all(len({x['side'] for x in self.entries.values() if x['ticker']==t and (x['held'] or x['pending'])})<=1 for t in tickers)

    def snapshot(self):
        with self.lock:return json.dumps(dict(entries=self.entries,exit_fills=self.exit_fills),sort_keys=True)

    @classmethod
    def restore(cls,raw):
        b=cls();saved=json.loads(raw);b.entries=saved['entries'];b.exit_fills=saved['exit_fills'];b.reconciled=False;return b

    def reconcile(self,held,pending):
        with self.lock:
            expected_held={k:v['held'] for k,v in self.entries.items() if v['held']}
            expected_pending={k:v['pending'] for k,v in self.entries.items() if v['pending']}
            self.reconciled=held==expected_held and pending==expected_pending and self.invariant()
            return self.reconciled
