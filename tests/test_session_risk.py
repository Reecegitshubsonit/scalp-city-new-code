"""2026-11-06 risk changes: 5-minute EMA50 sizing, engine-wide remaining-room loss cap, no new entries from 11:00 ET (open trades run to stop, target or 15:55 ET)."""
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from scalpcity.bot import Bot, Position, State
from scalpcity.broker import ModeledBroker
from scalpcity.config import BOT_SPECS, Settings
from scalpcity.engine import Engine
from scalpcity.events import EventLog
from scalpcity.indicators import IndicatorSet
from scalpcity.triggers import Ema50Cross5m, RangeBreak, VwapCross
from scalpcity.types import ET, Bar, Fill, OrderIntent, Quote

from tests.test_bot import B, _enter, step, vwap_bot, warmed

DAY = date(2026, 11, 9)
LIVE = Settings(daily_loss=800)   # what run_newcode.sh passes


def ind_with_atr(atr1):
    return SimpleNamespace(atr=SimpleNamespace(value=atr1))


# ---- A) 5-minute EMA50 contracts ----

@pytest.mark.parametrize("atr1, atr5, qty", [
    (1.0, 1.0, 10),     # same ATR -> full size
    (1.0, 2.0, 5),
    (1.0, 2.3, 4),      # 2026-11-06 QQQ-EMA50: 5m stop ~2.3x a 1m stop
    (1.0, 2.5, 4),      # 10 / 2.5 = 4
    (1.0, 4.0, 3),      # 2.5 rounds half up to 3
    (1.0, 30.0, 1),     # never below 1
    (2.0, 1.0, 10),     # never above Settings.contracts
])
def test_ema50_qty_matches_a_full_size_one_minute_stop(atr1, atr5, qty):
    bot = Bot("QQQ", BOT_SPECS["ema50"], Ema50Cross5m(), LIVE)
    got, _ = bot._qty(ind_with_atr(atr1), SimpleNamespace(atr=atr5))
    assert got == qty


def test_ema50_without_a_one_minute_atr_uses_the_fallback_of_4():
    bot = Bot("QQQ", BOT_SPECS["ema50"], Ema50Cross5m(), LIVE)
    assert bot._qty(ind_with_atr(None), SimpleNamespace(atr=2.5))[0] == 4 == LIVE.ema50_fallback_contracts


@pytest.mark.parametrize("kind, trig", [("vwap", VwapCross), ("range", RangeBreak)])
def test_vwap_and_range_stay_at_ten(kind, trig):
    bot = Bot("QQQ", BOT_SPECS[kind], trig(), LIVE)
    assert bot._qty(ind_with_atr(1.0), SimpleNamespace(atr=None))[0] == 10
    assert bot._qty(ind_with_atr(1.0), None)[0] == 10


def test_ema50_fire_puts_the_shrunk_qty_on_position_and_intent_and_keeps_1_and_2_atr_levels(mk):
    bot = Bot("QQQ", BOT_SPECS["ema50"], Ema50Cross5m(), LIVE)
    ind = warmed(mk)
    view = SimpleNamespace(atr=ind.atr.value * 2.5, signal="CALL")
    b = mk("QQQ", "10:10", 130.0)
    [intent] = bot._fire(b, ind, "CALL", view)
    assert intent.qty == bot.position.qty == 4
    assert bot.position.stop_und == pytest.approx(130.0 - view.atr) and bot.position.target_und == pytest.approx(130.0 + 2 * view.atr)


# ---- B) engine-wide loss cap ----

class Quotes:
    def __init__(self, bid=2.00, ask=2.02):
        self.bid, self.ask = bid, ask

    def get(self, contract, ts):
        return Quote(contract, ts, self.bid, self.ask)


def engine(tmp_path, quotes=None):
    e = Engine(LIVE, EventLog(str(tmp_path), "live"), ModeledBroker(), quotes or Quotes())
    e.start_session(DAY, {})
    return e


def at(h, m):
    return datetime(2026, 11, 9, h, m, tzinfo=ET)


def bar_for(ticker, h, m, close=100.0):
    return Bar(ticker, at(h, m), close, close, close, close, 1000)


