# Scalp City Engine Implementation Plan (phases 0-3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build nine paper-trading options bots (VWAP-cross, EMA50-cross, 15-minute range-break on QQQ, SPY, IWM) with an append-only event log, replay, Webull sandbox live feed and paper orders, a risk gate, an API server, and a plain table dashboard that shows what every bot is doing and why.

**Architecture:** A Python engine runs nine pure state-machine bots. Every state change is appended to one event-log file per trading day, which is the single source of truth. A risk gate is the only path to the broker. A FastAPI server streams the log over WebSocket to a browser view. Replay and live share the same engine and event shapes.

**Tech Stack:** Python 3.11 (project-local `.venv`), pytest, FastAPI + uvicorn, `webull-openapi-python-sdk` 3.0.2, `requests`, vanilla HTML/JS for the table view.

**Spec:** `docs/superpowers/specs/2026-10-08-scalp-city-design.md`

**Scope note:** This plan covers phases 0-3 of the spec. Phase 4 (the 3D city) gets its own plan after phase 3 proves the event stream, because the 3D scene is a separate subsystem that only reads that stream.

**Verified before writing:** every code block below was run first in a scratch copy. 65 tests pass, and a real replay of 2026-10-07 (QQQ, SPY, IWM with real Alpaca option history) ran end to end with all nine bots.

## Global Constraints

- Paper/sandbox only. Startup must refuse unless `WEBULL_ENV=sandbox`, `WEBULL_SANDBOX_ACCOUNT_ATTESTED=true`, host is `api.sandbox.webull.com`, and `WEBULL_PAPER_ACCOUNT_NUMBER` matches exactly one sandbox account.
- No production hostname in any code path that can send orders.
- Never read, run, use or modify anything in `/home/ronaldsecret/MarketScanners` or `/home/ronaldsecret/trading-agents-tauric`.
- Keys live in `.env` (mode 600, git-ignored); code reads environment variables only. Never log or print keys, secrets or full account ids; never put them in events.
- Python 3.11 (`.venv`); Webull SDK requires Python 3.8-3.11.
- Defaults: 10 contracts per trade; daily goal +$600 and daily loss limit -$100 per bot as lockouts checked after each closed trade (one trade can overshoot); cooldown 2 minutes (120 s); last entry 15:30 ET; positions flat by 15:55 ET.
- Windows per bot (ET): VWAP-cross and EMA50-cross may enter from 9:30 (EMAs warm-started from the previous session); range-break is armed and shown watching from 9:40 and may fire from 9:45.
- Chop filter: skip when |EMA9 - EMA21| < 0.15 x ATR; VWAP-cross bot only. Reason code `CHOP_SQUEEZE`.
- Stale rule: no new bar for 120 s (idle bots); no fresh option quote for 30 s while in a trade; flatten the paper position after 300 s stale.
- Replay half-spread per side: SPY $0.01, QQQ $0.015, IWM $0.02. Buys fill at the ask, sells at the bid.
- One event-log file per trading day and mode: `logs/YYYY-MM-DD-<mode>.jsonl`, append-only, `seq` gapless from 1.
- Commit messages end with: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`

## File Structure

```
pyproject.toml                      project and pytest config
scalpcity/types.py                  Bar, Quote, OrderIntent, Fill, ET
scalpcity/config.py                 Settings, BotSpec, BOT_SPECS, TICKERS
scalpcity/events.py                 EventLog (append-only JSONL), build_snapshot
scalpcity/indicators.py             Ema, Atr, SessionVwap, IndicatorSet
scalpcity/contracts.py              OCC symbols, next trading day, ATM strike, holidays
scalpcity/triggers.py               VwapCross, Ema50Cross, RangeBreak, TriggerView
scalpcity/bot.py                    State, Position, Bot (the state machine)
scalpcity/risk.py                   RiskGate
scalpcity/broker.py                 ModeledBroker
scalpcity/quotes.py                 QuoteSource protocol, BarQuoteSource (replay)
scalpcity/engine.py                 Engine, build_bots
scalpcity/replay.py                 ReplayFeed, run_replay
scalpcity/alpaca_history.py         read-only historical data with disk cache
scalpcity/guard.py                  assert_paper_only
scalpcity/webull_parse.py           parsers for Webull responses
scalpcity/webull_client.py          WebullClient (SDK wrapper)
scalpcity/webull_broker.py          WebullPaperBroker
scalpcity/live.py                   LiveFeed, LiveQuoteSource, market_open
scalpcity/stale.py                  check_stale
scalpcity/server.py                 FastAPI app, websocket hub
web/index.html                      plain table dashboard
scripts/run_replay.py               replay a past day
scripts/phase0_market_open.py       market-hours checks
scripts/run_live.py                 live paper run + dashboard
tests/...                           one test file per module, plus tests/fixtures/webull/
```

Working directory for every command: `/home/ronaldsecret/scalp-city`. Interpreter: `.venv/bin/python`.

---

### Task 1: Project scaffold, types and settings

**Files:**
- Create: `pyproject.toml`
- Create: `scalpcity/__init__.py`
- Create: `scalpcity/types.py`
- Create: `scalpcity/config.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: `Bar(ticker, ts, open, high, low, close, volume)` with `.end`; `Quote(symbol, ts, bid, ask)`; `OrderIntent(bot_id, ticker, kind, right, qty, reason, und_price, contract=None)`; `Fill(bot_id, kind, contract, qty, price, source, ts)`; `ET`; `Settings` (frozen dataclass of the spec defaults); `BotSpec(trigger, arm, start, chop_filter)`; `BOT_SPECS` keyed `vwap|ema50|range`; `TICKERS`; pytest fixture `mk(ticker, 'H:MM', close, high=None, low=None, volume=1000.0, day=(2026,10,8), open_=None) -> Bar`.

- [ ] **Step 1: Install dependencies into the existing project venv**

```bash
export PATH=$HOME/.local/bin:$PATH
[ -d .venv ] || uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python fastapi uvicorn requests httpx pytest webull-openapi-python-sdk
mkdir -p scalpcity tests logs data web scripts && touch scalpcity/__init__.py tests/__init__.py
```
Expected: `.venv/bin/python --version` prints `Python 3.11.x`.

- [ ] **Step 2: Write the failing tests**

Create `tests/test_config.py`:

```python
from datetime import time

from scalpcity.config import BOT_SPECS, TICKERS, Settings


def test_defaults_match_the_spec():
    s = Settings()
    assert (s.contracts, s.daily_goal, s.daily_loss, s.cooldown_s) == (10, 600.0, 100.0, 120)
    assert (s.stale_idle_s, s.stale_in_trade_s, s.flatten_after_stale_s) == (120, 30, 300)
    assert s.last_entry == time(15, 30) and s.flat_by == time(15, 55)


def test_nine_bots_worth_of_specs_and_windows():
    assert TICKERS == ("QQQ", "SPY", "IWM") and set(BOT_SPECS) == {"vwap", "ema50", "range"}
    assert BOT_SPECS["range"].arm == time(9, 40) and BOT_SPECS["range"].start == time(9, 45)
    assert BOT_SPECS["vwap"].start == time(9, 30) and BOT_SPECS["ema50"].start == time(9, 30)
    assert BOT_SPECS["vwap"].chop_filter is True and BOT_SPECS["ema50"].chop_filter is False and BOT_SPECS["range"].chop_filter is False
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_config.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'scalpcity.config'`

- [ ] **Step 4: Write the implementation**

Create `pyproject.toml`:

```toml
[project]
name = "scalpcity"
version = "0.1.0"
description = "Scalp City: nine paper-trading options bots with a visible event log"
requires-python = ">=3.11,<3.12"
dependencies = [
  "fastapi>=0.110",
  "uvicorn>=0.29",
  "requests>=2.31",
  "webull-openapi-python-sdk>=3.0.2",
]

[project.optional-dependencies]
dev = ["pytest>=8", "httpx>=0.27"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

Create `scalpcity/types.py`:

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class Bar:
    ticker: str
    ts: datetime  # bar START, tz-aware ET
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def end(self) -> datetime:
        return self.ts + timedelta(minutes=1)


@dataclass(frozen=True)
class Quote:
    symbol: str
    ts: datetime
    bid: float
    ask: float


@dataclass(frozen=True)
class OrderIntent:
    bot_id: str
    ticker: str
    kind: str  # "BUY_OPEN" | "SELL_CLOSE"
    right: str  # "CALL" | "PUT"
    qty: int
    reason: str
    und_price: float
    contract: str | None = None  # set for SELL_CLOSE (the held contract)


@dataclass(frozen=True)
class Fill:
    bot_id: str
    kind: str
    contract: str
    qty: int
    price: float
    source: str  # "broker" | "modeled"
    ts: datetime
```

Create `scalpcity/config.py`:

```python
from dataclasses import dataclass, field
from datetime import time

TICKERS = ("QQQ", "SPY", "IWM")


@dataclass(frozen=True)
class Settings:
    contracts: int = 10
    daily_goal: float = 600.0
    daily_loss: float = 100.0
    cooldown_s: int = 120
    last_entry: time = time(15, 30)
    flat_by: time = time(15, 55)
    stale_idle_s: int = 120
    stale_in_trade_s: int = 30
    flatten_after_stale_s: int = 300
    squeeze_atr: float = 0.15
    stop_atr: float = 1.0
    target_atr: float = 2.0
    charge_range_atr: float = 1.0
    forming_min_charge: float = 30.0
    atr_period: int = 14
    max_spread_pct: float = 0.15
    cash_per_bot: float = 25_000.0
    half_spread: dict = field(default_factory=lambda: {"SPY": 0.01, "QQQ": 0.015, "IWM": 0.02})


@dataclass(frozen=True)
class BotSpec:
    trigger: str  # "vwap" | "ema50" | "range"
    arm: time  # bot is shown armed/watching from this time
    start: time  # first time an entry is allowed
    chop_filter: bool


BOT_SPECS = {
    "vwap": BotSpec("vwap", time(9, 30), time(9, 30), True),
    "ema50": BotSpec("ema50", time(9, 30), time(9, 30), False),
    "range": BotSpec("range", time(9, 40), time(9, 45), False),
}
```

Create `tests/conftest.py`:

```python
from datetime import datetime, timedelta

import pytest

from scalpcity.types import Bar, ET


@pytest.fixture
def mk():
    """mk(ticker, 'HH:MM', close, high=None, low=None, volume=1000) -> Bar starting at that time on 2026-10-08."""
    def make(ticker, hhmm, close, high=None, low=None, volume=1000.0, day=(2026, 10, 8), open_=None):
        h, m = map(int, hhmm.split(":"))
        ts = datetime(*day, h, m, tzinfo=ET)
        return Bar(ticker, ts, open_ if open_ is not None else close,
                   high if high is not None else close, low if low is not None else close, close, volume)
    return make
```

- [ ] **Step 5: Run the full suite to verify it passes**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, 2 tests passed.

- [ ] **Step 6: Commit**

```bash
git add tests/test_config.py pyproject.toml scalpcity/types.py scalpcity/config.py tests/conftest.py
git commit -m "feat: project scaffold, shared types and settings"
```

### Task 2: Event log and snapshot

**Files:**
- Create: `scalpcity/events.py`
- Test: `tests/test_events.py`

**Interfaces:**
- Consumes: `ET` from Task 1 (tests only).
- Produces: `EventLog(directory, mode)` with `.append(time, bot, ticker, kind, state='', reason_code='', reason_text='', inputs=None, charge_pct=None, **extra) -> dict`, `.read(day) -> list[dict]`, `.reset(day)`, `.path_for(day)`, `.listeners: list[callable]`; `build_snapshot(events) -> {'bots': {bot: {...}}, 'last_seq': int}`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_events.py`:

```python
from datetime import datetime

from scalpcity.events import EventLog, build_snapshot
from scalpcity.types import ET


def t(h, m):
    return datetime(2026, 10, 8, h, m, tzinfo=ET)


def test_append_assigns_increasing_seq_and_persists(tmp_path):
    log = EventLog(str(tmp_path), "replay")
    a = log.append(t(9, 31), "QQQ-VWAP", "QQQ", "tick", state="idle")
    b = log.append(t(9, 32), "QQQ-VWAP", "QQQ", "tick", state="forming", charge_pct=41.0)
    assert (a["seq"], b["seq"]) == (1, 2)
    rows = log.read(t(9, 31).date())
    assert [r["seq"] for r in rows] == [1, 2] and rows[1]["charge_pct"] == 41.0


def test_seq_continues_after_restart(tmp_path):
    EventLog(str(tmp_path), "live").append(t(9, 31), "b", "QQQ", "tick")
    again = EventLog(str(tmp_path), "live").append(t(9, 32), "b", "QQQ", "tick")
    assert again["seq"] == 2


def test_listener_called_and_reset_clears_file(tmp_path):
    log = EventLog(str(tmp_path), "replay")
    seen = []
    log.listeners.append(seen.append)
    log.append(t(9, 31), "b", "QQQ", "tick")
    assert len(seen) == 1
    log.reset(t(9, 31).date())
    assert log.read(t(9, 31).date()) == []
    assert log.append(t(9, 31), "b", "QQQ", "tick")["seq"] == 1


def test_snapshot_uses_last_state_and_trade_totals(tmp_path):
    log = EventLog(str(tmp_path), "replay")
    log.append(t(9, 31), "QQQ-VWAP", "QQQ", "tick", state="idle", reason_code="WATCHING")
    log.append(t(9, 32), "QQQ-VWAP", "QQQ", "tick", state="forming", reason_code="WATCHING", charge_pct=55.0)
    log.append(t(9, 33), "QQQ-VWAP", "QQQ", "trade_closed", pnl=120.0, pnl_day=120.0, trades=1)
    log.append(t(9, 34), "QQQ-VWAP", "QQQ", "control", paused=True)
    snap = build_snapshot(log.read(t(9, 31).date()))
    row = snap["bots"]["QQQ-VWAP"]
    assert row["state"] == "forming" and row["charge_pct"] == 55.0
    assert row["pnl_day"] == 120.0 and row["trades"] == 1 and row["paused"] is True
    assert snap["last_seq"] == 4
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_events.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'scalpcity.events'`

- [ ] **Step 3: Write the implementation**

Create `scalpcity/events.py`:

```python
import json
import os
from datetime import date, datetime


