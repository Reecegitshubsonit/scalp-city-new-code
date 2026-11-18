"""Does buying in the money lower the real cost hurdle?

COST_R = quoted spread / (realised premium response per 1 ATR of underlying move).

Moving in the money raises delta, which raises the denominator and should lower the hurdle.
It may also widen the quoted spread, which raises the numerator. Only measurement settles it,
and our Webull capture holds roughly +/-10 strikes around spot on every paper day, so both
sides can be measured on the same contracts the engine could actually have bought.

Two independent measurements per moneyness bucket:
  quoted   median (ask - bid) from snapshots.jsonl, and the quoted delta alongside it
  realised delta_eff, fitted from 1-minute option bars against 1-minute stock bars - the
           actual premium move per $1 of underlying, which is what the hurdle depends on

Moneyness is signed so positive is IN the money, in dollars, for both calls and puts.

    .venv/bin/python backtest/moneyness_cost.py
"""
import json
import math
import os
import statistics as st
from collections import defaultdict
from datetime import date, datetime

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = os.path.join(ROOT, "data", "webull")
TICKERS = ("QQQ", "SPY", "IWM")
BUCKETS = [(-99, -2.5), (-2.5, -1.5), (-1.5, -0.5), (-0.5, 0.5),
           (0.5, 1.5), (1.5, 2.5), (2.5, 3.5), (3.5, 99)]
LABEL = ["<-2.5 OTM", "-2.5..-1.5", "-1.5..-0.5", "ATM +/-0.5",
         "+0.5..+1.5", "+1.5..+2.5", "+2.5..+3.5", ">+3.5 ITM"]


def occ_parse(sym):
    i = 0
    while i < len(sym) and sym[i].isalpha():
        i += 1
    root = sym[:i]
    right = sym[i + 6]
    strike = int(sym[i + 7:]) / 1000.0
    return root, right, strike


def stock_series(day, tkr):
    p = os.path.join(W, day, f"stock-{tkr}.json")
    if not os.path.exists(p):
        return None
    out = {}
    for b in json.load(open(p)):
        out[b["time"]] = float(b["close"])
    return out


def atr_median(day, tkr):
    p = os.path.join(W, day, f"stock-{tkr}.json")
    if not os.path.exists(p):
        return None
    bars = []
    for b in json.load(open(p)):
        bars.append((b["time"], float(b["high"]), float(b["low"]), float(b["close"])))
    bars.sort()
    atr, pc, vals = None, None, []
    for i, (t, h, l, c) in enumerate(bars):
        tr = (h - l) if pc is None else max(h - l, abs(h - pc), abs(l - pc))
        pc = c
        n = i + 1
        atr = tr if atr is None else ((atr * 13 + tr) / 14 if n > 14 else (atr * (n - 1) + tr) / n)
        vals.append(atr)
    return st.median(vals) if vals else None


def bucket_of(m):
    for i, (lo, hi) in enumerate(BUCKETS):
        if lo <= m < hi:
            return i
    return None