def open_and_close(e, bot_id, entry, exit_, qty=10, h=9, m=40):
    """Run a full trade through Engine._execute: buy at `entry`, sell at `exit_` (bid==ask for exact P&L)."""
    bot, ind = e.by_id[bot_id], IndicatorSet()
    e.quotes.bid = e.quotes.ask = entry
    bot.position, bot.pending = Position("CALL", qty, 100.0, 99.9, 100.2), "entry"
    e._execute(bot, OrderIntent(bot_id, bot.ticker, "BUY_OPEN", "CALL", qty, "signal", 100.0), bar_for(bot.ticker, h, m), ind)
    assert bot.position.entry_price == entry
    e.quotes.bid = e.quotes.ask = exit_
    bot.pending = "exit"
    e._execute(bot, OrderIntent(bot_id, bot.ticker, "SELL_CLOSE", "CALL", qty, "STOP", 99.9, contract=bot.position.contract),
               bar_for(bot.ticker, h, m + 1), ind)
    assert bot.position is None


def test_two_bots_whose_losses_reach_800_lock_every_bot(tmp_path):
    e = engine(tmp_path)
    open_and_close(e, "IWM-RANGE", 2.00, 1.55)    # -450
    assert e.loss_room() == 350 and not any(b.locked for b in e.bots)
    open_and_close(e, "IWM-VWAP", 2.00, 1.65)     # -350 -> engine -800
    assert e.engine_pnl() == -800 and e.loss_room() == 0
    capped = [b for b in e.bots if b.ticker != "QQQ"]
    assert {b.locked for b in capped} == {"ENGINE_DAILY_LOSS"} and all(b.state == State.LOCKED for b in capped)
    assert all(b.locked is None for b in e.bots if b.ticker == "QQQ")   # QQQ keeps trading


def test_one_loser_past_800_locks_every_spy_and_iwm_bot_but_not_qqq(tmp_path):
    e = engine(tmp_path)
    open_and_close(e, "SPY-EMA50", 2.00, 0.05)    # -1,950
    assert e.by_id["SPY-EMA50"].locked == "DAILY_LOSS"   # its own per-bot lock is kept
    assert all(b.locked == "ENGINE_DAILY_LOSS" for b in e.bots if b.ticker != "QQQ" and b.bot_id != "SPY-EMA50")
    assert all(b.locked is None for b in e.bots if b.ticker == "QQQ")


def test_other_bots_up_keep_the_engine_open(tmp_path):
    e = engine(tmp_path)
    open_and_close(e, "SPY-VWAP", 2.00, 2.50)     # +500
    open_and_close(e, "IWM-VWAP", 2.00, 1.30)     # -700 -> engine -200
    assert e.loss_room() == 600 and not any(b.locked for b in e.bots)


def fire(e, bot_id, stop_dist, qty=10):
    bot = e.by_id[bot_id]
    bot.position, bot.pending = Position("CALL", qty, 100.0, 100.0 - stop_dist, 100.0 + 2 * stop_dist), "entry"
    e._execute(bot, OrderIntent(bot_id, bot.ticker, "BUY_OPEN", "CALL", qty, "signal", 100.0), bar_for(bot.ticker, 10, 5), IndicatorSet())
    return bot


def test_entry_whose_stop_risk_exceeds_remaining_room_is_skipped(tmp_path):
    e = engine(tmp_path)
    e.by_id["IWM-RANGE"].pnl_day = -600.0          # room $200
    assert e.loss_room() == 200
    bot = fire(e, "SPY-VWAP", 0.40)                 # 0.40 * 0.75 * 10 * 100 = $300 > $200
    assert bot.position is None and bot.reason_code == "ORDER_FAILED"
    rej = [ev for ev in e.log.read(DAY) if ev["kind"] == "order_rejected"][-1]
    assert rej["reason_code"] == "LOSS_ROOM" and rej["est_risk"] == 300.0 and rej["loss_room"] == 200.0
    bot = fire(e, "SPY-RANGE", 0.20)                # $150 <= $200 -> sent and filled
    assert bot.position is not None and bot.position.entry_price is not None


def test_entry_risk_never_exceeds_premium_and_unknown_risk_is_refused(tmp_path):
    e = engine(tmp_path, Quotes(0.10, 0.11))
    bot = fire(e, "QQQ-VWAP", 5.0)                  # $3,750 by ATR but only $110 of premium at risk
    assert bot.position is not None
    e2 = engine(tmp_path / "b")
    bot = fire(e2, "SPY-VWAP", 0.0)                 # no ATR -> cannot size the risk -> skip
    assert bot.position is None
    assert [ev for ev in e2.log.read(DAY) if ev["kind"] == "order_rejected"][-1]["reason_code"] == "RISK_UNKNOWN"