class EventLog:
    """Append-only JSONL, one file per trading day and mode. The single source of truth."""

    def __init__(self, directory: str, mode: str):
        self.dir = directory
        self.mode = mode
        self._seq: dict[date, int] = {}
        self.listeners = []
        os.makedirs(directory, exist_ok=True)

    def path_for(self, day: date) -> str:
        return os.path.join(self.dir, f"{day.isoformat()}-{self.mode}.jsonl")

    def reset(self, day: date) -> None:
        """Replay only: start the day's file fresh."""
        path = self.path_for(day)
        if os.path.exists(path):
            os.remove(path)
        self._seq.pop(day, None)

    def _next_seq(self, day: date) -> int:
        if day not in self._seq:
            path = self.path_for(day)
            n = 0
            if os.path.exists(path):
                with open(path) as handle:
                    n = sum(1 for _ in handle)
            self._seq[day] = n
        self._seq[day] += 1
        return self._seq[day]

    def append(self, time: datetime, bot: str, ticker: str, kind: str, state: str = "",
               reason_code: str = "", reason_text: str = "", inputs: dict | None = None,
               charge_pct: float | None = None, **extra) -> dict:
        day = time.date()
        event = {
            "seq": self._next_seq(day), "time": time.isoformat(), "mode": self.mode,
            "bot": bot, "ticker": ticker, "kind": kind, "state": state,
            "reason_code": reason_code, "reason_text": reason_text,
            "inputs": inputs or {}, "charge_pct": charge_pct,
        }
        event.update(extra)
        with open(self.path_for(day), "a") as handle:
            handle.write(json.dumps(event, separators=(",", ":"), default=str) + "\n")
        for listener in list(self.listeners):
            listener(event)
        return event

    def read(self, day: date) -> list[dict]:
        path = self.path_for(day)
        if not os.path.exists(path):
            return []
        with open(path) as handle:
            return [json.loads(line) for line in handle if line.strip()]


def build_snapshot(events: list[dict]) -> dict:
    """Current state of every bot, derived purely from the event list."""
    bots: dict[str, dict] = {}
    last_seq = 0
    for ev in events:
        last_seq = max(last_seq, ev["seq"])
        bot = ev["bot"]
        if not bot:
            continue
        row = bots.setdefault(bot, {"bot": bot, "ticker": ev["ticker"], "state": "idle", "reason_code": "",
                                    "reason_text": "", "charge_pct": None, "inputs": {}, "time": None,
                                    "pnl_day": 0.0, "trades": 0, "paused": False})
        if ev["kind"] in ("tick", "state_change"):
            row.update(state=ev["state"], reason_code=ev["reason_code"], reason_text=ev["reason_text"],
                       charge_pct=ev["charge_pct"], inputs=ev["inputs"], time=ev["time"])
        elif ev["kind"] == "trade_closed":
            row["pnl_day"] = ev.get("pnl_day", row["pnl_day"])
            row["trades"] = ev.get("trades", row["trades"])
        elif ev["kind"] == "control":
            row["paused"] = bool(ev.get("paused", row["paused"]))
    return {"bots": bots, "last_seq": last_seq}
```

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, 6 tests passed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_events.py scalpcity/events.py
git commit -m "feat: append-only event log and snapshot"
```

### Task 3: Indicators and contract helpers

**Files:**
- Create: `scalpcity/indicators.py`
- Create: `scalpcity/contracts.py`
- Test: `tests/test_indicators_contracts.py`

**Interfaces:**
- Consumes: `Bar` from Task 1.
- Produces: `Ema(period).update(x)`, `Atr(period).update(bar)`, `SessionVwap().update(bar)/reset()`, `IndicatorSet(atr_period).warm(bar)/update(bar)/new_session()/squeezed(atr_mult)/as_dict()` with attributes `ema9, ema21, ema50, atr, vwap, last_close`; `occ_symbol(underlying, expiry, right, strike)`, `next_trading_day(day, holidays=HOLIDAYS)`, `atm_strike(price)`, `underlying_of(contract)`, `HOLIDAYS`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_indicators_contracts.py`:

```python
from datetime import date

import pytest

from scalpcity.contracts import atm_strike, next_trading_day, occ_symbol, underlying_of
from scalpcity.indicators import Atr, Ema, IndicatorSet, SessionVwap


def test_ema_seeds_with_first_value_then_smooths():
    e = Ema(9)
    assert e.update(10.0) == 10.0
    assert e.update(20.0) == pytest.approx(12.0)  # alpha = 0.2


def test_atr_average_then_wilder(mk):
    a = Atr(2)
    assert a.update(mk("QQQ", "9:30", 10, high=11, low=9)) == 2.0
    assert a.update(mk("QQQ", "9:31", 10, high=12, low=10)) == 2.0  # avg(2, 2)
    # third bar: Wilder smoothing (2*1 + tr)/2, tr = max(1, |11-10|, |10-10|) = 1
    assert a.update(mk("QQQ", "9:32", 10, high=11, low=10)) == pytest.approx(1.5)


def test_vwap_is_volume_weighted_and_resets(mk):
    v = SessionVwap()
    v.update(mk("QQQ", "9:30", 10, volume=100))
    assert v.update(mk("QQQ", "9:31", 20, volume=300)) == pytest.approx(17.5)
    v.reset()
    assert v.value is None


def test_warm_feeds_emas_but_not_vwap(mk):
    s = IndicatorSet()
    s.warm(mk("QQQ", "15:59", 100))
    assert s.ema50.n == 1 and s.vwap.value is None
    s.update(mk("QQQ", "9:30", 101))
    assert s.vwap.value == 101


def test_squeeze_needs_atr_and_compares_gap(mk):
    s = IndicatorSet()
    assert s.squeezed(0.15) is False
    for i in range(30):
        s.warm(mk("QQQ", "10:00", 100.0, high=100.5, low=99.5))
    assert s.squeezed(0.15) is True  # flat price: EMA9 == EMA21


def test_occ_symbol_matches_webull_format():
    assert occ_symbol("SPY", date(2026, 10, 9), "CALL", 774.0) == "SPY261009C00774000"
    assert occ_symbol("QQQ", date(2026, 10, 9), "PUT", 748.0) == "QQQ261009P00748000"
    assert underlying_of("IWM261009C00278000") == "IWM"


def test_next_trading_day_skips_weekend_and_holiday():
    assert next_trading_day(date(2026, 10, 8)) == date(2026, 10, 9)   # Thu -> Fri
    assert next_trading_day(date(2026, 10, 9)) == date(2026, 10, 12)  # Fri -> Mon
    assert next_trading_day(date(2026, 9, 4)) == date(2026, 9, 8)     # Fri before Labor Day (Mon 9/7)


def test_atm_strike_rounds_to_dollar():
    assert atm_strike(747.58) == 748.0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_indicators_contracts.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'scalpcity.contracts'`

- [ ] **Step 3: Write the implementation**

Create `scalpcity/indicators.py`:

```python
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
```

Create `scalpcity/contracts.py`:

```python
from datetime import date, timedelta

# NYSE full-day holidays 2024-2027 (early closes ignored).
HOLIDAYS = frozenset(date.fromisoformat(d) for d in (
    "2024-01-01 2024-01-15 2024-02-19 2024-03-29 2024-05-27 2024-06-19 2024-07-04 2024-09-02 2024-11-28 2024-12-25 "
    "2025-01-01 2025-01-09 2025-01-20 2025-02-17 2025-04-18 2025-05-26 2025-06-19 2025-07-04 2025-09-01 2025-11-27 2025-12-25 "
    "2026-01-01 2026-01-19 2026-02-16 2026-04-03 2026-05-25 2026-06-19 2026-07-03 2026-09-07 2026-11-26 2026-12-25 "
    "2027-01-01 2027-01-18 2027-02-15 2027-03-26 2027-05-31 2027-06-18 2027-07-05 2027-09-06 2027-11-25 2027-12-24"
).split())


def next_trading_day(day: date, holidays=HOLIDAYS) -> date:
    d = day + timedelta(days=1)
    while d.weekday() >= 5 or d in holidays:
        d += timedelta(days=1)
    return d


def atm_strike(price: float) -> float:
    return float(round(price))


def occ_symbol(underlying: str, expiry: date, right: str, strike: float) -> str:
    """Standard OCC name, e.g. SPY261009C00774000. right is CALL or PUT."""
    return f"{underlying}{expiry:%y%m%d}{'C' if right == 'CALL' else 'P'}{int(round(strike * 1000)):08d}"


def underlying_of(contract: str) -> str:
    i = 0
    while i < len(contract) and contract[i].isalpha():
        i += 1
    return contract[:i]
```

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, 14 tests passed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_indicators_contracts.py scalpcity/indicators.py scalpcity/contracts.py
git commit -m "feat: streaming indicators and option contract helpers"
```

### Task 4: Triggers (VWAP cross, EMA50 cross, range break)

**Files:**
- Create: `scalpcity/triggers.py`
- Test: `tests/test_triggers.py`

**Interfaces:**
- Consumes: `IndicatorSet`, `Bar`.
- Produces: `TriggerView(signal, charge_pct, distance_atr, reason_code, ready)`; `charge(dist_atr, range_atr)`; `VwapCross(charge_range_atr)`, `Ema50Cross(charge_range_atr)`, `RangeBreak(charge_range_atr)`, each with `.update(bar, ind) -> TriggerView` and `.new_session()`. A signal is `'CALL'` or `'PUT'`; a cross must go from strictly one side to strictly the other.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_triggers.py`:

```python
import pytest

from scalpcity.indicators import IndicatorSet
from scalpcity.triggers import Ema50Cross, RangeBreak, VwapCross, charge


def ind_with_atr(mk, atr_bar=(101, 99), n=20):
    s = IndicatorSet()
    for _ in range(n):
        s.warm(mk("QQQ", "15:59", 100, high=atr_bar[0], low=atr_bar[1]))
    return s


def test_charge_matches_video_example():
    assert charge(0.6, 1.0) == 40.0
    assert charge(0.0, 1.0) == 100.0
    assert charge(2.0, 1.0) == 0.0


def test_vwap_cross_up_down_and_no_signal_on_first_bar(mk):
    ind, trig = ind_with_atr(mk), VwapCross(1.0)
    bars = [mk("QQQ", "9:30", 99, volume=100), mk("QQQ", "9:31", 98, volume=100), mk("QQQ", "9:32", 102, volume=100)]
    views = []
    for b in bars:
        ind.update(b)
        views.append(trig.update(b, ind))
    assert views[0].signal is None and views[1].signal is None   # first bar: close == VWAP is not a cross
    assert views[2].signal == "CALL"          # closed up through VWAP
    b = mk("QQQ", "9:33", 95, volume=100)
    ind.update(b)
    assert trig.update(b, ind).signal == "PUT"


def test_ema50_not_ready_until_50_samples(mk):
    trig = Ema50Cross(1.0)
    ind = IndicatorSet()
    for _ in range(10):
        ind.warm(mk("QQQ", "15:59", 100))
    view = trig.update(mk("QQQ", "9:30", 100), ind)
    assert view.ready is False and view.reason_code == "WARMING_UP"
    for _ in range(45):
        ind.warm(mk("QQQ", "15:59", 100))
    assert trig.update(mk("QQQ", "9:30", 100), ind).ready is True


def test_range_forms_then_breaks_once_per_crossing(mk):
    ind, trig = ind_with_atr(mk, (101, 99)), RangeBreak(1.0)
    for minute in range(30, 45):                       # 9:30..9:44 build the range 99..101
        v = trig.update(mk("QQQ", f"9:{minute}", 100, high=101, low=99), ind)
        assert v.ready is False and v.reason_code == "RANGE_FORMING"
    v = trig.update(mk("QQQ", "9:45", 100.5), ind)   # inside
    assert v.signal is None and v.charge_pct is not None and v.charge_pct < 100
    assert trig.update(mk("QQQ", "9:46", 101.5), ind).signal == "CALL"   # inside -> outside
    assert trig.update(mk("QQQ", "9:47", 102.0), ind).signal is None     # still outside: no re-fire
    assert trig.update(mk("QQQ", "9:48", 100.0), ind).signal is None     # back inside
    assert trig.update(mk("QQQ", "9:49", 98.0), ind).signal == "PUT"     # crossing the other side


def test_range_new_session_clears(mk):
    ind, trig = ind_with_atr(mk), RangeBreak(1.0)
    trig.update(mk("QQQ", "9:30", 100, high=101, low=99), ind)
    trig.new_session()
    assert trig.update(mk("QQQ", "9:50", 100), ind).reason_code == "NO_RANGE"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_triggers.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'scalpcity.triggers'`

- [ ] **Step 3: Write the implementation**

Create `scalpcity/triggers.py`:

```python
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
```

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, 19 tests passed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_triggers.py scalpcity/triggers.py
git commit -m "feat: VWAP, EMA50 and range-break triggers"
```

### Task 5: Bot state machine

**Files:**
- Create: `scalpcity/bot.py`
- Test: `tests/test_bot.py`

**Interfaces:**
- Consumes: `Settings`, `BotSpec`, `IndicatorSet`, trigger classes, `Bar`, `Fill`, `OrderIntent`.
- Produces: `State` enum (`idle, forming, fired, managing, exiting, cooldown, locked, paused, stale`); `Position`; `BotOutput(events, intents)`; `Bot(ticker, spec, trigger, settings)` with `.bot_id` (e.g. `QQQ-VWAP`), `.on_bar(bar, ind) -> BotOutput`, `.on_fill(fill, inputs=None) -> list[dict]`, `.on_order_failed(kind, reason) -> list[dict]`, `.set_paused(bool) -> list[dict]`, `.set_stale(bool, text='') -> list[dict]`, `.new_session()`, and attributes `state, reason_code, reason_text, position, pending, pnl_day, trades, locked, paused, stale, cooldown_until`. Event dicts carry keys `kind, state, reason_code, reason_text, inputs, charge_pct` plus extras.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bot.py`:

```python
from datetime import datetime, timedelta

