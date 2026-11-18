"""Hunt for a state that predicts QQQ/SPY/IWM direction over 5-30 minutes.

Scalp City's three triggers are EVENTS (a cross, a breakout) and entry_quality.py showed they
carry no directional information. This tests STATES instead: given where the market is right
now, what is the expected signed move over the next h minutes?

Testing states rather than events matters for power. Every eligible bar is an observation
(~250k) instead of only the 11k bars a trigger happens to fire on.

Discipline, because a hunt overfits by construction:
  - the feature list below is fixed before running and is not extended after seeing results
  - the sample is split in time; the FIRST 60% of days rank candidates, the LAST 40% judges them
  - a candidate counts only if the out-of-sample bucket mean keeps the in-sample SIGN
  - the bar to clear is the measured round-trip cost, 0.079-0.094 R on SPY/QQQ
  - forward returns are signed long, so a reliably negative bucket is tradeable short

    .venv/bin/python backtest/entry_hunt.py
"""
import argparse
import json
import math
import os
import statistics as st
import sys
from datetime import date, time as T, timedelta

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import filters as F
from trail_grid import COST_BY_TICKER, load_range

HORIZONS = (5, 15, 30)
NBUCKET = 5


def features(t, rows):
    """One record per eligible bar: feature values plus forward signed-long returns."""
    out = []
    byday = {}
    for r in rows:
        byday.setdefault(r["t"].date(), []).append(r)
    prev_close = None
    prev_atr_med = None   # previous day's median 1-min ATR: known before this day opens
    for day in sorted(byday):
        xs = byday[day]
        n = len(xs)
        c = [F.bars_hl[(t, x["i"])][2] for x in xs]
        h_ = [F.bars_hl[(t, x["i"])][0] for x in xs]
        l_ = [F.bars_hl[(t, x["i"])][1] for x in xs]
        vol = [x.get("v", 0.0) for x in xs]
        day_open = c[0]
        hi15 = lo15 = None
        for k, x in enumerate(xs):
            if x["t"].time() < T(9, 45):
                hi15 = h_[k] if hi15 is None else max(hi15, h_[k])
                lo15 = l_[k] if lo15 is None else min(lo15, l_[k])
        atr_today = st.median([x["atr"] for x in xs if x["atr"]]) or 1.0
        atr_day = prev_atr_med          # strictly prior information
        if atr_day is None:
            prev_close, prev_atr_med = c[-1], atr_today
            continue
        for k, x in enumerate(xs):
            end = x["t"] + timedelta(minutes=1)
            if end.time() > F.LAST_ENTRY or end.time() < T(9, 45):
                continue
            atr = x["atr"]
            if not atr or hi15 is None or hi15 <= lo15:
                continue
            fwd = {}
            for hh in HORIZONS:
                if k + hh < n:
                    fwd[hh] = (c[k + hh] - c[k]) / atr
            if len(fwd) < len(HORIZONS):
                continue
            mom5 = (c[k] - c[k - 5]) / atr if k >= 5 else 0.0
            mom15 = (c[k] - c[k - 15]) / atr if k >= 15 else 0.0
            rng_pos = (c[k] - lo15) / (hi15 - lo15)
            gap = (day_open - prev_close) / atr_day if prev_close else 0.0
            rec = dict(
                t=t, day=day, minute=(x["t"].hour * 60 + x["t"].minute) - 570,
                fwd=fwd,
                mom5=mom5,
                mom15=mom15,
                ema_spread=(x["e9"] - x["e21"]) / atr,
                range_pos=rng_pos,
                atr_rel=atr / atr_day,
                bar_range=(h_[k] - l_[k]) / atr,
                gap=gap,
                from_open=(c[k] - day_open) / atr,
            )
            out.append(rec)
        prev_close, prev_atr_med = c[-1], atr_today
    return out


FEATURES = ["mom5", "mom15", "ema_spread", "range_pos", "atr_rel", "bar_range", "gap", "from_open", "minute"]


def buckets(vals, nb):
    qs = [np.quantile(vals, i / nb) for i in range(nb + 1)]
    qs[0], qs[-1] = -np.inf, np.inf
    return qs


