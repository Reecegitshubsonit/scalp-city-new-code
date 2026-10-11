import json
import threading
import time
from datetime import datetime,timedelta
from types import SimpleNamespace
import pytest
from scalpcity.safe_engine import SafeEngine
from scalpcity.bot import Position,State
from scalpcity.config import Settings
from scalpcity.events import EventLog
from scalpcity.types import ET,Bar,Quote

NOW=datetime(2026,10,9,11,58,tzinfo=ET)
CONTRACT='QQQ261012C00750000'

class Broker:
    capability='PAPER'
    def __init__(self):self.orders={};self.submits=[];self.cancelled=[];self.block=None;self.fail_submit=False
    def submit(self,o):
        self.submits.append(o)
        self.orders[o['client_order_id']]=dict(client_order_id=o['client_order_id'],status='SUBMITTED',filled_qty=0,avg_price=None,fees=0,fill_time=NOW.isoformat())
        if self.block:self.block.wait(3)
        if self.fail_submit:raise TimeoutError('accepted but response lost')
        return dict(self.orders[o['client_order_id']])
    def poll(self,oid):return dict(self.orders[oid])
    def cancel(self,oid):
        self.cancelled.append(oid)
        return dict(self.orders[oid]) # acknowledgement is not terminal cancellation
    def fill(self,oid,n,price,status='FILLED',fees=0):
        self.orders[oid].update(status=status,filled_qty=n,avg_price=price,fees=fees,fill_time=NOW.isoformat())

@pytest.fixture
def setup(tmp_path):
    clock=[NOW];broker=Broker();cache={CONTRACT:Quote(CONTRACT,NOW,3.06,3.08)}
    e=SafeEngine(Settings(),EventLog(str(tmp_path/'log'),'candidate'),broker,SimpleNamespace(get=lambda c,t:cache.get(c)),tmp_path/'state.json',now_fn=lambda:clock[0])
    e.start_session(NOW.date(),{})
    yield e,broker,clock,cache
    if broker.block:broker.block.set()
    e.close()


def seed(e,bid='QQQ-VWAP',qty=10,entry=2.79):
    b=e.by_id[bid];b.position=Position('CALL',qty,750.08,749.77,750.70,CONTRACT,entry,NOW,entry_qty=qty);b.state=State.MANAGING
    return b

def reconcile(e,broker,qty):
    return e.reconcile({'observed_at':e.now_fn().isoformat(),'orders':list(broker.orders.values()),'positions':{CONTRACT:qty} if qty else {}})

def settle(e):
    for f,op in list(e.futures.values()):f.result(timeout=3)
    e.service()

def only(e):return next(iter(e.orders))


def test_candidate_is_using_isolated_production_engine():
    import scalpcity.engine
    assert '/candidate/' in scalpcity.engine.__file__
    assert issubclass(SafeEngine,scalpcity.engine.Engine)


def test_real_target_trace_integration_reversal_partial_cancel_replacement(setup):
    e,broker,clock,cache=setup;b=seed(e);assert reconcile(e,broker,10)
    e.monitor('QQQ',750.705,NOW);settle(e);oid=only(e)
    broker.fill(oid,4,3.06,'PARTIALLY_FILLED',2.6);settle(e);settle(e)
    assert b.position.qty==6 and b.pnl_day==pytest.approx(105.4)
    clock[0]+=timedelta(seconds=16);cache[CONTRACT]=Quote(CONTRACT,clock[0],2.94,2.96)
    e.monitor('QQQ',750.46,clock[0]);settle(e);settle(e)
    assert len(broker.submits)==1 and b.exit_reason=='TARGET'
    broker.fill(oid,4,3.06,'CANCELLED',2.6);settle(e);settle(e)
    e.monitor('QQQ',750.46,clock[0]);settle(e)
    new=next(x for x in e.orders if x!=oid)
    assert e.orders[new]['qty']==6
    broker.fill(new,6,2.94,fees=3.9);settle(e);settle(e)
    assert b.position is None and b.trades==1 and b.pnl_day==pytest.approx(191.5)
    closed=[x for x in e.log.read(NOW.date()) if x['kind']=='trade_closed']
    assert len(closed)==1 and closed[0]['pnl']==pytest.approx(191.5)


def test_late_fill_after_cancel_no_duplicate_sell(setup):
    e,broker,clock,cache=setup;b=seed(e);reconcile(e,broker,10)
    e.monitor('QQQ',749,NOW);settle(e);oid=only(e)
    clock[0]+=timedelta(seconds=16);settle(e);settle(e)
    broker.fill(oid,10,2.50);settle(e);settle(e)
    e.monitor('QQQ',751,clock[0]);assert len(broker.submits)==1 and b.position is None


