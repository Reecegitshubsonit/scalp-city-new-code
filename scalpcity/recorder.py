"""Webull market data recorder: keeps the full picture of every paper day, all from Webull.

Files under data/webull/YYYY-MM-DD/:
  stock-TICKER.live.jsonl   every one-minute bar the engine received, as it received it
  snapshots.jsonl           after each new bar (at least once a minute): full option snapshots (bid/ask, sizes, greeks,
                            IV, volume) of held contracts and the ATM strike +/- STRIKES_EACH_SIDE, calls and puts
  contracts.json            every contract snapshotted or traded that day
  stock-TICKER.json         end of day: Webull's full-day one-minute bars (raw rows)
  option-CONTRACT.json      end of day: Webull's full-day one-minute bars of that option (raw rows)

Webull only serves the newest N bars (no date range) and the bots trade 1DTE contracts, so the end-of-day fetch
must run the same day. Every Webull call here is background priority: engine calls always go first.
"""
import json
import os
import threading
import traceback
from datetime import date, datetime, time, timedelta

from .config import TICKERS
from .contracts import atm_strike, next_trading_day, occ_symbol
from .types import ET, Bar

MAX_BARS = 1200          # Webull's limit per request
OPTION_BATCH = 10        # contracts per option bars / snapshot request
EOD_AFTER = time(16, 5)  # closing bars are final
STRIKES_EACH_SIDE = 2    # strikes recorded above and below ATM, so replays can price entries a rule change moves
SNAPSHOT_EVERY = timedelta(seconds=60)   # snapshot interval when no new bar arrives


def day_dir(root: str, day: date) -> str:
    return os.path.join(root, day.isoformat())


def bar_day(row: dict) -> date:
    return datetime.strptime(row["time"], "%Y-%m-%dT%H:%M:%S.%f%z").astimezone(ET).date()


def traded_contracts(events: list[dict]) -> set[str]:
    return {ev["contract"] for ev in events if ev.get("contract") and ev["kind"] in ("order_sent", "fill")}


def atm_contracts(ticker: str, price: float, day: date, width: int = 0) -> list[str]:
    """The contracts a bot on this ticker would buy right now (next-day expiry, ATM strike), plus `width`
    one-dollar strikes above and below it."""
    expiry = next_trading_day(day)
    atm = atm_strike(price)
    return [occ_symbol(ticker, expiry, right, atm + k) for k in range(-width, width + 1) for right in ("CALL", "PUT")]


def _write_json(path: str, rows) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w") as handle:
        json.dump(rows, handle, separators=(",", ":"))
    os.replace(tmp, path)


def _keep(path: str, rows: list[dict]) -> bool:
    """Write only when there is something new: never replace a saved day with fewer bars."""
    if not rows:
        return False
    if os.path.exists(path):
        with open(path) as handle:
            if len(json.load(handle)) >= len(rows):
                return False
    _write_json(path, sorted(rows, key=lambda r: r["time"]))
    return True


def fetch_day(client, day: date, contracts, root: str, tickers=TICKERS) -> dict[str, int]:
    """Full-day Webull one-minute bars of the tickers and contracts for `day`. Returns bars saved per name."""
    out_dir = day_dir(root, day)
    os.makedirs(out_dir, exist_ok=True)
    saved: dict[str, int] = {}
    for t in tickers:
        rows = [r for r in client.stock_bars_raw(t, MAX_BARS) if bar_day(r) == day]
        saved[t] = len(rows)
        _keep(os.path.join(out_dir, f"stock-{t}.json"), rows)
    names = sorted(set(contracts))
    for i in range(0, len(names), OPTION_BATCH):
        batch = names[i:i + OPTION_BATCH]
        got = client.option_bars_raw(batch, MAX_BARS)
        for c in batch:
            rows = [r for r in got.get(c, []) if bar_day(r) == day]
            saved[c] = len(rows)
            _keep(os.path.join(out_dir, f"option-{c}.json"), rows)
    return saved