import pytest

from scalpcity.bot import Bot, State
from scalpcity.config import BOT_SPECS, Settings
from scalpcity.indicators import IndicatorSet
from scalpcity.triggers import RangeBreak, VwapCross
from scalpcity.types import ET, Fill

S = Settings()


def vwap_bot(**kw):
    return Bot("QQQ", BOT_SPECS["vwap"], VwapCross(S.charge_range_atr), Settings(**kw) if kw else S)


B = 129.5  # last warm-up close below


def warmed(mk, n=60, start=100.0, slope=0.5, rng=1.0):
    """Rising history: EMA9 sits well above EMA21 (not squeezed); last close is B."""
    ind = IndicatorSet()
    for i in range(n):
        c = start + slope * i
        ind.warm(mk("QQQ", "15:59", c, high=c + rng / 2, low=c - rng / 2))
    return ind


def step(bot, ind, bar):
    ind.update(bar)
    return bot.on_bar(bar, ind)


def states(out):
    return [e["state"] for e in out.events]


def test_before_arm_time_reports_outside_window(mk):
    bot, ind = vwap_bot(), warmed(mk)
    out = step(bot, ind, mk("QQQ", "9:25", 103))
    assert bot.state == State.IDLE and bot.reason_code == "OUTSIDE_WINDOW"
    assert out.events[0]["kind"] == "state_change" and out.events[-1]["kind"] == "tick"


def test_signal_fires_buy_intent_with_atr_stop_and_target(mk):
    bot, ind = vwap_bot(), warmed(mk)
    # session bars under VWAP then close up through it
    step(bot, ind, mk("QQQ", "9:30", B - 1.0, volume=1000))
    step(bot, ind, mk("QQQ", "9:31", B - 1.5, volume=1000))
    out = step(bot, ind, mk("QQQ", "9:32", B + 5.0, volume=1000))
    assert bot.state == State.FIRED and len(out.intents) == 1
    intent = out.intents[0]
    assert (intent.kind, intent.right, intent.qty) == ("BUY_OPEN", "CALL", 10)
    p = bot.position
    assert p.stop_und == pytest.approx(B + 5.0 - ind.atr.value) and p.target_und == pytest.approx(B + 5.0 + 2 * ind.atr.value)


def test_chop_squeeze_blocks_vwap_signal(mk):
    bot = vwap_bot()
    ind = IndicatorSet()
    for _ in range(40):  # flat history: EMA9 == EMA21
        ind.warm(mk("QQQ", "15:59", 100.0, high=100.5, low=99.5))
    step(bot, ind, mk("QQQ", "9:30", 99.0, volume=1000))
    step(bot, ind, mk("QQQ", "9:31", 98.9, volume=1000))
    out = step(bot, ind, mk("QQQ", "9:32", 100.4, volume=1000))
    assert out.intents == [] and bot.reason_code == "CHOP_SQUEEZE"


def _enter(bot, ind, mk):
    step(bot, ind, mk("QQQ", "9:30", B - 1.0, volume=1000))
    step(bot, ind, mk("QQQ", "9:31", B - 1.5, volume=1000))
    out = step(bot, ind, mk("QQQ", "9:32", B + 5.0, volume=1000))
    fill = Fill(bot.bot_id, "BUY_OPEN", "QQQ261009C00105000", 10, 3.00, "modeled", mk("QQQ", "9:32", 1).end)
    bot.on_fill(fill)
    return out.intents[0]


def test_fill_moves_to_managing_then_stop_exit_and_cooldown(mk):
    bot, ind = vwap_bot(), warmed(mk)
    _enter(bot, ind, mk)
    assert bot.state == State.MANAGING
    out = step(bot, ind, mk("QQQ", "9:33", B - 30.0))          # far below the stop
    assert out.intents[0].kind == "SELL_CLOSE" and bot.state == State.EXITING
    assert step(bot, ind, mk("QQQ", "9:34", B - 30.0)).intents == []   # no duplicate exit while pending
    t = mk("QQQ", "9:34", 1).end
    events = bot.on_fill(Fill(bot.bot_id, "SELL_CLOSE", "QQQ261009C00105000", 10, 2.00, "modeled", t))
    assert [e["kind"] for e in events] == ["fill", "trade_closed", "state_change"]
    assert bot.pnl_day == pytest.approx(-1000.0)            # (2.00-3.00)*10*100
    assert bot.locked == "DAILY_LOSS" and bot.state == State.LOCKED


def test_goal_locks_for_the_day(mk):
    bot, ind = vwap_bot(), warmed(mk)
    _enter(bot, ind, mk)
    step(bot, ind, mk("QQQ", "9:33", B + 100.0))                # far above target
    bot.on_fill(Fill(bot.bot_id, "SELL_CLOSE", "x", 10, 3.80, "modeled", mk("QQQ", "9:34", 1).end))
    assert bot.pnl_day == pytest.approx(800.0) and bot.locked == "DAILY_GOAL"


def test_small_loss_goes_to_cooldown_then_resumes(mk):
    bot, ind = vwap_bot(), warmed(mk)
    _enter(bot, ind, mk)
    step(bot, ind, mk("QQQ", "9:33", B - 30.0))
    bot.on_fill(Fill(bot.bot_id, "SELL_CLOSE", "x", 10, 2.95, "modeled", mk("QQQ", "9:34", 1).end))  # -50
    assert bot.state == State.COOLDOWN and bot.locked is None
    step(bot, ind, mk("QQQ", "9:35", B - 30.0))
    assert bot.reason_code == "COOLDOWN"
    step(bot, ind, mk("QQQ", "9:37", B - 30.0))                # 2+ minutes after 9:35 close
    assert bot.reason_code != "COOLDOWN"


def test_time_exit_at_flat_by(mk):
    bot, ind = vwap_bot(), warmed(mk)
    _enter(bot, ind, mk)
    out = step(bot, ind, mk("QQQ", "15:54", B + 5.2))         # bar ends 15:55
    assert out.intents[0].kind == "SELL_CLOSE" and bot.reason_code == "EXIT_TIME"


def test_pause_blocks_entries_but_keeps_managing(mk):
    bot, ind = vwap_bot(), warmed(mk)
    bot.set_paused(True)
    step(bot, ind, mk("QQQ", "9:30", B - 1.0, volume=1000))
    step(bot, ind, mk("QQQ", "9:31", B - 1.5, volume=1000))
    out = step(bot, ind, mk("QQQ", "9:32", B + 5.0, volume=1000))
    assert out.intents == [] and bot.state == State.PAUSED
    bot.set_paused(False)
    bot2, ind2 = vwap_bot(), warmed(mk)
    _enter(bot2, ind2, mk)
    bot2.set_paused(True)
    assert bot2.state == State.MANAGING                      # still managing the open position
    assert step(bot2, ind2, mk("QQQ", "9:33", B - 30.0)).intents[0].kind == "SELL_CLOSE"


def test_order_failed_entry_returns_to_idle(mk):
    bot, ind = vwap_bot(), warmed(mk)
    step(bot, ind, mk("QQQ", "9:30", B - 1.0, volume=1000))
    step(bot, ind, mk("QQQ", "9:31", B - 1.5, volume=1000))
    step(bot, ind, mk("QQQ", "9:32", B + 5.0, volume=1000))
    bot.on_order_failed("BUY_OPEN", "NO_QUOTE")
    assert bot.position is None and bot.reason_code == "ORDER_FAILED"


def test_range_bot_armed_at_940_fires_after_945(mk):
    bot = Bot("QQQ", BOT_SPECS["range"], RangeBreak(S.charge_range_atr), S)
    ind = warmed(mk)
    for minute in range(30, 40):
        step(bot, ind, mk("QQQ", f"9:{minute}", 100, high=101, low=99))
    assert bot.reason_code == "OUTSIDE_WINDOW" or bot.reason_code == "RANGE_FORMING"
    step(bot, ind, mk("QQQ", "9:39", 100, high=101, low=99))
    assert bot.reason_code == "RANGE_FORMING"                # armed from 9:40 (bar 9:39 ends 9:40)
    for minute in range(40, 45):
        step(bot, ind, mk("QQQ", f"9:{minute}", 100, high=101, low=99))
    step(bot, ind, mk("QQQ", "9:45", 100.5))
    out = step(bot, ind, mk("QQQ", "9:46", 102.0))
    assert out.intents and out.intents[0].right == "CALL"


def test_stale_flag_sets_state_when_flat(mk):
    bot = vwap_bot()
    ev = bot.set_stale(True, "no bar for 2 min")
    assert bot.state == State.STALE and ev[0]["kind"] == "feed_stale"
    assert bot.set_stale(True) == []
    assert bot.set_stale(False)[0]["kind"] == "feed_fresh"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_bot.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'scalpcity.bot'`

- [ ] **Step 3: Write the implementation**

Create `scalpcity/bot.py`:

```python
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
```

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, 30 tests passed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_bot.py scalpcity/bot.py
git commit -m "feat: bot state machine with windows, chop filter, cooldown, lockouts and pause"
```

### Task 6: Risk gate, modeled broker and replay quotes

**Files:**
- Create: `scalpcity/risk.py`
- Create: `scalpcity/broker.py`
- Create: `scalpcity/quotes.py`
- Test: `tests/test_risk_broker.py`
- Test: `tests/test_quotes.py`

**Interfaces:**
- Consumes: `Settings`, `OrderIntent`, `Quote`, `Fill`, `underlying_of`.
- Produces: `RiskGate(settings).check(intent, quote, stale_tickers, halted=False) -> (bool, reason_code)`; `ModeledBroker().execute(intent, contract, quote, ts) -> Fill | None` (buys at ask, sells at bid, source `'modeled'`); `QuoteSource` protocol with `.get(contract, ts) -> Quote | None`; `BarQuoteSource(bars_for, half_spread, max_age)` where `bars_for(contract, ts) -> list[(bar_start_ts, close)]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_risk_broker.py`:

```python
from datetime import datetime

from scalpcity.broker import ModeledBroker
from scalpcity.config import Settings
from scalpcity.risk import RiskGate
from scalpcity.types import ET, OrderIntent, Quote

NOW = datetime(2026, 10, 8, 10, 0, tzinfo=ET)


def intent(kind="BUY_OPEN", qty=10, ticker="QQQ"):
    return OrderIntent("QQQ-VWAP", ticker, kind, "CALL", qty, "signal", 748.0, contract="QQQ261009C00748000")


def q(bid=2.9, ask=2.95):
    return Quote("QQQ261009C00748000", NOW, bid, ask)


def test_gate_allows_normal_entry_and_all_exits():
    g = RiskGate(Settings())
    assert g.check(intent(), q(), set()) == (True, "")
    assert g.check(intent("SELL_CLOSE"), None, {"QQQ"}, halted=True) == (True, "")


def test_gate_refusals():
    g = RiskGate(Settings())
    assert g.check(intent(), q(), {"QQQ"})[1] == "STALE_DATA"
    assert g.check(intent(), q(), set(), halted=True)[1] == "HALTED"
    assert g.check(intent(qty=11), q(), set())[1] == "SIZE_LIMIT"
    assert g.check(intent(), None, set())[1] == "NO_QUOTE"
    assert g.check(intent(), q(0.0, 1.0), set())[1] == "BAD_QUOTE"
    assert g.check(intent(), q(1.0, 2.0), set())[1] == "WIDE_SPREAD"
    assert g.check(intent(), q(30.0, 30.5), set())[1] == "CASH_LIMIT"   # 30.5*10*100 = 30,500 > 25,000


def test_modeled_broker_buys_ask_sells_bid():
    b = ModeledBroker()
    assert b.execute(intent(), "C", q(), NOW).price == 2.95
    assert b.execute(intent("SELL_CLOSE"), "C", q(), NOW).price == 2.9
    assert b.execute(intent(), "C", q(1.0, 0.0), NOW) is None
```

Create `tests/test_quotes.py`:

```python
from datetime import datetime, timedelta

from scalpcity.quotes import BarQuoteSource
from scalpcity.types import ET

T0 = datetime(2026, 10, 8, 10, 0, tzinfo=ET)


def src(rows, hs=None):
    return BarQuoteSource(lambda c, t: rows, hs or {"QQQ": 0.015})


def test_uses_last_completed_bar_and_modeled_half_spread():
    rows = [(T0 - timedelta(minutes=2), 3.00), (T0 - timedelta(minutes=1), 3.10), (T0, 9.99)]
    q = src(rows, {"QQQ": 0.02}).get("QQQ261009C00748000", T0)
    assert (q.bid, q.ask) == (3.08, 3.12)


def test_none_when_no_completed_bar_or_too_stale():
    assert src([(T0, 3.0)]).get("QQQ261009C00748000", T0) is None
    assert src([(T0 - timedelta(minutes=30), 3.0)]).get("QQQ261009C00748000", T0) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_risk_broker.py tests/test_quotes.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'scalpcity.risk'`

- [ ] **Step 3: Write the implementation**

Create `scalpcity/risk.py`:

```python
from .config import Settings
from .types import OrderIntent, Quote


class RiskGate:
    """The only path to the broker. Entries are checked; exits always pass."""

    def __init__(self, settings: Settings):
        self.s = settings

    def check(self, intent: OrderIntent, quote: Quote | None, stale_tickers: set, halted: bool = False) -> tuple[bool, str]:
        if intent.kind == "SELL_CLOSE":
            return True, ""
        if halted:
            return False, "HALTED"
        if intent.ticker in stale_tickers:
            return False, "STALE_DATA"
        if intent.qty > self.s.contracts:
            return False, "SIZE_LIMIT"
        if quote is None:
            return False, "NO_QUOTE"
        if quote.bid <= 0 or quote.ask <= 0 or quote.ask < quote.bid:
            return False, "BAD_QUOTE"
        if (quote.ask - quote.bid) / quote.ask > self.s.max_spread_pct:
            return False, "WIDE_SPREAD"
        if quote.ask * intent.qty * 100 > self.s.cash_per_bot:
            return False, "CASH_LIMIT"
        return True, ""
```

