from datetime import date, datetime

from scalpcity.broker import ModeledBroker
from scalpcity.config import Settings
from scalpcity.engine import Engine
from scalpcity.events import EventLog, build_snapshot
from scalpcity.types import ET, Bar, Quote

from tests.test_recover import DAY, OPEN

CONTRACT = "SPY261012P00776000"


class Quotes:
    def __init__(self, quote):
        self.quote, self.asked = quote, []

    def get(self, contract, ts):
        self.asked.append(contract)
        if isinstance(self.quote, Exception):
            raise self.quote
        return self.quote


def holding_engine(tmp_path, quote):
    e = Engine(Settings(), EventLog(str(tmp_path), "live"), ModeledBroker(), Quotes(quote))
    e.start_session(DAY, {})
    e.recover(OPEN)   # SPY-VWAP holds 10 puts bought at 1.96, entry 776.20, stop 776.60, target 775.40
    return e


def bar(close):
    return Bar("SPY", datetime(2026, 10, 9, 10, 0, tzinfo=ET), close, close, close, close, 1000)


def spy_vwap_ticks(e):
    return [ev for ev in e.log.read(DAY) if ev["bot"] == "SPY-VWAP" and ev["kind"] == "tick"]


def test_tick_of_a_held_position_carries_side_levels_option_mid_and_open_pnl(tmp_path):
    e = holding_engine(tmp_path, Quote(CONTRACT, datetime(2026, 10, 9, 10, 1, tzinfo=ET), 2.00, 2.10))
    e.on_bar(bar(776.00))
    tick = spy_vwap_ticks(e)[-1]
    assert tick["state"] == "managing"
    assert (tick["side"], tick["contract"], tick["entry_price"], tick["qty"]) == ("PUT", CONTRACT, 1.96, 10)
    assert (tick["entry_und"], tick["stop_und"], tick["target_und"]) == (776.2, 776.6, 775.4)
    assert tick["option_mid"] == 2.05
    assert tick["open_pnl"] == 90.0   # (2.05 - 1.96) * 10 * 100


def test_missing_or_failing_quote_still_logs_the_tick_without_open_pnl(tmp_path):
    for quote in (None, RuntimeError("webull down")):
        e = holding_engine(tmp_path / type(quote).__name__, quote)
        e.on_bar(bar(776.00))
        tick = spy_vwap_ticks(e)[-1]
        assert tick["side"] == "PUT" and tick["stop_und"] == 776.6
        assert "option_mid" not in tick and "open_pnl" not in tick


def test_flat_bots_ask_no_quote_and_log_no_position_fields(tmp_path):
    e = holding_engine(tmp_path, Quote(CONTRACT, datetime(2026, 10, 9, 10, 1, tzinfo=ET), 2.00, 2.10))
    e.on_bar(bar(776.00))
    assert e.quotes.asked == [CONTRACT]
    flat = [ev for ev in e.log.read(DAY) if ev["bot"] == "SPY-EMA50" and ev["kind"] == "tick"][-1]
    assert "side" not in flat and "open_pnl" not in flat


def test_snapshot_carries_the_open_position_and_drops_it_after_the_trade(tmp_path):
    e = holding_engine(tmp_path, Quote(CONTRACT, datetime(2026, 10, 9, 10, 1, tzinfo=ET), 2.00, 2.10))
    e.on_bar(bar(776.00))
    row = build_snapshot(e.log.read(DAY))["bots"]["SPY-VWAP"]
    assert (row["side"], row["open_pnl"], row["option_mid"], row["stop_und"], row["target_und"], row["entry_und"]) == ("PUT", 90.0, 2.05, 776.6, 775.4, 776.2)
    e.on_bar(Bar("SPY", datetime(2026, 10, 9, 10, 1, tzinfo=ET), 775.0, 775.0, 775.0, 775.0, 1000))   # target hit: exits
    row = build_snapshot(e.log.read(DAY))["bots"]["SPY-VWAP"]
    assert row["state"] == "cooldown" and row["side"] is None and row["open_pnl"] is None