class Recorder:
    """Live side of the recorder. on_bar() is called from the engine loop and never calls Webull; a background
    thread takes the per-minute option snapshots and runs the end-of-day fetch. Errors are printed, never raised."""

    def __init__(self, client, root: str, held_fn, events_fn, now_fn=lambda: datetime.now(ET), tickers=TICKERS):
        self.client, self.root, self.held_fn, self.events_fn, self.now_fn = client, root, held_fn, events_fn, now_fn
        self.tickers = tickers
        self._lock = threading.Lock()
        self._price: dict[str, tuple[date, float]] = {}   # ticker -> (bar day, last close)
        self._bar = None               # start of the newest bar received
        self._snapped_bar = None       # newest bar when the last snapshot was taken
        self._snapped_at = None        # wall time of the last snapshot
        self._seen: dict[date, set[str]] = {}
        self._eod_done: set[date] = set()

    # ---- called from the engine loop ----
    def on_bar(self, bar: Bar) -> None:
        try:
            day = bar.ts.date()
            path = os.path.join(day_dir(self.root, day), f"stock-{bar.ticker}.live.jsonl")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            row = {"time": bar.ts.isoformat(), "open": bar.open, "high": bar.high, "low": bar.low, "close": bar.close,
                   "volume": bar.volume, "received_at": self.now_fn().isoformat()}
            with self._lock, open(path, "a") as handle:
                handle.write(json.dumps(row, separators=(",", ":")) + "\n")
                self._price[bar.ticker] = (day, bar.close)
                self._bar = bar.ts if self._bar is None else max(self._bar, bar.ts)
        except Exception:
            traceback.print_exc()

    # ---- background thread ----
    def start(self) -> None:
        threading.Thread(target=self._run, name="recorder", daemon=True).start()

    def _run(self) -> None:
        import time as _time
        while True:
            try:
                self.step()
            except Exception:
                traceback.print_exc()
            _time.sleep(5)

    def step(self) -> None:
        now = self.now_fn()
        if now.weekday() >= 5:
            return
        if time(9, 30) <= now.time() < time(16, 0):
            with self._lock:
                bar = self._bar
            new_bar = bar is not None and bar.date() == now.date() and bar != self._snapped_bar
            overdue = self._snapped_at is not None and now - self._snapped_at >= SNAPSHOT_EVERY
            if new_bar or overdue:
                # right after the engine acts on a bar, so the quotes are the ones its orders saw
                self._snapped_bar, self._snapped_at = bar, now
                self.snapshot(now)
        if now.time() >= EOD_AFTER and now.date() not in self._eod_done:
            self.end_of_day(now.date())

    def snapshot(self, now: datetime) -> None:
        day = now.date()
        with self._lock:
            prices = {t: p for t, (d, p) in self._price.items() if d == day}   # never strikes from a prior day's price
        contracts = set(self.held_fn())
        for t, price in prices.items():
            contracts.update(atm_contracts(t, price, day, STRIKES_EACH_SIDE))
        if not contracts:
            return
        names = sorted(contracts)
        rows = []
        for i in range(0, len(names), OPTION_BATCH):
            rows += self.client.option_snapshots_raw(names[i:i + OPTION_BATCH])
        out_dir = day_dir(self.root, day)
        os.makedirs(out_dir, exist_ok=True)
        line = {"recorded_at": now.isoformat(), "held": sorted(self.held_fn()), "snapshots": rows}
        with open(os.path.join(out_dir, "snapshots.jsonl"), "a") as handle:
            handle.write(json.dumps(line, separators=(",", ":")) + "\n")
        self._remember(day, names)

    def _remember(self, day: date, names) -> None:
        seen = self._seen.setdefault(day, set())
        path = os.path.join(day_dir(self.root, day), "contracts.json")
        if not seen and os.path.exists(path):   # restart mid-day: keep what was seen before
            with open(path) as handle:
                seen.update(json.load(handle))
        if not set(names) <= seen:
            seen.update(names)
            _write_json(path, sorted(seen))

    def end_of_day(self, day: date) -> None:
        traded = traded_contracts(self.events_fn(day))
        self._remember(day, traded)
        saved = fetch_day(self.client, day, self._seen.get(day, set()), self.root, self.tickers)
        self._eod_done.add(day)
        print(f"Recorder: saved Webull bars for {day}: " + ", ".join(f"{k} {v}" for k, v in saved.items()), flush=True)
