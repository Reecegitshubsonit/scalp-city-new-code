from dataclasses import dataclass
from datetime import time

from .indicators import IndicatorSet
from .types import Bar


@dataclass(frozen=True)
class TriggerView:
    signal: str | None = None  # "CALL" | "PUT"
    charge_pct: float | None = None
    distance_atr: float | None = None
    reason_code: str | None = None  # why not ready: WARMING_UP / RANGE_FORMING / NO_RANGE
    ready: bool = True


def charge(dist_atr: float, range_atr: float) -> float:
    """0-100: 100 at the trigger, 0 at range_atr ATR away. 0.6 ATR with range 1.0 -> 40."""
    return round(max(0.0, min(1.0, 1 - dist_atr / range_atr)) * 100, 1)


class _LevelCross:
    name = "level"

    def __init__(self, charge_range_atr: float = 1.0):
        self.rng = charge_range_atr
        self.prev_close: float | None = None
        self.prev_level: float | None = None

    def level(self, ind: IndicatorSet) -> float | None:
        raise NotImplementedError

    def new_session(self) -> None:
        self.prev_close = None
        self.prev_level = None

    def update(self, bar: Bar, ind: IndicatorSet) -> TriggerView:
        lvl = self.level(ind)
        if lvl is None:
            return TriggerView(ready=False, reason_code="WARMING_UP")
        atr = ind.atr.value or 0.0
        dist = abs(bar.close - lvl) / atr if atr > 0 else 0.0
        sig = None
        if self.prev_close is not None and self.prev_level is not None:
            if self.prev_close < self.prev_level and bar.close > lvl:
                sig = "CALL"
            elif self.prev_close > self.prev_level and bar.close < lvl:
                sig = "PUT"
        self.prev_close, self.prev_level = bar.close, lvl
        return TriggerView(signal=sig, charge_pct=100.0 if sig else charge(dist, self.rng), distance_atr=round(dist, 3))


class VwapCross(_LevelCross):
    name = "vwap"

    def level(self, ind):
        return ind.vwap.value


class Ema50Cross(_LevelCross):
    name = "ema50"

    def level(self, ind):
        return ind.ema50.value if ind.ema50.n >= 50 else None


class RangeBreak:
    """First-15-minute range (bars starting 9:30..9:44). Signal on a close that moves from inside to outside."""
    name = "range"

    def __init__(self, charge_range_atr: float = 1.0, start: time = time(9, 30), end: time = time(9, 45)):
        self.rng, self.start, self.end = charge_range_atr, start, end
        self.new_session()

    def new_session(self) -> None:
        self.hi: float | None = None
        self.lo: float | None = None
        self.prev_close: float | None = None

    def update(self, bar: Bar, ind: IndicatorSet) -> TriggerView:
        t = bar.ts.time()
        if self.start <= t < self.end:
            self.hi = bar.high if self.hi is None else max(self.hi, bar.high)
            self.lo = bar.low if self.lo is None else min(self.lo, bar.low)
            self.prev_close = bar.close
            return TriggerView(ready=False, reason_code="RANGE_FORMING")
        if self.hi is None:
            return TriggerView(ready=False, reason_code="NO_RANGE")
        atr = ind.atr.value or 0.0
        inside = self.lo <= bar.close <= self.hi
        prev_inside = self.prev_close is not None and self.lo <= self.prev_close <= self.hi
        sig = None
        if prev_inside and bar.close > self.hi:
            sig = "CALL"
        elif prev_inside and bar.close < self.lo:
            sig = "PUT"
        self.prev_close = bar.close
        if inside:
            dist = min(self.hi - bar.close, bar.close - self.lo) / atr if atr > 0 else 0.0
            pct = charge(dist, self.rng)
        else:
            dist, pct = 0.0, (100.0 if sig else 0.0)
        return TriggerView(signal=sig, charge_pct=pct, distance_atr=round(dist, 3))
