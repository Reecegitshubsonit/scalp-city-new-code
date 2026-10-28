from datetime import datetime, timedelta

from .types import ET, Bar


class LiveFeed:
    """Polls Webull for recent one-minute bars and emits each completed bar once, in order."""

    def __init__(self, client, tickers, now_fn, lag_s: float = 2.0, count: int = 3):
        self.client, self.tickers, self.now_fn, self.lag, self.count = client, tickers, now_fn, lag_s, count
        self.last_ts: dict[str, datetime] = {}
        self.last_bar_wall: dict[str, datetime] = {}

    def warm_bars(self, count: int = 300) -> dict:
        return {t: self.client.recent_bars(t, count) for t in self.tickers}

    def startup(self, today, count: int = 600):
        """Returns (prior-session warm bars, today's completed bars) and marks every completed bar it fetched as already seen.

        Prior-session bars count as seen too: they go into the warm-up, so poll() must not hand them out again.
        (Before, a start before 9:30 or a day rollover left last_ts empty, and the first poll re-sent yesterday's
        last bars into the new session's VWAP and triggers.)"""
        prior, todays = {}, []
        now = self.now_fn()
        for t in self.tickers:
            rows = self.client.recent_bars(t, count)
            prior[t] = [b for b in rows if b.ts.date() < today]
            done = [b for b in rows if b.ts.date() == today and b.end + timedelta(seconds=self.lag) <= now]
            todays += done
            seen = [b.ts for b in rows if b.end + timedelta(seconds=self.lag) <= now]
            if seen:
                self.last_ts[t] = max(seen)
            if done:
                self.last_bar_wall[t] = now
        return prior, sorted(todays, key=lambda b: (b.ts, b.ticker))

    def poll(self) -> list[Bar]:
        now = self.now_fn()
        fresh: list[Bar] = []
        for t in self.tickers:
            for bar in self.client.recent_bars(t, self.count):
                if bar.end + timedelta(seconds=self.lag) > now:
                    continue  # still forming
                if t in self.last_ts and bar.ts <= self.last_ts[t]:
                    continue
                self.last_ts[t] = bar.ts
                self.last_bar_wall[t] = now
                fresh.append(bar)
        return sorted(fresh, key=lambda b: (b.ts, b.ticker))


def market_open(now: datetime) -> bool:
    t = now.astimezone(ET)
    return t.weekday() < 5 and (t.hour, t.minute) >= (9, 30) and t.hour < 16


class LiveQuoteSource:
    """Live option quotes straight from Webull; implements the QuoteSource protocol."""

    def __init__(self, client, now_fn=None, max_age_s: float = 30.0):
        self.client, self.max_age_s = client, max_age_s
        self.now_fn = now_fn or (lambda: datetime.now(ET))

    def get(self, contract: str, ts: datetime):
        """None (no trade) when Webull reports the quote as delayed or older than max_age_s: only live data is used."""
        got = self.client.option_quote(contract)
        if not got:
            return None
        quote, delay_minutes = got
        if delay_minutes > 0 or (self.now_fn() - quote.ts).total_seconds() > self.max_age_s:
            return None
        return quote
