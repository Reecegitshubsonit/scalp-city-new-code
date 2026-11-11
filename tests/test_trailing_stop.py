"""Scalp City V2 exit: 1 ATR initial stop, no fixed target, 1.5 ATR chandelier trail armed at +0.5 ATR (bar closes).
Mirrors backtest cell none_trail1.5_arm0.5 (exit-grid lib.resolve)."""
from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

from scalpcity.bot import Bot, Position, State, effective_stop, update_trail
from scalpcity.broker import ModeledBroker
from scalpcity.config import BOT_SPECS, Settings
from scalpcity.engine import Engine
from scalpcity.events import EventLog, build_snapshot
from scalpcity.types import ET, Bar, Fill

S = Settings()
DAY = date(2026, 10, 9)


class StubTrigger:
    def __init__(self):
        self.exits = []

    def new_session(self):
        pass

    def on_trade_exit(self, side, reason):
        self.exits.append((side, reason))


def at(h, m):
    return datetime(2026, 10, 9, h, m, tzinfo=ET)


def held_bot(right="CALL", entry=100.0, atr=1.0, **kw):
    s = Settings(**kw) if kw else S
    bot = Bot("QQQ", BOT_SPECS["vwap"], StubTrigger(), s)
    sgn = 1 if right == "CALL" else -1
    bot.position = Position(right, 10, entry, stop_und=entry - sgn * atr, target_und=entry + sgn * 2 * atr,
                            contract="QQQ261009C00100000", entry_price=2.0, opened_at=at(10, 0), entry_qty=10,
                            trail=s.trail_enabled, entry_atr=atr, signal_at=at(10, 0))
    bot.state = State.MANAGING
    return bot


def close(bot, minute, px, atr=1.0):
    bar = Bar("QQQ", at(10, minute), px, px, px, px, 1000)
    return bot._manage(bar, bar.end, SimpleNamespace(atr=SimpleNamespace(value=atr)))


def test_defaults_are_the_backtested_cell():
    assert (S.trail_enabled, S.trail_atr, S.trail_arm_atr, S.stop_atr) == (True, 1.5, 0.5, 1.0)


def test_arms_only_on_a_close_half_an_entry_atr_in_favor():
    bot = held_bot()
    assert close(bot, 1, 100.49) == [] and not bot.position.trail_armed and bot.position.trail_stop is None
    assert effective_stop(bot.position) == 99.0
    assert "trail arms on a close >= 100.50" in bot.reason_text
    assert close(bot, 2, 100.50) == [] and bot.position.trail_armed
    assert bot.position.trail_stop == pytest.approx(99.0)   # 100.5 - 1.5 x 1.0


def test_trail_ratchets_up_only_and_exits_as_trail_stop():
    bot = held_bot()
    close(bot, 1, 101.0)
    assert bot.position.trail_stop == pytest.approx(99.5)
    close(bot, 2, 102.0)
    assert bot.position.trail_stop == pytest.approx(100.5)
    close(bot, 3, 101.2, atr=2.0)                      # wider ATR would put the level at 99.0: ignored, never loosens
    assert bot.position.trail_stop == pytest.approx(100.5) and bot.position.best_close == 102.0
    assert "trail 100.50" in bot.reason_text and "no target" in bot.reason_text
    out = close(bot, 4, 100.5)
    assert len(out) == 1 and out[0].reason == "TRAIL_STOP" and bot.reason_code == "EXIT_TRAIL_STOP"
    assert bot.position.exit_win is True and bot.trigger.exits == []   # a winning trail clears memory only after the fill
    bot.on_fill(Fill(bot.bot_id, "SELL_CLOSE", "QQQ261009C00100000", 10, 2.5, "modeled", at(10, 5)))
    assert bot.trigger.exits == [("CALL", "TARGET")]


def test_put_side_is_mirrored():
    bot = held_bot("PUT")
    close(bot, 1, 99.6)
    assert not bot.position.trail_armed
    close(bot, 2, 99.5)
    assert bot.position.trail_armed and effective_stop(bot.position) == pytest.approx(101.0)
    close(bot, 3, 98.0)
    assert bot.position.trail_stop == pytest.approx(99.5) and bot.position.best_close == 98.0
    close(bot, 4, 98.5)
    assert bot.position.trail_stop == pytest.approx(99.5)   # ratchets down only
    out = close(bot, 5, 99.5)
    assert out[0].reason == "TRAIL_STOP" and bot.position.exit_win is True


def test_never_looser_than_the_initial_stop():
    bot = held_bot()
    close(bot, 1, 100.5, atr=2.0)                      # armed, level 97.5 is below the 99.0 stop
    assert bot.position.trail_armed and effective_stop(bot.position) == 99.0
    out = close(bot, 2, 99.0, atr=2.0)
    assert out[0].reason == "STOP" and bot.trigger.exits == [("CALL", "STOP")]


