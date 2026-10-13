"""Cache real one-minute bars for every logged trading day that has none yet, so replays draw real candles.
Read-only market data (Alpaca); never touches the engine or orders. Safe to run any time, as often as you like:
a day is fetched only once it is finished (after 16:15 ET), and a cached day is never fetched again.
Usage: .venv/bin/python scripts/cache_day_bars.py [--logdir logs] [--cache-dir data/cache]
"""
import argparse
import os
import re
import sys
from datetime import date, datetime, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scalpcity.alpaca_history import AlpacaHistory
from scalpcity.config import TICKERS
from scalpcity.types import ET

from run_replay import load_env

_LOG = re.compile(r"^(\d{4}-\d{2}-\d{2})-(live|replay)\.jsonl$")
DONE_AFTER = time(16, 15)   # the session is over and Alpaca has the closing bars


def days_missing(logdir: str, cache_dir: str, now: datetime) -> list[date]:
    """Logged days (any mode) with at least one ticker's bars missing from the cache, finished days only."""
    out = set()
    for name in os.listdir(logdir):
        m = _LOG.match(name)
        if not m:
            continue
        day = date.fromisoformat(m.group(1))
        if day > now.date() or (day == now.date() and now.time() < DONE_AFTER):
            continue   # an unfinished day would stay cached half-empty
        if any(not os.path.exists(os.path.join(cache_dir, f"stock-{t}-{day}.json")) for t in TICKERS):
            out.add(day)
    return sorted(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logdir", default="logs")
    ap.add_argument("--cache-dir", default="data/cache")
    args = ap.parse_args()
    missing = days_missing(args.logdir, args.cache_dir, datetime.now(ET))
    if not missing:
        print("bar cache up to date")
        return
    load_env()
    hist = AlpacaHistory(args.cache_dir)
    for day in missing:
        for t in TICKERS:
            bars = hist.stock_bars(t, day)
            print(f"{day} {t}: {len(bars)} bars", flush=True)


if __name__ == "__main__":
    main()
