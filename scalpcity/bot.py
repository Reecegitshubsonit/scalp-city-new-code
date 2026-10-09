from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from .config import BotSpec, Settings
from .indicators import IndicatorSet
from .types import Bar, Fill, OrderIntent


class State(str, Enum):
    IDLE = "idle"
    FORMING = "forming"
    FIRED = "fired"
    MANAGING = "managing"
    EXITING = "exiting"
    COOLDOWN = "cooldown"
    LOCKED = "locked"
    PAUSED = "paused"
    STALE = "stale"


@dataclass
class Position:
    right: str
    qty: int
    entry_und: float
    stop_und: float
    target_und: float
    contract: str | None = None
    entry_price: float | None = None
    opened_at: datetime | None = None


@dataclass
class BotOutput:
    events: list = field(default_factory=list)   # dicts: kind, state, reason_code, reason_text, inputs, charge_pct, extras
    intents: list = field(default_factory=list)  # OrderIntent


class Bot:
    def __init__(self, ticker: str, spec: BotSpec, trigger, settings: Settings):
        self.ticker, self.spec, self.trigger, self.s = ticker, spec, trigger, settings
        self.bot_id = f"{ticker}-{spec.trigger.upper()}"
        self.state, self.reason_code, self.reason_text = State.IDLE, "OUTSIDE_WINDOW", ""
        self._last_emitted: tuple | None = None
        self.paused = False
        self.stale = False
        self.new_session()

    # ---- session ----
    def new_session(self) -> None:
        self.position: Position | None = None
        self.pending: str | None = None  # "entry" | "exit"
        self.cooldown_until: datetime | None = None
        self.locked: str | None = None   # DAILY_GOAL | DAILY_LOSS
        self.pnl_day = 0.0
        self.trades = 0
        self.trigger.new_session()
        self.state, self.reason_code, self.reason_text = State.IDLE, "OUTSIDE_WINDOW", ""
        self._last_emitted = None

    # ---- helpers ----
    def _set(self, state: State, code: str, text: str) -> None:
        self.state, self.reason_code, self.reason_text = state, code, text

    def _snapshot_event(self, kind, inputs, charge_pct, **extra) -> dict:
        return {"kind": kind, "state": self.state.value, "reason_code": self.reason_code,
                "reason_text": self.reason_text, "inputs": inputs, "charge_pct": charge_pct, **extra}

    def _finish(self, inputs: dict, charge_pct, intents: list) -> BotOutput:
        out = BotOutput(intents=intents)
        key = (self.state, self.reason_code)
        if key != self._last_emitted:
            out.events.append(self._snapshot_event("state_change", inputs, charge_pct))
            self._last_emitted = key
        out.events.append(self._snapshot_event("tick", inputs, charge_pct))
        return out

    # ---- per bar ----
    def on_bar(self, bar: Bar, ind: IndicatorSet) -> BotOutput:
        now = bar.end
        view = self.trigger.update(bar, ind)
        inputs = ind.as_dict()
        inputs["distance_atr"] = view.distance_atr
        intents: list[OrderIntent] = []
        if self.position is not None:
            if self.pending is None:
                intents += self._manage(bar, now, ind)
        elif self.pending is None:
            intents += self._evaluate_flat(bar, now, ind, view)
        return self._finish(inputs, view.charge_pct, intents)

    def _evaluate_flat(self, bar: Bar, now: datetime, ind: IndicatorSet, view) -> list:
        t = now.time()
        if self.locked:
            self._set(State.LOCKED, self.locked, f"locked for the day, day P&L {self.pnl_day:+.0f}")
        elif self.paused:
            self._set(State.PAUSED, "PAUSED", "paused by user; no new entries")
        elif self.stale:
            self._set(State.STALE, "STALE_DATA", "no fresh data")
        elif t < self.spec.arm:
            self._set(State.IDLE, "OUTSIDE_WINDOW", f"before {self.spec.arm:%H:%M}")
        elif t < self.spec.start:
            self._set(State.IDLE, "RANGE_FORMING", f"armed, range forming until {self.spec.start:%H:%M}")
        elif t > self.s.last_entry:
            self._set(State.IDLE, "OUTSIDE_WINDOW", f"after last entry {self.s.last_entry:%H:%M}")
        elif not view.ready:
            self._set(State.IDLE, view.reason_code or "NOT_READY", "waiting for indicator or range")
        elif self.cooldown_until is not None and now < self.cooldown_until:
            self._set(State.COOLDOWN, "COOLDOWN", f"cooldown until {self.cooldown_until:%H:%M:%S}")
        elif self.spec.chop_filter and ind.squeezed(self.s.squeeze_atr):
            self._set(State.IDLE, "CHOP_SQUEEZE", "EMA9 and EMA21 squeezed, skipping")
        elif view.signal:
            return self._fire(bar, ind, view.signal)
        elif view.charge_pct is not None and view.charge_pct >= self.s.forming_min_charge:
            self._set(State.FORMING, "WATCHING", f"{view.distance_atr} ATR from trigger, {view.charge_pct:.0f}% charged")
        else:
            self._set(State.IDLE, "WATCHING", f"{view.distance_atr} ATR from trigger" if view.distance_atr is not None else "watching")
        return []

    def _fire(self, bar: Bar, ind: IndicatorSet, side: str) -> list:
        atr = ind.atr.value or 0.0
        sgn = 1 if side == "CALL" else -1
        self.position = Position(side, self.s.contracts, bar.close,
                                 stop_und=bar.close - sgn * self.s.stop_atr * atr,
                                 target_und=bar.close + sgn * self.s.target_atr * atr)
        self.pending = "entry"
        self._set(State.FIRED, "SIGNAL", f"{side} signal at {bar.close:.2f}")
        return [OrderIntent(self.bot_id, self.ticker, "BUY_OPEN", side, self.s.contracts, "signal", bar.close)]

    def _manage(self, bar: Bar, now: datetime, ind: IndicatorSet) -> list:
        p = self.position
        sgn = 1 if p.right == "CALL" else -1
        why = None
        if now.time() >= self.s.flat_by:
            why = "TIME"
        elif sgn * (bar.close - p.stop_und) <= 0:
            why = "STOP"
        elif sgn * (bar.close - p.target_und) >= 0:
            why = "TARGET"
        if why:
            self.pending = "exit"
            self._set(State.EXITING, f"EXIT_{why}", f"closing {p.right}: {why.lower()}")
            return [OrderIntent(self.bot_id, self.ticker, "SELL_CLOSE", p.right, p.qty, why, bar.close, contract=p.contract)]
        self._set(State.MANAGING, "HOLDING", f"{p.right} held, stop {p.stop_und:.2f}, target {p.target_und:.2f}")
        return []

    # ---- broker results ----
    def on_fill(self, fill: Fill, inputs: dict | None = None) -> list:
        inputs = inputs or {}
        p = self.position
        if fill.kind == "BUY_OPEN":
            p.contract, p.entry_price, p.opened_at = fill.contract, fill.price, fill.ts
            self.pending = None
            self._set(State.MANAGING, "HOLDING", f"{p.right} filled at {fill.price:.2f}")
            self._last_emitted = (self.state, self.reason_code)
            return [self._snapshot_event("state_change", inputs, None),
                    {"kind": "fill", "state": self.state.value, "reason_code": "ENTRY_FILL", "reason_text": f"bought {fill.qty} {fill.contract} @ {fill.price:.2f} ({fill.source})",
                     "inputs": inputs, "charge_pct": None, "contract": fill.contract, "qty": fill.qty, "fill_price": fill.price, "fill_source": fill.source}]
        pnl = round((fill.price - p.entry_price) * fill.qty * 100, 2)
        self.pnl_day = round(self.pnl_day + pnl, 2)
        self.trades += 1
        self.position, self.pending = None, None
        self.cooldown_until = fill.ts + timedelta(seconds=self.s.cooldown_s)
        if self.pnl_day >= self.s.daily_goal:
            self.locked = "DAILY_GOAL"
        elif self.pnl_day <= -self.s.daily_loss:
            self.locked = "DAILY_LOSS"
        if self.locked:
            self._set(State.LOCKED, self.locked, f"locked for the day, day P&L {self.pnl_day:+.0f}")
        else:
            self._set(State.COOLDOWN, "COOLDOWN", f"cooldown until {self.cooldown_until:%H:%M:%S}")
        self._last_emitted = (self.state, self.reason_code)
        return [{"kind": "fill", "state": self.state.value, "reason_code": "EXIT_FILL", "reason_text": f"sold {fill.qty} {fill.contract} @ {fill.price:.2f} ({fill.source})",
                 "inputs": inputs, "charge_pct": None, "contract": fill.contract, "qty": fill.qty, "fill_price": fill.price, "fill_source": fill.source},
                {"kind": "trade_closed", "state": self.state.value, "reason_code": self.reason_code, "reason_text": f"trade P&L {pnl:+.2f}, day {self.pnl_day:+.2f}",
                 "inputs": inputs, "charge_pct": None, "pnl": pnl, "pnl_day": self.pnl_day, "trades": self.trades},
                self._snapshot_event("state_change", inputs, None)]

    def on_order_failed(self, kind: str, reason: str) -> list:
        if kind == "BUY_OPEN":
            self.position, self.pending = None, None
            self._set(State.IDLE, "ORDER_FAILED", f"entry not filled: {reason}")
        else:
            self.pending = None
            self._set(State.MANAGING, "EXIT_RETRY", f"exit not filled ({reason}); retrying next bar")
        self._last_emitted = (self.state, self.reason_code)
        return [self._snapshot_event("state_change", {}, None)]

    # ---- controls ----
    def set_paused(self, paused: bool) -> list:
        self.paused = paused
        if self.position is None and self.pending is None and not self.locked:
            if paused:
                self._set(State.PAUSED, "PAUSED", "paused by user; no new entries")
            else:
                self._set(State.IDLE, "WATCHING", "resumed")
            self._last_emitted = (self.state, self.reason_code)
        return [{"kind": "control", "state": self.state.value, "reason_code": self.reason_code, "reason_text": "paused" if paused else "resumed",
                 "inputs": {}, "charge_pct": None, "paused": paused}]

    def set_stale(self, stale: bool, text: str = "") -> list:
        if stale == self.stale:
            return []
        self.stale = stale
        if stale and self.position is None and self.pending is None and not self.locked:
            self._set(State.STALE, "STALE_DATA", text or "no fresh data")
            self._last_emitted = (self.state, self.reason_code)
        return [{"kind": "feed_stale" if stale else "feed_fresh", "state": self.state.value, "reason_code": "STALE_DATA" if stale else "FEED_OK",
                 "reason_text": text or ("data stale" if stale else "data fresh"), "inputs": {}, "charge_pct": None}]