def test_losing_trail_stop_fails_the_side_at_once():
    bot = held_bot()
    close(bot, 1, 100.5)
    close(bot, 2, 101.0)                               # trail 99.5, above the 99.0 stop
    out = close(bot, 3, 99.4)
    assert out[0].reason == "TRAIL_STOP" and bot.position.exit_win is False
    assert bot.trigger.exits == [("CALL", "STOP")]


def test_no_fixed_target_exit_when_trailing():
    bot = held_bot()
    assert close(bot, 1, 103.0) == [] and bot.state == State.MANAGING   # past the old 102.0 target
    legacy = held_bot(trail_enabled=False)
    out = close(legacy, 1, 103.0)
    assert out[0].reason == "TARGET" and "target" in legacy.reason_text


def test_update_trail_matches_backtest_order_on_one_bar():
    p = Position("CALL", 10, 100.0, 99.0, 102.0, trail=True, entry_atr=1.0)
    update_trail(p, 101.0, 0.4, S)                      # best, arm and level all on the same close
    assert p.best_close == 101.0 and p.trail_armed and p.trail_stop == pytest.approx(100.4)


# ---- restart recovery ----
CALL = "SPY261009C00700000"


def ev(seq, time, kind, reason="", **extra):
    return {"seq": seq, "time": time.isoformat(), "mode": "live", "bot": "SPY-VWAP", "ticker": "SPY", "kind": kind, "state": "",
            "reason_code": reason, "reason_text": "", "inputs": extra.pop("inputs", {}), "charge_pct": None, **extra}


OPEN = [ev(1, at(10, 0), "order_sent", "BUY_OPEN", contract=CALL, qty=10, inputs={"price": 700.0, "atr": 1.0},
           stop_und=699.0, target_und=702.0, trail=True, entry_atr=1.0),
        ev(2, at(10, 0) + timedelta(seconds=5), "fill", "ENTRY_FILL", contract=CALL, qty=10, fill_price=2.0)]


def spy(minute, px):
    return Bar("SPY", at(10, minute), px, px, px, px, 1000)


def fresh_engine(tmp_path):
    e = Engine(Settings(), EventLog(str(tmp_path), "live"), ModeledBroker(), SimpleNamespace(get=lambda c, t: None))
    e.start_session(DAY, {})
    return e


def test_restart_rebuilds_trail_from_todays_bars(tmp_path):
    e = fresh_engine(tmp_path)
    e.today_bars["SPY"] = [   # only bars starting at/after the signal bar end count
        (Bar("SPY", at(9, 59), 700, 700, 700, 699.0, 1), 1.0),   # the signal bar itself: ignored
        (spy(0, 700.6), 1.0), (spy(1, 702.0), 1.0), (spy(2, 701.0), 2.0)]
    e.recover(OPEN)
    p = e.by_id["SPY-VWAP"].position
    assert p.trail and p.entry_atr == 1.0 and p.signal_at == at(10, 0)
    assert p.best_close == 702.0 and p.trail_armed and p.trail_stop == pytest.approx(700.5)
    assert "trail 700.50" in e.by_id["SPY-VWAP"].reason_text


def test_restart_falls_back_to_last_logged_trail_tick(tmp_path):
    e = fresh_engine(tmp_path)
    tick = ev(3, at(10, 3), "tick", "HOLDING", side="CALL", best_close=701.8, trail_stop=700.3, trail=True)
    e.recover(OPEN + [tick])
    p = e.by_id["SPY-VWAP"].position
    assert (p.best_close, p.trail_stop, p.trail_armed) == (701.8, 700.3, True)


def test_restart_with_no_trail_history_starts_unarmed(tmp_path):
    e = fresh_engine(tmp_path)
    e.recover(OPEN)
    p = e.by_id["SPY-VWAP"].position
    assert p.trail and not p.trail_armed and p.trail_stop is None and effective_stop(p) == 699.0


def test_tick_and_snapshot_show_trail_level(tmp_path):
    e = fresh_engine(tmp_path)
    e.recover(OPEN)
    bot = e.by_id["SPY-VWAP"]
    bar = spy(1, 701.0)
    out = bot._manage(bar, bar.end, SimpleNamespace(atr=SimpleNamespace(value=1.0)))
    assert out == []
    held = e._held(bot, bar)
    assert held["trail"] is True and held["best_close"] == 701.0 and held["trail_stop"] == pytest.approx(699.5)
    e._write(bar.end, bot, [{"kind": "tick", "state": "managing", "reason_code": "HOLDING", "reason_text": "", **held}])
    row = build_snapshot(e.log.read(DAY))["bots"]["SPY-VWAP"]
    assert row["trail_stop"] == pytest.approx(699.5)
