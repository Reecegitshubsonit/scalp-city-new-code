"""Fault-injection fuzz of the candidate SafeEngine against a fake broker. Offline only.
Run: PYTHONPATH=../candidate python fuzz_candidate.py [seeds] [steps]
"""
import json, random, sys, tempfile
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from scalpcity.safe_engine import SafeEngine
from scalpcity.bot import Position, State
from scalpcity.config import Settings
from scalpcity.events import EventLog
from scalpcity.types import ET, Quote

START = datetime(2026, 10, 9, 11, 58, tzinfo=ET)
C = 'QQQ261012C00750000'
ENTRY = 2.79
SEEDS = {'QQQ-VWAP': 10, 'QQQ-EMA50': 7, 'QQQ-RANGE': 5}
TERM = {'FILLED', 'CANCELLED', 'REJECTED', 'EXPIRED'}


class FuzzBroker:
    capability = 'PAPER'

    def __init__(self, rng, clock, p):
        self.rng, self.clock, self.p = rng, clock, p
        self.orders, self.pos, self.sells = {}, {C: sum(SEEDS.values())}, []
        self.violations = []
        self.fees, self.sell_fills = 0.0, []   # (qty, price)

    def _snap(self, o): return dict(o)

    def submit(self, o):
        r = self.rng.random()
        if r < self.p['submit_reject_lost']:
            raise TimeoutError('request lost before broker accepted')   # broker never saw it
        committed = sum(x['qty'] - x['filled_qty'] for x in self.orders.values()
                        if x['status'] not in TERM and x['side'] == 'SELL')
        if o['kind'] == 'SELL_CLOSE' and o['qty'] + committed > self.pos[C]:
            self.violations.append('OVERSELL_SUBMIT')
        self.orders[o['client_order_id']] = dict(
            client_order_id=o['client_order_id'], status='SUBMITTED', filled_qty=0, avg_price=None, fees=0.0,
            fill_time=self.clock[0].isoformat(), contract=o['contract'], qty=o['qty'],
            side='BUY' if o['kind'] == 'BUY_OPEN' else 'SELL')
        if r < self.p['submit_reject_lost'] + self.p['submit_accepted_lost']:
            raise TimeoutError('accepted but response lost')
        return self._snap(self.orders[o['client_order_id']])

    def poll(self, oid):
        if self.rng.random() < self.p['poll_fail']:
            raise ConnectionError('poll failed')
        return self._snap(self.orders[oid])

    def cancel(self, oid):
        if self.rng.random() < self.p['poll_fail']:
            raise ConnectionError('cancel failed')
        return self._snap(self.orders[oid])   # ack is not terminal

    def advance(self, oid, mode):
        o = self.orders[oid]
        if o['status'] in TERM:
            return
        rem = o['qty'] - o['filled_qty']
        n = rem if mode == 'full' else self.rng.randint(1, max(1, rem - 1)) if mode == 'part' else 0
        if n:
            px = round(self.rng.uniform(2.4, 3.1), 2)
            old = o['filled_qty'] * (o['avg_price'] or 0)
            o['filled_qty'] += n
            o['avg_price'] = round((old + n * px) / o['filled_qty'], 6)
            fee = round(0.65 * n, 2)
            o['fees'] = round(o['fees'] + fee, 2)
            self.fees += fee
            o['fill_time'] = self.clock[0].isoformat()
            if o['side'] == 'SELL':
                self.pos[C] -= n
                self.sell_fills.append((n, px))
            else:
                self.pos[C] += n
        o['status'] = 'FILLED' if o['filled_qty'] == o['qty'] else 'PARTIALLY_FILLED' if mode == 'part' else \
            self.rng.choice(['CANCELLED', 'EXPIRED', 'REJECTED']) if mode == 'end' else o['status']
        if mode == 'end' and o['status'] == 'FILLED':
            o['status'] = 'CANCELLED' if o['filled_qty'] < o['qty'] else 'FILLED'

    def snapshot(self):
        return {'observed_at': self.clock[0].isoformat(), 'orders': [self._snap(o) for o in self.orders.values()],
                'positions': {k: v for k, v in self.pos.items() if v}}


def build(tmp, broker, clock, cache):
    e = SafeEngine(Settings(), EventLog(str(Path(tmp) / 'log'), 'fuzz'), broker,
                   SimpleNamespace(get=lambda c, t: cache.get(c)), Path(tmp) / 'state.json', now_fn=lambda: clock[0],
                   fee_per_contract=0.65)
    e.start_session(START.date(), {})
    return e


def settle(e):
    for f, _ in list(e.futures.values()):
        try: f.result(timeout=3)
        except Exception: pass
    e.service()


