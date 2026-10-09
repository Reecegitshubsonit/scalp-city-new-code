from datetime import datetime, timedelta
from typing import Protocol

from .contracts import underlying_of
from .types import Quote


class QuoteSource(Protocol):
    def get(self, contract: str, ts: datetime) -> Quote | None: ...


class BarQuoteSource:
    """Replay quotes from option trade bars: bid/ask = last close -/+ a modeled half-spread.

    `bars_for(contract, ts)` must return a list of (bar_start_ts, close) for that contract's day.
    A bar is usable once it has ended (start + 1 min <= ts); anything older than `max_age` is too stale.
    """

    def __init__(self, bars_for, half_spread: dict, max_age: timedelta = timedelta(minutes=5)):
        self.bars_for, self.half_spread, self.max_age = bars_for, half_spread, max_age

    def get(self, contract: str, ts: datetime) -> Quote | None:
        rows = self.bars_for(contract, ts) or []
        usable = [(t, c) for t, c in rows if t + timedelta(minutes=1) <= ts]
        if not usable:
            return None
        t, close = max(usable, key=lambda r: r[0])
        if ts - (t + timedelta(minutes=1)) > self.max_age:
            return None
        hs = self.half_spread.get(underlying_of(contract), 0.02)
        return Quote(contract, ts, round(max(0.01, close - hs), 2), round(close + hs, 2))