def test_restart_rebuilds_the_engine_lock(tmp_path):
    from tests.test_recover import ev, t
    closed = [ev(1, t(9, 47), "IWM-RANGE", "trade_closed", "", pnl=-500.0, pnl_day=-500.0, trades=1),
              ev(2, t(9, 50), "IWM-VWAP", "trade_closed", "", pnl=-300.0, pnl_day=-300.0, trades=1)]
    e = Engine(LIVE, EventLog(str(tmp_path), "live"), ModeledBroker(), None)
    e.start_session(date(2026, 10, 9), {})
    e.recover(closed)
    assert all(b.locked == "ENGINE_DAILY_LOSS" for b in e.bots if b.ticker != "QQQ")
    assert all(b.locked is None for b in e.bots if b.ticker == "QQQ")


# ---- QQQ exempt from the $800 cap (2026-11-06, Reece) ----

def test_qqq_entry_over_800_and_over_remaining_room_is_allowed_but_spy_and_iwm_are_skipped(tmp_path):
    e = engine(tmp_path)
    e.by_id["IWM-RANGE"].pnl_day = -600.0              # capped room $200
    bot = fire(e, "QQQ-VWAP", 1.50)                     # 1.50 * 0.75 * 10 * 100 = $1,125 > $800 and > $200
    assert bot.position is not None and bot.position.entry_price is not None
    for bot_id in ("SPY-VWAP", "IWM-VWAP"):
        bot = fire(e, bot_id, 1.50)
        assert bot.position is None and bot.reason_code == "ORDER_FAILED"
    assert [ev["reason_code"] for ev in e.log.read(DAY) if ev["kind"] == "order_rejected"] == ["LOSS_ROOM", "LOSS_ROOM"]


def test_qqq_entry_allowed_even_after_spy_and_iwm_hit_the_cap(tmp_path):
    e = engine(tmp_path)
    open_and_close(e, "IWM-RANGE", 2.00, 1.10)          # -900 -> capped bots locked
    assert e.loss_room() <= 0 and e.by_id["SPY-VWAP"].locked == "ENGINE_DAILY_LOSS"
    assert e.by_id["QQQ-RANGE"].locked is None
    bot = fire(e, "QQQ-RANGE", 1.50)
    assert bot.position is not None


def test_qqq_pnl_neither_uses_up_nor_inflates_spy_iwm_room(tmp_path):
    e = engine(tmp_path)
    open_and_close(e, "QQQ-EMA50", 2.00, 0.05)          # QQQ -1,950: no lock anywhere, room untouched
    assert e.loss_room() == 800 and not any(b.locked for b in e.bots)
    open_and_close(e, "QQQ-VWAP", 2.00, 5.00)           # QQQ +3,000 (goal lock for that bot only)
    assert e.loss_room() == 800 and e.by_id["QQQ-VWAP"].locked == "DAILY_GOAL"
    open_and_close(e, "IWM-VWAP", 2.00, 1.20)           # IWM -800 -> capped bots lock despite QQQ net +1,050
    assert all(b.locked for b in e.bots if b.ticker != "QQQ")
    assert e.by_id["QQQ-RANGE"].locked is None and e.by_id["QQQ-EMA50"].locked is None


# ---- C) no new entries from 11:00 ET; open trades run to stop, target or 15:55 ET ----

def signal_bars(bot, ind, mk, first):
    """VWAP cross up on the third bar starting at `first` (HH:MM)."""
    h, m = map(int, first.split(":"))
    step(bot, ind, mk("QQQ", f"{h}:{m:02d}", B - 1.0))
    step(bot, ind, mk("QQQ", f"{h}:{m + 1:02d}", B - 1.5))
    return step(bot, ind, mk("QQQ", f"{h}:{m + 2:02d}", B + 5.0))


def test_entry_on_the_bar_ending_1059_is_allowed(mk):
    bot, ind = vwap_bot(), warmed(mk)
    out = signal_bars(bot, ind, mk, "10:56")       # third bar 10:58-10:59
    assert out.intents and out.intents[0].kind == "BUY_OPEN"


def test_no_entry_at_or_after_1100_et(mk):
    bot, ind = vwap_bot(), warmed(mk)
    out = signal_bars(bot, ind, mk, "10:57")       # third bar ends 11:00:00 ET
    assert not out.intents and bot.reason_code == "OUTSIDE_WINDOW"
    bot2, ind2 = vwap_bot(), warmed(mk)
    out = signal_bars(bot2, ind2, mk, "11:30")
    assert not out.intents and bot2.position is None


