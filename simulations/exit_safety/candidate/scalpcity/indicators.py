from .types import Bar


class Ema:
    def __init__(self, period: int):
        self.alpha = 2 / (period + 1)
        self.value: float | None = None
        self.n = 0

    def update(self, x: float) -> float:
        self.value = x if self.value is None else self.alpha * x + (1 - self.alpha) * self.value
        self.n += 1
        return self.value


class Atr:
    """Wilder ATR. Before `period` bars it is the plain average of true ranges so far."""

    def __init__(self, period: int = 14):
        self.period = period
        self.value: float | None = None
        self.prev_close: float | None = None
        self.n = 0
        self._trs: list[float] = []

    def update(self, bar: Bar) -> float:
        if self.prev_close is None:
            tr = bar.high - bar.low
        else:
            tr = max(bar.high - bar.low, abs(bar.high - self.prev_close), abs(bar.low - self.prev_close))
        self.prev_close = bar.close
        self.n += 1
        if self.n <= self.period:
            self._trs.append(tr)
            self.value = sum(self._trs) / len(self._trs)
        else:
            self.value = (self.value * (self.period - 1) + tr) / self.period
        return self.value


class SessionVwap:
    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.pv = 0.0
        self.v = 0.0
        self.value: float | None = None

    def update(self, bar: Bar) -> float:
        typical = (bar.high + bar.low + bar.close) / 3
        self.pv += typical * bar.volume
        self.v += bar.volume
        self.value = self.pv / self.v if self.v > 0 else typical
        return self.value


class IndicatorSet:
    def __init__(self, atr_period: int = 14):
        self.ema9, self.ema21, self.ema50 = Ema(9), Ema(21), Ema(50)
        self.atr = Atr(atr_period)
        self.vwap = SessionVwap()
        self.last_close: float | None = None

    def warm(self, bar: Bar) -> None:
        """Feed a previous-session bar: EMAs and ATR only, never VWAP."""
        self._core(bar)

    def update(self, bar: Bar) -> None:
        self._core(bar)
        self.vwap.update(bar)

    def _core(self, bar: Bar) -> None:
        for ema in (self.ema9, self.ema21, self.ema50):
            ema.update(bar.close)
        self.atr.update(bar)
        self.last_close = bar.close

    def new_session(self) -> None:
        self.vwap.reset()

    def squeezed(self, atr_mult: float) -> bool:
        if self.ema9.value is None or self.ema21.value is None or not self.atr.value:
            return False
        return abs(self.ema9.value - self.ema21.value) < atr_mult * self.atr.value

    def as_dict(self) -> dict:
        def r(x):
            return None if x is None else round(x, 4)
        return {"price": r(self.last_close), "vwap": r(self.vwap.value), "ema9": r(self.ema9.value),
                "ema21": r(self.ema21.value), "ema50": r(self.ema50.value), "atr": r(self.atr.value)}
