import json
import os
import re
import threading

from .types import Bar

_SIDE = re.compile(r"\b(CALL|PUT)\b")


class BarStore:
    """Today's one-minute bars per ticker, for the /history endpoint. add() may be called from the feed thread."""

    def __init__(self):
        self._bars: dict[str, dict] = {}
        self._lock = threading.Lock()

    def add(self, bar: Bar) -> None:
        with self._lock:
            self._bars.setdefault(bar.ticker, {})[bar.ts] = bar

    def extend(self, bars) -> None:
        for b in bars:
            self.add(b)

    def get(self, ticker: str) -> list[Bar]:
        with self._lock:
            return [b for _, b in sorted(self._bars.get(ticker, {}).items())]


def build_history(ticker: str, bars: list[Bar], events: list[dict]) -> dict:
    """Candles, indicator levels and trade markers for one ticker. Levels and markers come from the day's event log."""
    levels: dict[str, dict] = {}
    side_of: dict[str, str | None] = {}
    marks: list[dict] = []
    for e in events:
        if e.get("ticker") != ticker:
            continue
        kind, bot, t = e.get("kind"), e.get("bot"), e.get("time")
        if kind == "tick":
            inp = e.get("inputs") or {}
            if t not in levels and "vwap" in inp:
                levels[t] = {"time": t, **{k: inp.get(k) for k in ("vwap", "ema9", "ema21", "ema50")}}
        elif e.get("reason_code") == "SIGNAL":
            m = _SIDE.search(e.get("reason_text") or "")
            side_of[bot] = m.group(1) if m else None
        elif kind == "fill" and e.get("reason_code") == "ENTRY_FILL":
            marks.append({"time": t, "bot": bot, "type": "entry", "side": side_of.get(bot), "pnl": None})
        elif kind == "trade_closed":
            marks.append({"time": t, "bot": bot, "type": "exit", "side": side_of.get(bot), "pnl": e.get("pnl")})
    return {
        "ticker": ticker,
        "bars": [{"time": b.ts.isoformat(), "open": b.open, "high": b.high, "low": b.low, "close": b.close, "volume": b.volume} for b in bars],
        "levels": sorted(levels.values(), key=lambda lv: lv["time"]),
        "marks": marks,
    }


_DAY_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(live|replay)\.jsonl$")
MODES = ("live", "replay")


def list_days(directory: str) -> list[dict]:
    """Event logs on disk, newest first, for the dashboard's replay picker."""
    out = []
    if not os.path.isdir(directory):
        return out
    for name in os.listdir(directory):
        m = _DAY_FILE.match(name)
        if not m:
            continue
        first = last = None
        n = 0
        with open(os.path.join(directory, name)) as handle:
            for line in handle:
                if not line.strip():
                    continue
                t = json.loads(line).get("time")
                first = first or t
                last = t
                n += 1
        out.append({"day": m.group(1), "mode": m.group(2), "events": n, "first": first, "last": last})
    return sorted(out, key=lambda d: (d["day"], d["mode"]), reverse=True)


def read_day(directory: str, day: str, mode: str) -> list[dict] | None:
    """All events of one logged day; None for a malformed day or mode (never touches paths outside the log directory)."""
    if mode not in MODES or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        return None
    path = os.path.join(directory, f"{day}-{mode}.jsonl")
    if not os.path.exists(path):
        return []
    with open(path) as handle:
        return [json.loads(line) for line in handle if line.strip()]