Create `scalpcity/broker.py`:

```python
from datetime import datetime

from .types import Fill, OrderIntent, Quote


class ModeledBroker:
    """Fills at the quote: buys at the ask, sells at the bid. Labelled 'modeled'."""
    source = "modeled"

    def execute(self, intent: OrderIntent, contract: str, quote: Quote, ts: datetime) -> Fill | None:
        price = quote.ask if intent.kind == "BUY_OPEN" else quote.bid
        if price <= 0:
            return None
        return Fill(intent.bot_id, intent.kind, contract, intent.qty, round(price, 2), self.source, ts)
```

Create `scalpcity/quotes.py`:

```python
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
```

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, 35 tests passed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_risk_broker.py tests/test_quotes.py scalpcity/risk.py scalpcity/broker.py scalpcity/quotes.py
git commit -m "feat: risk gate, modeled broker and replay quote source"
```

### Task 7: Engine and replay

**Files:**
- Create: `scalpcity/engine.py`
- Create: `scalpcity/replay.py`
- Test: `tests/test_engine_replay.py`

**Interfaces:**
- Consumes: Everything from Tasks 1-6.
- Produces: `build_bots(settings) -> list[Bot]` (nine bots); `Engine(settings, log, broker, quotes, risk=None, bots=None)` with `.start_session(day, warm_bars)`, `.on_bar(bar)`, `.check_stale(now, last_bar_wall, open_quote_wall=None)` (needs Task 11), `.set_paused(bot_id, paused, time)`, `.by_id`, `.bots`, `.stale`, `.lock`; `ReplayFeed(bars)` with `.days()`, `.warm_bars(day, n=200)`, `.day_bars(day)`; `run_replay(engine, feed, day)`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_engine_replay.py`:

```python
from datetime import date, datetime, timedelta

from scalpcity.broker import ModeledBroker
from scalpcity.config import Settings
from scalpcity.engine import Engine
from scalpcity.events import EventLog, build_snapshot
from scalpcity.quotes import BarQuoteSource
from scalpcity.replay import ReplayFeed, run_replay
from scalpcity.types import Bar, ET, Quote

DAY = date(2026, 10, 8)


def synth_bars(ticker, day, base, drift=0.0, wiggle=0.0):
    out, price = [], base
    t = datetime(day.year, day.month, day.day, 9, 30, tzinfo=ET)
    for i in range(390):
        price += drift + (wiggle if i % 2 == 0 else -wiggle)
        out.append(Bar(ticker, t + timedelta(minutes=i), price, price + 0.1, price - 0.1, price, 1000.0))
    return out


def make_feed():
    prev = date(2026, 10, 7)
    bars = {}
    for tk, base in (("QQQ", 748.0), ("SPY", 774.0), ("IWM", 278.0)):
        bars[tk] = synth_bars(tk, prev, base, drift=0.05) + synth_bars(tk, DAY, base + 20, drift=0.0, wiggle=0.6)
    return ReplayFeed(bars)


def flat_option_quotes():
    def bars_for(contract, ts):
        base = ts.replace(hour=9, minute=30, second=0, microsecond=0)
        return [(base + timedelta(minutes=i), 3.0) for i in range(390)]
    return BarQuoteSource(bars_for, Settings().half_spread)


def run_once(tmp_path, name):
    log = EventLog(str(tmp_path / name), "replay")
    eng = Engine(Settings(), log, ModeledBroker(), flat_option_quotes())
    run_replay(eng, make_feed(), DAY)
    return log, eng


def test_replay_is_deterministic_byte_for_byte(tmp_path):
    a, _ = run_once(tmp_path, "a")
    b, _ = run_once(tmp_path, "b")
    assert open(a.path_for(DAY)).read() == open(b.path_for(DAY)).read()
    assert len(a.read(DAY)) > 1000


def test_every_bot_logs_a_tick_every_bar_and_seq_is_gapless(tmp_path):
    log, eng = run_once(tmp_path, "a")
    events = log.read(DAY)
    assert [e["seq"] for e in events] == list(range(1, len(events) + 1))
    ticks = [e for e in events if e["kind"] == "tick" and e["bot"] == "QQQ-VWAP"]
    assert len(ticks) == 390
    assert {e["bot"] for e in events} == set(eng.by_id)


def test_snapshot_covers_all_nine_bots_with_reasons(tmp_path):
    log, _ = run_once(tmp_path, "a")
    snap = build_snapshot(log.read(DAY))
    assert len(snap["bots"]) == 9
    assert all(row["reason_code"] for row in snap["bots"].values())


def test_trades_have_matching_fills_and_pnl_adds_up(tmp_path):
    log, eng = run_once(tmp_path, "a")
    events = log.read(DAY)
    closed = [e for e in events if e["kind"] == "trade_closed"]
    for bot_id, bot in eng.by_id.items():
        mine = [e["pnl"] for e in closed if e["bot"] == bot_id]
        assert round(sum(mine), 2) == bot.pnl_day
    assert len(closed) >= 5, "synthetic day must actually produce trades or this test proves nothing"
    buys = [e for e in events if e["kind"] == "fill" and e["reason_code"] == "ENTRY_FILL"]
    sells = [e for e in events if e["kind"] == "fill" and e["reason_code"] == "EXIT_FILL"]
    assert len(buys) == len(sells) and all(e["fill_source"] == "modeled" for e in buys + sells)


def test_risk_gate_rejects_when_no_quote(tmp_path):
    log = EventLog(str(tmp_path / "c"), "replay")
    eng = Engine(Settings(), log, ModeledBroker(), BarQuoteSource(lambda c, t: [], Settings().half_spread))
    run_replay(eng, make_feed(), DAY)
    kinds = {e["kind"] for e in log.read(DAY)}
    assert "order_sent" not in kinds
    if "order_rejected" in kinds:
        assert {e["reason_code"] for e in log.read(DAY) if e["kind"] == "order_rejected"} == {"NO_QUOTE"}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_engine_replay.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'scalpcity.engine'`

- [ ] **Step 3: Write the implementation**

Create `scalpcity/engine.py`:

```python
import threading
from datetime import date

from .bot import Bot
from .config import BOT_SPECS, TICKERS, Settings
from .contracts import atm_strike, next_trading_day, occ_symbol
from .events import EventLog
from .indicators import IndicatorSet
from .risk import RiskGate
from .triggers import Ema50Cross, RangeBreak, VwapCross
from .types import Bar, OrderIntent

_TRIGGERS = {"vwap": VwapCross, "ema50": Ema50Cross, "range": RangeBreak}


def build_bots(settings: Settings) -> list[Bot]:
    return [Bot(t, spec, _TRIGGERS[key](settings.charge_range_atr), settings)
            for t in TICKERS for key, spec in BOT_SPECS.items()]


class Engine:
    def __init__(self, settings: Settings, log: EventLog, broker, quotes, risk: RiskGate | None = None, bots=None):
        self.s, self.log, self.broker, self.quotes = settings, log, broker, quotes
        self.risk = risk or RiskGate(settings)
        self.bots = bots or build_bots(settings)
        self.by_id = {b.bot_id: b for b in self.bots}
        self.ind = {t: IndicatorSet(settings.atr_period) for t in TICKERS}
        self.stale: set[str] = set()
        self.halted = False
        self.day: date | None = None
        # Live: the bar loop, the stale checks and the pause endpoint all touch the engine from different threads.
        self.lock = threading.RLock()

    def start_session(self, day: date, warm_bars: dict) -> None:
        with self.lock:
            self.day = day
            for ticker in self.ind:
                self.ind[ticker] = IndicatorSet(self.s.atr_period)
                for bar in warm_bars.get(ticker, []):
                    self.ind[ticker].warm(bar)
            for bot in self.bots:
                bot.new_session()

    def _write(self, time, bot, events: list) -> None:
        for ev in events:
            ev = dict(ev)
            self.log.append(time, bot.bot_id, bot.ticker, ev.pop("kind"), ev.pop("state", ""), ev.pop("reason_code", ""),
                            ev.pop("reason_text", ""), ev.pop("inputs", None), ev.pop("charge_pct", None), **ev)

    def on_bar(self, bar: Bar) -> None:
        with self.lock:
            ind = self.ind[bar.ticker]
            ind.update(bar)
            for bot in [b for b in self.bots if b.ticker == bar.ticker]:
                out = bot.on_bar(bar, ind)
                self._write(bar.end, bot, out.events)
                for intent in out.intents:
                    self._execute(bot, intent, bar, ind)

    def _execute(self, bot: Bot, intent: OrderIntent, bar: Bar, ind: IndicatorSet) -> None:
        if intent.kind == "BUY_OPEN":
            expiry = next_trading_day(bar.ts.date())
            contract = occ_symbol(intent.ticker, expiry, intent.right, atm_strike(bar.close))
        else:
            contract = intent.contract
        quote = self.quotes.get(contract, bar.end)
        inputs = ind.as_dict()
        if intent.kind == "BUY_OPEN":
            ok, why = self.risk.check(intent, quote, self.stale, self.halted)
            if not ok:
                self._write(bar.end, bot, [{"kind": "order_rejected", "state": bot.state.value, "reason_code": why,
                                            "reason_text": f"risk gate refused entry: {why}", "inputs": inputs, "charge_pct": None, "contract": contract}])
                self._write(bar.end, bot, bot.on_order_failed("BUY_OPEN", why))
                return
        elif quote is None:
            self._write(bar.end, bot, [{"kind": "order_rejected", "state": bot.state.value, "reason_code": "NO_QUOTE",
                                        "reason_text": "no quote to exit; retrying next bar", "inputs": inputs, "charge_pct": None, "contract": contract}])
            self._write(bar.end, bot, bot.on_order_failed("SELL_CLOSE", "NO_QUOTE"))
            return
        self._write(bar.end, bot, [{"kind": "order_sent", "state": bot.state.value, "reason_code": intent.kind,
                                    "reason_text": f"{intent.kind} {intent.qty} {contract} bid/ask {quote.bid}/{quote.ask}",
                                    "inputs": inputs, "charge_pct": None, "contract": contract, "qty": intent.qty}])
        fill = self.broker.execute(intent, contract, quote, bar.end)
        if fill is None:
            self._write(bar.end, bot, bot.on_order_failed(intent.kind, "NO_FILL"))
            return
        self._write(bar.end, bot, bot.on_fill(fill, inputs))

    def check_stale(self, now, last_bar_wall: dict, open_quote_wall: dict | None = None) -> None:
        """Live only. Implemented in scalpcity/stale.py (plan Task 11)."""
        from .stale import check_stale
        with self.lock:
            check_stale(self, now, last_bar_wall, open_quote_wall or {})

    def set_paused(self, bot_id: str, paused: bool, time) -> None:
        with self.lock:
            bot = self.by_id[bot_id]
            self._write(time, bot, bot.set_paused(paused))
```

Create `scalpcity/replay.py`:

```python
from datetime import date

from .types import Bar


class ReplayFeed:
    """In-memory replay of underlying bars. bars[ticker] is a list of Bar sorted by ts."""

    def __init__(self, bars: dict):
        self.bars = {t: sorted(v, key=lambda b: b.ts) for t, v in bars.items()}

    def days(self) -> list[date]:
        return sorted({b.ts.date() for v in self.bars.values() for b in v})

    def warm_bars(self, day: date, n: int = 200) -> dict:
        out = {}
        for t, v in self.bars.items():
            prior = [b for b in v if b.ts.date() < day]
            out[t] = prior[-n:]
        return out

    def day_bars(self, day: date) -> list[Bar]:
        merged = [b for v in self.bars.values() for b in v if b.ts.date() == day]
        return sorted(merged, key=lambda b: (b.ts, b.ticker))


def run_replay(engine, feed: ReplayFeed, day: date) -> None:
    engine.log.reset(day)
    engine.start_session(day, feed.warm_bars(day))
    for bar in feed.day_bars(day):
        engine.on_bar(bar)
```

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, 40 tests passed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_engine_replay.py scalpcity/engine.py scalpcity/replay.py
git commit -m "feat: engine wiring and deterministic replay"
```

### Task 8: Alpaca history and the replay script

**Files:**
- Create: `scalpcity/alpaca_history.py`
- Create: `scripts/run_replay.py`
- Test: `tests/test_alpaca_history.py`

**Interfaces:**
- Consumes: `Bar`, `ET`; `Engine`, `ReplayFeed`, `run_replay`, `BarQuoteSource`, `ModeledBroker`, `EventLog`.
- Produces: `AlpacaHistory(cache_dir, key=None, secret=None, session=None)` with `.stock_bars(ticker, day) -> list[Bar]` and `.option_closes(contract, day) -> list[(ts, close)]` (read-only GETs, cached under `data/cache`); `parse_alpaca_rows(rows, ticker)`; `scripts/run_replay.py YYYY-MM-DD` prints per-bot trades and P&L.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_alpaca_history.py`:

```python
import json
from datetime import date

from scalpcity.alpaca_history import AlpacaHistory, parse_alpaca_rows


class FakeHttp:
    def __init__(self, pages): self.pages, self.calls = list(pages), 0
    def get(self, url, headers=None, params=None, timeout=None):
        self.calls += 1
        body = self.pages.pop(0)
        return type("R", (), {"status_code": 200, "json": lambda s: body})()


ROWS = [{"t": "2026-10-08T13:30:00Z", "o": 1.0, "h": 2.0, "l": 0.5, "c": 1.5, "v": 10, "n": 1, "vw": 1.2}]


def test_parse_converts_utc_to_new_york():
    bar = parse_alpaca_rows(ROWS, "QQQ")[0]
    assert (bar.ts.hour, bar.ts.minute, bar.close, bar.ticker) == (9, 30, 1.5, "QQQ")


def test_pages_are_joined_and_cached(tmp_path):
    http = FakeHttp([{"bars": {"QQQ": ROWS}, "next_page_token": "t2"}, {"bars": {"QQQ": ROWS}}])
    hist = AlpacaHistory(str(tmp_path), key="k", secret="s", session=http)
    assert len(hist.stock_bars("QQQ", date(2026, 10, 8))) == 2 and http.calls == 2
    assert len(hist.stock_bars("QQQ", date(2026, 10, 8))) == 2 and http.calls == 2   # second call served from cache
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_alpaca_history.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'scalpcity.alpaca_history'`

