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
        """Returns (prior-session warm bars, today's completed bars) and marks today's bars as already seen."""
        prior, todays = {}, []
        now = self.now_fn()
        for t in self.tickers:
            rows = self.client.recent_bars(t, count)
            prior[t] = [b for b in rows if b.ts.date() < today]
            done = [b for b in rows if b.ts.date() == today and b.end + timedelta(seconds=self.lag) <= now]
            todays += done
            if done:
                self.last_ts[t] = done[-1].ts
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

    def __init__(self, client):
        self.client = client

    def get(self, contract: str, ts: datetime):
        got = self.client.option_quote(contract)
        return got[0] if got else None
