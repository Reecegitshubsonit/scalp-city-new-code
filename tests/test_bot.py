from datetime import datetime, timedelta

import pytest

from scalpcity.bot import Bot, State
from scalpcity.config import BOT_SPECS, Settings
from scalpcity.indicators import IndicatorSet
from scalpcity.triggers import RangeBreak, VwapCross
from scalpcity.types import ET, Fill

S = Settings()


def vwap_bot(**kw):
    return Bot("QQQ", BOT_SPECS["vwap"], VwapCross(S.charge_range_atr), Settings(**kw) if kw else S)


B = 129.5  # last warm-up close below


def warmed(mk, n=60, start=100.0, slope=0.5, rng=1.0):
    """Rising history: EMA9 sits well above EMA21 (not squeezed); last close is B."""
    ind = IndicatorSet()
    for i in range(n):
        c = start + slope * i
        ind.warm(mk("QQQ", "15:59", c, high=c + rng / 2, low=c - rng / 2))
    return ind


def step(bot, ind, bar):
    ind.update(bar)
    return bot.on_bar(bar, ind)


def states(out):
    return [e["state"] for e in out.events]


def test_before_arm_time_reports_outside_window(mk):
    bot, ind = vwap_bot(), warmed(mk)
    out = step(bot, ind, mk("QQQ", "9:25", 103))
    assert bot.state == State.IDLE and bot.reason_code == "OUTSIDE_WINDOW"
    assert out.events[0]["kind"] == "state_change" and out.events[-1]["kind"] == "tick"


def test_signal_fires_buy_intent_with_atr_stop_and_target(mk):
    bot, ind = vwap_bot(), warmed(mk)
    # session bars under VWAP then close up through it
    step(bot, ind, mk("QQQ", "9:30", B - 1.0, volume=1000))
    step(bot, ind, mk("QQQ", "9:31", B - 1.5, volume=1000))
    out = step(bot, ind, mk("QQQ", "9:32", B + 5.0, volume=1000))
    assert bot.state == State.FIRED and len(out.intents) == 1
    intent = out.intents[0]
    assert (intent.kind, intent.right, intent.qty) == ("BUY_OPEN", "CALL", 10)
    p = bot.position
    assert p.stop_und == pytest.approx(B + 5.0 - ind.atr.value) and p.target_und == pytest.approx(B + 5.0 + 2 * ind.atr.value)


def test_chop_squeeze_blocks_vwap_signal(mk):
    bot = vwap_bot()
    ind = IndicatorSet()
    for _ in range(40):  # flat history: EMA9 == EMA21
        ind.warm(mk("QQQ", "15:59", 100.0, high=100.5, low=99.5))
    step(bot, ind, mk("QQQ", "9:30", 99.0, volume=1000))
    step(bot, ind, mk("QQQ", "9:31", 98.9, volume=1000))
    out = step(bot, ind, mk("QQQ", "9:32", 100.4, volume=1000))
    assert out.intents == [] and bot.reason_code == "CHOP_SQUEEZE"


def _enter(bot, ind, mk):
    step(bot, ind, mk("QQQ", "9:30", B - 1.0, volume=1000))
    step(bot, ind, mk("QQQ", "9:31", B - 1.5, volume=1000))
    out = step(bot, ind, mk("QQQ", "9:32", B + 5.0, volume=1000))
    fill = Fill(bot.bot_id, "BUY_OPEN", "QQQ261009C00105000", 10, 3.00, "modeled", mk("QQQ", "9:32", 1).end)
    bot.on_fill(fill)
    return out.intents[0]


def test_fill_moves_to_managing_then_stop_exit_and_cooldown(mk):
    bot, ind = vwap_bot(), warmed(mk)
    _enter(bot, ind, mk)
    assert bot.state == State.MANAGING
    out = step(bot, ind, mk("QQQ", "9:33", B - 30.0))          # far below the stop
    assert out.intents[0].kind == "SELL_CLOSE" and bot.state == State.EXITING
    assert step(bot, ind, mk("QQQ", "9:34", B - 30.0)).intents == []   # no duplicate exit while pending
    t = mk("QQQ", "9:34", 1).end
    events = bot.on_fill(Fill(bot.bot_id, "SELL_CLOSE", "QQQ261009C00105000", 10, 2.00, "modeled", t))
    assert [e["kind"] for e in events] == ["fill", "trade_closed", "state_change"]
    assert bot.pnl_day == pytest.approx(-1000.0)            # (2.00-3.00)*10*100
    assert bot.locked == "DAILY_LOSS" and bot.state == State.LOCKED


