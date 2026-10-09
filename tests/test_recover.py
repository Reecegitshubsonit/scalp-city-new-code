from datetime import date, datetime, timedelta

from scalpcity.bot import State
from scalpcity.broker import ModeledBroker
from scalpcity.config import Settings
from scalpcity.engine import Engine
from scalpcity.events import EventLog
from scalpcity.types import ET

DAY = date(2026, 10, 9)


def t(h, m, s=0):
    return datetime(2026, 10, 9, h, m, s, tzinfo=ET).isoformat()


def ev(seq, time, bot, kind, reason="", **extra):
    ticker = bot.split("-")[0]
    return {"seq": seq, "time": time, "mode": "live", "bot": bot, "ticker": ticker, "kind": kind, "state": "", "reason_code": reason,
            "reason_text": "", "inputs": extra.pop("inputs", {}), "charge_pct": None, **extra}


def engine(tmp_path, **kw):
    e = Engine(Settings(**kw), EventLog(str(tmp_path), "live"), ModeledBroker(), None)
    e.start_session(DAY, {})
    return e


CLOSED = [
    ev(1, t(9, 47), "IWM-RANGE", "order_sent", "BUY_OPEN", contract="IWM261012P00278000", qty=10, inputs={"price": 278.10, "atr": 0.10}),
    ev(2, t(9, 47), "IWM-RANGE", "fill", "ENTRY_FILL", contract="IWM261012P00278000", qty=10, fill_price=1.51),
    ev(3, t(9, 52), "IWM-RANGE", "fill", "EXIT_FILL", contract="IWM261012P00278000", qty=10, fill_price=1.26),
    ev(4, t(9, 52), "IWM-RANGE", "trade_closed", "DAILY_LOSS", pnl=-250.0, pnl_day=-250.0, trades=1),
]
OPEN = [
    ev(5, t(9, 43), "SPY-VWAP", "order_sent", "BUY_OPEN", contract="SPY261012P00776000", qty=10, inputs={"price": 776.20, "atr": 0.40}),
    ev(6, t(9, 43), "SPY-VWAP", "fill", "ENTRY_FILL", contract="SPY261012P00776000", qty=10, fill_price=1.96),
]
FAILED = [
    ev(7, t(9, 55), "QQQ-EMA50", "order_sent", "BUY_OPEN", contract="QQQ261012C00750000", qty=10, inputs={"price": 750.0, "atr": 0.3}),
    ev(8, t(9, 55), "QQQ-EMA50", "state_change", "ORDER_FAILED"),
]


def test_closed_trade_restores_pnl_trades_cooldown_and_lock_follows_the_current_limit(tmp_path):
    strict = engine(tmp_path, daily_loss=100.0); strict.recover(CLOSED)
    bot = strict.by_id["IWM-RANGE"]
    assert (bot.pnl_day, bot.trades, bot.position) == (-250.0, 1, None)
    assert bot.cooldown_until == datetime.fromisoformat(t(9, 52)) + timedelta(seconds=120)
    assert bot.locked == "DAILY_LOSS"
    loose = engine(tmp_path, daily_loss=500.0); loose.recover(CLOSED)
    assert loose.by_id["IWM-RANGE"].locked is None and loose.by_id["IWM-RANGE"].pnl_day == -250.0


def test_open_position_is_rebuilt_with_its_atr_stop_and_target(tmp_path):
    e = engine(tmp_path); e.recover(OPEN)
    bot = e.by_id["SPY-VWAP"]; p = bot.position
    assert bot.state == State.MANAGING and bot.pending is None
    assert (p.right, p.qty, p.contract, p.entry_price) == ("PUT", 10, "SPY261012P00776000", 1.96)
    assert p.entry_und == 776.20 and abs(p.stop_und - 776.60) < 1e-9 and abs(p.target_und - 775.40) < 1e-9   # put: stop above, target below


def test_failed_entry_leaves_no_position(tmp_path):
    e = engine(tmp_path); e.recover(FAILED)
    assert e.by_id["QQQ-EMA50"].position is None


def test_unknown_bots_and_empty_log_are_ignored(tmp_path):
    e = engine(tmp_path); e.recover([])
    e.recover([ev(1, t(9, 40), "XYZ-VWAP", "tick")])
    assert all(b.position is None and b.pnl_day == 0 for b in e.bots)
