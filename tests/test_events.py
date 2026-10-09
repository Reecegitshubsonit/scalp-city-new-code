from datetime import datetime

from scalpcity.events import EventLog, build_snapshot
from scalpcity.types import ET


def t(h, m):
    return datetime(2026, 10, 8, h, m, tzinfo=ET)


def test_append_assigns_increasing_seq_and_persists(tmp_path):
    log = EventLog(str(tmp_path), "replay")
    a = log.append(t(9, 31), "QQQ-VWAP", "QQQ", "tick", state="idle")
    b = log.append(t(9, 32), "QQQ-VWAP", "QQQ", "tick", state="forming", charge_pct=41.0)
    assert (a["seq"], b["seq"]) == (1, 2)
    rows = log.read(t(9, 31).date())
    assert [r["seq"] for r in rows] == [1, 2] and rows[1]["charge_pct"] == 41.0


def test_seq_continues_after_restart(tmp_path):
    EventLog(str(tmp_path), "live").append(t(9, 31), "b", "QQQ", "tick")
    again = EventLog(str(tmp_path), "live").append(t(9, 32), "b", "QQQ", "tick")
    assert again["seq"] == 2


def test_listener_called_and_reset_clears_file(tmp_path):
    log = EventLog(str(tmp_path), "replay")
    seen = []
    log.listeners.append(seen.append)
    log.append(t(9, 31), "b", "QQQ", "tick")
    assert len(seen) == 1
    log.reset(t(9, 31).date())
    assert log.read(t(9, 31).date()) == []
    assert log.append(t(9, 31), "b", "QQQ", "tick")["seq"] == 1


def test_snapshot_uses_last_state_and_trade_totals(tmp_path):
    log = EventLog(str(tmp_path), "replay")
    log.append(t(9, 31), "QQQ-VWAP", "QQQ", "tick", state="idle", reason_code="WATCHING")
    log.append(t(9, 32), "QQQ-VWAP", "QQQ", "tick", state="forming", reason_code="WATCHING", charge_pct=55.0)
    log.append(t(9, 33), "QQQ-VWAP", "QQQ", "trade_closed", pnl=120.0, pnl_day=120.0, trades=1)
    log.append(t(9, 34), "QQQ-VWAP", "QQQ", "control", paused=True)
    snap = build_snapshot(log.read(t(9, 31).date()))
    row = snap["bots"]["QQQ-VWAP"]
    assert row["state"] == "forming" and row["charge_pct"] == 55.0
    assert row["pnl_day"] == 120.0 and row["trades"] == 1 and row["paused"] is True
    assert snap["last_seq"] == 4
