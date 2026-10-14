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


def test_list_days_and_read_day(tmp_path):
    import json
    from scalpcity.history import list_days, read_day
    (tmp_path / "2026-10-07-replay.jsonl").write_text(
        json.dumps({"time": "2026-10-07T09:31:00-04:00", "kind": "tick"}) + "\n" + json.dumps({"time": "2026-10-07T16:01:00-04:00", "kind": "tick"}) + "\n")
    (tmp_path / "2026-10-09-live.jsonl").write_text(json.dumps({"time": "2026-10-09T09:40:00-04:00", "kind": "tick"}) + "\n")
    (tmp_path / "order_history_raw.json").write_text("{}")
    (tmp_path / "junk-live.jsonl").write_text("{}\n")
    days = list_days(str(tmp_path))
    assert days == [
        {"day": "2026-10-09", "mode": "live", "events": 1, "first": "2026-10-09T09:40:00-04:00", "last": "2026-10-09T09:40:00-04:00", "pnl": 0.0, "trades": 0, "wins": 0},
        {"day": "2026-10-07", "mode": "replay", "events": 2, "first": "2026-10-07T09:31:00-04:00", "last": "2026-10-07T16:01:00-04:00", "pnl": 0.0, "trades": 0, "wins": 0},
    ]
    assert len(read_day(str(tmp_path), "2026-10-07", "replay")) == 2
    assert read_day(str(tmp_path), "2026-10-08", "replay") == []
    assert read_day(str(tmp_path), "../../etc/passwd", "replay") is None
    assert read_day(str(tmp_path), "2026-10-07", "bogus") is None


def test_list_days_totals_closed_trades(tmp_path):
    import json
    from scalpcity.history import list_days
    rows = [{"time": "2026-10-09T09:45:00-04:00", "kind": "trade_closed", "pnl": 100.0}, {"time": "2026-10-09T09:50:00-04:00", "kind": "trade_closed", "pnl": -30.5},
            {"time": "2026-10-09T09:55:00-04:00", "kind": "tick"}]
    (tmp_path / "2026-10-09-live.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    d = list_days(str(tmp_path))[0]
    assert (d["pnl"], d["trades"], d["wins"]) == (69.5, 2, 1)


def ev(seq, t, bot, kind, **kw):
    base = {"seq": seq, "time": t, "bot": bot, "ticker": bot.split("-")[0], "kind": kind, "state": "", "reason_code": "", "reason_text": "", "inputs": {}}
    base.update(kw)
    return base


def test_build_trades_pairs_entry_exit_and_pnl():
    from scalpcity.history import build_trades
    events = [
        ev(1, "2026-10-09T09:43:00-04:00", "IWM-VWAP", "state_change", state="fired", reason_code="SIGNAL", reason_text="PUT signal at 278.1"),
        ev(2, "2026-10-09T09:43:00-04:00", "IWM-VWAP", "fill", state="managing", reason_code="ENTRY_FILL", contract="IWM261012P00278000", qty=10, fill_price=1.22, fill_source="broker"),
        ev(3, "2026-10-09T09:50:00-04:00", "IWM-VWAP", "state_change", state="exiting", reason_code="EXIT_TARGET", reason_text="target hit"),
        ev(4, "2026-10-09T09:50:00-04:00", "IWM-VWAP", "fill", state="exiting", reason_code="EXIT_FILL", fill_price=1.52, fill_source="broker"),
        ev(5, "2026-10-09T09:50:00-04:00", "IWM-VWAP", "trade_closed", state="cooldown", pnl=300.0, pnl_day=300.0, trades=1),
        ev(6, "2026-10-09T10:05:00-04:00", "QQQ-EMA50", "trade_closed", state="locked", pnl=-80.0, pnl_day=-80.0, trades=1),   # no entry seen (restart)
    ]
    t = build_trades(events)
    assert t[0] == {"bot": "IWM-VWAP", "ticker": "IWM", "side": "PUT", "contract": "IWM261012P00278000", "qty": 10,
                    "entry_time": "2026-10-09T09:43:00-04:00", "entry_price": 1.22, "exit_time": "2026-10-09T09:50:00-04:00",
                    "exit_price": 1.52, "exit_code": "EXIT_TARGET", "pnl": 300.0, "pnl_day": 300.0, "source": "broker"}
    assert t[1]["bot"] == "QQQ-EMA50" and t[1]["entry_time"] is None and t[1]["pnl"] == -80.0 and t[1]["side"] is None
    assert build_trades([]) == []


import json

from scalpcity.history import read_webull_bars


def _webull(tmp_path, ticker="QQQ", day="2026-10-07", name=None, rows=None):
    rows = rows if rows is not None else [
        {"time": "2026-10-07T13:31:00.000+0000", "open": "754.08", "close": "754.515", "high": "754.71", "low": "754.02", "volume": "219489", "trading_session": "RTH"},
        {"time": "2026-10-07T13:30:00.000+0000", "open": "753.8", "close": "754.03", "high": "754.37", "low": "753.35", "volume": "505774", "trading_session": "RTH"},
    ]
    (tmp_path / day).mkdir(exist_ok=True)
    (tmp_path / day / (name or f"stock-{ticker}.json")).write_text(json.dumps(rows))


def test_webull_bars_are_converted_to_et_bars(tmp_path):
    _webull(tmp_path)
    got = read_webull_bars(str(tmp_path), "QQQ", "2026-10-07")
    assert [b.ts.isoformat() for b in got] == ["2026-10-07T09:30:00-04:00", "2026-10-07T09:31:00-04:00"]
    assert (got[0].open, got[0].high, got[0].low, got[0].close, got[0].volume) == (753.8, 754.37, 753.35, 754.03, 505774)


def test_webull_bars_fall_back_to_what_the_live_engine_received(tmp_path):
    rows = [{"time": "2026-10-07T09:30:00-04:00", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 9, "received_at": "x"}]
    (tmp_path / "2026-10-07").mkdir()
    (tmp_path / "2026-10-07" / "stock-QQQ.live.jsonl").write_text("\n".join(json.dumps(r) for r in rows * 2) + "\n")
    got = read_webull_bars(str(tmp_path), "QQQ", "2026-10-07")
    assert len(got) == 1 and got[0].close == 1.5   # a repeated bar (engine restart) counts once


def test_webull_bars_missing_or_bad_input_gives_none(tmp_path):
    assert read_webull_bars(str(tmp_path), "QQQ", "2026-10-07") is None          # no file
    _webull(tmp_path)
    assert read_webull_bars(str(tmp_path), "../QQQ", "2026-10-07") is None       # never leaves the Webull directory
    assert read_webull_bars(str(tmp_path), "QQQ", "2026-10-7") is None
