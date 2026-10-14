import json
from datetime import datetime

from scalpcity.quotes import SnapshotQuoteSource
from scalpcity.types import ET

C = "SPY261014C00777000"


def write(tmp_path, lines):
    d = tmp_path / "2026-10-13"
    d.mkdir()
    (d / "snapshots.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))


def snap(t, bid, ask, symbol=C):
    return {"recorded_at": f"2026-10-13T{t}-04:00", "held": [], "snapshots": [{"symbol": symbol, "bid": bid, "ask": ask}]}


def at(h, m, s=0):
    return datetime(2026, 10, 13, h, m, s, tzinfo=ET)


def test_uses_the_first_snapshot_after_the_decision(tmp_path):
    write(tmp_path, [snap("09:59:02", "1.00", "1.02"), snap("10:00:07", "1.10", "1.12"), snap("10:01:07", "1.20", "1.22")])
    q = SnapshotQuoteSource(str(tmp_path)).get(C, at(10, 0))
    assert (q.bid, q.ask) == (1.10, 1.12)


def test_falls_back_to_a_recent_earlier_snapshot(tmp_path):
    write(tmp_path, [snap("09:59:40", "1.00", "1.02")])
    q = SnapshotQuoteSource(str(tmp_path)).get(C, at(10, 0))
    assert (q.bid, q.ask) == (1.00, 1.02)


def test_no_quote_when_missing_too_old_or_empty(tmp_path):
    write(tmp_path, [snap("09:50:00", "1.00", "1.02"), snap("10:00:05", "", "1.02", symbol="SPY261014P00777000")])
    src = SnapshotQuoteSource(str(tmp_path))
    assert src.get(C, at(10, 0)) is None                       # only snapshot is 10 minutes old
    assert src.get("SPY261014P00777000", at(10, 0)) is None    # blank bid
    assert src.get("QQQ261014C00700000", at(10, 0)) is None    # never recorded
    assert src.missing == {("2026-10-13", C): "10:00", ("2026-10-13", "SPY261014P00777000"): "10:00",
                           ("2026-10-13", "QQQ261014C00700000"): "10:00"}


def test_no_snapshot_file(tmp_path):
    assert SnapshotQuoteSource(str(tmp_path)).get(C, at(10, 0)) is None