- [ ] **Step 3: Write the implementation**

Create `scalpcity/alpaca_history.py`:

```python
import json
import os
import time
from datetime import date, datetime, timedelta

import requests

from .types import ET, Bar

URL_STOCK = "https://data.alpaca.markets/v2/stocks/bars"
URL_OPTION = "https://data.alpaca.markets/v1beta1/options/bars"


def parse_alpaca_rows(rows: list[dict], ticker: str) -> list[Bar]:
    return [Bar(ticker, datetime.fromisoformat(r["t"].replace("Z", "+00:00")).astimezone(ET),
                r["o"], r["h"], r["l"], r["c"], r["v"]) for r in rows]


class AlpacaHistory:
    """Read-only historical data for replay. Caches every response on disk. Needs ALPACA keys in env."""

    def __init__(self, cache_dir: str, key: str | None = None, secret: str | None = None, session=None):
        self.cache = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.headers = {"APCA-API-KEY-ID": key or os.environ["ALPACA_API_KEY"],
                        "APCA-API-SECRET-KEY": secret or os.environ["ALPACA_SECRET_KEY"]}
        self.http = session or requests
        self._last = 0.0

    def _get(self, url: str, params: dict) -> dict:
        for attempt in range(6):
            wait = 0.4 - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            r = self.http.get(url, headers=self.headers, params=params, timeout=60)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (404, 422):
                return {"bars": {}}
            time.sleep(2 ** attempt)
        raise RuntimeError(f"alpaca {url} failed: {r.status_code}")

    def _paged(self, url: str, params: dict, symbol: str) -> list[dict]:
        rows, token = [], None
        while True:
            body = self._get(url, {**params, **({"page_token": token} if token else {})})
            rows += body.get("bars", {}).get(symbol, [])
            token = body.get("next_page_token")
            if not token:
                return rows

    def _cached(self, name: str, loader):
        path = os.path.join(self.cache, name + ".json")
        if os.path.exists(path):
            return json.load(open(path))
        data = loader()
        json.dump(data, open(path, "w"))
        return data

    def stock_bars(self, ticker: str, day: date) -> list[Bar]:
        start = datetime(day.year, day.month, day.day, 9, 30, tzinfo=ET).astimezone().isoformat()
        end = datetime(day.year, day.month, day.day, 16, 0, tzinfo=ET).astimezone().isoformat()
        rows = self._cached(f"stock-{ticker}-{day}", lambda: self._paged(
            URL_STOCK, dict(symbols=ticker, timeframe="1Min", start=start, end=end, feed="sip", limit=10000, adjustment="split"), ticker))
        return parse_alpaca_rows(rows, ticker)

    def option_closes(self, contract: str, day: date) -> list[tuple[datetime, float]]:
        rows = self._cached(f"option-{contract}-{day}", lambda: self._paged(
            URL_OPTION, dict(symbols=contract, timeframe="1Min", start=f"{day}T12:00:00Z", end=f"{day}T22:00:00Z", limit=10000), contract))
        return [(datetime.fromisoformat(r["t"].replace("Z", "+00:00")).astimezone(ET), r["c"]) for r in rows]
```

Create `scripts/run_replay.py`:

```python
"""Replay one past trading day through the engine. Read-only data. Usage: python scripts/run_replay.py 2026-10-07"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scalpcity.alpaca_history import AlpacaHistory
from scalpcity.broker import ModeledBroker
from scalpcity.config import TICKERS, Settings
from scalpcity.contracts import HOLIDAYS
from scalpcity.engine import Engine
from scalpcity.events import EventLog
from scalpcity.quotes import BarQuoteSource
from scalpcity.replay import ReplayFeed, run_replay


def load_env(path=".env"):
    for raw in open(path):
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def prior_trading_days(day: date, n: int) -> list[date]:
    out, d = [], day
    while len(out) < n:
        d -= timedelta(days=1)
        if d.weekday() < 5 and d not in HOLIDAYS:
            out.append(d)
    return sorted(out)


def main(day: date) -> None:
    load_env()
    settings = Settings()
    hist = AlpacaHistory("data/cache")
    bars = {t: [b for d in prior_trading_days(day, 2) + [day] for b in hist.stock_bars(t, d)] for t in TICKERS}
    quotes = BarQuoteSource(lambda contract, ts: hist.option_closes(contract, ts.date()), settings.half_spread)
    log = EventLog("logs", "replay")
    engine = Engine(settings, log, ModeledBroker(), quotes)
    run_replay(engine, ReplayFeed(bars), day)
    print(f"events: {len(log.read(day))}  file: {log.path_for(day)}")
    for bot in engine.bots:
        print(f"{bot.bot_id:10s} trades={bot.trades:2d} pnl={bot.pnl_day:9.2f} state={bot.state.value}/{bot.reason_code}")


if __name__ == "__main__":
    main(date.fromisoformat(sys.argv[1]))
```

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, 42 tests passed.

- [ ] **Step 5: Replay a real day (manual check, needs your `.env` Alpaca keys, read-only GETs)**

Run: `.venv/bin/python scripts/run_replay.py 2026-10-07`
Expected: prints `events: <about 3000+>` and nine lines of the form `QQQ-VWAP trades=1 pnl=... state=locked/DAILY_GOAL`. Re-run the same command and confirm `logs/2026-10-07-replay.jsonl` is byte-identical: `md5sum logs/2026-10-07-replay.jsonl` twice gives the same hash.

- [ ] **Step 6: Commit**

```bash
git add tests/test_alpaca_history.py scalpcity/alpaca_history.py scripts/run_replay.py
git commit -m "feat: Alpaca history loader and replay runner"
```

### Task 9: Paper-only guard and Webull response parsers

**Files:**
- Create: `scalpcity/guard.py`
- Create: `scalpcity/webull_parse.py`
- Create: `tests/fixtures/webull/*.json (copied)`
- Test: `tests/test_guard_parse.py`

**Interfaces:**
- Consumes: `Bar`, `Quote`, `ET`.
- Produces: `SANDBOX_HOST`, `GuardError`, `assert_paper_only(env, host, accounts) -> account_row`; `parse_bars(response, ticker, rth_only=True) -> list[Bar]`, `parse_snapshot(response, contract) -> (Quote, delay_minutes) | None`, `parse_occ(contract) -> (underlying, expiry, right, strike)`, `parse_order_detail(detail) -> (status, filled_qty, avg_price)`, `FILLED_PRICE_KEYS`, `FILLED_QTY_KEYS`, `TERMINAL_FAILED`.

- [ ] **Step 1: Copy the real Webull responses captured by the probe into test fixtures**

```bash
mkdir -p tests/fixtures/webull
cp probe/raw/QQQ_bars.json tests/fixtures/webull/stock_bars_QQQ.json
cp probe/raw/QQQ261009C00748000_snapshot.json tests/fixtures/webull/option_snapshot.json
cp probe/raw/QQQ261009C00748000_bars.json tests/fixtures/webull/option_bars.json
```
These files hold market data only (no keys, no account ids). Add them to the commit in the last step.

- [ ] **Step 2: Write the failing tests**

Create `tests/test_guard_parse.py`:

```python
import json
import pathlib
from datetime import date

import pytest

from scalpcity.guard import GuardError, SANDBOX_HOST, assert_paper_only
from scalpcity.webull_parse import parse_bars, parse_occ, parse_order_detail, parse_snapshot

FIX = pathlib.Path(__file__).parent / "fixtures" / "webull"
ENV = {"WEBULL_ENV": "sandbox", "WEBULL_SANDBOX_ACCOUNT_ATTESTED": "true", "WEBULL_PAPER_ACCOUNT_NUMBER": "ACC3J5B"}
ACCOUNTS = [{"account_number": "ACC3GT2", "account_id": "a"}, {"account_number": "ACC3J5B", "account_id": "b"}]


def test_guard_selects_matching_account():
    assert assert_paper_only(ENV, SANDBOX_HOST, ACCOUNTS)["account_id"] == "b"


@pytest.mark.parametrize("mutate,host", [
    ({"WEBULL_ENV": "prod"}, SANDBOX_HOST),
    ({"WEBULL_SANDBOX_ACCOUNT_ATTESTED": "false"}, SANDBOX_HOST),
    ({}, "api.webull.com"),
    ({"WEBULL_PAPER_ACCOUNT_NUMBER": "NOPE"}, SANDBOX_HOST),
    ({"WEBULL_PAPER_ACCOUNT_NUMBER": ""}, SANDBOX_HOST),
])
def test_guard_refuses(mutate, host):
    with pytest.raises(GuardError):
        assert_paper_only({**ENV, **mutate}, host, ACCOUNTS)


def test_parse_real_stock_bars_fixture():
    bars = parse_bars(json.loads((FIX / "stock_bars_QQQ.json").read_text()), "QQQ")
    assert len(bars) == 5 and bars == sorted(bars, key=lambda b: b.ts)
    assert bars[-1].ts.hour == 15 and bars[-1].ts.minute == 59 and bars[-1].close == 747.58


def test_parse_real_option_snapshot_fixture():
    quote, delay = parse_snapshot(json.loads((FIX / "option_snapshot.json").read_text()), "QQQ261009C00748000")
    assert (quote.bid, quote.ask, delay) == (2.92, 2.95, 0)
    assert quote.ts.tzinfo is not None


def test_parse_snapshot_none_without_bid_ask():
    assert parse_snapshot([{"bid": "", "ask": ""}], "X") is None


def test_parse_occ():
    assert parse_occ("SPY261009C00774000") == ("SPY", date(2026, 10, 9), "CALL", 774.0)
    with pytest.raises(ValueError):
        parse_occ("garbage")


def test_parse_order_detail_statuses():
    assert parse_order_detail({"orders": [{"status": "SUBMITTED"}]}) == ("SUBMITTED", None, None)
    assert parse_order_detail({"orders": [{"status": "filled", "filled_quantity": "10", "filled_price": "2.95"}]}) == ("FILLED", 10.0, 2.95)
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_guard_parse.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'scalpcity.guard'`

- [ ] **Step 4: Write the implementation**

Create `scalpcity/guard.py`:

```python
from typing import Mapping

SANDBOX_HOST = "api.sandbox.webull.com"


class GuardError(RuntimeError):
    pass


def assert_paper_only(env: Mapping[str, str], host: str, accounts: list[dict]) -> dict:
    """Refuse to continue unless everything says paper/sandbox. Returns the selected account row."""
    if env.get("WEBULL_ENV", "").lower() != "sandbox":
        raise GuardError("WEBULL_ENV must be 'sandbox'")
    if env.get("WEBULL_SANDBOX_ACCOUNT_ATTESTED", "").lower() != "true":
        raise GuardError("WEBULL_SANDBOX_ACCOUNT_ATTESTED must be 'true'")
    if host != SANDBOX_HOST:
        raise GuardError(f"host must be {SANDBOX_HOST}, got {host}")
    wanted = env.get("WEBULL_PAPER_ACCOUNT_NUMBER", "")
    match = [a for a in accounts if wanted and a.get("account_number") == wanted]
    if len(match) != 1:
        raise GuardError(f"WEBULL_PAPER_ACCOUNT_NUMBER matches {len(match)} sandbox accounts; need exactly 1")
    return match[0]
```

Create `scalpcity/webull_parse.py`:

```python
import re
from datetime import date, datetime
from typing import Any

from .types import ET, Bar, Quote

# Confirm these against a FILLED order's detail JSON in the phase-0 capture (plan Task 12).
FILLED_PRICE_KEYS = ("filled_price", "avg_filled_price", "average_filled_price", "avg_price")
FILLED_QTY_KEYS = ("filled_quantity", "filled_qty", "total_filled_quantity")
TERMINAL_FAILED = {"CANCELLED", "REJECTED", "FAILED", "EXPIRED"}


def _bar_rows(obj: Any) -> list[dict]:
    """Find the list of bar dicts (have 'time' and 'close') anywhere in a response."""
    if isinstance(obj, list):
        if obj and isinstance(obj[0], dict) and "close" in obj[0] and "time" in obj[0]:
            return obj
        for item in obj:
            found = _bar_rows(item)
            if found:
                return found
    elif isinstance(obj, dict):
        for value in obj.values():
            found = _bar_rows(value)
            if found:
                return found
    return []


def _parse_time(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%f%z").astimezone(ET)


def parse_bars(response: Any, ticker: str, rth_only: bool = True) -> list[Bar]:
    rows = _bar_rows(response)
    bars = [Bar(ticker, _parse_time(r["time"]), float(r["open"]), float(r["high"]), float(r["low"]),
                float(r["close"]), float(r.get("volume") or 0))
            for r in rows if not rth_only or r.get("trading_session", "RTH") == "RTH"]
    return sorted(bars, key=lambda b: b.ts)


def parse_snapshot(response: Any, contract: str) -> tuple[Quote, int] | None:
    """Returns (Quote, delay_minutes) or None when bid/ask are missing."""
    row = response[0] if isinstance(response, list) and response else response
    if not isinstance(row, dict) or not row.get("bid") or not row.get("ask"):
        return None
    ts = datetime.fromtimestamp(int(row["quote_time"]) / 1000, ET)
    return Quote(contract, ts, float(row["bid"]), float(row["ask"])), int(row.get("delay_minutes") or 0)


def parse_occ(contract: str) -> tuple[str, date, str, float]:
    m = re.fullmatch(r"([A-Z]+)(\d{6})([CP])(\d{8})", contract)
    if not m:
        raise ValueError(f"not an OCC symbol: {contract}")
    root, ymd, cp, strike = m.groups()
    return root, datetime.strptime(ymd, "%y%m%d").date(), "CALL" if cp == "C" else "PUT", int(strike) / 1000


def _find_key(obj: Any, keys: tuple) -> Any:
    if isinstance(obj, dict):
        for k in keys:
            if obj.get(k) not in (None, "", "0", 0):
                return obj[k]
        for v in obj.values():
            found = _find_key(v, keys)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_key(v, keys)
            if found is not None:
                return found
    return None


def parse_order_detail(detail: Any) -> tuple[str, float | None, float | None]:
    """(status, filled_qty, avg_fill_price). status is the first leg's status, upper-case."""
    order = detail["orders"][0] if isinstance(detail, dict) and detail.get("orders") else detail
    status = str(order.get("status", "")).upper()
    qty = _find_key(order, FILLED_QTY_KEYS)
    price = _find_key(order, FILLED_PRICE_KEYS)
    return status, (float(qty) if qty is not None else None), (float(price) if price is not None else None)
```

