"""Scenario 1 on candidate: TARGET latched at 11:58, exit order ends unfilled, price reverts, exit still re-sent."""
import json, sys, tempfile
sys.path.insert(0, 'fuzz')
import fuzz_candidate as f
from datetime import timedelta
from scalpcity.types import Quote
import random
clock=[f.START]; cache={}
broker=f.FuzzBroker(random.Random(0),clock,dict(submit_reject_lost=0,submit_accepted_lost=0,poll_fail=0,stale_quote=0,dup_update=0,restart=0))
tmp=tempfile.mkdtemp(); e=f.build(tmp,broker,clock,cache)
b=e.by_id['QQQ-VWAP']
from scalpcity.bot import Position,State
b.position=Position('CALL',10,750.08,749.77,750.70,f.C,2.79,f.START,entry_qty=10); b.state=State.MANAGING
broker.pos[f.C]=10
cache[f.C]=Quote(f.C,clock[0],3.06,3.08); e.reconcile(broker.snapshot())
trace=[]
def step(px,label):
    e.monitor('QQQ',px,clock[0]); f.settle(e)
    trace.append(dict(step=label,und=px,exit_reason=b.exit_reason,holding=bool(b.position),orders=len(broker.orders)))
step(750.71,'11:58 target touched, order sent')
oid=next(iter(broker.orders)); broker.advance(oid,'end'); f.settle(e)   # NO_FILL equivalent
clock[0]+=timedelta(seconds=60); cache[f.C]=Quote(f.C,clock[0],2.94,2.96); e.reconcile(broker.snapshot())
step(750.46,'11:59 price reverted below target')
step(750.20,'12:00 still below target')
print(json.dumps(trace,indent=1))
e.close()
