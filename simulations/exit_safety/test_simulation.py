from datetime import datetime, timedelta
from pathlib import Path
import json
import pytest
from model import ExitController
from scalpcity.bot import Bot, Position
from scalpcity.config import Settings, BOT_SPECS
from scalpcity.triggers import VwapCross
from scalpcity.indicators import IndicatorSet
from scalpcity.types import Bar, ET


def controller():
    return ExitController(10,99,102)


def test_current_bot_drops_target_exit_after_no_fill():
    b=Bot('QQQ',BOT_SPECS['vwap'],VwapCross(1),Settings())
    b.position=Position('CALL',10,100,99,102,contract='SIM',entry_price=2)
    now=datetime(2026,10,9,11,58,tzinfo=ET)
    bar=lambda p:Bar('QQQ',now-timedelta(minutes=1),p,p,p,p,1)
    assert b._manage(bar(102),now,IndicatorSet())[0].reason=='TARGET'
    b.on_order_failed('SELL_CLOSE','NO_FILL')
    assert b._manage(bar(101),now,IndicatorSet())==[]


def test_target_reversal_retries_only_after_confirmed_cancel():
    c=controller();c.observe(102);assert c.submit('one')==10
    c.cancel_requested();c.observe(101)
    assert c.submit('two') is None
    c.broker_update('one','CANCELLED',0)
    assert c.reason=='TARGET' and c.submit('two')==10


def test_late_fill_after_cancel_request_prevents_duplicate_sell():
    c=controller();c.observe(98);c.submit('one');c.cancel_requested()
    c.broker_update('one','FILLED',10)
    assert c.qty==0 and c.submit('two') is None


def test_partial_fill_and_cancel_sells_remaining_only():
    c=controller();c.observe(98);c.submit('one')
    c.broker_update('one','PARTIALLY_FILLED',4)
    assert c.qty==6 and c.submit('two') is None
    c.cancel_requested();c.broker_update('one','CANCELLED',6)
    assert c.qty==4 and c.submit('two')==4
    c.broker_update('two','FILLED',4);assert c.qty==0


def test_duplicate_fill_update_is_idempotent():
    c=controller();c.observe(98);c.submit('one')
    for _ in range(3):c.broker_update('one','PARTIALLY_FILLED',4)
    assert c.qty==6


def test_unknown_submission_blocks_replacement_and_modeled_fill():
    c=controller();c.observe(98);c.submit('one');c.uncertain()
    assert c.qty==10 and c.submit('two') is None
    c.broker_update('one','FILLED',10);assert c.qty==0


def test_restart_preserves_exit_order_and_requires_reconciliation():
    c=controller();c.observe(102);c.submit('one')
    c.broker_update('one','CANCELLED',3)
    r=ExitController.restore(c.snapshot());r.observe(100)
    assert r.submit('two') is None
    assert r.reconcile(7,0)
    assert r.reason=='TARGET' and r.submit('two')==7


def test_position_mismatch_blocks_trading():
    c=controller();c.observe(98)
    assert not c.reconcile(6,0) and c.submit('one') is None


def test_unexpected_open_order_blocks_trading():
    c=controller();c.observe(98)
    assert not c.reconcile(10,1) and c.submit('one') is None


@pytest.mark.parametrize('age,bid',[(3,1),(-1,1),(0,0)])
def test_bad_exit_quote_preserves_intent_without_submission(age,bid):
    c=controller();c.observe(98)
    assert c.submit('one',age,bid) is None and c.reason=='STOP'


def test_stale_underlying_does_not_create_false_trigger():
    c=controller();c.observe(98,age_s=30)
    assert c.reason is None
    c.observe(None,flat_due=True);assert c.reason=='TIME'


def test_put_thresholds():
    c=ExitController(10,101,98,-1);c.observe(98)
    assert c.reason=='TARGET'


def test_independent_monitor_sees_second_bot_during_first_order_wait():
    first,second=controller(),controller()
    first.observe(98);first.submit('one')
    # Deterministic scheduler: order one remains unresolved for 15 virtual seconds.
    for second_at in range(1,16):
        second.observe(98 if second_at>=2 else 100)
        if second.ready():
            assert second_at==2 and second.submit('second')==10
    assert first.status=='SUBMITTING' and second.status=='SUBMITTING'


def test_intrabar_touch_is_seen_without_assuming_exact_fill():
    c=controller()
    for price in [100,99.8,98.7,100]:c.observe(price)
    assert c.reason=='STOP' and c.qty==10  # no fabricated fill at 99


def test_real_trade_29_trace_preserves_target_after_reversal():
    events=[json.loads(x) for x in Path('logs/2026-10-09-live.jsonl').read_text().splitlines()]
    entry=next(e for e in events if e['bot']=='QQQ-VWAP' and e['kind']=='order_sent' and e['reason_code']=='BUY_OPEN' and 'T11:48:' in e['time'])
    price,atr=entry['inputs']['price'],entry['inputs']['atr']
    c=ExitController(10,price-atr,price+2*atr)
    ticks=[e for e in events if e['bot']=='QQQ-VWAP' and e['kind']=='tick' and 'T11:58:' in e['time'] or e['bot']=='QQQ-VWAP' and e['kind']=='tick' and 'T11:59:' in e['time']]
    for e in ticks:c.observe(e['inputs']['price'])
    assert len(ticks)==2 and c.reason=='TARGET'


def test_missing_tracked_order_requires_status_reconciliation():
    c=controller();c.observe(98);c.submit('one')
    assert not c.reconcile(10,0) and c.submit('two') is None


@pytest.mark.parametrize('filled',[-1,11])
def test_invalid_fill_quantity_rejected(filled):
    c=controller();c.observe(98);c.submit('one')
    with pytest.raises(ValueError):c.broker_update('one','PARTIALLY_FILLED',filled)
    assert c.qty==10


def test_outage_cannot_be_repaired_by_local_monitor():
    c=controller();c.observe(100)
    # No observations delivered during outage; first recovered price gaps below stop.
    c.observe(96)
    assert c.reason=='STOP' and c.qty==10  # no claim of having sold at stop=99


def test_monitor_sampling_misses_touch_between_observations():
    c=controller()
    for observed in [100,100]:c.observe(observed)
    assert c.reason is None  # an unobserved price of 98 in between is unknowable


def test_restart_from_disk_preserves_intent_and_cumulative_fill(tmp_path):
    c=controller();c.observe(98);c.submit('stable-client-id')
    c.broker_update('stable-client-id','PARTIALLY_FILLED',4)
    journal=tmp_path/'state.json';journal.write_text(c.snapshot())
    r=ExitController.restore(journal.read_text())
    assert r.qty==6 and r.order_id=='stable-client-id' and not r.ready()
    r.broker_update('stable-client-id','CANCELLED',4)
    assert r.submit('replacement')==6


def test_reference_broker_ignores_partial_fill_on_cancel():
    from scalpcity.webull_broker import WebullPaperBroker
    from scalpcity.types import Quote, OrderIntent
    class Fake:
        def place_option(self,*args):return 'one'
        def order_detail(self,*args):return {'orders':[{'status':'CANCELLED','filled_quantity':'4','filled_price':'2'}]}
    now=datetime(2026,10,9,12,tzinfo=ET)
    intent=OrderIntent('QQQ-VWAP','QQQ','SELL_CLOSE','CALL',10,'STOP',99,'SIM')
    result=WebullPaperBroker(Fake(),'fake',sleep=lambda _:None).execute(intent,'SIM',Quote('SIM',now,2,2.01),now)
    assert result is None  # baseline exposes no accounting for the four executed contracts
