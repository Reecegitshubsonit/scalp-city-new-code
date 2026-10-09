from datetime import datetime

from scalpcity.broker import ModeledBroker
from scalpcity.config import Settings
from scalpcity.risk import RiskGate
from scalpcity.types import ET, OrderIntent, Quote

NOW = datetime(2026, 10, 8, 10, 0, tzinfo=ET)


def intent(kind="BUY_OPEN", qty=10, ticker="QQQ"):
    return OrderIntent("QQQ-VWAP", ticker, kind, "CALL", qty, "signal", 748.0, contract="QQQ261009C00748000")


def q(bid=2.9, ask=2.95):
    return Quote("QQQ261009C00748000", NOW, bid, ask)


def test_gate_allows_normal_entry_and_all_exits():
    g = RiskGate(Settings())
    assert g.check(intent(), q(), set()) == (True, "")
    assert g.check(intent("SELL_CLOSE"), None, {"QQQ"}, halted=True) == (True, "")


def test_gate_refusals():
    g = RiskGate(Settings())
    assert g.check(intent(), q(), {"QQQ"})[1] == "STALE_DATA"
    assert g.check(intent(), q(), set(), halted=True)[1] == "HALTED"
    assert g.check(intent(qty=11), q(), set())[1] == "SIZE_LIMIT"
    assert g.check(intent(), None, set())[1] == "NO_QUOTE"
    assert g.check(intent(), q(0.0, 1.0), set())[1] == "BAD_QUOTE"
    assert g.check(intent(), q(1.0, 2.0), set())[1] == "WIDE_SPREAD"
    assert g.check(intent(), q(30.0, 30.5), set())[1] == "CASH_LIMIT"   # 30.5*10*100 = 30,500 > 25,000


def test_modeled_broker_buys_ask_sells_bid():
    b = ModeledBroker()
    assert b.execute(intent(), "C", q(), NOW).price == 2.95
    assert b.execute(intent("SELL_CLOSE"), "C", q(), NOW).price == 2.9
    assert b.execute(intent(), "C", q(1.0, 0.0), NOW) is None
