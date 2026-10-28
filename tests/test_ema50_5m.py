"""5-minute EMA50 bot, explicit side rules and the open/rollover re-feed fix."""
from dataclasses import replace
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace

from scalpcity.bot import Bot
from scalpcity.broker import ModeledBroker
from scalpcity.config import BOT_SPECS, Settings
from scalpcity.engine import Engine, build_bots
from scalpcity.events import EventLog
from scalpcity.indicators import IndicatorSet
from scalpcity.live import LiveFeed
from scalpcity.triggers import Ema50Cross5m, FiveMinBars, VwapCross
from scalpcity.types import ET, Bar

PREV, DAY = date(2026, 10, 8), date(2026, 10, 9)
S = Settings()


def at(day, h, m):
    return datetime(day.year, day.month, day.day, h, m, tzinfo=ET)


def bar(ts, close, high=None, low=None, volume=1000.0, ticker="QQQ", open_=None):
    return Bar(ticker, ts, close if open_ is None else open_, close if high is None else high, close if low is None else low, close, volume)


def flat_prior(n=300, price=100.0, ticker="QQQ"):
    """n quiet one-minute bars ending at 15:59 the day before, high/low +-0.25."""
    t0 = at(PREV, 15, 59) - timedelta(minutes=n - 1)
    return [bar(t0 + timedelta(minutes=i), price, price + 0.25, price - 0.25, ticker=ticker) for i in range(n)]


def feed(trig, ind, bars):
    views = []
    for b in bars:
        ind.update(b)
        views.append(trig.update(b, ind))
    return views


# ---- 5-minute aggregation ----

def test_five_minute_bars_aggregate_ohlcv_and_close_on_the_last_minute():
    agg = FiveMinBars()
    closed = []
    for i, (o, h, l, c) in enumerate([(10, 11, 9, 10.5), (10.5, 12, 10, 11), (11, 11.5, 8, 9), (9, 10, 8.5, 9.5), (9.5, 10, 9, 9.8),
                                      (9.8, 10, 9.7, 9.9)]):
        closed += agg.add(Bar("QQQ", at(DAY, 9, 30 + i), o, h, l, c, 100.0 * (i + 1)))
    assert len(closed) == 1
    b5, on_time = closed[0]
    assert on_time and b5.ts == at(DAY, 9, 30)
    assert (b5.open, b5.high, b5.low, b5.close, b5.volume) == (10, 12, 8, 9.8, 1500.0)
    assert agg.cur.ts == at(DAY, 9, 35) and agg.cur.close == 9.9   # 9:35 bucket still building


def test_bucket_missing_its_last_minute_closes_late_on_the_next_bucket():
    agg = FiveMinBars()
    out = [agg.add(bar(at(DAY, 9, 30 + i), 100 + i)) for i in range(4)]   # 9:30..9:33, the 9:34 bar never comes
    assert all(o == [] for o in out)
    late = agg.add(bar(at(DAY, 9, 35), 200))
    assert len(late) == 1 and late[0][1] is False and late[0][0].ts == at(DAY, 9, 30) and late[0][0].close == 103
    assert agg.add(bar(at(DAY, 9, 33), 1)) == []   # an older bar is ignored


# ---- 5-minute EMA50 cross ----

def warmed_trigger(prior=None):
    trig, ind = Ema50Cross5m(1.0), IndicatorSet()
    prior = flat_prior() if prior is None else prior
    for b in prior:
        ind.warm(b)
    trig.warm_up(prior)
    return trig, ind


def test_warm_up_alone_is_not_ready_and_needs_50_five_minute_bars():
    trig, ind = warmed_trigger(flat_prior(n=245))   # 49 five-minute bars
    views = feed(trig, ind, [bar(at(DAY, 9, 30 + i), 100) for i in range(10)])
    assert trig.ema.n == 49 + 2 and views[3].ready is False   # not ready while the EMA has < 50 bars
    trig, ind = warmed_trigger()                    # 60 five-minute bars
    views = feed(trig, ind, [bar(at(DAY, 9, 30 + i), 100) for i in range(5)])
    assert [v.ready for v in views] == [False] * 4 + [True]   # ready only once today's first 5-minute bar closes
    assert views[4].reason_code is None


def test_gap_from_yesterday_never_counts_as_a_cross():
    prior = flat_prior()[:-1] + [bar(at(PREV, 15, 59), 99.0, 99.25, 98.75)]   # yesterday closed below EMA50
    trig, ind = warmed_trigger(prior)
    views = feed(trig, ind, [bar(at(DAY, 9, 30 + i), 103) for i in range(10)])   # gaps up above it and stays
    assert all(v.signal is None for v in views)