- [ ] **Step 5: Run the full suite to verify it passes**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, 53 tests passed.

- [ ] **Step 6: Commit**

```bash
git add tests/test_guard_parse.py scalpcity/guard.py scalpcity/webull_parse.py tests/fixtures/webull
git commit -m "feat: paper-only guard and Webull response parsers"
```

### Task 10: Webull client, paper broker and live feed

**Files:**
- Create: `scalpcity/webull_client.py`
- Create: `scalpcity/webull_broker.py`
- Create: `scalpcity/live.py`
- Test: `tests/test_live_broker.py`

**Interfaces:**
- Consumes: `parse_bars`, `parse_snapshot`, `parse_occ`, `parse_order_detail`, `TERMINAL_FAILED`, `SANDBOX_HOST`, `ModeledBroker`, `OrderIntent`, `Quote`, `Fill`, `Bar`.
- Produces: `WebullClient(data, trade)` with `.from_env(env)`, `.recent_bars(ticker, count=3) -> list[Bar]`, `.option_quote(contract) -> (Quote, delay) | None`, `.accounts() -> list[dict]`, `.place_option(account_id, contract, side, qty, limit) -> client_order_id`, `.order_detail(account_id, client_order_id) -> dict`, `.cancel_option(account_id, client_order_id)`; `WebullPaperBroker(client, account_id, fill_timeout_s=15.0, poll_s=1.0, sleep=time.sleep, fallback=None)` with `.execute(intent, contract, quote, ts) -> Fill | None` (marketable limit; fills labelled `'broker'`; falls back to the modeled broker when placing raises; cancels and returns None on timeout); `LiveFeed(client, tickers, now_fn, lag_s=2.0, count=3)` with `.warm_bars(count=300)`, `.poll() -> list[Bar]`, `.last_bar_wall`; `LiveQuoteSource(client).get(contract, ts)`; `market_open(now) -> bool`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_live_broker.py`:

```python
import json
import pathlib
from datetime import datetime, timedelta
from types import SimpleNamespace

from scalpcity.broker import ModeledBroker
from scalpcity.live import LiveFeed, market_open
from scalpcity.types import Bar, ET, OrderIntent, Quote
from scalpcity.webull_broker import WebullPaperBroker
from scalpcity.webull_client import WebullClient

NOW = datetime(2026, 10, 8, 10, 5, 30, tzinfo=ET)


def bar(ticker, hh, mm, close=100.0):
    return Bar(ticker, datetime(2026, 10, 8, hh, mm, tzinfo=ET), close, close, close, close, 1.0)


class FakeBars:
    def __init__(self, rows): self.rows = rows
    def recent_bars(self, ticker, count): return list(self.rows.get(ticker, []))[-count:]


def test_live_feed_emits_only_completed_new_bars_once():
    rows = {"QQQ": [bar("QQQ", 10, 3), bar("QQQ", 10, 4), bar("QQQ", 10, 5)]}  # 10:05 bar ends 10:06 -> still forming
    clock = [NOW]
    feed = LiveFeed(FakeBars(rows), ["QQQ"], lambda: clock[0])
    assert [b.ts.minute for b in feed.poll()] == [3, 4]
    assert feed.poll() == []                                  # nothing new, nothing repeated
    rows["QQQ"].append(bar("QQQ", 10, 6))
    clock[0] = NOW + timedelta(seconds=40)                    # 10:06:10 -> the 10:05 bar is now complete
    assert [b.ts.minute for b in feed.poll()] == [5]
    assert feed.last_bar_wall["QQQ"] == NOW + timedelta(seconds=40)


def test_market_open_hours():
    assert market_open(datetime(2026, 10, 8, 9, 30, tzinfo=ET))
    assert not market_open(datetime(2026, 10, 8, 9, 29, tzinfo=ET))
    assert not market_open(datetime(2026, 10, 8, 16, 0, tzinfo=ET))
    assert not market_open(datetime(2026, 10, 10, 11, 0, tzinfo=ET))  # Saturday


class FakeWebull:
    def __init__(self, statuses, fail_place=False):
        self.statuses, self.fail_place, self.cancelled, self.placed = list(statuses), fail_place, [], []
    def place_option(self, account_id, contract, side, qty, limit):
        if self.fail_place: raise RuntimeError("sandbox rejects options")
        self.placed.append((contract, side, qty, limit)); return "oid1"
    def order_detail(self, account_id, oid):
        s = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
        return {"orders": [dict(s)]}
    def cancel_option(self, account_id, oid): self.cancelled.append(oid)


def intent(kind="BUY_OPEN"):
    return OrderIntent("QQQ-VWAP", "QQQ", kind, "CALL", 10, "signal", 748.0, contract="QQQ261009C00748000")


QUOTE = Quote("QQQ261009C00748000", NOW, 2.92, 2.95)


def test_paper_broker_fills_at_ask_and_labels_broker():
    fake = FakeWebull([{"status": "SUBMITTED"}, {"status": "FILLED", "filled_quantity": "10", "filled_price": "2.94"}])
    b = WebullPaperBroker(fake, "acct", sleep=lambda s: None)
    fill = b.execute(intent(), "QQQ261009C00748000", QUOTE, NOW)
    assert (fill.price, fill.qty, fill.source) == (2.94, 10, "broker")
    assert fake.placed == [("QQQ261009C00748000", "BUY", 10, 2.95)]


def test_paper_broker_sells_at_bid_and_cancels_on_timeout():
    fake = FakeWebull([{"status": "SUBMITTED"}])
    b = WebullPaperBroker(fake, "acct", fill_timeout_s=3, sleep=lambda s: None)
    assert b.execute(intent("SELL_CLOSE"), "QQQ261009C00748000", QUOTE, NOW) is None
    assert fake.placed[0][1:] == ("SELL", 10, 2.92) and fake.cancelled == ["oid1"]


def test_paper_broker_returns_none_on_terminal_reject():
    fake = FakeWebull([{"status": "REJECTED"}])
    assert WebullPaperBroker(fake, "a", sleep=lambda s: None).execute(intent(), "C", QUOTE, NOW) is None


def test_paper_broker_falls_back_to_modeled_when_place_fails():
    b = WebullPaperBroker(FakeWebull([{}], fail_place=True), "a", fallback=ModeledBroker())
    fill = b.execute(intent(), "QQQ261009C00748000", QUOTE, NOW)
    assert (fill.price, fill.source) == (2.95, "modeled")