def test_goal_locks_for_the_day(mk):
    bot, ind = vwap_bot(), warmed(mk)
    _enter(bot, ind, mk)
    step(bot, ind, mk("QQQ", "9:33", B + 100.0))                # far above target
    bot.on_fill(Fill(bot.bot_id, "SELL_CLOSE", "x", 10, 3.80, "modeled", mk("QQQ", "9:34", 1).end))
    assert bot.pnl_day == pytest.approx(800.0) and bot.locked == "DAILY_GOAL"


def test_small_loss_goes_to_cooldown_then_resumes(mk):
    bot, ind = vwap_bot(), warmed(mk)
    _enter(bot, ind, mk)
    step(bot, ind, mk("QQQ", "9:33", B - 30.0))
    bot.on_fill(Fill(bot.bot_id, "SELL_CLOSE", "x", 10, 2.95, "modeled", mk("QQQ", "9:34", 1).end))  # -50
    assert bot.state == State.COOLDOWN and bot.locked is None
    step(bot, ind, mk("QQQ", "9:35", B - 30.0))
    assert bot.reason_code == "COOLDOWN"
    step(bot, ind, mk("QQQ", "9:37", B - 30.0))                # 2+ minutes after 9:35 close
    assert bot.reason_code != "COOLDOWN"


def test_time_exit_at_flat_by(mk):
    bot, ind = vwap_bot(), warmed(mk)
    _enter(bot, ind, mk)
    out = step(bot, ind, mk("QQQ", "15:54", B + 5.2))         # bar ends 15:55
    assert out.intents[0].kind == "SELL_CLOSE" and bot.reason_code == "EXIT_TIME"


def test_pause_blocks_entries_but_keeps_managing(mk):
    bot, ind = vwap_bot(), warmed(mk)
    bot.set_paused(True)
    step(bot, ind, mk("QQQ", "9:30", B - 1.0, volume=1000))
    step(bot, ind, mk("QQQ", "9:31", B - 1.5, volume=1000))
    out = step(bot, ind, mk("QQQ", "9:32", B + 5.0, volume=1000))
    assert out.intents == [] and bot.state == State.PAUSED
    bot.set_paused(False)
    bot2, ind2 = vwap_bot(), warmed(mk)
    _enter(bot2, ind2, mk)
    bot2.set_paused(True)
    assert bot2.state == State.MANAGING                      # still managing the open position
    assert step(bot2, ind2, mk("QQQ", "9:33", B - 30.0)).intents[0].kind == "SELL_CLOSE"


def test_order_failed_entry_returns_to_idle(mk):
    bot, ind = vwap_bot(), warmed(mk)
    step(bot, ind, mk("QQQ", "9:30", B - 1.0, volume=1000))
    step(bot, ind, mk("QQQ", "9:31", B - 1.5, volume=1000))
    step(bot, ind, mk("QQQ", "9:32", B + 5.0, volume=1000))
    bot.on_order_failed("BUY_OPEN", "NO_QUOTE")
    assert bot.position is None and bot.reason_code == "ORDER_FAILED"


def test_range_bot_armed_at_940_fires_after_945(mk):
    bot = Bot("QQQ", BOT_SPECS["range"], RangeBreak(S.charge_range_atr), S)
    ind = warmed(mk)
    for minute in range(30, 40):
        step(bot, ind, mk("QQQ", f"9:{minute}", 100, high=101, low=99))
    assert bot.reason_code == "OUTSIDE_WINDOW" or bot.reason_code == "RANGE_FORMING"
    step(bot, ind, mk("QQQ", "9:39", 100, high=101, low=99))
    assert bot.reason_code == "RANGE_FORMING"                # armed from 9:40 (bar 9:39 ends 9:40)
    for minute in range(40, 45):
        step(bot, ind, mk("QQQ", f"9:{minute}", 100, high=101, low=99))
    step(bot, ind, mk("QQQ", "9:45", 100.5))
    out = step(bot, ind, mk("QQQ", "9:46", 102.0))
    assert out.intents and out.intents[0].right == "CALL"


def test_stale_flag_sets_state_when_flat(mk):
    bot = vwap_bot()
    ev = bot.set_stale(True, "no bar for 2 min")
    assert bot.state == State.STALE and ev[0]["kind"] == "feed_stale"
    assert bot.set_stale(True) == []
    assert bot.set_stale(False)[0]["kind"] == "feed_fresh"
