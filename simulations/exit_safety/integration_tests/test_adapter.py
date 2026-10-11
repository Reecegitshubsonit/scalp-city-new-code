import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from scalpcity.paper_adapter import PaperAdapter
from scalpcity.order_records import normalize_order,normalize_positions
from scalpcity.guard import GuardError,SANDBOX_HOST
ROOT=Path(__file__).resolve().parents[3]
ENV={'WEBULL_ENV':'sandbox','WEBULL_SANDBOX_ACCOUNT_ATTESTED':'true','WEBULL_PAPER_ACCOUNT_NUMBER':'fake'}
ACCOUNTS=[{'account_number':'fake','account_id':'fake-id'}]

def record():
    # Sanitized fixture built from the actual captured Webull response schema.
    return {'client_order_id':'stable-id','orders':[{'instrument_type':'OPTION','total_quantity':'10','filled_quantity':'4','filled_price':'2.91','status':'CANCELLED','side':'SELL','filled_time_at':'2026-10-09T16:01:01Z','fees':[{'actual_value':'.2'}],'commission':{},'legs':[{'symbol':'QQQ','option_type':'CALL','option_expire_date':'2026-10-12','strike_price':'750.00','option_contract_multiplier':'100'}]}]}

def test_real_captured_orders_parse_without_dropping_partial_quantities():
    r=normalize_order(record());assert r['filled_qty']==4 and r['fees']==.2 and r['contract']=='QQQ261012C00750000'


def test_submission_reuses_journal_id_and_never_fabricates_fill():
    calls=[]
    c=SimpleNamespace(trade=SimpleNamespace(order_v2=SimpleNamespace(place_option=lambda *a:calls.append(a))),order_detail=lambda *a:record())
    a=PaperAdapter(c,ENV,ACCOUNTS,SANDBOX_HOST)
    r=a.submit({'client_order_id':'stable-id','contract':'QQQ261012C00750000','qty':10,'limit':2.91,'kind':'SELL_CLOSE'})
    assert calls[0][1][0]['client_order_id']=='stable-id' and r['filled_qty']==4


def test_submission_timeout_propagates_as_unknown():
    def fail(*a):raise TimeoutError()
    c=SimpleNamespace(trade=SimpleNamespace(order_v2=SimpleNamespace(place_option=fail)))
    a=PaperAdapter(c,ENV,ACCOUNTS,SANDBOX_HOST)
    with pytest.raises(TimeoutError):a.submit({'client_order_id':'stable-id','contract':'QQQ261012C00750000','qty':10,'limit':2.91,'kind':'SELL_CLOSE'})


def test_adapter_refuses_live_endpoint():
    with pytest.raises(GuardError):PaperAdapter(None,ENV,ACCOUNTS,'api.webull.com')


def test_cancel_reads_final_order_status():
    calls=[]
    c=SimpleNamespace(cancel_option=lambda *a:calls.append(a),order_detail=lambda *a:record())
    r=PaperAdapter(c,ENV,ACCOUNTS,SANDBOX_HOST).cancel('stable-id')
    assert calls and r['status']=='CANCELLED' and r['filled_qty']==4


def test_unknown_commission_schema_does_not_assume_zero():
    r=record();r['orders'][0]['commission']={'unknown':'1'}
    with pytest.raises(ValueError):normalize_order(r)