def test_webull_client_parses_stock_bars_and_snapshot_from_real_fixtures():
    fix = pathlib.Path(__file__).parent / "fixtures" / "webull"
    stock = json.loads((fix / "stock_bars_QQQ.json").read_text())
    snap = json.loads((fix / "option_snapshot.json").read_text())
    data = SimpleNamespace(
        market_data=SimpleNamespace(get_history_bar=lambda *a, **k: SimpleNamespace(json=lambda: stock)),
        option_market_data=SimpleNamespace(get_option_snapshot=lambda *a, **k: SimpleNamespace(json=lambda: snap)))
    client = WebullClient(data, SimpleNamespace())
    assert len(client.recent_bars("QQQ", 5)) == 5
    quote, delay = client.option_quote("QQQ261009C00748000")
    assert (quote.bid, quote.ask, delay) == (2.92, 2.95, 0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_live_broker.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'scalpcity.live'`

- [ ] **Step 3: Write the implementation**

Create `scalpcity/webull_client.py`:

```python
import uuid
from datetime import datetime

from .guard import SANDBOX_HOST
from .types import Bar, Quote
from .webull_parse import parse_bars, parse_occ, parse_snapshot


def _json(response):
    return response.json() if hasattr(response, "json") else response


class WebullClient:
    """Thin wrapper over the Webull SDK. `data` and `trade` are injectable for tests."""

    def __init__(self, data, trade):
        self.data, self.trade = data, trade

    @classmethod
    def from_env(cls, env) -> "WebullClient":
        from webull.core.client import ApiClient
        from webull.data.data_client import DataClient
        from webull.trade.trade_client import TradeClient
        api = ApiClient(env["WEBULL_APP_KEY"], env["WEBULL_APP_SECRET"], "us")
        api.add_endpoint("us", SANDBOX_HOST)
        api._stream_logger_set = True   # no SDK console/file logging: it can print request headers
        api._file_logger_set = True
        return cls(DataClient(api), TradeClient(api))

    # ---- data ----
    def recent_bars(self, ticker: str, count: int = 3) -> list[Bar]:
        resp = self.data.market_data.get_history_bar(ticker, "US_STOCK", "M1", count=str(count),
                                                     real_time_required=True, trading_sessions="RTH")
        return parse_bars(_json(resp), ticker)

    def option_quote(self, contract: str) -> tuple[Quote, int] | None:
        resp = self.data.option_market_data.get_option_snapshot(contract, "US_OPTION")
        return parse_snapshot(_json(resp), contract)

    # ---- account / orders ----
    def accounts(self) -> list[dict]:
        rows = _json(self.trade.account_v2.get_account_list())
        return rows if isinstance(rows, list) else rows.get("data") or []

    def place_option(self, account_id: str, contract: str, side: str, qty: int, limit: float) -> str:
        underlying, expiry, right, strike = parse_occ(contract)
        client_order_id = uuid.uuid4().hex[:32]
        order = [{
            "client_order_id": client_order_id, "combo_type": "NORMAL", "order_type": "LIMIT", "quantity": str(qty),
            "limit_price": f"{limit:.2f}", "option_strategy": "SINGLE", "side": side, "time_in_force": "DAY",
            "entrust_type": "QTY",
            "orders": [{"side": side, "quantity": str(qty), "symbol": underlying, "strike_price": f"{strike:.1f}",
                        "init_exp_date": str(expiry), "instrument_type": "OPTION", "option_type": right, "market": "US"}],
        }]
        resp = self.trade.order_v2.place_option(account_id, order)
        status = getattr(resp, "status_code", 200)
        if status != 200:
            raise RuntimeError(f"place_option http {status}: {str(_json(resp))[:200]}")
        return client_order_id

    def order_detail(self, account_id: str, client_order_id: str) -> dict:
        return _json(self.trade.order_v2.get_order_detail(account_id, client_order_id))

    def cancel_option(self, account_id: str, client_order_id: str) -> None:
        self.trade.order_v2.cancel_option(account_id, client_order_id)
```

Create `scalpcity/webull_broker.py`:

```python
import time as _time
from datetime import datetime

from .broker import ModeledBroker
from .types import Fill, OrderIntent, Quote
from .webull_parse import TERMINAL_FAILED, parse_order_detail


class WebullPaperBroker:
    """Places a marketable LIMIT on the Webull sandbox and waits for the fill.

    Buys at the ask, sells at the bid. If placing fails (e.g. the sandbox rejects option orders), falls back to
    the ModeledBroker, which labels the fill 'modeled'. Not filled in time -> cancel and return None.
    """
    source = "broker"

    def __init__(self, client, account_id: str, fill_timeout_s: float = 15.0, poll_s: float = 1.0,
                 sleep=_time.sleep, fallback: ModeledBroker | None = None):
        self.client, self.account_id = client, account_id
        self.fill_timeout_s, self.poll_s, self.sleep = fill_timeout_s, poll_s, sleep
        self.fallback = fallback

    def execute(self, intent: OrderIntent, contract: str, quote: Quote, ts: datetime) -> Fill | None:
        side = "BUY" if intent.kind == "BUY_OPEN" else "SELL"
        limit = quote.ask if side == "BUY" else quote.bid
        try:
            order_id = self.client.place_option(self.account_id, contract, side, intent.qty, limit)
        except Exception:
            return self.fallback.execute(intent, contract, quote, ts) if self.fallback else None
        waited = 0.0
        while waited <= self.fill_timeout_s:
            status, qty, price = parse_order_detail(self.client.order_detail(self.account_id, order_id))
            if status == "FILLED":
                return Fill(intent.bot_id, intent.kind, contract, int(qty or intent.qty), round(price or limit, 2), self.source, ts)
            if status in TERMINAL_FAILED:
                return None
            self.sleep(self.poll_s)
            waited += self.poll_s
        self.client.cancel_option(self.account_id, order_id)
        return None
```

Create `scalpcity/live.py`:

```python
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
```

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, 60 tests passed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_live_broker.py scalpcity/webull_client.py scalpcity/webull_broker.py scalpcity/live.py
git commit -m "feat: Webull client, paper broker and live bar feed"
```

### Task 11: Stale-data handling

**Files:**
- Create: `scalpcity/stale.py`
- Test: `tests/test_stale.py`

**Interfaces:**
- Consumes: `Engine` (Task 7, whose `check_stale` imports this module), `market_open` (Task 10), `State`, `OrderIntent`.
- Produces: `check_stale(engine, now, last_bar_wall, open_quote_wall)`: marks tickers stale after 120 s without a bar (market hours only), blocks entries for stale tickers via `engine.stale`, marks in-trade bots stale after 30 s without an option quote, and flattens them after 300 s.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_stale.py`:

```python
from datetime import date, datetime, timedelta
from types import SimpleNamespace

from scalpcity.broker import ModeledBroker
from scalpcity.config import Settings
from scalpcity.engine import Engine
from scalpcity.events import EventLog
from scalpcity.types import ET, Quote

NOW = datetime(2026, 10, 8, 10, 5, 30, tzinfo=ET)


def test_engine_marks_ticker_stale_and_blocks_entries(tmp_path):
    log = EventLog(str(tmp_path), "live")
    eng = Engine(Settings(), log, ModeledBroker(), SimpleNamespace(get=lambda c, t: None))
    eng.start_session(date(2026, 10, 8), {})
    wall = {"QQQ": NOW - timedelta(seconds=200), "SPY": NOW - timedelta(seconds=10), "IWM": NOW - timedelta(seconds=10)}
    eng.check_stale(NOW, wall)
    assert eng.stale == {"QQQ"}
    assert eng.by_id["QQQ-VWAP"].state.value == "stale" and eng.by_id["SPY-VWAP"].state.value != "stale"
    eng.check_stale(NOW, {**wall, "QQQ": NOW - timedelta(seconds=5)})
    assert eng.stale == set()


def test_engine_flattens_bot_stale_in_trade_after_5_minutes(tmp_path):
    from scalpcity.bot import Position, State
    log = EventLog(str(tmp_path), "live")
    quotes = SimpleNamespace(get=lambda c, t: Quote(c, t, 2.0, 2.1))
    eng = Engine(Settings(), log, ModeledBroker(), quotes)
    eng.start_session(date(2026, 10, 8), {})
    bot = eng.by_id["QQQ-VWAP"]
    bot.position = Position("CALL", 10, 748.0, 747.0, 750.0, contract="QQQ261009C00748000", entry_price=3.0, opened_at=NOW)
    bot.state = State.MANAGING
    wall = {t: NOW for t in ("QQQ", "SPY", "IWM")}
    eng.check_stale(NOW, wall, {"QQQ-VWAP": NOW - timedelta(seconds=310)})
    assert bot.position is None and bot.pnl_day == -1000.0     # sold at the 2.00 bid: (2.00-3.00)*10*100
    kinds = [e["kind"] for e in log.read(NOW.date())]
    assert "feed_stale" in kinds and "trade_closed" in kinds
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_stale.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'scalpcity.stale'`

- [ ] **Step 3: Write the implementation**

Create `scalpcity/stale.py`:

```python
from .bot import State
from .live import market_open
from .types import OrderIntent


def check_stale(engine, now, last_bar_wall: dict, open_quote_wall: dict) -> None:
    """now / last_bar_wall / open_quote_wall are wall-clock datetimes.

    A ticker is stale when no new bar for stale_idle_s (market hours only). Entries are blocked for stale tickers
    through engine.stale. A bot in a trade is stale when its option quote is older than stale_in_trade_s, and is
    flattened once that age passes flatten_after_stale_s.
    """
    s = engine.s
    if not market_open(now):
        engine.stale.clear()
        return
    for ticker in engine.ind:
        seen = last_bar_wall.get(ticker)
        age = (now - seen).total_seconds() if seen else None
        is_stale = age is None or age > s.stale_idle_s
        if is_stale:
            engine.stale.add(ticker)
        else:
            engine.stale.discard(ticker)
        text = f"no bar for {int(age)}s" if age is not None else "no bars yet"
        for bot in [b for b in engine.bots if b.ticker == ticker and b.position is None]:
            engine._write(now, bot, bot.set_stale(is_stale, text))
    for bot in engine.bots:
        if bot.position is None or bot.pending == "entry":
            continue
        seen = open_quote_wall.get(bot.bot_id)
        age = (now - seen).total_seconds() if seen else None
        quote_stale = age is None or age > s.stale_in_trade_s
        engine._write(now, bot, bot.set_stale(quote_stale, f"option quote {int(age)}s old" if age is not None else "no option quote"))
        if quote_stale and age is not None and age > s.flatten_after_stale_s and bot.pending is None:
            bot.pending = "exit"
            bot._set(State.EXITING, "EXIT_STALE", "flattening: data stale too long")
            engine._write(now, bot, [bot._snapshot_event("state_change", {}, None)])
            intent = OrderIntent(bot.bot_id, bot.ticker, "SELL_CLOSE", bot.position.right, bot.position.qty, "STALE",
                                 bot.position.entry_und, contract=bot.position.contract)
            quote = engine.quotes.get(intent.contract, now)
            if quote is None:
                engine._write(now, bot, bot.on_order_failed("SELL_CLOSE", "NO_QUOTE"))
                continue
            fill = engine.broker.execute(intent, intent.contract, quote, now)
            engine._write(now, bot, bot.on_fill(fill, {}) if fill else bot.on_order_failed("SELL_CLOSE", "NO_FILL"))
```

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, 62 tests passed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_stale.py scalpcity/stale.py
git commit -m "feat: stale-data detection, entry block and flatten"
```

### Task 12: Phase-0 market-open script and live runner

**Files:**
- Create: `scripts/phase0_market_open.py`
- Create: `scripts/run_live.py`

**Interfaces:**
- Consumes: `WebullClient`, `assert_paper_only`, `WebullPaperBroker`, `LiveFeed`, `LiveQuoteSource`, `Engine`, `EventLog`, `create_app` (Task 13, imported by `run_live.py` only).
- Produces: `scripts/phase0_market_open.py [--place]` (quote freshness over 60 s; with `--place`, one resting 1-contract SPY call order, a 30 s wait, a cancel, and a saved order-detail fixture; with `--fill-test`, buy 1 and sell it back and save the filled order detail); `scripts/run_live.py` (starts the engine plus the dashboard server on `http://127.0.0.1:8000`).

- [ ] **Step 1: Note**

This task has no unit tests; both scripts are verified by running them. `run_live.py` imports `scalpcity.server`, created in Task 13, so run `run_live.py` only after Task 13.

- [ ] **Step 2: Write the implementation**

Create `scripts/phase0_market_open.py`:

```python
"""Phase-0 checks for market hours (run ~10:00 ET on a trading day, in manual permission mode).

1. Option quote freshness: polls 3 contracts for 60 s, prints quote age and delay flag.
2. Option order path: places ONE resting 1-contract limit far below the market, waits 30 s, cancels.
3. --place saves the resting-order detail JSON to tests/fixtures/webull/.
4. --fill-test buys 1 SPY call at the ask, waits for the fill, sells it back at the bid, and saves both filled
   order-detail JSONs so FILLED_PRICE_KEYS / FILLED_QTY_KEYS can be confirmed.
Run: python scripts/phase0_market_open.py [--place] [--fill-test]
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scalpcity.contracts import atm_strike, next_trading_day, occ_symbol
from scalpcity.guard import SANDBOX_HOST, assert_paper_only
from scalpcity.types import ET
from scalpcity.webull_client import WebullClient


def load_env(path=".env"):
    for raw in open(path):
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def wait_filled(client, account_id, order_id, seconds=30):
    detail = None
    for _ in range(seconds):
        detail = client.order_detail(account_id, order_id)
        if detail["orders"][0]["status"].upper() == "FILLED":
            break
        time.sleep(1)
    return detail


def fill_test(client, account_id, contract):
    """Sandbox only: marketable BUY 1 at the ask, wait for FILLED, then SELL 1 at the bid and wait."""
    quote, _ = client.option_quote(contract)
    print(f"buying 1 {contract} at the ask {quote.ask}")
    buy_id = client.place_option(account_id, contract, "BUY", 1, quote.ask)
    buy = wait_filled(client, account_id, buy_id)
    quote, _ = client.option_quote(contract)
    print(f"selling 1 {contract} at the bid {quote.bid}")
    sell_id = client.place_option(account_id, contract, "SELL", 1, quote.bid)
    sell = wait_filled(client, account_id, sell_id)
    os.makedirs("tests/fixtures/webull", exist_ok=True)
    json.dump({"buy": buy, "sell": sell}, open("tests/fixtures/webull/option_filled_order_detail.json", "w"), indent=1)
    print("buy status:", buy["orders"][0]["status"], "| sell status:", sell["orders"][0]["status"])
    print("fields on the filled order:", sorted(buy["orders"][0].keys()))


def main():
    load_env()
    client = WebullClient.from_env(os.environ)
    account = assert_paper_only(os.environ, SANDBOX_HOST, client.accounts())
    now = datetime.now(ET)
    expiry = next_trading_day(now.date())
    contracts = {}
    for t in ("QQQ", "SPY", "IWM"):
        bars = client.recent_bars(t, 1)
        contracts[t] = occ_symbol(t, expiry, "CALL", atm_strike(bars[-1].close))
    print("contracts:", contracts)
    print("--- quote freshness, 12 polls over 60 s ---")
    for i in range(12):
        row = []
        for t, c in contracts.items():
            got = client.option_quote(c)
            if got is None:
                row.append(f"{t}: none")
                continue
            quote, delay = got
            age = (datetime.now(ET) - quote.ts).total_seconds()
            row.append(f"{t}: {quote.bid}/{quote.ask} age={age:.1f}s delay={delay}m")
        print(datetime.now(ET).strftime("%H:%M:%S"), " | ".join(row))
        time.sleep(5)
    if "--place" not in sys.argv and "--fill-test" not in sys.argv:
        print("quote check only. Re-run with --place (resting order) or --fill-test (buy and sell back 1 contract).")
        return
    contract = contracts["SPY"]
    if "--fill-test" in sys.argv:
        fill_test(client, account["account_id"], contract)
        return
    got = client.option_quote(contract)
    print("placing 1 SPY call limit 0.05 (market ~", got[0].ask if got else "?", ") then cancelling after 30 s")
    oid = client.place_option(account["account_id"], contract, "BUY", 1, 0.05)
    detail1 = client.order_detail(account["account_id"], oid)
    time.sleep(30)
    detail2 = client.order_detail(account["account_id"], oid)
    client.cancel_option(account["account_id"], oid)
    detail3 = client.order_detail(account["account_id"], oid)
    os.makedirs("tests/fixtures/webull", exist_ok=True)
    json.dump({"submitted": detail1, "after_30s": detail2, "cancelled": detail3}, open("tests/fixtures/webull/option_order_detail.json", "w"), indent=1)
    print("saved tests/fixtures/webull/option_order_detail.json; statuses:",
          [d["orders"][0]["status"] for d in (detail1, detail2, detail3)])


if __name__ == "__main__":
    main()
```

Create `scripts/run_live.py`:

```python
"""Live paper run: Webull sandbox feed + paper orders + API server on http://127.0.0.1:8000
Start before 9:30 ET on a trading day, in a 3.11 venv:  .venv/bin/python scripts/run_live.py
"""
import os
import sys
import threading
import time
from datetime import datetime

import uvicorn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scalpcity.broker import ModeledBroker
from scalpcity.config import TICKERS, Settings
from scalpcity.engine import Engine
from scalpcity.events import EventLog
from scalpcity.guard import SANDBOX_HOST, assert_paper_only
from scalpcity.live import LiveFeed, LiveQuoteSource, market_open
from scalpcity.server import create_app
from scalpcity.types import ET
from scalpcity.webull_broker import WebullPaperBroker
from scalpcity.webull_client import WebullClient


def load_env(path=".env"):
    for raw in open(path):
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def main():
    load_env()
    client = WebullClient.from_env(os.environ)
    account = assert_paper_only(os.environ, SANDBOX_HOST, client.accounts())
    settings, log = Settings(), EventLog("logs", "live")
    broker = WebullPaperBroker(client, account["account_id"], fallback=ModeledBroker())
    engine = Engine(settings, log, broker, LiveQuoteSource(client))
    feed = LiveFeed(client, TICKERS, lambda: datetime.now(ET))
    engine.start_session(datetime.now(ET).date(), feed.warm_bars())
    app = create_app(log, lambda: datetime.now(ET).date(), engine.set_paused, [b.bot_id for b in engine.bots])
    threading.Thread(target=uvicorn.run, args=(app,), kwargs=dict(host="127.0.0.1", port=8000, log_level="warning"), daemon=True).start()
    print("Scalp City live (paper). Dashboard: http://127.0.0.1:8000   Ctrl+C to stop.", flush=True)
    quote_wall: dict[str, datetime] = {}
    while True:
        now = datetime.now(ET)
        if market_open(now):
            for bar in feed.poll():
                engine.on_bar(bar)
            for bot in engine.bots:
                if bot.position is not None and bot.position.contract:
                    if client.option_quote(bot.position.contract):
                        quote_wall[bot.bot_id] = now
        engine.check_stale(now, feed.last_bar_wall, quote_wall)
        time.sleep(5)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Syntax-check both scripts**

Run: `.venv/bin/python -c "import ast; [ast.parse(open(f).read()) for f in ('scripts/phase0_market_open.py','scripts/run_live.py')]; print('ok')"`
Expected: `ok`.

- [ ] **Step 4: Phase 0 at the next market open (~10:00 ET on a trading day; run in manual permission mode so you approve the order)**

Run in the terminal pane: `.venv/bin/python scripts/phase0_market_open.py --place`
Expected: 12 lines of `QQQ: bid/ask age=...s delay=0m ...` with ages mostly under 5 s, then `saved tests/fixtures/webull/option_order_detail.json; statuses: ['SUBMITTED', 'SUBMITTED', 'CANCELLED']`.

If an age stays above 30 s, quotes are not real-time: stop and re-check the OPRA non-display subscription before going live.

- [ ] **Step 5: Confirm the fill-field names (same session, manual permission mode)**

A resting order never fills, so the saved JSON has no fill fields. Run: `.venv/bin/python scripts/phase0_market_open.py --fill-test`
It buys 1 SPY 1DTE call at the ask, waits for FILLED, sells it back at the bid, and saves `tests/fixtures/webull/option_filled_order_detail.json`.
Expected: `buy status: FILLED | sell status: FILLED` and a `fields on the filled order:` list.

Open the saved JSON and find the keys holding the filled price and filled quantity. If they are not already in `FILLED_PRICE_KEYS` / `FILLED_QTY_KEYS` in `scalpcity/webull_parse.py`, add them to those tuples. Then add a test to `tests/test_guard_parse.py` that loads `option_filled_order_detail.json`, feeds `['buy']` to `parse_order_detail`, and asserts the returned tuple is `('FILLED', 1.0, <the buy price in the JSON>)`. Run the full suite; expected `63 passed`. Commit the fixture and test: `git add tests/fixtures/webull scalpcity/webull_parse.py tests/test_guard_parse.py && git commit -m "test: confirm Webull filled-order fields"`.

- [ ] **Step 6: Commit**

```bash
git add scripts/phase0_market_open.py scripts/run_live.py
git commit -m "feat: phase-0 market-open checks and live runner"
```

### Task 13: API server

**Files:**
- Create: `scalpcity/server.py`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `EventLog`, `build_snapshot`, `ET`.
- Produces: `Hub` (thread-safe fan-out); `create_app(log, day_fn, set_paused, bot_ids, web_dir=None) -> FastAPI` exposing `GET /snapshot`, `POST /control/pause {bot, paused}` (404 for unknown bot), `WS /ws` (sends `{type:'snapshot',...}` then `{type:'event',event:{...}}`), and static files from `web/`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_server.py`:

```python
from datetime import date, datetime

from fastapi.testclient import TestClient

from scalpcity.events import EventLog
from scalpcity.server import create_app
from scalpcity.types import ET

DAY = date(2026, 10, 8)
BOTS = ["QQQ-VWAP", "QQQ-EMA50"]


def t(h, m):
    return datetime(2026, 10, 8, h, m, tzinfo=ET)


def make(tmp_path):
    log = EventLog(str(tmp_path), "live")
    calls = []
    app = create_app(log, lambda: DAY, lambda bot, paused, when: calls.append((bot, paused)), BOTS, web_dir=str(tmp_path / "nonexistent"))
    return log, calls, app


def test_snapshot_lists_every_bot_even_before_events(tmp_path):
    log, _, app = make(tmp_path)
    with TestClient(app) as client:
        snap = client.get("/snapshot").json()
        assert set(snap["bots"]) == set(BOTS) and snap["bots"]["QQQ-VWAP"]["reason_code"] == "NO_DATA"
        log.append(t(9, 31), "QQQ-VWAP", "QQQ", "tick", state="forming", reason_code="WATCHING", charge_pct=55.0)
        assert client.get("/snapshot").json()["bots"]["QQQ-VWAP"]["state"] == "forming"


def test_websocket_sends_snapshot_then_streams_new_events(tmp_path):
    log, _, app = make(tmp_path)
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            first = ws.receive_json()
            assert first["type"] == "snapshot" and "QQQ-VWAP" in first["bots"]
            log.append(t(9, 32), "QQQ-VWAP", "QQQ", "state_change", state="fired", reason_code="SIGNAL")
            msg = ws.receive_json()
            assert msg["type"] == "event" and msg["event"]["state"] == "fired"


def test_pause_endpoint_calls_back_and_rejects_unknown_bot(tmp_path):
    _, calls, app = make(tmp_path)
    with TestClient(app) as client:
        assert client.post("/control/pause", json={"bot": "QQQ-VWAP", "paused": True}).json()["ok"] is True
        assert calls == [("QQQ-VWAP", True)]
        assert client.post("/control/pause", json={"bot": "NOPE", "paused": True}).status_code == 404
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_server.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'scalpcity.server'`

- [ ] **Step 3: Write the implementation**

Create `scalpcity/server.py`:

```python
import asyncio
import pathlib
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Callable

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .events import EventLog, build_snapshot
from .types import ET


class Hub:
    """Fans events out to websocket clients. push() may be called from any thread."""

    def __init__(self):
        self.clients: set[asyncio.Queue] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    def push(self, event: dict) -> None:
        if self.loop is None:
            return
        for q in list(self.clients):
            self.loop.call_soon_threadsafe(q.put_nowait, event)


class PauseBody(BaseModel):
    bot: str
    paused: bool


def create_app(log: EventLog, day_fn: Callable, set_paused: Callable[[str, bool, datetime], None],
               bot_ids: list[str], web_dir: str | None = None) -> FastAPI:
    hub = Hub()

    @asynccontextmanager
    async def lifespan(_app):
        hub.loop = asyncio.get_running_loop()
        yield

    app = FastAPI(title="Scalp City", lifespan=lifespan)
    log.listeners.append(hub.push)

    @app.get("/snapshot")
    def snapshot():
        snap = build_snapshot(log.read(day_fn()))
        for bot in bot_ids:
            snap["bots"].setdefault(bot, {"bot": bot, "ticker": bot.split("-")[0], "state": "idle", "reason_code": "NO_DATA",
                                          "reason_text": "no events yet", "charge_pct": None, "inputs": {}, "time": None,
                                          "pnl_day": 0.0, "trades": 0, "paused": False})
        return snap

    @app.post("/control/pause")
    def pause(body: PauseBody):
        if body.bot not in bot_ids:
            raise HTTPException(404, "unknown bot")
        set_paused(body.bot, body.paused, datetime.now(ET))
        return {"ok": True, "bot": body.bot, "paused": body.paused}

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        await socket.accept()
        queue: asyncio.Queue = asyncio.Queue()
        hub.clients.add(queue)
        try:
            await socket.send_json({"type": "snapshot", **snapshot()})
            while True:
                await socket.send_json({"type": "event", "event": await queue.get()})
        except WebSocketDisconnect:
            pass
        finally:
            hub.clients.discard(queue)

    directory = web_dir or str(pathlib.Path(__file__).resolve().parent.parent / "web")
    if pathlib.Path(directory).exists():
        app.mount("/", StaticFiles(directory=directory, html=True), name="web")
    return app
```

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, 65 tests passed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_server.py scalpcity/server.py
git commit -m "feat: API server with snapshot, websocket stream and pause control"
```


### Task 14: Plain table dashboard

**Files:**
- Create: `web/index.html`

**Interfaces:**
- Consumes: `GET /snapshot`, `WS /ws`, `POST /control/pause` from Task 13.
- Produces: a table with one row per bot (state, reason, charge %, price, day P&L, trades, last update, Pause/Resume button) plus a thoughts feed of non-tick events.

- [ ] **Step 1: Create the page**

Create `web/index.html`:

```html
<!doctype html>
<meta charset="utf-8">
<title>Scalp City</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 16px; background: #0d1020; color: #e6e9f5; }
  table { border-collapse: collapse; width: 100%; }
  th, td { padding: 6px 10px; border-bottom: 1px solid #262b45; text-align: left; font-size: 14px; }
  .state-idle { color: #8892b0; } .state-forming { color: #ffd166; } .state-fired { color: #06d6a0; }
  .state-managing { color: #4cc9f0; } .state-exiting { color: #f78c6b; } .state-cooldown { color: #7b8cff; }
  .state-locked { color: #f4a261; } .state-paused { color: #adb5bd; } .state-stale { color: #ef476f; font-weight: bold; }
  .pos { color: #06d6a0; } .neg { color: #ef476f; }
  #feed { margin-top: 16px; height: 260px; overflow: auto; font: 12px ui-monospace, monospace; background: #0a0d1a; padding: 8px; }
  #status { margin-bottom: 8px; color: #8892b0; }
  button { cursor: pointer; }
</style>
<h2>Scalp City</h2>
<div id="status">connecting...</div>
<table>
  <thead><tr><th>Bot</th><th>State</th><th>Why</th><th>Charge</th><th>Price</th><th>Day P&amp;L</th><th>Trades</th><th>Last update</th><th></th></tr></thead>
  <tbody id="rows"></tbody>
</table>
<div id="feed"></div>
<script>
const rows = {}, feed = document.getElementById("feed"), tbody = document.getElementById("rows");
const fmtTime = t => t ? t.slice(11, 19) : "-";
function render(bot) {
  let tr = rows[bot.bot];
  if (!tr) { tr = rows[bot.bot] = document.createElement("tr"); tbody.appendChild(tr); }
  const pnl = bot.pnl_day || 0;
  tr.innerHTML = `<td>${bot.bot}</td><td class="state-${bot.state}">${bot.state}</td><td>${bot.reason_code} ${bot.reason_text || ""}</td>
    <td>${bot.charge_pct == null ? "-" : bot.charge_pct + "%"}</td><td>${(bot.inputs && bot.inputs.price) ?? "-"}</td>
    <td class="${pnl >= 0 ? "pos" : "neg"}">${pnl.toFixed(2)}</td><td>${bot.trades || 0}</td><td>${fmtTime(bot.time)}</td>
    <td><button data-bot="${bot.bot}">${bot.paused ? "Resume" : "Pause"}</button></td>`;
  tr.querySelector("button").onclick = () => fetch("/control/pause", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ bot: bot.bot, paused: !bot.paused }) });
  tr._bot = bot;
}
function apply(ev) {
  const row = rows[ev.bot] && rows[ev.bot]._bot; if (!row) return;
  if (ev.kind === "tick" || ev.kind === "state_change") Object.assign(row, { state: ev.state, reason_code: ev.reason_code, reason_text: ev.reason_text, charge_pct: ev.charge_pct, inputs: ev.inputs, time: ev.time });
  if (ev.kind === "trade_closed") Object.assign(row, { pnl_day: ev.pnl_day, trades: ev.trades });
  if (ev.kind === "control") row.paused = ev.paused;
  render(row);
  if (ev.kind !== "tick") {
    const line = document.createElement("div");
    line.textContent = `${fmtTime(ev.time)} ${ev.bot} ${ev.kind} ${ev.state} ${ev.reason_code} ${ev.reason_text}`;
    feed.prepend(line);
  }
}
function connect() {
  const ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onopen = () => document.getElementById("status").textContent = "live";
  ws.onclose = () => { document.getElementById("status").textContent = "disconnected, retrying..."; setTimeout(connect, 2000); };
  ws.onmessage = m => {
    const msg = JSON.parse(m.data);
    if (msg.type === "snapshot") Object.values(msg.bots).forEach(render); else apply(msg.event);
  };
}
connect();
</script>
```

- [ ] **Step 2: Serve a replayed day and look at it**

Run a small server over the replay log from Task 8 (read-only; the pause button writes control events to the replay log):

```bash
.venv/bin/python - <<'EOF'
import uvicorn
from datetime import date
from scalpcity.config import TICKERS, BOT_SPECS
from scalpcity.events import EventLog
from scalpcity.server import create_app
day = date(2026, 10, 7)
log = EventLog("logs", "replay")
ids = [f"{t}-{k.upper()}" for t in TICKERS for k in BOT_SPECS]
uvicorn.run(create_app(log, lambda: day, lambda bot, paused, when: log.append(when, bot, bot.split("-")[0], "control", paused=paused), ids), host="127.0.0.1", port=8000)
EOF
```

Open `http://127.0.0.1:8000` in the browser pane. Expected: nine rows, every row with a state and a non-empty reason, day P&L matching the replay summary from Task 8, status text `live`. Click Pause on one row: the button changes to Resume and a `control` event is appended.

- [ ] **Step 3: Commit**

```bash
git add web/index.html
git commit -m "feat: plain table dashboard"
```

---

### Task 15: End-to-end smoke test and handoff

**Files:**
- Modify: `docs/superpowers/specs/2026-10-08-scalp-city-design.md` (status line only)

- [ ] **Step 1: Full suite**

Run: `.venv/bin/python -m pytest -q`
Expected: `65 passed`.

- [ ] **Step 2: Paper-only guard check**

```bash
.venv/bin/python - <<'EOF'
from scalpcity.guard import assert_paper_only, GuardError
env = {"WEBULL_ENV": "sandbox", "WEBULL_SANDBOX_ACCOUNT_ATTESTED": "true", "WEBULL_PAPER_ACCOUNT_NUMBER": "X"}
try:
    assert_paper_only(env, "api.webull.com", [{"account_number": "X", "account_id": "y"}])
except GuardError as e:
    print("refused as expected:", e)
EOF
```

Expected: `refused as expected: host must be api.sandbox.webull.com, got api.webull.com`.

- [ ] **Step 3: Live dry run on the next trading day**

Start `.venv/bin/python scripts/run_live.py` before 9:30 ET, open `http://127.0.0.1:8000`, and watch until 10:30. Expected: nine rows updating each minute, range-break bots showing `RANGE_FORMING` from 9:40, VWAP bots showing `CHOP_SQUEEZE` or `WATCHING`, any trade appearing as `fired` then `managing`, and fills labelled `broker` or `modeled` in the feed. Copy `logs/<date>-live.jsonl` aside for review.

- [ ] **Step 4: Mark the spec and commit**

Change the spec's status line from `awaiting user review` to `phases 0-3 implemented`, then:

```bash
git add docs/superpowers/specs/2026-10-08-scalp-city-design.md
git commit -m "docs: mark phases 0-3 implemented"
```

---

## Self-Review

**Spec coverage (spec section -> task):** 2 decisions and 3 defaults -> Tasks 1, 5, 6, 7; 4 architecture -> Task 7; 5 bot states and reason codes -> Task 5; 6 event format -> Task 2; 7 feeds and orders -> Tasks 8-12; 8 safety -> Tasks 9 and 10; 9 dashboard (table form) -> Tasks 13 and 14; 10 build phases and testing -> all tasks; 11 risks -> Task 12 (phase 0). Deferred on purpose: section 9's 3D city (phase 4, own plan), flatten button and office scene (phase 5).

**Placeholder scan:** no TBD or TODO. One value is intentionally confirmed at runtime: the Webull filled-order field names (`FILLED_PRICE_KEYS`, `FILLED_QTY_KEYS`) are guesses until Task 12 step "Confirm the fill-field names" captures a real filled order.

**Type consistency:** names were checked against the tested code: `Bot.on_fill(fill, inputs)`, `Engine.check_stale(now, last_bar_wall, open_quote_wall)`, `QuoteSource.get(contract, ts)`, `ModeledBroker.execute(intent, contract, quote, ts)`, `WebullPaperBroker.execute` (same signature), `EventLog.append(...)`.
