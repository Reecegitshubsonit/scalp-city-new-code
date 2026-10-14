"""Fetch Webull's full-day one-minute bars (tickers + every contract traded or snapshotted) for finished days.
The live engine does this on its own at 16:05 ET; run this for a day it missed. Read-only market data, no orders.
Webull serves only the newest 1200 bars and expired contracts may be gone, so run it the same day when possible.
Usage: .venv/bin/python scripts/fetch_webull_day.py 2026-10-13 [2026-10-12 ...] [--logdir logs] [--root data/webull]
"""
import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scalpcity.events import EventLog
from scalpcity.recorder import day_dir, fetch_day, traded_contracts
from scalpcity.webull_client import WebullClient

from run_live import load_env


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("days", nargs="+")
    ap.add_argument("--logdir", default="logs")
    ap.add_argument("--root", default="data/webull")
    args = ap.parse_args()
    load_env()
    # a second process has no view of the engine's queue: space calls wider so the engine keeps its share
    client = WebullClient.from_env(os.environ)
    client.min_interval = 1.0
    log = EventLog(args.logdir, "live")
    for text in args.days:
        day = date.fromisoformat(text)
        contracts = traded_contracts(log.read(day))
        seen = os.path.join(day_dir(args.root, day), "contracts.json")
        if os.path.exists(seen):
            with open(seen) as handle:
                contracts |= set(json.load(handle))
        saved = fetch_day(client, day, contracts, args.root)
        empty = [k for k, v in saved.items() if v == 0]
        print(f"{day}: {sum(1 for v in saved.values() if v)} of {len(saved)} names saved"
              + (f"; no bars from Webull for {', '.join(empty)}" if empty else ""), flush=True)
        for k, v in saved.items():
            print(f"  {k}: {v} bars")


if __name__ == "__main__":
    main()
