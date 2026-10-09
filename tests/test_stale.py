from datetime import date, datetime, timedelta
from types import SimpleNamespace

from scalpcity.broker import ModeledBroker
from scalpcity.config import Settings
from scalpcity.engine import Engine
from scalpcity.events import EventLog
from scalpcity.types import ET, Quote

NOW = datetime(2026, 10, 8, 10, 5, 30, tzinfo=ET)


def test_engine_marks_ticker_stale_and_blocks_entries(tmp_path):
    log = EventLog(str(tmp_path), "live")
    eng = Engine(Settings(), log, ModeledBroker(), SimpleNamespace(get=lambda c, t: None))
    eng.start_session(date(2026, 10, 8), {})
    wall = {"QQQ": NOW - timedelta(seconds=200), "SPY": NOW - timedelta(seconds=10), "IWM": NOW - timedelta(seconds=10)}
    eng.check_stale(NOW, wall)
    assert eng.stale == {"QQQ"}
    assert eng.by_id["QQQ-VWAP"].state.value == "stale" and eng.by_id["SPY-VWAP"].state.value != "stale"
    eng.check_stale(NOW, {**wall, "QQQ": NOW - timedelta(seconds=5)})
    assert eng.stale == set()


def test_engine_flattens_bot_stale_in_trade_after_5_minutes(tmp_path):
    from scalpcity.bot import Position, State
    log = EventLog(str(tmp_path), "live")
    quotes = SimpleNamespace(get=lambda c, t: Quote(c, t, 2.0, 2.1))
    eng = Engine(Settings(), log, ModeledBroker(), quotes)
    eng.start_session(date(2026, 10, 8), {})
    bot = eng.by_id["QQQ-VWAP"]
    bot.position = Position("CALL", 10, 748.0, 747.0, 750.0, contract="QQQ261009C00748000", entry_price=3.0, opened_at=NOW)
    bot.state = State.MANAGING
    wall = {t: NOW for t in ("QQQ", "SPY", "IWM")}
    eng.check_stale(NOW, wall, {"QQQ-VWAP": NOW - timedelta(seconds=310)})
    assert bot.position is None and bot.pnl_day == -1000.0     # sold at the 2.00 bid: (2.00-3.00)*10*100
    kinds = [e["kind"] for e in log.read(NOW.date())]
    assert "feed_stale" in kinds and "trade_closed" in kinds
