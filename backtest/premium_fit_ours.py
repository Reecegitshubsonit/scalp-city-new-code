"""Measure the option-premium response and the per-trade cost from OUR OWN paper record.

Two independent fits, deliberately kept apart:

  A. FILL FIT - our Webull sandbox paper trades. Every row carries the option price and the
     underlying price at both ends, so there is no bar-alignment guesswork. What this fit's
     intercept captures is OUR execution cost: spread crossed, slippage, fill quality.

  B. MARKET FIT - raw Webull 1-minute option bars against 1-minute stock bars, with no trades
     involved at all. This measures how premium tracks the underlying in the market itself,
     free of anything our engine did.

Model, premium in dollars per share:

    d_premium = delta_eff * favourable_underlying_move + decay_per_min * minutes + intercept

The gap between fit A's intercept and fit B's is what execution costs us. Fit A's intercept,
expressed in ATR units, is the COST_R constant that backtest/filters.py and
backtest/trail_grid.py currently assume to be 0.2.

    .venv/bin/python backtest/premium_fit_ours.py
"""
import csv
import json
import os
import statistics as st
from collections import defaultdict
from datetime import datetime

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEEDS = {
    "Scalp City V2": "/home/ronaldsecret/scalp-city-ceo-feed-extract/scalp-city-v2-paper_trades.csv",
    "new Scalp City": "/home/ronaldsecret/scalp-city-ceo-feed-extract/new-scalp-city-paper_trades.csv",
}
WEBULL = os.path.join(ROOT, "data", "webull")


def fit(rows):
    """rows: dicts with move, hold_m, d_prem. Returns coefs, r2, n."""
    if len(rows) < 20:
        return None
    X = np.array([[r["move"], r["hold_m"], 1.0] for r in rows])
    y = np.array([r["d_prem"] for r in rows])
    c, *_ = np.linalg.lstsq(X, y, rcond=None)
    p = X @ c
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - float(((y - p) ** 2).sum()) / ss_tot if ss_tot else float("nan")
    return dict(delta=c[0], decay=c[1], intercept=c[2], r2=r2, n=len(rows))


def load_fills(clean_only=True):
    out = []
    for engine, path in FEEDS.items():
        if not os.path.exists(path):
            continue
        for r in csv.DictReader(open(path)):
            if r["open"] != "False" or not r["option_exit_price"]:
                continue
            if clean_only and not (r["entry_source"] == "broker" and r["exit_source"] == "broker"):
                continue
            try:
                pe, px = float(r["option_entry_price"]), float(r["option_exit_price"])
                ue, ux = float(r["und_entry_price"]), float(r["und_exit_price"])
                atr = float(r["atr_entry"])
                t0 = datetime.fromisoformat(r["entry_time"])
                t1 = datetime.fromisoformat(r["exit_time"])
            except (ValueError, KeyError):
                continue
            if atr <= 0:
                continue
            move = (ux - ue) if r["right"] == "C" else (ue - ux)
            out.append(dict(engine=engine, ticker=r["underlying"], right=r["right"],
                            qty=int(r["qty"]), d_prem=px - pe, move=move,
                            hold_m=(t1 - t0).total_seconds() / 60.0, atr=atr,
                            entry=pe, exit_reason=r["exit_reason"],
                            day=r["entry_time"][:10]))
    return out


def load_market(max_days=None):
    """Per-minute option bar moves against the same minute's stock move. No trades involved."""
    pts = []
    days = sorted(d for d in os.listdir(WEBULL) if d[0].isdigit())
    if max_days:
        days = days[-max_days:]
    for day in days:
        d = os.path.join(WEBULL, day)
        stock = {}
        for tkr in ("QQQ", "SPY", "IWM"):
            p = os.path.join(d, f"stock-{tkr}.json")
            if not os.path.exists(p):
                continue
            s = {}
            for b in json.load(open(p)):
                s[b["time"]] = float(b["close"])
            stock[tkr] = s
        for fn in os.listdir(d):
            if not fn.startswith("option-"):
                continue
            occ = fn[len("option-"):-len(".json")]
            tkr = "".join(ch for ch in occ[:3] if ch.isalpha())
            if tkr not in stock:
                continue
            right = "C" if occ[9] == "C" else "P"
            try:
                bars = json.load(open(os.path.join(d, fn)))
            except json.JSONDecodeError:
                continue
            bars = [(b["time"], float(b["close"])) for b in bars]
            bars.sort()
            for i in range(1, len(bars)):
                t_prev, p_prev = bars[i - 1]
                t_now, p_now = bars[i]
                if t_prev not in stock[tkr] or t_now not in stock[tkr]:
                    continue
                dt = (datetime.fromisoformat(t_now.replace("Z", "+00:00"))
                      - datetime.fromisoformat(t_prev.replace("Z", "+00:00"))).total_seconds() / 60.0
                if dt <= 0 or dt > 5:          # skip gaps in thin contracts
                    continue
                du = stock[tkr][t_now] - stock[tkr][t_prev]
                move = du if right == "C" else -du
                if abs(move) < 1e-9:
                    continue
                pts.append(dict(ticker=tkr, move=move, hold_m=dt, d_prem=p_now - p_prev))
    return pts


