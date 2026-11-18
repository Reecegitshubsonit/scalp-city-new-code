"""Fetch 1-minute stock bars for an explicit date range into its own file.

Unlike fetch_stock.py this never overwrites backtest/data/{T}_1m.json; it writes
backtest/data/{T}_1m_{start}_{end}.json so earlier runs stay reproducible.

    .venv/bin/python backtest/fetch_stock_range.py 2025-11-17 2026-11-14
"""
import json
import os
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    start, end = sys.argv[1], sys.argv[2]
    env = {}
    for l in open(os.path.join(ROOT, ".env")):
        l = l.strip()
        if "=" in l and not l.startswith("#"):
            k, v = l.split("=", 1)
            env[k] = v.strip().strip("\"'")
    h = {"APCA-API-KEY-ID": env["ALPACA_API_KEY"], "APCA-API-SECRET-KEY": env["ALPACA_SECRET_KEY"]}
    for t in ("QQQ", "SPY", "IWM"):
        out = os.path.join(ROOT, "backtest", "data", f"{t}_1m_{start}_{end}.json")
        if os.path.exists(out):
            print(f"{t} exists, skipping {out}")
            continue
        bars, tok = [], None
        while True:
            p = dict(timeframe="1Min", start=f"{start}T00:00:00Z", end=f"{end}T23:00:00Z",
                     feed="sip", limit=10000, adjustment="raw")
            if tok:
                p["page_token"] = tok
            r = requests.get(f"https://data.alpaca.markets/v2/stocks/{t}/bars", headers=h, params=p, timeout=60)
            if r.status_code == 429:
                time.sleep(15)
                continue
            if r.status_code != 200:
                print(t, r.status_code, r.text[:300])
                break
            time.sleep(0.5)
            j = r.json()
            bars += j["bars"] or []
            tok = j.get("next_page_token")
            print(f"  {t} {len(bars)} bars", flush=True)
            if not tok:
                break
        json.dump(bars, open(out, "w"))
        print(f"{t} {len(bars)} -> {out}", flush=True)


if __name__ == "__main__":
    main()
