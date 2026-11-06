"""Failure memory, per-side re-arm and real IWM 2026-11-06 acceptance tape."""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from scalpcity.bot import Bot, Position
from scalpcity.config import BOT_SPECS, Settings
from scalpcity.indicators import IndicatorSet
from scalpcity.triggers import Ema50Cross5m, RangeBreak, VwapCross
from scalpcity.types import Bar, Fill


def fixed_ind(level=100, trend="CALL", atr=1):
    ind = IndicatorSet()
    ind.vwap.value = level
    ind.atr.value = atr
    ind.ema9.value, ind.ema21.value = (102, 100) if trend == "CALL" else (98, 100)
    return ind


def trigger(kind, mk):
    trig = RangeBreak() if kind == "range" else VwapCross()
    if kind == "range":
        trig.update(mk("QQQ", "9:30", 100, high=101, low=99), fixed_ind())
    return trig


def level(kind, side):
    return (101 if side == "CALL" else 99) if kind == "range" else 100


@pytest.mark.parametrize("kind", ["range", "vwap"])
@pytest.mark.parametrize("side", ["CALL", "PUT"])
def test_first_cross_one_close_stop_requires_rearm_and_two_closes(kind, side, mk):
    trig, ind = trigger(kind, mk), fixed_ind()
    lvl, sign = level(kind, side), (1 if side == "CALL" else -1)
    inside, outside = lvl - sign * .25, lvl + sign * .25
    assert trig.update(mk("QQQ", "9:45", inside), ind).signal is None
    assert trig.update(mk("QQQ", "9:46", outside), ind).signal == side
    trig.on_trade_exit(side, "STOP")  # stopped while still outside the trigger level
    for minute in (47, 48, 49):
        view = trig.update(mk("QQQ", f"9:{minute}", outside), ind)
        assert view.signal is None and "re-arm" in view.reason_text
    trig.update(mk("QQQ", "9:50", inside), ind)
    view = trig.update(mk("QQQ", "9:51", outside), ind)
    assert view.signal is None and "1/2" in view.reason_text
    assert trig.update(mk("QQQ", "9:52", outside), ind).signal == side
    assert trig.update(mk("QQQ", "9:53", outside), ind).signal is None  # no repeated entries


@pytest.mark.parametrize("kind", ["range", "vwap"])
@pytest.mark.parametrize("side", ["CALL", "PUT"])
def test_wick_rejection_and_interrupted_confirmation(kind, side, mk):
    trig, ind = trigger(kind, mk), fixed_ind()
    lvl, sign = level(kind, side), (1 if side == "CALL" else -1)
    inside, outside = lvl - sign * .25, lvl + sign * .25
    kw = {"high": outside} if side == "CALL" else {"low": outside}
    view = trig.update(mk("QQQ", "9:45", inside, **kw), ind)
    assert view.signal is None and "wick rejection" in view.reason_text
    assert trig.update(mk("QQQ", "9:46", outside), ind).signal is None
    trig.update(mk("QQQ", "9:47", inside), ind)  # interruption resets first close
    assert trig.update(mk("QQQ", "9:48", outside), ind).signal is None
    assert trig.update(mk("QQQ", "9:49", outside), ind).signal == side


@pytest.mark.parametrize("kind", ["range", "vwap"])
def test_failure_is_per_side_target_clears_and_session_resets(kind, mk):
    trig, ind = trigger(kind, mk), fixed_ind()
    trig.on_trade_exit("CALL", "STOP")
    assert trig.memory.sides["CALL"].failed
    assert not trig.memory.sides["PUT"].failed
    trig.update(mk("QQQ", "9:45", 100.5), ind)
    assert trig.update(mk("QQQ", "9:46", 98.5), ind).signal == "PUT"
    trig.on_trade_exit("CALL", "TARGET")
    assert not trig.memory.sides["CALL"].failed
    trig.update(mk("QQQ", "9:47", 99.5), ind)
    assert trig.update(mk("QQQ", "9:48", 101.5), ind).signal == "CALL"
    trig.on_trade_exit("PUT", "STOP")
    trig.new_session()
    assert not any(s.failed for s in trig.memory.sides.values())


@pytest.mark.parametrize("side", ["CALL", "PUT"])
def test_trend_filter_agreement_disagreement_and_own_ema50(side):
    ind = fixed_ind(trend=side)
    bot = Bot("QQQ", BOT_SPECS["range"], RangeBreak(), Settings())
    opposite = "PUT" if side == "CALL" else "CALL"
    assert bot._side(side, ind) == side
    assert bot._side(opposite, ind) is None
    own = Bot("QQQ", BOT_SPECS["ema50"], Ema50Cross5m(), Settings())
    assert own._side(opposite, ind) == opposite
    assert not hasattr(own.trigger, "memory")
    ind.ema9.value = None
    assert bot._side(side, ind) is None
    assert own._side(opposite, ind) == opposite


def test_equal_emas_use_put_side_as_specified():
    ind = fixed_ind()
    ind.ema9.value = ind.ema21.value
    bot = Bot("QQQ", BOT_SPECS["range"], RangeBreak(), Settings())
    assert bot._side("CALL", ind) is None
    assert bot._side("PUT", ind) == "PUT"


