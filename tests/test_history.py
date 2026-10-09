from datetime import datetime

from scalpcity.history import BarStore, build_history
from scalpcity.types import ET, Bar


def bar(h, m, o=100.0, hi=101.0, lo=99.0, c=100.5, v=1000.0, ticker="QQQ"):
    return Bar(ticker, datetime(2026, 10, 9, h, m, tzinfo=ET), o, hi, lo, c, v)


def tick(t, price=100.5, bot="QQQ-VWAP", ticker="QQQ", vwap=100.0, ema50=99.0):
    return {"time": t, "bot": bot, "ticker": ticker, "kind": "tick", "state": "idle", "reason_code": "WATCHING",
            "reason_text": "", "inputs": {"price": price, "vwap": vwap, "ema9": 100.4, "ema21": 100.2, "ema50": ema50}}


def test_store_keeps_bars_in_order_and_replaces_a_repeated_bar():
    s = BarStore()
    s.add(bar(9, 31)); s.add(bar(9, 30)); s.add(bar(9, 31, c=100.9))
    got = s.get("QQQ")
    assert [b.ts.minute for b in got] == [30, 31] and got[1].close == 100.9
    assert s.get("SPY") == []


def test_store_extend_and_copy():
    s = BarStore()
    s.extend([bar(9, 30), bar(9, 31)])
    got = s.get("QQQ"); got.clear()
    assert len(s.get("QQQ")) == 2


def test_history_bars_levels_marks():
    bars = [bar(9, 30), bar(9, 31, o=100.5, hi=102, lo=100, c=101.5)]
    ev = [
        tick("2026-10-09T09:30:00-04:00"),
        tick("2026-10-09T09:30:00-04:00", bot="QQQ-EMA50", vwap=555.0),   # same bar: first tick wins
        tick("2026-10-09T09:31:00-04:00", price=101.5),
        tick("2026-10-09T09:31:00-04:00", ticker="SPY", bot="SPY-VWAP", price=700.0),
        {"time": "2026-10-09T09:31:00-04:00", "bot": "QQQ-VWAP", "ticker": "QQQ", "kind": "state_change", "state": "fired",
         "reason_code": "SIGNAL", "reason_text": "PUT signal at 101.5", "inputs": {}},
        {"time": "2026-10-09T09:31:00-04:00", "bot": "QQQ-VWAP", "ticker": "QQQ", "kind": "fill", "state": "fired",
         "reason_code": "ENTRY_FILL", "reason_text": "", "inputs": {}, "fill_price": 3.2},
        {"time": "2026-10-09T09:35:00-04:00", "bot": "QQQ-VWAP", "ticker": "QQQ", "kind": "trade_closed", "state": "cooldown",
         "reason_code": "EXIT_FILL", "reason_text": "", "inputs": {}, "pnl": 55.0},
    ]
    h = build_history("QQQ", bars, ev)
    assert h["ticker"] == "QQQ"
    assert h["bars"][1] == {"time": "2026-10-09T09:31:00-04:00", "open": 100.5, "high": 102, "low": 100, "close": 101.5, "volume": 1000.0}
    assert [lv["time"][11:16] for lv in h["levels"]] == ["09:30", "09:31"]
    assert h["levels"][0]["vwap"] == 100.0 and h["levels"][0]["ema50"] == 99.0
    assert h["marks"] == [
        {"time": "2026-10-09T09:31:00-04:00", "bot": "QQQ-VWAP", "type": "entry", "side": "PUT", "pnl": None},
        {"time": "2026-10-09T09:35:00-04:00", "bot": "QQQ-VWAP", "type": "exit", "side": "PUT", "pnl": 55.0},
    ]


def test_history_without_events_or_bars():
    assert build_history("QQQ", [], []) == {"ticker": "QQQ", "bars": [], "levels": [], "marks": []}
