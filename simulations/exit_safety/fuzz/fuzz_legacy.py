"""Same fault classes against the CURRENT production Engine (read-only import) + scenario-1 replay of QQQ-VWAP #29.
Run from repo root: PYTHONPATH=. .venv/bin/python simulations/exit_safety/fuzz/fuzz_legacy.py
Model assumption (labelled): when execute() returns None (NO_FILL) the order may still fill later at the broker.
"""
import json, random, sys, tempfile
from datetime import datetime, timedelta
from types import SimpleNamespace

from scalpcity.engine import Engine
from scalpcity.bot import Position, State
from scalpcity.config import Settings
from scalpcity.events import EventLog
from scalpcity.types import ET, Bar, Fill, Quote

START = datetime(2026, 10, 9, 11, 58, tzinfo=ET)
C = 'QQQ261012C00750000'
ENTRY = 2.79
SEEDS = {'QQQ-VWAP': 10, 'QQQ-EMA50': 7, 'QQQ-RANGE': 5}


class LegacyFuzzBroker:
    source = 'broker'

    def __init__(self, rng, p):
        self.rng, self.p, self.pos, self.late, self.viol = rng, p, sum(SEEDS.values()), [], set()

    def execute(self, intent, contract, quote, ts):
        r = self.rng.random()
        sgn = -1 if intent.kind == 'SELL_CLOSE' else 1
        if sgn < 0 and intent.qty > self.pos: self.viol.add('OVERSELL_SUBMIT')
        if r < self.p['nofill']:                      # engine sees NO_FILL...
            if self.rng.random() < self.p['late_fill']:   # ...but broker fills it afterwards
                self.pos += sgn * intent.qty; self.viol.add('_late')
            return None
        if r < self.p['nofill'] + self.p['raise_']:
            if self.rng.random() < .5: self.pos += sgn * intent.qty
            raise TimeoutError()
        self.pos += sgn * intent.qty
        return Fill(intent.bot_id, intent.kind, contract, intent.qty, quote.bid, 'broker', ts, quote.bid, quote.ask)


def run(seed, steps, p):
    rng = random.Random(seed)
    broker = LegacyFuzzBroker(rng, p)
    clock = [START]
    e = Engine(Settings(), EventLog(tempfile.mkdtemp(), 'fuzz'), broker,
               SimpleNamespace(get=lambda c, t: Quote(c, clock[0], 2.9, 2.92)))
    e.start_session(START.date(), {})
    for bid, q in SEEDS.items():
        b = e.by_id[bid]; b.position = Position('CALL', q, 750.08, 749.77, 750.70, C, ENTRY, START); b.state = State.MANAGING
    price, touched = 750.08, set()
    for i in range(steps):
        price = round(min(751.2, max(749.2, price + rng.uniform(-.5, .5))), 3)
        bar = Bar('QQQ', clock[0], price, price, price, price, 1000)
        clock[0] += timedelta(minutes=1)
        for b in e.bots:
            if b.ticker == 'QQQ' and b.position and (price <= b.position.stop_und or price >= b.position.target_und): touched.add(b.bot_id)
        e.on_bar(bar)
    local = sum(b.position.qty for b in e.bots if b.position)
    left = {b.bot_id for b in e.bots if b.position}
    viol = broker.viol - {'_late'}
    if broker.pos < 0: viol.add('NEGATIVE_BROKER_POSITION')
    return dict(seed=seed, violations=sorted(viol), local_qty=local, broker_qty=broker.pos,
                diverged=local != broker.pos, intent_lost=len(touched & left))


def scenario1():
    """QQQ-VWAP #29: TARGET at 11:58 gets NO_FILL, price reverts 11:59."""
    e = Engine(Settings(), EventLog(tempfile.mkdtemp(), 's1'), SimpleNamespace(execute=lambda *a: None),
               SimpleNamespace(get=lambda c, t: Quote(c, t, 3.06, 3.08)))
    e.start_session(START.date(), {})
    b = e.by_id['QQQ-VWAP']; b.position = Position('CALL', 10, 750.08, 749.77, 750.70, C, 2.79, START); b.state = State.MANAGING
    trace = []
    for t, px in [(START, 750.71), (START + timedelta(minutes=1), 750.46), (START + timedelta(minutes=2), 750.20)]:
        bar = Bar('QQQ', t, px, px, px, px, 1000)
        e.on_bar(bar)
        trace.append(dict(bar_close=px, state=b.state.value, reason=b.reason_code, holding=bool(b.position)))
    return trace


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    profiles = {'nofill_then_late_fill': dict(nofill=.12, late_fill=.5, raise_=.04),
                'no_late_fills (pure retry)': dict(nofill=.12, late_fill=0, raise_=0)}
    out = {'scenario1_legacy_trace': scenario1()}
    for name, p in profiles.items():
        rows = [run(s, 60, p) for s in range(n)]
        out[name] = dict(runs=n, violation_runs=sum(bool(r['violations']) for r in rows),
                         violations={v: sum(v in r['violations'] for r in rows) for v in {v for r in rows for v in r['violations']}},
                         diverged_runs=sum(r['diverged'] for r in rows), intent_lost_runs=sum(r['intent_lost'] > 0 for r in rows))
    print(json.dumps(out, indent=1))
