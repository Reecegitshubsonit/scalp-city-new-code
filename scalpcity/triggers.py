from dataclasses import dataclass
from datetime import time, timedelta

from .indicators import Atr, Ema, IndicatorSet
from .types import Bar


@dataclass(frozen=True)
class TriggerView:
    signal: str | None = None  # "CALL" | "PUT"
    charge_pct: float | None = None
    distance_atr: float | None = None
    reason_code: str | None = None  # why not ready: WARMING_UP / RANGE_FORMING / NO_RANGE
    ready: bool = True
    atr: float | None = None  # ATR the trigger works in, used for stop/target; None = the 1-minute ATR
    reason_text: str | None = None


def charge(dist_atr: float, range_atr: float) -> float:
    """0-100: 100 at the trigger, 0 at range_atr ATR away. 0.6 ATR with range 1.0 -> 40."""
    return round(max(0.0, min(1.0, 1 - dist_atr / range_atr)) * 100, 1)


@dataclass
class _RetrySide:
    failed: bool = False
    armed: bool = False
    closes: int = 0
    non_signal: bool = False


class _BreakoutMemory:
    """Session-local, independent CALL/PUT failures. Only a target or new session clears failure.

    A rejection/stop needs a return to the non-signal side before counting two closes.
    Confirmation consumes the arm, so remaining outside never repeatedly fires entries.
    """

    def __init__(self):
        self.sides = {side: _RetrySide() for side in ("CALL", "PUT")}

    def fail(self, side):
        state = self.sides[side]
        state.failed, state.armed, state.closes = True, state.non_signal, 0

    def clear(self, side):
        state = self.sides[side]
        self.sides[side] = _RetrySide(non_signal=state.non_signal)

    def observe(self, side, *, beyond, non_signal, rejection, fresh):
        state = self.sides[side]
        state.non_signal = non_signal
        if rejection:
            self.fail(side)
        if not state.failed:
            return fresh, None
        if non_signal:
            state.armed, state.closes = True, 0
        elif not beyond:
            state.closes = 0
        elif state.armed:
            state.closes += 1
            if state.closes == 2:
                state.armed, state.closes = False, 0
                return True, None
        if beyond:
            text = (f"{side} failed-breakout retry blocked: {state.closes}/2 consecutive closes beyond level"
                    if state.armed else f"{side} failed-breakout retry blocked: return to non-signal side to re-arm")
            return False, text
        if rejection:
            return False, f"{side} wick rejection: marked failed; next attempt needs re-arm and two closes"
        return False, None


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

    def __init__(self, charge_range_atr: float = 1.0):
        super().__init__(charge_range_atr)
        self.new_session()

    def new_session(self):
        super().new_session()
        self.memory = _BreakoutMemory()

    def on_trade_exit(self, side, reason):
        if reason == "STOP":
            self.memory.fail(side)
        elif reason == "TARGET":
            self.memory.clear(side)

    def level(self, ind):
        return ind.vwap.value

    def update(self, bar, ind):
        view = super().update(bar, ind)
        lvl = self.level(ind)
        if lvl is None:
            return view
        signal, reason = None, None
        for side in ("CALL", "PUT"):
            beyond = bar.close > lvl if side == "CALL" else bar.close < lvl
            # VWAP moves: compare each close with that bar's VWAP, not a frozen entry VWAP.
            non_signal = bar.close <= lvl if side == "CALL" else bar.close >= lvl
            rejection = (bar.high > lvl if side == "CALL" else bar.low < lvl) and non_signal
            fire, blocked = self.memory.observe(side, beyond=beyond, non_signal=non_signal,
                                                rejection=rejection, fresh=view.signal == side)
            if fire:
                signal = side
            reason = blocked or reason
        return TriggerView(signal=signal, charge_pct=100.0 if signal else view.charge_pct,
                           distance_atr=view.distance_atr,
                           reason_code="FAILED_BREAKOUT_HOLD" if reason and not signal else None,
                           reason_text=reason if not signal else None)


class Ema50Cross(_LevelCross):
    name = "ema50"

    def level(self, ind):
        return ind.ema50.value if ind.ema50.n >= 50 else None


