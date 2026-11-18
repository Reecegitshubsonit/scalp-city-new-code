"""Adversarial controls and causal replay checks, all disconnected."""
import json
import sys
from pathlib import Path
from threading import Barrier,Thread
import pytest
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT.parents[2]/'simulations/exit_safety'))
from coordination import DirectionBook
from model import ExitController
from run import load,simulate,retry_traces


def test_pending_opposite_entries_reserve_atomically():
    book=DirectionBook();barrier=Barrier(2);results=[]
    def submit(side):
        barrier.wait();results.append(book.reserve(side,'QQQ',side,10))
    threads=[Thread(target=submit,args=(side,)) for side in ('CALL','PUT')]
    for t in threads:t.start()
    for t in threads:t.join(timeout=2);assert not t.is_alive()
    assert sorted(results)==[False,True] and book.invariant()


def test_unknown_entry_blocks_opposite_until_reconciled_terminal():
    b=DirectionBook();assert b.reserve('a','QQQ','CALL',10)
    b.update_entry('a',0,'UNKNOWN');assert not b.reserve('b','QQQ','PUT',10)
    b.update_entry('a',0,'CANCELLED');assert b.reserve('b','QQQ','PUT',10)


def test_partial_entry_cancel_keeps_actual_position_and_exits_available():
    b=DirectionBook();b.reserve('a','QQQ','CALL',10);b.update_entry('a',4,'PARTIAL')
    b.update_entry('a',4,'CANCELLED');assert not b.reserve('b','QQQ','PUT',10)
    b.reduce('a',3,'x');assert not b.reserve('b','QQQ','PUT',10)
    b.reduce('a',1,'y');assert b.reserve('b','QQQ','PUT',10)


def test_duplicate_fill_updates_do_not_change_exposure():
    b=DirectionBook();b.reserve('a','QQQ','CALL',10)
    for _ in range(3):b.update_entry('a',10,'FILLED')
    assert b.entries['a']['held']==10
    b.reduce('a',4,'x');b.reduce('a',4,'x');assert b.entries['a']['held']==6
    with pytest.raises(ValueError):b.reduce('a',5,'x')


def test_excess_exit_is_rejected_without_creating_short_position():
    b=DirectionBook();b.reserve('a','QQQ','CALL',10);b.update_entry('a',4,'PARTIAL')
    with pytest.raises(ValueError):b.reduce('a',5)
    assert b.entries['a']['held']==4


def test_stale_terminal_status_cannot_reopen_reservation():
    b=DirectionBook();b.reserve('a','QQQ','CALL',10);b.update_entry('a',4,'CANCELLED')
    b.update_entry('a',4,'PARTIAL');assert b.entries['a']['pending']==0


def test_unexpected_late_fill_is_accounted_and_freezes_new_entries():
    b=DirectionBook();b.reserve('a','QQQ','CALL',10);b.update_entry('a',0,'CANCELLED')
    b.reserve('b','QQQ','PUT',10);b.update_entry('a',2,'PARTIAL')
    assert b.entries['a']['held']==2 and not b.reconciled
    assert not b.reserve('c','SPY','CALL',10)
    assert not b.reconcile({'a':2},{'a':8,'b':10})


def test_restore_blocks_entries_until_positions_and_pending_reconciled():
    b=DirectionBook();b.reserve('a','QQQ','CALL',10);b.update_entry('a',4,'PARTIAL')
    c=DirectionBook.restore(b.snapshot());assert not c.reserve('x','SPY','CALL',10)
    assert not c.reconcile({'a':3},{'a':6})
    assert c.reconcile({'a':4},{'a':6})
    assert not c.reserve('x','QQQ','PUT',10)
    assert c.reserve('x','SPY','PUT',10)


def test_same_side_allowed_different_ticker_independent():
    b=DirectionBook();assert b.reserve('a','QQQ','CALL',10)
    assert b.reserve('b','QQQ','CALL',10) and b.reserve('c','SPY','PUT',10)


def test_exit_retry_preserves_target_and_prevents_duplicate_sells():
    c=ExitController(10,99,102);c.observe(102);assert c.submit('one')==10
    c.cancel_requested();c.observe(100);assert c.submit('two') is None
    c.broker_update('one','CANCELLED',4);assert c.qty==6
    assert c.reason=='TARGET' and c.submit('two')==6
    c.broker_update('two','FILLED',6);c.broker_update('two','FILLED',6)
    assert c.qty==0 and c.submit('three') is None


def test_unknown_exit_no_replacement_before_reconciliation():
    c=ExitController(10,99,102);c.observe(98);c.submit('one');c.uncertain()
    assert c.submit('two') is None
    c.broker_update('one','FILLED',10);assert c.qty==0


def test_friday_29_actual_current_bot_retries_next_observed_bar():
    observations,expanded,_,_=load();r=retry_traces(expanded,observations)
    old=next(x for x in r if x['n']==29 and x['mode']=='legacy_re_evaluate')
    new=next(x for x in r if x['n']==29 and x['mode']=='current_latched')
    assert [a['time'] for a in old['attempts']]==['11:58','12:01']
    assert [a['reason'] for a in old['attempts']]==['TARGET','STOP']
    assert [a['time'] for a in new['attempts']]==['11:58','11:59']
    assert [a['reason'] for a in new['attempts']]==['TARGET','TARGET']


def test_replay_causal_prefix_and_stateful_coordinated_exposure():
    obs,_,retries,ranges=load()
    full=simulate(obs,retries,ranges,name='full',coordinate=True,squeeze=True)
    prefix=[x for x in obs if x[0].strftime('%H:%M')<='11:00']
    short=simulate(prefix,retries,ranges,name='prefix',coordinate=True,squeeze=True)
    assert short['trades']==[t for t in full['trades'] if t['exit_time'][11:16]<='11:00']
    assert full['summary']['opposing_observation_steps']==0
    assert full['summary']['open']==0
    assert all((t['bot'],t['entry_time'][11:16]) not in {('SPY-VWAP','09:43'),('QQQ-EMA50','09:55'),('QQQ-RANGE','09:55')} for t in full['trades'])


def test_no_exit_inside_missing_observation_gap():
    obs,_,retries,ranges=load()
    r=simulate(obs,retries,ranges,name='delayed',coordinate=True,delay=2)
    observed={(tk,t.isoformat()) for t,tk,_ in obs}
    assert all((x['ticker'],x['exit_time']) in observed for x in r['trades'])
