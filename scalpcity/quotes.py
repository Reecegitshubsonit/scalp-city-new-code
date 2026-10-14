import json
import os
from datetime import datetime, timedelta
from typing import Protocol

from .contracts import underlying_of
from .types import ET, Quote


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


class SnapshotQuoteSource:
    """Replay quotes from the real Webull bid/ask the recorder saved (data/webull/DAY/snapshots.jsonl).

    For a decision at `ts` it takes the first snapshot within `after` of it (the live engine orders a few seconds
    after the bar ends, and the recorder snapshots right then), else the newest snapshot up to `before` earlier.
    No snapshot, a blank side or a zero bid/ask means no quote: the trade cannot be priced and is listed in
    `missing` ({(day, contract): first HH:MM asked}), never filled from candle closes.
    """

    def __init__(self, root: str, after: timedelta = timedelta(seconds=60), before: timedelta = timedelta(seconds=60)):
        self.root, self.after, self.before = root, after, before
        self._days: dict = {}
        self.missing: dict = {}

    def _load(self, day: str) -> list:
        if day not in self._days:
            rows = []
            path = os.path.join(self.root, day, "snapshots.jsonl")
            if os.path.exists(path):
                with open(path) as handle:
                    for line in handle:
                        snap = json.loads(line)
                        quotes = {s["symbol"]: (s.get("bid"), s.get("ask")) for s in snap.get("snapshots", [])}
                        rows.append((datetime.fromisoformat(snap["recorded_at"]), quotes))
            self._days[day] = sorted(rows, key=lambda r: r[0])
        return self._days[day]

    def get(self, contract: str, ts: datetime) -> Quote | None:
        day = ts.astimezone(ET).date().isoformat()
        rows = [(t, q[contract]) for t, q in self._load(day) if contract in q]
        later = [r for r in rows if ts <= r[0] <= ts + self.after]
        earlier = [r for r in rows if ts - self.before <= r[0] < ts]
        pick = later[0] if later else (earlier[-1] if earlier else None)
        bid = ask = 0.0
        if pick is not None:
            try:
                bid, ask = float(pick[1][0]), float(pick[1][1])
            except (TypeError, ValueError):
                pass
        if bid <= 0 or ask <= 0:
            self.missing.setdefault((day, contract), ts.astimezone(ET).strftime("%H:%M"))
            return None
        return Quote(contract, ts, round(bid, 2), round(ask, 2))