def main():
    days = sorted(d for d in os.listdir(W) if d[0].isdigit())
    quoted = {t: defaultdict(lambda: {"spread": [], "delta": [], "mid": []}) for t in TICKERS}
    bars_pts = {t: defaultdict(list) for t in TICKERS}
    atrs = {t: [] for t in TICKERS}

    for day in days:
        stocks = {t: stock_series(day, t) for t in TICKERS}
        for t in TICKERS:
            a = atr_median(day, t)
            if a:
                atrs[t].append(a)

        # quoted side
        p = os.path.join(W, day, "snapshots.jsonl")
        if os.path.exists(p):
            for line in open(p):
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = datetime.fromisoformat(rec["recorded_at"])
                key = ts.astimezone().strftime("%Y-%m-%dT%H:%M:00.000+0000")
                for s in rec.get("snapshots", []):
                    sym = s.get("symbol", "")
                    try:
                        root, right, strike = occ_parse(sym)
                        bid, ask = float(s["bid"]), float(s["ask"])
                        dlt = float(s["delta"])
                    except (ValueError, KeyError, TypeError, IndexError):
                        continue
                    if root not in TICKERS or bid <= 0 or ask <= bid:
                        continue
                    sp = stocks.get(root)
                    if not sp:
                        continue
                    # nearest stock price in time
                    spot = None
                    for k in (key,):
                        spot = sp.get(k)
                    if spot is None:
                        spot = st.median(list(sp.values()))
                    m = (spot - strike) if right == "C" else (strike - spot)
                    b = bucket_of(m)
                    if b is None:
                        continue
                    mid = (ask + bid) / 2
                    if mid < 0.3 or mid > 30:
                        continue
                    quoted[root][b]["spread"].append(ask - bid)
                    quoted[root][b]["delta"].append(abs(dlt))
                    quoted[root][b]["mid"].append(mid)

        # realised side, from option bars
        for fn in os.listdir(os.path.join(W, day)):
            if not fn.startswith("option-"):
                continue
            sym = fn[len("option-"):-len(".json")]
            try:
                root, right, strike = occ_parse(sym)
            except (ValueError, IndexError):
                continue
            if root not in TICKERS or not stocks.get(root):
                continue
            try:
                ob = json.load(open(os.path.join(W, day, fn)))
            except json.JSONDecodeError:
                continue
            series = sorted((b["time"], float(b["close"])) for b in ob)
            sp = stocks[root]
            for i in range(1, len(series)):
                t0, p0 = series[i - 1]
                t1, p1 = series[i]
                if t0 not in sp or t1 not in sp:
                    continue
                dt = (datetime.fromisoformat(t1.replace("Z", "+00:00"))
                      - datetime.fromisoformat(t0.replace("Z", "+00:00"))).total_seconds() / 60
                if dt <= 0 or dt > 3:
                    continue
                du = sp[t1] - sp[t0]
                if abs(du) < 1e-9:
                    continue
                move = du if right == "C" else -du
                m = (sp[t0] - strike) if right == "C" else (strike - sp[t0])
                b = bucket_of(m)
                if b is None:
                    continue
                bars_pts[root][b].append((move, p1 - p0))

    print("Signed moneyness: positive = IN the money, dollars.\n")
    results = {}
    for t in TICKERS:
        med_atr = st.median(atrs[t]) if atrs[t] else None
        print(f"=== {t}   median 1-min ATR {med_atr:.3f}")
        print(f"{'bucket':12s} {'n_quote':>8s} {'spread':>8s} {'mid':>7s} {'|delta|':>8s} "
              f"{'n_bars':>8s} {'delta_eff':>10s} {'$/ATR':>7s} {'COST_R':>7s}")
        results[t] = {}
        for b in range(len(BUCKETS)):
            q = quoted[t].get(b)
            pts = bars_pts[t].get(b) or []
            if not q or len(q["spread"]) < 200 or len(pts) < 300:
                continue
            X = np.array([[m] for m, _ in pts])
            y = np.array([d for _, d in pts])
            de = float(np.linalg.lstsq(X, y, rcond=None)[0][0])
            sp_med = st.median(q["spread"])
            per_atr = de * med_atr
            cost = sp_med / per_atr if per_atr > 0 else float("nan")
            print(f"{LABEL[b]:12s} {len(q['spread']):8d} {sp_med:8.4f} {st.median(q['mid']):7.2f} "
                  f"{st.median(q['delta']):8.3f} {len(pts):8d} {de:10.4f} {per_atr:7.3f} {cost:7.3f}")
            results[t][LABEL[b]] = dict(n_quote=len(q["spread"]), spread=sp_med,
                                        mid=st.median(q["mid"]), delta_q=st.median(q["delta"]),
                                        n_bars=len(pts), delta_eff=de, per_atr=per_atr, cost_R=cost)
        print()

    d = os.path.join(ROOT, "reports", f"moneyness-cost-{date.today():%Y-%m-%d}")
    os.makedirs(d, exist_ok=True)
    json.dump(results, open(os.path.join(d, "results.json"), "w"), indent=1)
    print(f"wrote {d}/results.json")


if __name__ == "__main__":
    main()