def run(seed, steps, p):
    rng = random.Random(seed)
    clock = [START]
    cache = {}
    broker = FuzzBroker(rng, clock, p)
    tmp = tempfile.mkdtemp()
    e = build(tmp, broker, clock, cache)
    for bid, q in SEEDS.items():
        b = e.by_id[bid]
        b.position = Position('CALL', q, 750.08, 749.77, 750.70, C, ENTRY, START, entry_qty=q)
        b.state = State.MANAGING
    cache[C] = Quote(C, clock[0], 2.95, 2.97)
    e.reconcile(broker.snapshot())
    price, touched, latch_cleared, restarts, notes = 750.08, set(), 0, 0, []
    for _ in range(steps):
        clock[0] += timedelta(seconds=rng.choice([1, 2, 3, 8, 16, 20]))
        cache[C] = Quote(C, clock[0] - timedelta(seconds=0 if rng.random() > p['stale_quote'] else 5), 2.9, 2.92)
        price = round(min(751.2, max(749.2, price + rng.uniform(-.35, .35))), 3)
        before = {b.bot_id: b.exit_reason for b in e.bots}
        if rng.random() < .85:
            e.monitor('QQQ', price, clock[0])
        for b in e.bots:
            if b.exit_reason: touched.add(b.bot_id)
        act = [o for o in broker.orders.values() if o['status'] not in TERM]
        if act and rng.random() < .6:
            o = rng.choice(act)
            broker.advance(o['client_order_id'], rng.choice(['full', 'part', 'part', 'end', 'none']))
        if broker.orders and rng.random() < p['dup_update']:
            try: e._apply(dict(rng.choice(list(broker.orders.values()))))
            except ValueError as ex: notes.append(f'dup_rejected:{ex}')
        settle(e)
        for b in e.bots:   # latch must never clear while position remains
            if before[b.bot_id] and b.position and not b.exit_reason: latch_cleared += 1
            sells = [1 for oid, o in e.orders.items() if o['bot'] == b.bot_id and o['kind'] == 'SELL_CLOSE' and o['status'] not in {'FILLED','CANCELLED','REJECTED','EXPIRED','FAILED'}]
            if len(sells) > 1: broker.violations.append('DUP_ACTIVE_SELL')
        if rng.random() < .25: e.reconcile(broker.snapshot())
        if rng.random() < p['restart']:
            e.close(); restarts += 1
            e = build(tmp, broker, clock, cache); e.load_state()
            e.reconcile(broker.snapshot())
    # end of day: broker resolves everything, then a final reconcile
    for _ in range(4):
        clock[0] += timedelta(seconds=20)
        cache[C] = Quote(C, clock[0], 2.9, 2.92)
        for oid, o in list(broker.orders.items()):
            if o['status'] not in TERM: broker.advance(oid, rng.choice(['full', 'end']))
        settle(e); settle(e)
        e.monitor('QQQ', price, clock[0]); settle(e); settle(e)
    clock[0] += timedelta(seconds=1)
    for _ in range(3):
        for oid, o in list(broker.orders.items()):
            if o['status'] not in TERM: broker.advance(oid, 'end')
        settle(e)
    ok = e.reconcile(broker.snapshot())
    owned = e._owned().get(C, 0)
    truth = broker.pos[C]
    exp = sum((px - ENTRY) * n * 100 for n, px in broker.sell_fills) - sum(
        o['fees'] for o in broker.orders.values() if o['side'] == 'SELL')
    pnl = sum(b.pnl_day for b in e.bots)
    unmanaged = sum(b.position.qty for b in e.bots if b.position and b.exit_reason)
    res = dict(seed=seed, reconciled=ok, local_qty=owned, broker_qty=truth, violations=sorted(set(broker.violations)),
               latch_cleared=latch_cleared, restarts=restarts, halted=e.halted,
               stuck_unknown=sum(1 for o in e.orders.values() if o['status'] == 'UNKNOWN'),
               unmanaged_latched_qty=unmanaged if not ok else 0,
               pnl_local=round(pnl, 2), pnl_expected=round(exp, 2),
               pnl_ok=abs(pnl - exp) < .05 if owned == truth else None,
               submits=sum(1 for o in broker.orders.values()))
    if truth < 0: res['violations'].append('NEGATIVE_BROKER_POSITION')
    e.close()
    return res


PROFILES = {
    'baseline_faults': dict(submit_reject_lost=0, submit_accepted_lost=0, poll_fail=.05, stale_quote=.1, dup_update=.2, restart=.03),
    'lossy_submit': dict(submit_reject_lost=.05, submit_accepted_lost=.08, poll_fail=.1, stale_quote=.15, dup_update=.3, restart=.05),
}

if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    steps = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    out = {}
    for name, p in PROFILES.items():
        rows = [run(s, steps, p) for s in range(n)]
        out[name] = dict(
            runs=len(rows),
            violations={v: sum(v in r['violations'] for r in rows) for v in {v for r in rows for v in r['violations']}},
            latch_cleared_runs=sum(r['latch_cleared'] > 0 for r in rows),
            ended_reconciled=sum(r['reconciled'] for r in rows),
            ended_halted_not_reconciled=sum(not r['reconciled'] for r in rows),
            ended_with_unknown_order=sum(r['stuck_unknown'] > 0 for r in rows),
            ended_diverged_qty=sum(r['local_qty'] != r['broker_qty'] for r in rows),
            pnl_mismatch_when_qty_agrees=sum(r['pnl_ok'] is False for r in rows),
            unmanaged_latched_runs=sum(r['unmanaged_latched_qty'] > 0 for r in rows),
            restarts=sum(r['restarts'] for r in rows), orders=sum(r['submits'] for r in rows),
            examples=[r for r in rows if r['violations'] or r['pnl_ok'] is False or r['latch_cleared']][:3] +
                     [r for r in rows if not r['reconciled']][:2])
    print(json.dumps(out, indent=1, default=str))