def test_cross_fires_only_on_the_completed_five_minute_close_in_its_own_direction():
    trig, ind = warmed_trigger()
    below = [bar(at(DAY, 9, 30 + i), 99.5) for i in range(5)]            # first 5-min close below EMA50 (~100)
    # 9:35-9:39: the 9:36 one-minute close pokes above the EMA but the 5-minute bar is not done yet
    up = [bar(at(DAY, 9, 35), 99.6), bar(at(DAY, 9, 36), 101.0), bar(at(DAY, 9, 37), 100.8), bar(at(DAY, 9, 38), 100.9), bar(at(DAY, 9, 39), 101.2)]
    views = feed(trig, ind, below + up)
    assert [v.signal for v in views[:9]] == [None] * 9
    assert views[9].signal == "CALL" and views[9].charge_pct == 100.0
    assert views[9].atr == trig.atr.value and trig.atr.value > ind.atr.value   # 5-minute ATR, wider than the 1-minute one
    down = [bar(at(DAY, 9, 40 + i), 98.0) for i in range(5)]
    views = feed(trig, ind, down)
    assert [v.signal for v in views] == [None] * 4 + ["PUT"]


def test_late_closed_bucket_updates_the_ema_but_never_fires():
    trig, ind = warmed_trigger()
    feed(trig, ind, [bar(at(DAY, 9, 30 + i), 99.5) for i in range(5)])
    feed(trig, ind, [bar(at(DAY, 9, 35 + i), 101.5) for i in range(4)])   # 9:39 bar missing (feed gap)
    n = trig.ema.n
    views = feed(trig, ind, [bar(at(DAY, 9, 40), 101.5)])
    assert trig.ema.n == n + 1 and views[0].signal is None


# ---- side rules ----

def falling_ind():
    """EMA9 well below EMA21 (downtrend) so a 'trend' bot would buy PUTs."""
    ind = IndicatorSet()
    for i in range(60):
        c = 250.0 - 2.0 * i
        ind.warm(bar(at(PREV, 14, 0) + timedelta(minutes=i), c, c + 0.5, c - 0.5))
    return ind


def test_own_side_trades_the_cross_even_against_the_trend_and_trend_side_fades_it():
    for side, want in (("own", "CALL"), ("trend", "PUT")):
        ind = falling_ind()
        last = 250.0 - 2.0 * 59
        bot = Bot("QQQ", replace(BOT_SPECS["vwap"], side=side, chop_filter=False), VwapCross(1.0), S)
        for m, c in ((30, last - 1.0), (31, last - 1.5), (32, last + 1.0)):   # closes up through VWAP at 9:32
            b = bar(at(DAY, 9, m), c)
            ind.update(b)
            out = bot.on_bar(b, ind)
        assert ind.ema9.value < ind.ema21.value
        assert [i.right for i in out.intents] == [want], side
        assert f"{side} side" in bot.reason_text and "CALL trigger" in bot.reason_text


def ema50_session(start_h=9, start_m=30, minutes=40, cross_at=None):
    """Run the real EMA50 spec/bot through a session: below EMA50 until `cross_at` (bar start), then above."""
    bot = [b for b in build_bots(S) if b.bot_id == "QQQ-EMA50"][0]
    bot.trigger.warm_up(flat_prior())
    ind = falling_ind()   # 1-minute EMA9 < EMA21 the whole time, so a 'trend' rule would say PUT
    fired = []
    t = at(DAY, start_h, start_m)
    for i in range(minutes):
        ts = t + timedelta(minutes=i)
        c = 101.5 if cross_at is not None and ts >= cross_at else 99.5
        b = bar(ts, c, c + 0.2, c - 0.2)
        ind.update(bar(ts, 100.0 - 0.5 * i))   # the 1-minute indicators keep falling; the trigger only reads the bar
        out = bot.on_bar(b, ind)
        fired += [(ts, x) for x in out.intents]
        if out.intents:
            break
    return bot, ind, fired


def test_ema50_bot_buys_the_call_on_an_up_cross_with_5_minute_atr_stops():
    bot, ind, fired = ema50_session(10, 0, 30, cross_at=at(DAY, 10, 10))
    assert ind.ema9.value < ind.ema21.value          # 1-minute trend is down
    assert len(fired) == 1
    ts, intent = fired[0]
    assert ts == at(DAY, 10, 14) and intent.right == "CALL"   # the 10:10-10:14 five-minute bar closes above EMA50
    p = bot.position
    atr5 = bot.trigger.atr.value
    assert abs((p.entry_und - p.stop_und) - S.stop_atr * atr5) < 1e-9 and abs((p.target_und - p.entry_und) - S.target_atr * atr5) < 1e-9