def test_stop_callback_and_wicks_do_not_exit_position(mk):
    trig, ind = trigger("range", mk), fixed_ind()
    bot = Bot("QQQ", BOT_SPECS["range"], trig, Settings())
    bot.on_bar(mk("QQQ", "9:30", 100, high=101, low=99), ind)
    bot.on_bar(mk("QQQ", "9:45", 101.5), ind)
    bot.on_fill(Fill(bot.bot_id, "BUY_OPEN", "x", 10, 2, "modeled", mk("QQQ", "9:45", 1).end))
    assert not bot.on_bar(mk("QQQ", "9:46", 101.5, low=90), ind).intents
    # Stop above the range: no wick rejection, yet the actual close stop marks CALL failed.
    bot.position.stop_und = 101.4
    out = bot.on_bar(mk("QQQ", "9:47", 101.3), ind)
    assert out.intents[0].reason == "STOP"
    assert trig.memory.sides["CALL"].failed and not trig.memory.sides["CALL"].armed


def test_target_clears_only_after_full_fill(mk):
    trig, ind = trigger("range", mk), fixed_ind()
    bot = Bot("QQQ", BOT_SPECS["range"], trig, Settings())
    bot.position = Position("CALL", 10, 101, 100, 103, contract="x", entry_price=2, entry_qty=10)
    trig.on_trade_exit("CALL", "STOP")
    out = bot.on_bar(mk("QQQ", "9:46", 104), ind)
    assert out.intents[0].reason == "TARGET"
    assert trig.memory.sides["CALL"].failed
    bot.on_fill(Fill(bot.bot_id, "SELL_CLOSE", "x", 5, 3, "modeled", mk("QQQ", "9:46", 1).end))
    assert trig.memory.sides["CALL"].failed
    bot.on_fill(Fill(bot.bot_id, "SELL_CLOSE", "x", 5, 3, "modeled", mk("QQQ", "9:46", 1).end))
    assert not trig.memory.sides["CALL"].failed


def test_vwap_rearm_uses_current_bar_vwap(mk):
    trig, ind = VwapCross(), fixed_ind()
    trig.update(mk("QQQ", "9:45", 101), ind)
    trig.on_trade_exit("CALL", "STOP")
    assert trig.update(mk("QQQ", "9:46", 101), ind).signal is None
    ind.vwap.value = 102  # price below new VWAP re-arms even with unchanged close
    trig.update(mk("QQQ", "9:47", 101), ind)
    ind.vwap.value = 100
    assert trig.update(mk("QQQ", "9:48", 101), ind).signal is None
    assert trig.update(mk("QQQ", "9:49", 101), ind).signal == "CALL"


def test_iwm_2026_11_06_skips_0801_loser_and_takes_held_breakout():
    """Real tape: bar start 08:00 MST -> old 08:01 entry; 08:09 + 08:10 confirm at 08:11.

    Recorded indicators isolate the entry rules, reproduce the actual first ATR
    stop, and verify real 9/21 agreement without depending on prior-day warm bars.
    No broker calls, simulated option returns or claims that the delayed entry earns $480.
    """
    rows = json.loads((Path(__file__).parent / "fixtures/iwm-2026-11-06-opening.json").read_text())
    bot = Bot("IWM", BOT_SPECS["range"], RangeBreak(), Settings(daily_loss=800))
    ind = fixed_ind(atr=.4736)
    entries, stops, reasons = [], [], {}
    mt = ZoneInfo("America/Denver")
    for r in rows:
        bar = Bar("IWM", datetime.fromisoformat(r["time"]), *(r[k] for k in ("open", "high", "low", "close", "volume")))
        recorded = r.get("indicators", {})
        for obj, key in ((ind.atr, "atr"), (ind.ema9, "ema9"), (ind.ema21, "ema21"), (ind.vwap, "vwap")):
            if key in recorded:
                obj.value = recorded[key]
        out = bot.on_bar(bar, ind)
        hhmm = bar.ts.astimezone(mt).strftime("%H:%M")
        reasons[hhmm] = bot.reason_code
        for intent in out.intents:
            if intent.kind == "BUY_OPEN":
                entries.append((bar.end.astimezone(mt).strftime("%H:%M"), intent.right))
                bot.on_fill(Fill(bot.bot_id, "BUY_OPEN", "fixture", 10, 2.47, "modeled", bar.end))
            else:
                stops.append((bar.end.astimezone(mt).strftime("%H:%M"), intent.reason))
                bot.on_fill(Fill(bot.bot_id, "SELL_CLOSE", "fixture", 10, 2.08, "modeled", bar.end))
    assert (bot.trigger.hi, bot.trigger.lo) == (272.11, 270.24)
    assert entries == [("07:46", "CALL"), ("08:11", "CALL")]
    assert stops == [("07:55", "STOP")]
    assert reasons["08:00"] == "FAILED_BREAKOUT_HOLD"  # old 08:01 loser is skipped
    assert reasons["08:09"] == "FAILED_BREAKOUT_HOLD"  # first held close
    assert reasons["08:10"] == "SIGNAL"                # second held close, previous close OUTSIDE