def test_real_thread_blocked_submit_does_not_block_other_bot_or_control(setup):
    e,broker,clock,cache=setup;seed(e);seed(e,'QQQ-EMA50');reconcile(e,broker,20)
    broker.block=threading.Event()
    started=time.perf_counter();e.monitor('QQQ',749,NOW)
    assert time.perf_counter()-started<.5
    until=time.monotonic()+1
    while len(broker.submits)<2 and time.monotonic()<until:time.sleep(.001)
    assert len(broker.submits)==2
    e.set_paused('QQQ-VWAP',True,NOW)
    assert e.by_id['QQQ-VWAP'].paused
    broker.block.set();settle(e)


def test_same_contract_ownership_is_aggregated_not_assigned_to_one_bot(setup):
    e,broker,clock,cache=setup;a=seed(e);b=seed(e,'QQQ-EMA50',qty=7)
    assert reconcile(e,broker,17)
    e.monitor('QQQ',749,NOW);settle(e)
    assert sorted(o['qty'] for o in broker.submits)==[7,10]
    oid=next(k for k,v in e.orders.items() if v['bot']=='QQQ-VWAP')
    broker.fill(oid,10,2.5);settle(e);settle(e)
    assert a.position is None and b.position.qty==7
    assert reconcile(e,broker,7)


def test_partial_entry_uses_actual_quantity_then_stop_cancels_remainder(setup):
    e,broker,clock,cache=setup;assert reconcile(e,broker,0)
    b=e.by_id['QQQ-VWAP'];bar=Bar('QQQ',NOW-timedelta(minutes=1),750,750,750,750,1)
    e.ind['QQQ'].atr.value=.3
    intent=b._fire(bar,e.ind['QQQ'],'CALL')[0]
    e._execute(b,intent,bar,e.ind['QQQ']);settle(e);oid=only(e)
    broker.fill(oid,3,3,'PARTIALLY_FILLED',1.95);settle(e);settle(e)
    assert b.position.qty==3 and b.pending=='entry'
    e.monitor('QQQ',749,NOW);settle(e);settle(e)
    assert oid in broker.cancelled and len(broker.submits)==1
    broker.fill(oid,3,3,'CANCELLED',1.95);settle(e);settle(e)
    e.monitor('QQQ',750,NOW);settle(e)
    assert broker.submits[-1]['kind']=='SELL_CLOSE' and broker.submits[-1]['qty']==3


def test_unknown_submit_has_no_modeled_fallback(setup):
    e,broker,clock,cache=setup;b=seed(e);reconcile(e,broker,10);broker.fail_submit=True
    e.monitor('QQQ',749,NOW)
    for f,_ in e.futures.values():
        with pytest.raises(TimeoutError):f.result(timeout=2)
    e.service()
    assert not e.reconciled and b.position.qty==10
    e.monitor('QQQ',749,NOW);assert len(broker.submits)==1
    broker.fill(only(e),10,2.5);assert reconcile(e,broker,0)
    assert b.position is None


def test_restart_reconciles_late_fill_without_resubmission(setup,tmp_path):
    e,broker,clock,cache=setup;seed(e);reconcile(e,broker,10)
    e.monitor('QQQ',749,NOW);settle(e);oid=only(e)
    state=e.state_path.read_text()
    broker.fill(oid,10,2.5)
    other=SafeEngine(Settings(),EventLog(str(tmp_path/'other'),'candidate'),broker,e.quotes,tmp_path/'restarted.json',now_fn=lambda:clock[0])
    other.start_session(NOW.date(),{});other.state_path.write_text(state);other.load_state()
    try:
        assert not other.reconciled
        assert reconcile(other,broker,0)
        other.monitor('QQQ',749,NOW)
        assert other.by_id['QQQ-VWAP'].position is None and len(broker.submits)==1
        saved=json.loads(other.state_path.read_text());assert saved['orders'][oid]['filled']==10
    finally:other.close()


def test_account_mismatch_and_unowned_orders_block_submissions(setup):
    e,broker,clock,cache=setup;seed(e)
    assert not reconcile(e,broker,9)
    e.monitor('QQQ',749,NOW);assert not broker.submits
    broker.orders['foreign']={'client_order_id':'foreign','status':'SUBMITTED','filled_qty':0}
    assert not reconcile(e,broker,10)


