from datetime import date, datetime, timedelta
from types import SimpleNamespace

from scalpcity.broker import ModeledBroker
from scalpcity.config import Settings
from scalpcity.engine import Engine
from scalpcity.events import EventLog
from scalpcity.live import LiveFeed
from scalpcity.types import Bar, ET

DAY = date(2026, 10, 9)


def bars(ticker, day, start_h, start_m, n, base):
    t0 = datetime(day.year, day.month, day.day, start_h, start_m, tzinfo=ET)
    return [Bar(ticker, t0 + timedelta(minutes=i), base + i * 0.01, base + i * 0.01 + 0.2, base + i * 0.01 - 0.2, base + i * 0.01 + 0.05, 1000.0)
            for i in range(n)]


def test_catch_up_rebuilds_vwap_and_range_without_trading_or_logging(tmp_path):
    log = EventLog(str(tmp_path), "live")
    eng = Engine(Settings(), log, ModeledBroker(), SimpleNamespace(get=lambda c, t: None))
    prior = {t: bars(t, date(2026, 10, 8), 9, 30, 200, 700.0) for t in ("QQQ", "SPY", "IWM")}
    eng.start_session(DAY, prior)
    todays = [b for t in ("QQQ", "SPY", "IWM") for b in bars(t, DAY, 9, 30, 20, 700.0)]   # 9:30-9:49 already happened
    eng.catch_up(todays)
    assert eng.ind["QQQ"].vwap.value is not None
    range_bot = eng.by_id["QQQ-RANGE"]
    assert range_bot.trigger.hi is not None and range_bot.trigger.lo is not None
    assert log.read(DAY) == [] and all(b.position is None for b in eng.bots)
    assert eng.ind["QQQ"].ema50.n == 200 + 20       # prior-session warm bars plus today's


class FakeBars:
    def __init__(self, rows): self.rows = rows
    def recent_bars(self, ticker, count): return list(self.rows[ticker])[-count:]


def test_live_feed_startup_splits_prior_from_today_and_marks_today_seen():
    rows = {t: bars(t, date(2026, 10, 8), 15, 0, 60, 700.0) + bars(t, DAY, 9, 30, 12, 700.0) for t in ("QQQ", "SPY", "IWM")}
    now = datetime(2026, 10, 9, 9, 42, 30, tzinfo=ET)          # the 9:41 bar (ends 9:42) is complete
    feed = LiveFeed(FakeBars(rows), ["QQQ", "SPY", "IWM"], lambda: now)
    prior, todays = feed.startup(DAY)
    assert all(b.ts.date() < DAY for b in prior["QQQ"]) and len(prior["QQQ"]) == 60
    assert len([b for b in todays if b.ticker == "QQQ"]) == 12      # 9:30..9:41, all complete
    assert [b.ts for b in todays] == sorted(b.ts for b in todays)
    assert feed.poll() == []                                    # nothing re-emitted
