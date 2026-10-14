import json
import os
import threading
from datetime import date, datetime
from types import SimpleNamespace

from scalpcity.recorder import Recorder, atm_contracts, fetch_day, traded_contracts
from scalpcity.types import ET, Bar
from scalpcity.webull_client import WebullClient

DAY = date(2026, 10, 13)


def row(t, close=1.0):
    return {"time": t, "open": str(close), "high": str(close), "low": str(close), "close": str(close), "volume": "5"}


class FakeClient:
    def __init__(self):
        self.snap_calls = []

    def stock_bars_raw(self, ticker, count):
        return [row("2026-10-12T19:59:00.000+0000"), row("2026-10-13T13:30:00.000+0000"), row("2026-10-13T19:59:00.000+0000")]

    def option_bars_raw(self, contracts, count):
        return {c: [row("2026-10-13T13:31:00.000+0000"), row("2026-10-14T13:31:00.000+0000")] for c in contracts}

    def option_snapshots_raw(self, contracts):
        self.snap_calls.append(list(contracts))
        return [{"symbol": c, "bid": "1.00", "ask": "1.02", "delta": "0.5"} for c in contracts]


def test_fetch_day_keeps_only_that_day_and_never_shrinks(tmp_path):
    saved = fetch_day(FakeClient(), DAY, {"SPY261014C00777000"}, str(tmp_path), tickers=("SPY",))
    assert saved == {"SPY": 2, "SPY261014C00777000": 1}
    path = tmp_path / "2026-10-13" / "stock-SPY.json"
    assert [r["time"][:10] for r in json.loads(path.read_text())] == ["2026-10-13", "2026-10-13"]
    big = [row(f"2026-10-13T14:{m:02d}:00.000+0000") for m in range(10)]
    path.write_text(json.dumps(big))
    fetch_day(FakeClient(), DAY, set(), str(tmp_path), tickers=("SPY",))
    assert len(json.loads(path.read_text())) == 10


def test_traded_and_atm_contracts():
    events = [{"kind": "order_sent", "contract": "SPY261014P00777000"}, {"kind": "tick"},
              {"kind": "fill", "contract": "QQQ261014C00741000"}]
    assert traded_contracts(events) == {"SPY261014P00777000", "QQQ261014C00741000"}
    assert atm_contracts("SPY", 777.4, DAY) == ["SPY261014C00777000", "SPY261014P00777000"]
    assert atm_contracts("SPY", 777.4, DAY, width=1) == [
        "SPY261014C00776000", "SPY261014P00776000", "SPY261014C00777000", "SPY261014P00777000",
        "SPY261014C00778000", "SPY261014P00778000"]


def test_recorder_writes_bars_snapshots_and_end_of_day(tmp_path):
    clock = {"now": datetime(2026, 10, 13, 10, 0, 5, tzinfo=ET)}
    client = FakeClient()
    rec = Recorder(client, str(tmp_path), held_fn=lambda: ["IWM261014C00276000"],
                   events_fn=lambda d: [{"kind": "fill", "contract": "IWM261014C00276000"}],
                   now_fn=lambda: clock["now"], tickers=("SPY",))
    rec.on_bar(Bar("SPY", datetime(2026, 10, 13, 9, 59, tzinfo=ET), 777, 778, 776, 777.4, 1000))
    rec.step()
    rec.step()   # same minute: no second snapshot
    out = tmp_path / "2026-10-13"
    assert len((out / "stock-SPY.live.jsonl").read_text().splitlines()) == 1
    lines = (out / "snapshots.jsonl").read_text().splitlines()
    assert len(lines) == 1 and len(json.loads(lines[0])["snapshots"]) == 11   # held + ATM +/- 2 strikes, calls and puts
    assert set(json.loads((out / "contracts.json").read_text())) == {"IWM261014C00276000"} | set(
        atm_contracts("SPY", 777.4, DAY, width=2))
    clock["now"] = datetime(2026, 10, 13, 16, 6, tzinfo=ET)
    rec.step()
    assert (out / "stock-SPY.json").exists() and (out / "option-SPY261014P00777000.json").exists()
    rec.step()
    assert (out / "option-IWM261014C00276000.json").exists()


def test_background_call_waits_for_queued_engine_call():
    order = []

    def snapshot(contracts, category):
        order.append("background")
        return []

    data = SimpleNamespace(option_market_data=SimpleNamespace(get_option_snapshot=snapshot))
    client = WebullClient(data, SimpleNamespace(), min_interval=0.0, background_gap=0.0)
    client._waiting = 1   # an engine call is queued: the background call must not take the slot
    bg = threading.Thread(target=client.option_snapshots_raw, args=(["X"],))
    bg.start()
    bg.join(0.3)
    assert order == [] and bg.is_alive()
    client._waiting = 0
    bg.join(2)
    assert order == ["background"]


def test_recorder_ignores_yesterdays_price_and_snapshots_after_each_new_bar(tmp_path):
    clock = {"now": datetime(2026, 10, 13, 9, 30, 5, tzinfo=ET)}
    client = FakeClient()
    rec = Recorder(client, str(tmp_path), held_fn=lambda: [], events_fn=lambda d: [],
                   now_fn=lambda: clock["now"], tickers=("SPY",))
    rec.on_bar(Bar("SPY", datetime(2026, 10, 10, 15, 59, tzinfo=ET), 770, 771, 769, 770.2, 1000))   # last bar of the prior day
    rec.step()
    assert client.snap_calls == []            # no strikes picked from yesterday's price
    clock["now"] = datetime(2026, 10, 13, 9, 31, 7, tzinfo=ET)
    rec.on_bar(Bar("SPY", datetime(2026, 10, 13, 9, 30, tzinfo=ET), 777, 778, 776, 777.4, 1000))
    rec.step()
    assert len(client.snap_calls) == 1 and "SPY261014C00777000" in client.snap_calls[0]
    clock["now"] = datetime(2026, 10, 13, 9, 31, 40, tzinfo=ET)
    rec.step()                                # no new bar and under a minute since the last snapshot
    assert len(client.snap_calls) == 1
    clock["now"] = datetime(2026, 10, 13, 9, 32, 6, tzinfo=ET)
    rec.on_bar(Bar("SPY", datetime(2026, 10, 13, 9, 31, tzinfo=ET), 777, 778, 776, 779.6, 1000))
    rec.step()                                # new bar: snapshot right away, strikes follow the new price
    assert len(client.snap_calls) == 2 and "SPY261014C00780000" in client.snap_calls[1]
    clock["now"] = datetime(2026, 10, 13, 9, 33, 30, tzinfo=ET)
    rec.step()                                # bars stopped: still one snapshot a minute
    assert len(client.snap_calls) == 3