@pytest.mark.parametrize('age,bid,ask',[(3,2,3),(-1,2,3),(0,3,2),(0,float('nan'),3)])
def test_bad_quotes_never_submit(setup,age,bid,ask):
    e,broker,clock,cache=setup;seed(e);reconcile(e,broker,10)
    cache[CONTRACT]=Quote(CONTRACT,NOW-timedelta(seconds=age),bid,ask)
    e.monitor('QQQ',749,NOW);assert not broker.submits
    assert e.by_id['QQQ-VWAP'].exit_reason=='STOP'


def test_duplicate_fill_updates_do_not_double_pnl(setup):
    e,broker,clock,cache=setup;b=seed(e);reconcile(e,broker,10)
    e.monitor('QQQ',749,NOW);settle(e);oid=only(e);broker.fill(oid,10,2.5,fees=6.5)
    settle(e);settle(e);original=b.pnl_day
    for _ in range(5):e._apply(broker.orders[oid])
    assert b.pnl_day==original and b.trades==1


def test_durable_prepare_exists_before_broker_submit(setup):
    e,broker,clock,cache=setup;seed(e);reconcile(e,broker,10)
    original=broker.submit
    def checked(o):
        disk=json.loads(e.state_path.read_text())
        assert disk['orders'][o['client_order_id']]['status']=='PREPARED'
        return original(o)
    broker.submit=checked;e.monitor('QQQ',749,NOW);settle(e)
    assert broker.submits


def test_persistence_error_prevents_external_submission(setup,monkeypatch):
    e,broker,clock,cache=setup;seed(e);reconcile(e,broker,10)
    import scalpcity.safe_engine as mod
    monkeypatch.setattr(mod.os,'replace',lambda *a: (_ for _ in ()).throw(OSError('disk full')))
    with pytest.raises(OSError):e.monitor('QQQ',749,NOW)
    assert not broker.submits and e.halted


def test_configuration_mismatch_blocks_restore(setup):
    e,broker,clock,cache=setup;seed(e);reconcile(e,broker,10)
    d=json.loads(e.state_path.read_text());d['config_hash']='changed';e.state_path.write_text(json.dumps(d))
    with pytest.raises(ValueError):e.load_state()


def test_second_engine_cannot_write_same_journal(setup):
    e,broker,clock,cache=setup
    with pytest.raises(RuntimeError,match='already in use'):
        SafeEngine(Settings(),e.log,broker,e.quotes,e.state_path)


def test_fill_identity_mismatch_rejected_without_pnl_change(setup):
    e,broker,clock,cache=setup;b=seed(e);reconcile(e,broker,10)
    e.monitor('QQQ',749,NOW);settle(e);oid=only(e)
    update={**broker.orders[oid],'contract':'WRONG','filled_qty':10,'avg_price':2.5,'status':'FILLED'}
    with pytest.raises(ValueError):e._apply(update)
    assert b.position.qty==10 and b.pnl_day==0


def test_terminal_duplicate_cannot_clear_new_order_pending(setup):
    e,broker,clock,cache=setup;b=seed(e);reconcile(e,broker,10)
    e.monitor('QQQ',749,NOW);settle(e);oid=only(e)
    broker.fill(oid,10,2.5);settle(e);settle(e)
    seed(e);b.pending='entry'
    e._apply(broker.orders[oid])
    assert b.pending=='entry' and b.position.qty==10


def test_pause_is_saved_for_restart(setup):
    e,broker,clock,cache=setup;e.set_paused('QQQ-VWAP',True,NOW)
    assert json.loads(e.state_path.read_text())['bots']['QQQ-VWAP']['paused']


def test_legacy_log_cannot_silently_discard_uncertain_orders(setup):
    e,*_=setup
    with pytest.raises(RuntimeError):e.recover([])


