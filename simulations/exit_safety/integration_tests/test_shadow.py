from datetime import datetime,timedelta
from types import SimpleNamespace
import pytest
from scalpcity.shadow_adapter import ShadowAdapter
from scalpcity.types import ET,Quote
NOW=datetime(2026,10,9,12,tzinfo=ET)

def test_shadow_accounting_never_needs_remote_order_client():
    q={'q':Quote('q',NOW,2,2.01)}
    broker=ShadowAdapter(SimpleNamespace(get=lambda c,t:q[c]),now_fn=lambda:NOW,fee_per_contract=.65)
    buy={'client_order_id':'buy','kind':'BUY_OPEN','contract':'q','qty':10,'limit':2.01}
    assert broker.submit(buy)['filled_qty']==10
    q['q']=Quote('q',NOW,2.2,2.21)
    sell={'client_order_id':'sell','kind':'SELL_CLOSE','contract':'q','qty':10,'limit':2.2}
    assert broker.submit(sell)['fees']==6.5
    assert broker.snapshot()['positions']=={} and not hasattr(broker,'client')


def test_shadow_stale_quote_is_not_filled():
    broker=ShadowAdapter(SimpleNamespace(get=lambda c,t:Quote('q',NOW-timedelta(seconds=5),2,2.01)),now_fn=lambda:NOW)
    r=broker.submit({'client_order_id':'one','kind':'BUY_OPEN','contract':'q','qty':10,'limit':2.01})
    assert r['status']=='SUBMITTED' and r['filled_qty']==0
    assert broker.cancel('one')['status']=='CANCELLED'


def test_shadow_rejects_sell_without_owned_contracts():
    broker=ShadowAdapter(SimpleNamespace(get=lambda c,t:Quote('q',NOW,2,2.01)),now_fn=lambda:NOW)
    with pytest.raises(ValueError):broker.submit({'client_order_id':'one','kind':'SELL_CLOSE','contract':'q','qty':10,'limit':2})