@pytest.mark.parametrize("kind", ["vwap", "ema50", "range"])
def test_every_bot_kind_refuses_entries_after_1100(kind, mk):
    bot = Bot("QQQ", BOT_SPECS[kind], {"vwap": VwapCross, "ema50": Ema50Cross5m, "range": RangeBreak}[kind](), LIVE)
    view = SimpleNamespace(ready=True, signal="CALL", charge_pct=100.0, distance_atr=0.0, reason_code=None, atr=None)
    ind = warmed(mk)
    assert bot._evaluate_flat(mk("QQQ", "10:59", 130), mk("QQQ", "10:59", 130).end, ind, view) == []
    assert bot.reason_code == "OUTSIDE_WINDOW"


def _enter_at_1059(bot, ind, mk):
    """Signal on the bar ending 10:59 ET (the last allowed entry), filled."""
    out = signal_bars(bot, ind, mk, "10:56")
    assert out.intents and out.intents[0].kind == "BUY_OPEN"
    bot.on_fill(Fill(bot.bot_id, "BUY_OPEN", "QQQ261009C00130000", 10, 3.00, "modeled", mk("QQQ", "10:58", 1).end))
    assert bot.state == State.MANAGING
    return bot.position


def test_position_open_at_1059_is_not_flattened_at_1100_or_after(mk):
    bot, ind = vwap_bot(), warmed(mk)
    p = _enter_at_1059(bot, ind, mk)
    hold = p.entry_und + 0.1   # between stop and target
    for hhmm in ("10:59", "11:00", "11:30", "13:00", "15:53"):   # bars ending 11:00, 11:01, 11:31, 13:01, 15:54 ET
        out = step(bot, ind, mk("QQQ", hhmm, hold))
        assert not out.intents and bot.position is p and bot.state == State.MANAGING and bot.reason_code == "HOLDING"


def test_held_position_still_exits_on_its_stop_after_1100(mk):
    bot, ind = vwap_bot(), warmed(mk)
    p = _enter_at_1059(bot, ind, mk)
    step(bot, ind, mk("QQQ", "10:59", p.entry_und + 0.1))
    out = step(bot, ind, mk("QQQ", "11:20", p.stop_und - 0.01))
    assert out.intents[0].kind == "SELL_CLOSE" and bot.reason_code == "EXIT_STOP"


def test_held_position_still_exits_on_its_target_after_1100(mk):
    bot, ind = vwap_bot(trail_enabled=False), warmed(mk)   # fixed-target exit mode
    p = _enter_at_1059(bot, ind, mk)
    step(bot, ind, mk("QQQ", "10:59", p.entry_und + 0.1))
    out = step(bot, ind, mk("QQQ", "11:20", p.target_und + 0.01))
    assert out.intents[0].kind == "SELL_CLOSE" and bot.reason_code == "EXIT_TARGET"


def test_held_position_is_flattened_at_1555_et_and_no_reentry(mk):
    bot, ind = vwap_bot(), warmed(mk)
    p = _enter_at_1059(bot, ind, mk)
    step(bot, ind, mk("QQQ", "10:59", p.entry_und + 0.1))
    out = step(bot, ind, mk("QQQ", "15:54", p.entry_und + 0.1))   # bar ends 15:55 ET
    assert out.intents[0].kind == "SELL_CLOSE" and bot.reason_code == "EXIT_TIME"
    bot.on_fill(Fill(bot.bot_id, "SELL_CLOSE", p.contract, 10, 3.0, "modeled", mk("QQQ", "15:54", 1).end))
    assert not step(bot, ind, mk("QQQ", "15:56", B + 9.0)).intents and bot.position is None


def test_times_are_eastern_even_for_a_utc_stamped_bar(mk):
    bot, ind = vwap_bot(), warmed(mk)
    p = _enter_at_1059(bot, ind, mk)
    def utc(hhmm):
        b = mk("QQQ", hhmm, p.entry_und + 0.1)
        return Bar("QQQ", b.ts.astimezone(timezone.utc), b.open, b.high, b.low, b.close, b.volume)
    assert not step(bot, ind, utc("10:59")).intents and bot.state == State.MANAGING     # 11:00 ET: no flatten
    out = step(bot, ind, utc("15:54"))                                                  # 15:55 ET: flatten
    assert out.intents[0].kind == "SELL_CLOSE" and bot.reason_code == "EXIT_TIME"