def test_actual_bar_signal_to_broker_fill_to_monitor_exit(setup):
    e,broker,clock,cache=setup
    e.quotes=SimpleNamespace(get=lambda c,t:Quote(c,clock[0],3,3.01))
    original=broker.submit
    def auto(o):
        original(o)
        broker.fill(o['client_order_id'],o['qty'],o['limit'],fees=.5)
        broker.orders[o['client_order_id']]['fill_time']=clock[0].isoformat()
        return dict(broker.orders[o['client_order_id']])
    broker.submit=auto
    # Same warmed crossing pattern used by the original production bot regression.
    warm=[]
    for i in range(60):
        c=100+.5*i
        warm.append(Bar('QQQ',NOW-timedelta(days=1,minutes=60-i),c,c+.5,c-.5,c,1000))
    e.start_session(NOW.date(),{'QQQ':warm});assert reconcile(e,broker,0)
    for minute,c in enumerate([128.5,128,134.5],30):
        bar=Bar('QQQ',NOW.replace(hour=9,minute=minute),c,c+.5,c-.5,c,1000)
        clock[0]=bar.end;e.on_bar(bar);settle(e);settle(e)
    b=e.by_id['QQQ-VWAP']
    assert b.position and b.position.entry_price==3.01
    e.monitor('QQQ',b.position.stop_und-1,clock[0]);settle(e);settle(e)
    assert b.position is None and b.trades==1 and b.pnl_day==pytest.approx(-11)
    assert any(o['kind']=='BUY_OPEN' for o in broker.submits)
    assert any(o['kind']=='SELL_CLOSE' for o in broker.submits)


def test_cumulative_average_fill_price_produces_correct_incremental_cash(setup):
    e,broker,clock,cache=setup;b=seed(e);reconcile(e,broker,10)
    e.monitor('QQQ',751,NOW);settle(e);oid=only(e)
    broker.fill(oid,4,3.06,'PARTIALLY_FILLED',2.6);settle(e);settle(e)
    broker.fill(oid,10,3.00,'FILLED',6.5);settle(e);settle(e)
    assert b.pnl_day==pytest.approx(203.5) and b.trades==1
    fills=[x for x in e.log.read(NOW.date()) if x['kind']=='fill']
    assert sum(x['qty']*x['fill_price']*100-x['fee'] for x in fills)==pytest.approx(2993.5)


def settle_lossy(e):
    for f,_ in list(e.futures.values()):
        try:f.result(timeout=3)
        except Exception:pass
    e.service()


def lose_submit(e,broker):
    """Submit raises before the broker records the order: the engine sees UNKNOWN, the broker has nothing."""
    def lost(o):raise TimeoutError('request lost before broker accepted')
    original,broker.submit=broker.submit,lost
    e.monitor('QQQ',749,NOW);settle_lossy(e)
    broker.submit=original


def test_unknown_order_never_accepted_is_failed_after_grace_and_exit_resent(setup):
    e,broker,clock,cache=setup;b=seed(e);reconcile(e,broker,10);lose_submit(e,broker)
    oid=only(e);assert e.orders[oid]['status']=='UNKNOWN' and not e.reconciled and not broker.orders
    clock[0]+=timedelta(seconds=10);cache[CONTRACT]=Quote(CONTRACT,clock[0],2.94,2.96)
    assert not reconcile(e,broker,10) and e.orders[oid]['status']=='UNKNOWN'   # inside the grace window: still unresolved
    clock[0]+=timedelta(seconds=25);cache[CONTRACT]=Quote(CONTRACT,clock[0],2.94,2.96)
    assert reconcile(e,broker,10) and e.orders[oid]['status']=='FAILED'
    assert b.exit_reason=='STOP' and b.position.qty==10 and b.pending is None
    e.monitor('QQQ',750.2,clock[0]);settle_lossy(e)   # latch survives; price has recovered
    assert len(broker.submits)==1 and broker.submits[0]['kind']=='SELL_CLOSE' and broker.submits[0]['qty']==10


def test_unknown_order_accepted_by_broker_is_not_failed(setup):
    e,broker,clock,cache=setup;seed(e);reconcile(e,broker,10);broker.fail_submit=True
    e.monitor('QQQ',749,NOW);settle_lossy(e);oid=only(e)
    assert e.orders[oid]['status']=='UNKNOWN' and oid in broker.orders
    clock[0]+=timedelta(seconds=40);cache[CONTRACT]=Quote(CONTRACT,clock[0],2.94,2.96)
    broker.fill(oid,10,2.5)
    assert reconcile(e,broker,0) and e.orders[oid]['status']=='FILLED'


def test_unknown_order_with_fills_missing_from_broker_stays_unresolved(setup):
    e,broker,clock,cache=setup;seed(e);reconcile(e,broker,10);lose_submit(e,broker)
    oid=only(e);e.orders[oid]['filled']=3
    clock[0]+=timedelta(seconds=40);cache[CONTRACT]=Quote(CONTRACT,clock[0],2.94,2.96)
    assert not reconcile(e,broker,10) and e.orders[oid]['status']=='UNKNOWN'