class RangeBreak:
    """First-15-minute range (bars starting 9:30..9:44).

    An unfailed side keeps the inside-to-outside rule. A failed side instead fires on
    its second consecutive outside close after returning inside, even though the
    previous close is now outside (and the original crossing rule would miss it).
    """
    name = "range"

    def __init__(self, charge_range_atr: float = 1.0, start: time = time(9, 30), end: time = time(9, 45)):
        self.rng, self.start, self.end = charge_range_atr, start, end
        self.new_session()

    def new_session(self) -> None:
        self.hi: float | None = None
        self.lo: float | None = None
        self.prev_close: float | None = None
        self.memory = _BreakoutMemory()

    def on_trade_exit(self, side, reason):
        if reason == "STOP":
            self.memory.fail(side)
        elif reason == "TARGET":
            self.memory.clear(side)

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
        sig, reason = None, None
        for side, beyond, rejection in (
            ("CALL", bar.close > self.hi, bar.high > self.hi and inside),
            ("PUT", bar.close < self.lo, bar.low < self.lo and inside),
        ):
            fire, blocked = self.memory.observe(side, beyond=beyond, non_signal=inside,
                                                rejection=rejection, fresh=prev_inside and beyond)
            if fire:
                sig = side
            reason = blocked or reason
        self.prev_close = bar.close
        if inside:
            dist = min(self.hi - bar.close, bar.close - self.lo) / atr if atr > 0 else 0.0
            pct = charge(dist, self.rng)
        else:
            dist, pct = 0.0, (100.0 if sig else 0.0)
        return TriggerView(signal=sig, charge_pct=pct, distance_atr=round(dist, 3),
                           reason_code="FAILED_BREAKOUT_HOLD" if reason and not sig else None,
                           reason_text=reason if not sig else None)


class FiveMinBars:
    """Builds 5-minute bars (9:30-9:34, 9:35-9:39, ...) from completed 1-minute bars.

    add() returns the 5-minute bars it closed as (bar, on_time). A bucket closes on time when its last minute
    (:x4 / :x9) arrives. If that minute never comes (feed gap), the bucket is closed late, on_time=False,
    when the first bar of a later bucket shows up. Bars older than the bucket being built are ignored.
    """

    def __init__(self):
        self.cur: Bar | None = None

    def add(self, bar: Bar) -> list:
        start = bar.ts.replace(second=0, microsecond=0) - timedelta(minutes=bar.ts.minute % 5)
        out = []
        if self.cur is not None and start != self.cur.ts:
            if start < self.cur.ts:
                return out
            out.append((self.cur, False))
            self.cur = None
        c = self.cur
        self.cur = Bar(bar.ticker, start, bar.open, bar.high, bar.low, bar.close, bar.volume) if c is None else \
            Bar(bar.ticker, start, c.open, max(c.high, bar.high), min(c.low, bar.low), bar.close, c.volume + bar.volume)
        if bar.ts.minute % 5 == 4:
            out.append((self.cur, True))
            self.cur = None
        return out


class Ema50Cross5m:
    """Close-vs-EMA50 cross on completed 5-minute bars, with a 5-minute ATR(14) for distance, stop and target.

    EMA50 and ATR warm on prior-session bars (warm_up), but a cross needs two 5-minute closes from this session:
    yesterday's last close is never compared with today's first, so an overnight gap cannot fire it. A signal comes
    only on the 1-minute bar that completes a 5-minute bar on time; a bucket closed late after a feed gap updates
    the EMA and ATR but never fires.
    """
    name = "ema50"

    def __init__(self, charge_range_atr: float = 1.0, period: int = 50, atr_period: int = 14):
        self.rng, self.period, self.atr_period = charge_range_atr, period, atr_period
        self.ema, self.atr = Ema(period), Atr(atr_period)
        self.new_session()

    def warm_up(self, bars) -> None:
        """Start over from prior-session 1-minute bars (oldest first): EMA50 and ATR only, never a signal."""
        self.ema, self.atr = Ema(self.period), Atr(self.atr_period)
        self.bars = FiveMinBars()
        for bar in bars:
            for b5, _ in self.bars.add(bar):
                self._fold(b5)
        self.new_session()

    def new_session(self) -> None:
        self.bars = FiveMinBars()   # drop a half-built bucket from the previous session
        self.prev: tuple | None = None   # (close, level) of this session's last completed 5-minute bar

    def _fold(self, b5: Bar) -> float:
        self.atr.update(b5)
        return self.ema.update(b5.close)

    def _view(self, close: float, sig: str | None) -> TriggerView:
        atr = self.atr.value or 0.0
        dist = abs(close - self.ema.value) / atr if atr > 0 else 0.0
        return TriggerView(signal=sig, charge_pct=100.0 if sig else charge(dist, self.rng), distance_atr=round(dist, 3), atr=atr or None)

    def update(self, bar: Bar, ind: IndicatorSet) -> TriggerView:
        sig = None
        for b5, on_time in self.bars.add(bar):
            lvl = self._fold(b5)
            if on_time and self.prev is not None and self.ema.n >= self.period:
                pc, pl = self.prev
                if pc < pl and b5.close > lvl:
                    sig = "CALL"
                elif pc > pl and b5.close < lvl:
                    sig = "PUT"
            self.prev = (b5.close, lvl)
        if self.ema.n < self.period or self.prev is None:
            return TriggerView(ready=False, reason_code="WARMING_UP")
        return self._view(bar.close, sig)