def test_ema50_bot_takes_no_entry_before_10_or_after_10_59():
    _, _, fired = ema50_session(9, 30, 30, cross_at=at(DAY, 9, 40))   # cross at 9:44 close: before the window
    assert fired == []
    bot, _, fired = ema50_session(10, 50, 20, cross_at=at(DAY, 11, 0))   # cross at the 11:04 close: after it
    assert fired == [] and bot.reason_code == "OUTSIDE_WINDOW"


# ---- open / rollover re-feed (bug A) ----

class FakeBars:
    def __init__(self, rows): self.rows = rows
    def recent_bars(self, ticker, count): return list(self.rows[ticker])[-count:]


def test_pre_open_start_does_not_resend_yesterdays_last_bars_at_the_first_poll():
    rows = {t: flat_prior(60, ticker=t) for t in ("QQQ", "SPY", "IWM")}
    clock = {"now": at(DAY, 9, 20)}
    lf = LiveFeed(FakeBars(rows), ["QQQ", "SPY", "IWM"], lambda: clock["now"])
    prior, todays = lf.startup(DAY)
    assert todays == [] and len(prior["QQQ"]) == 60
    for t in rows:
        rows[t] = rows[t] + [bar(at(DAY, 9, 30), 101.0, ticker=t)]
    clock["now"] = at(DAY, 9, 31) + timedelta(seconds=5)
    got = lf.poll()   # recent_bars(count=3) returns 15:58, 15:59 and 9:30; only 9:30 is new
    assert sorted((b.ticker, b.ts) for b in got) == sorted((t, at(DAY, 9, 30)) for t in rows)


def test_day_rollover_in_a_long_running_engine_does_not_resend_yesterdays_bars():
    rows = {t: flat_prior(60, ticker=t) for t in ("QQQ", "SPY", "IWM")}
    clock = {"now": at(PREV, 15, 59) + timedelta(minutes=1, seconds=5)}
    lf = LiveFeed(FakeBars(rows), ["QQQ", "SPY", "IWM"], lambda: clock["now"])
    lf.startup(PREV)
    lf.last_ts.clear(); lf.last_bar_wall.clear()      # what run_live does at midnight
    clock["now"] = datetime(2026, 10, 9, 0, 0, 5, tzinfo=ET)
    lf.startup(DAY)
    for t in rows:
        rows[t] = rows[t] + [bar(at(DAY, 9, 30), 101.0, ticker=t)]
    clock["now"] = at(DAY, 9, 31) + timedelta(seconds=5)
    assert sorted(b.ts for b in lf.poll()) == [at(DAY, 9, 30)] * 3


def test_engine_ignores_a_previous_sessions_bar_after_start_session(tmp_path):
    eng = Engine(S, EventLog(str(tmp_path), "live"), ModeledBroker(), SimpleNamespace(get=lambda c, t: None))
    eng.start_session(DAY, {t: flat_prior(300, ticker=t) for t in ("QQQ", "SPY", "IWM")})
    n = eng.ind["QQQ"].ema9.n
    eng.on_bar(bar(at(PREV, 15, 59), 90.0))
    assert eng.ind["QQQ"].ema9.n == n and eng.ind["QQQ"].vwap.value is None and EventLog(str(tmp_path), "live").read(PREV) == []
    eng.on_bar(bar(at(DAY, 9, 30), 101.0))
    assert eng.ind["QQQ"].ema9.n == n + 1 and eng.ind["QQQ"].vwap.value is not None


def test_engine_start_session_warms_the_5_minute_trigger_and_restart_rebuilds_its_stop(tmp_path):
    eng = Engine(S, EventLog(str(tmp_path), "live"), ModeledBroker(), SimpleNamespace(get=lambda c, t: None))
    eng.start_session(DAY, {t: flat_prior(300, ticker=t) for t in ("QQQ", "SPY", "IWM")})
    assert eng.by_id["QQQ-EMA50"].trigger.ema.n == 60
    t = at(DAY, 10, 15).isoformat()
    eng.recover([{"seq": 1, "time": t, "bot": "QQQ-EMA50", "ticker": "QQQ", "kind": "order_sent", "reason_code": "BUY_OPEN",
                  "contract": "QQQ261012C00100000", "qty": 10, "inputs": {"price": 100.0, "atr": 0.1}, "stop_und": 99.2, "target_und": 101.6},
                 {"seq": 2, "time": t, "bot": "QQQ-EMA50", "ticker": "QQQ", "kind": "fill", "reason_code": "ENTRY_FILL",
                  "contract": "QQQ261012C00100000", "qty": 10, "fill_price": 1.5}])
    p = eng.by_id["QQQ-EMA50"].position
    assert (p.stop_und, p.target_und) == (99.2, 101.6)   # the logged 5-minute-ATR levels, not 1-minute ATR