def main():
    print("=" * 78)
    print("A. FILL FIT - our paper trades, broker>broker fills only")
    print("=" * 78)
    fills = load_fills(clean_only=True)
    allf = load_fills(clean_only=False)
    print(f"clean broker>broker fills {len(fills)} of {len(allf)} closed trades\n")

    res = {}
    print(f"{'group':20s} {'n':>5s} {'delta_eff':>10s} {'decay/min':>10s} {'intercept':>10s} {'R2':>6s}")
    f = fit(fills)
    res["ALL"] = f
    print(f"{'ALL':20s} {f['n']:5d} {f['delta']:10.4f} {f['decay']:10.4f} {f['intercept']:10.4f} {f['r2']:6.3f}")
    for tkr in ("QQQ", "SPY", "IWM"):
        g = [r for r in fills if r["ticker"] == tkr]
        ff = fit(g)
        if ff:
            res[tkr] = ff
            print(f"{tkr:20s} {ff['n']:5d} {ff['delta']:10.4f} {ff['decay']:10.4f} {ff['intercept']:10.4f} {ff['r2']:6.3f}")
    for eng in FEEDS:
        g = [r for r in fills if r["engine"] == eng]
        ff = fit(g)
        if ff:
            print(f"{eng:20s} {ff['n']:5d} {ff['delta']:10.4f} {ff['decay']:10.4f} {ff['intercept']:10.4f} {ff['r2']:6.3f}")
    fdirty = fit([r for r in allf if not (r in fills)]) if len(allf) > len(fills) else None
    if fdirty:
        print(f"{'offmarket/modeled':20s} {fdirty['n']:5d} {fdirty['delta']:10.4f} {fdirty['decay']:10.4f} "
              f"{fdirty['intercept']:10.4f} {fdirty['r2']:6.3f}")

    print()
    print("=" * 78)
    print("B. MARKET FIT - raw option bars vs stock bars, no fills")
    print("=" * 78)
    mk = load_market()
    print(f"minute-pairs {len(mk):,}\n")
    print(f"{'group':20s} {'n':>7s} {'delta_eff':>10s} {'decay/min':>10s} {'intercept':>10s} {'R2':>6s}")
    mall = fit(mk)
    print(f"{'ALL':20s} {mall['n']:7d} {mall['delta']:10.4f} {mall['decay']:10.4f} {mall['intercept']:10.4f} {mall['r2']:6.3f}")
    mres = {"ALL": mall}
    for tkr in ("QQQ", "SPY", "IWM"):
        g = [r for r in mk if r["ticker"] == tkr]
        ff = fit(g)
        if ff:
            mres[tkr] = ff
            print(f"{tkr:20s} {ff['n']:7d} {ff['delta']:10.4f} {ff['decay']:10.4f} {ff['intercept']:10.4f} {ff['r2']:6.3f}")

    print()
    print("=" * 78)
    print("COST_R - fill intercept expressed in ATR units")
    print("=" * 78)
    print(f"{'ticker':10s} {'medATR':>8s} {'$/ATR':>9s} {'fill int':>10s} {'mkt int':>10s} "
          f"{'exec cost':>10s} {'COST_R':>8s}")
    cost = {}
    for tkr in ("QQQ", "SPY", "IWM", "ALL"):
        if tkr not in res:
            continue
        g = fills if tkr == "ALL" else [r for r in fills if r["ticker"] == tkr]
        med_atr = st.median([r["atr"] for r in g])
        dollar_per_atr = res[tkr]["delta"] * med_atr
        fill_int = res[tkr]["intercept"]
        mkt_int = mres.get(tkr, mres["ALL"])["intercept"]
        exec_cost = mkt_int - fill_int
        cr = -fill_int / dollar_per_atr if dollar_per_atr else float("nan")
        cost[tkr] = dict(median_atr=med_atr, dollar_per_atr=dollar_per_atr,
                         fill_intercept=fill_int, market_intercept=mkt_int,
                         exec_cost_per_share=exec_cost, cost_R=cr)
        print(f"{tkr:10s} {med_atr:8.3f} {dollar_per_atr:9.3f} {fill_int:10.4f} {mkt_int:10.4f} "
              f"{exec_cost:10.4f} {cr:8.3f}")

    out = os.path.join(ROOT, "reports", "premium-fit-ours.json")
    json.dump(dict(fill_fit={k: v for k, v in res.items()},
                   market_fit={k: v for k, v in mres.items()},
                   cost=cost, n_clean_fills=len(fills), n_all_fills=len(allf),
                   n_market_pairs=len(mk)), open(out, "w"), indent=1)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