def mean_t(v):
    m = float(np.mean(v))
    se = float(np.std(v, ddof=1)) / math.sqrt(len(v))
    return m, (m / se if se else 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suffix", default="2025-11-17_2026-11-14")
    ap.add_argument("--last-entry", default="10:59")
    a = ap.parse_args()
    hh, mm = (int(x) for x in a.last_entry.split(":"))
    F.LAST_ENTRY = T(hh, mm)

    recs = []
    for t in F.TICKERS:
        bars = load_range(t, a.suffix)
        for i, (s, o, h, l, c, v) in enumerate(bars):
            F.bars_hl[(t, i)] = (h, l, c)
        rows = F.prepare(bars)
        recs += features(t, rows)
    days = sorted({r["day"] for r in recs})
    cut = days[int(len(days) * 0.6)]
    ins = [r for r in recs if r["day"] < cut]
    oos = [r for r in recs if r["day"] >= cut]
    print(f"bars {len(recs):,}  days {len(days)}  split at {cut}")
    print(f"  in-sample {len(ins):,}   out-of-sample {len(oos):,}")
    print(f"  cost to clear: {COST_BY_TICKER}\n")

    # unconditional signed-long drift per ticker and horizon, measured IN-SAMPLE only
    drift = {}
    for t in F.TICKERS:
        for h in HORIZONS:
            v = [r["fwd"][h] for r in ins if r["t"] == t]
            drift[(t, h)] = float(np.mean(v)) if v else 0.0
    print("in-sample drift (signed long, ATR units):")
    for k, v in drift.items():
        print(f"  {k[0]} h={k[1]:2d}  {v:+.4f}")
    print()
    for r in recs:
        r["exc"] = {h: r["fwd"][h] - drift[(r["t"], h)] for h in HORIZONS}

    results = []
    for feat in FEATURES:
        for h in HORIZONS:
            vi = np.array([r[feat] for r in ins], dtype=float)
            yi = np.array([r["exc"][h] for r in ins], dtype=float)
            vo = np.array([r[feat] for r in oos], dtype=float)
            yo = np.array([r["exc"][h] for r in oos], dtype=float)
            qs = buckets(vi, NBUCKET)
            for b in range(NBUCKET):
                mi = (vi >= qs[b]) & (vi < qs[b + 1])
                mo = (vo >= qs[b]) & (vo < qs[b + 1])
                if mi.sum() < 500 or mo.sum() < 500:
                    continue
                m_i, t_i = mean_t(yi[mi])
                m_o, t_o = mean_t(yo[mo])
                results.append(dict(feat=feat, h=h, bucket=b,
                                    lo=float(qs[b]), hi=float(qs[b + 1]),
                                    n_in=int(mi.sum()), mean_in=m_i, t_in=t_i,
                                    n_oos=int(mo.sum()), mean_oos=m_o, t_oos=t_o,
                                    same_sign=(m_i > 0) == (m_o > 0),
                                    abs_oos=abs(m_o)))

    print(f"tested {len(results)} feature/horizon/bucket cells\n")
    ranked = sorted(results, key=lambda r: -abs(r["t_in"]))
    print("TOP 12 BY IN-SAMPLE |t|  (in-sample is for ranking only)")
    print(f"{'feature':12s} {'h':>3s} {'bkt':>3s} {'range':>18s} {'n_in':>7s} {'mean_in':>8s} {'t_in':>6s} "
          f"{'mean_oos':>9s} {'t_oos':>6s} {'same':>5s}")
    for r in ranked[:12]:
        rng = f"{r['lo']:+.2f}..{r['hi']:+.2f}" if abs(r['lo']) < 1e6 else f"  <{r['hi']:+.2f}"
        if abs(r['hi']) > 1e6:
            rng = f"  >{r['lo']:+.2f}"
        print(f"{r['feat']:12s} {r['h']:3d} {r['bucket']:3d} {rng:>18s} {r['n_in']:7d} "
              f"{r['mean_in']:+8.4f} {r['t_in']:+6.2f} {r['mean_oos']:+9.4f} {r['t_oos']:+6.2f} "
              f"{'yes' if r['same_sign'] else 'NO':>5s}")

    print()
    survivors = [r for r in results
                 if abs(r["t_in"]) > 3 and r["same_sign"] and abs(r["t_oos"]) > 2]
    print(f"SURVIVORS: |t_in| > 3, sign holds out of sample, |t_oos| > 2  ->  {len(survivors)}")
    if survivors:
        print(f"{'feature':12s} {'h':>3s} {'range':>18s} {'mean_oos':>9s} {'t_oos':>6s} {'clears cost?':>13s}")
        for r in sorted(survivors, key=lambda r: -r["abs_oos"]):
            rng = f"{r['lo']:+.2f}..{r['hi']:+.2f}"
            if abs(r['lo']) > 1e6:
                rng = f"  <{r['hi']:+.2f}"
            if abs(r['hi']) > 1e6:
                rng = f"  >{r['lo']:+.2f}"
            clears = abs(r["mean_oos"]) > 0.094
            print(f"{r['feat']:12s} {r['h']:3d} {rng:>18s} {r['mean_oos']:+9.4f} {r['t_oos']:+6.2f} "
                  f"{'YES' if clears else 'no':>13s}")
    tradeable = [r for r in survivors if abs(r["mean_oos"]) > 0.094]
    print(f"\nof those, clearing the QQQ round-trip cost of 0.094 R: {len(tradeable)}")

    d = os.path.join("reports", f"entry-hunt-{date.today():%Y-%m-%d}")
    os.makedirs(d, exist_ok=True)
    json.dump(dict(split=str(cut), n_cells=len(results), n_survivors=len(survivors),
                   n_tradeable=len(tradeable), cost=COST_BY_TICKER,
                   cells=results), open(os.path.join(d, "results.json"), "w"), indent=1)
    print(f"wrote {d}/results.json")


if __name__ == "__main__":
    main()
