"""Does a Scalp City entry signal predict anything? Exits are not involved.

For every bar on which a bot would fire, this measures what the underlying actually did next,
in ATR units at entry, signed so positive is in the trade's favour:

  fwd[h]   signed return h minutes after the entry bar's close
  MFE/MAE  best and worst signed excursion within 30 minutes

Nothing here can be improved by a smarter exit: MFE is the ceiling any exit could capture, and
the measured round-trip spread cost is the floor it has to clear.

Every signal mean is reported against a DRIFT BENCHMARK: the same horizon measured from every
eligible bar of the same session, signed the same way the signal set is signed. Over a rising
year a CALL-heavy signal set looks profitable without predicting anything, and subtracting the
benchmark removes that.

Costs in ATR units, measured in reports/premium-fit-2026-11-17/report.md.

    .venv/bin/python backtest/entry_quality.py --suffix 2025-11-17_2026-11-14
"""
import argparse
import json
import math
import os
import statistics as st
import sys
from datetime import date, datetime, time as T, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import filters as F
from trail_grid import COST_BY_TICKER, load_range

HORIZONS = (1, 2, 3, 5, 10, 15, 30)
MFE_WINDOW = 30
FILTER_SETS = [
    ("none (live rules)", {}),
    ("buffer 0.2", dict(buffer=0.2)),
    ("buffer 0.4", dict(buffer=0.4)),
    ("trend align", dict(trend=True)),
    ("chop all bots", dict(chop_all=True)),
    ("2 closes", dict(confirm=True)),
    ("buffer 0.2 + trend + chop all", dict(buffer=0.2, trend=True, chop_all=True)),
]


def collect(t, rows, cfg):
    """One record per signal, plus the per-bar drift benchmark for the same session."""
    sigs, drift = [], []
    byday = {}
    for r in rows:
        byday.setdefault(r["t"].date(), []).append(r)
    for day, xs in byday.items():
        n = len(xs)
        closes = [F.bars_hl[(t, x["i"])][2] for x in xs]
        highs = [F.bars_hl[(t, x["i"])][0] for x in xs]
        lows = [F.bars_hl[(t, x["i"])][1] for x in xs]
        for k, x in enumerate(xs):
            end = x["t"] + timedelta(minutes=1)
            if end.time() > F.LAST_ENTRY:
                continue
            atr = x["atr"]
            if not atr:
                continue
            # unconditional drift from this bar, signed long
            d = {}
            for h in HORIZONS:
                if k + h < n:
                    d[h] = (closes[k + h] - closes[k]) / atr
            if d:
                drift.append(d)
            for bot in ("vwap", "ema50", "range"):
                if bot == "range" and end.time() < T(9, 45):
                    continue
                sig = F.signal(xs, k, bot, cfg)
                if not sig:
                    continue
                call = sig == "CALL"
                rec = dict(t=t, bot=bot, day=day, dir=sig, atr=atr)
                for h in HORIZONS:
                    if k + h < n:
                        raw = (closes[k + h] - closes[k]) / atr
                        rec[f"f{h}"] = raw if call else -raw
                hi = k + 1
                best = worst = 0.0
                while hi < n and hi <= k + MFE_WINDOW:
                    up = (highs[hi] - closes[k]) / atr
                    dn = (lows[hi] - closes[k]) / atr
                    fav, adv = (up, dn) if call else (-dn, -up)
                    best = max(best, fav)
                    worst = min(worst, adv)
                    hi += 1
                rec["mfe"], rec["mae"] = best, worst
                sigs.append(rec)
    return sigs, drift


def mean_t(vals):
    if len(vals) < 3:
        return None
    m = st.mean(vals)
    se = st.stdev(vals) / math.sqrt(len(vals))
    return m, (m / se if se else float("nan")), len(vals)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suffix", default="2025-11-17_2026-11-14")
    ap.add_argument("--last-entry", default="10:59")
    a = ap.parse_args()
    hh, mm = (int(x) for x in a.last_entry.split(":"))
    F.LAST_ENTRY = T(hh, mm)

    allrows = {}
    for t in F.TICKERS:
        bars = load_range(t, a.suffix)
        for i, (s, o, h, l, c, v) in enumerate(bars):
            F.bars_hl[(t, i)] = (h, l, c)
        allrows[t] = F.prepare(bars)
    days = sorted({r["t"].date() for r in allrows["SPY"]})
    print(f"days {days[0]}..{days[-1]} ({len(days)}), entries to {F.LAST_ENTRY}")
    print(f"costs {COST_BY_TICKER}\n")

    out = {}
    for label, cfg in FILTER_SETS:
        sigs, drift = [], []
        for t in F.TICKERS:
            s, d = collect(t, allrows[t], cfg)
            sigs += s
            drift += d
        if not sigs:
            continue
        ncall = sum(1 for s in sigs if s["dir"] == "CALL")
        tilt = (ncall - (len(sigs) - ncall)) / len(sigs)
        print(f"--- {label}   signals {len(sigs)}  CALL share {100*ncall/len(sigs):.1f}%")
        print(f"    {'h':>4s} {'n':>6s} {'mean fwd':>9s} {'t':>7s} {'drift adj':>10s} {'excess':>8s}")
        row = {}
        for h in HORIZONS:
            v = [s[f"f{h}"] for s in sigs if f"f{h}" in s]
            dv = [d[h] for d in drift if h in d]
            r = mean_t(v)
            if not r or not dv:
                continue
            m, tt, n = r
            bench = st.mean(dv) * tilt
            print(f"    {h:4d} {n:6d} {m:+9.4f} {tt:+7.2f} {bench:+10.4f} {m-bench:+8.4f}")
            row[h] = dict(n=n, mean=m, t=tt, bench=bench, excess=m - bench)
        mfe = mean_t([s["mfe"] for s in sigs])
        mae = mean_t([s["mae"] for s in sigs])
        print(f"    MFE30 mean {mfe[0]:+.3f}  median {st.median([s['mfe'] for s in sigs]):+.3f}   "
              f"MAE30 mean {mae[0]:+.3f}  median {st.median([s['mae'] for s in sigs]):+.3f}")
        out[label] = dict(n=len(sigs), call_share=100 * ncall / len(sigs), horizons=row,
                          mfe_mean=mfe[0], mae_mean=mae[0])
        print()

    # per ticker / per bot on the live rule set, against each ticker's own cost
    sigs = []
    for t in F.TICKERS:
        s, _ = collect(t, allrows[t], {})
        sigs += s
    print("live rules, 15-minute forward return against that ticker's measured round-trip cost")
    print(f"{'ticker':7s} {'bot':7s} {'n':>6s} {'fwd15':>8s} {'t':>7s} {'cost':>7s} {'net':>8s} "
          f"{'medMFE':>8s} {'medMAE':>8s}")
    detail = {}
    for t in F.TICKERS:
        for bot in ("vwap", "ema50", "range"):
            g = [s for s in sigs if s["t"] == t and s["bot"] == bot and "f15" in s]
            r = mean_t([s["f15"] for s in g])
            if not r:
                continue
            m, tt, n = r
            c = COST_BY_TICKER[t]
            print(f"{t:7s} {bot:7s} {n:6d} {m:+8.4f} {tt:+7.2f} {c:7.3f} {m-c:+8.4f} "
                  f"{st.median([s['mfe'] for s in g]):+8.3f} {st.median([s['mae'] for s in g]):+8.3f}")
            detail[f"{t}/{bot}"] = dict(n=n, fwd15=m, t=tt, cost=c, net=m - c)

    d = os.path.join("reports", f"entry-quality-{date.today():%Y-%m-%d}")
    os.makedirs(d, exist_ok=True)
    json.dump(dict(filter_sets=out, per_ticker_bot=detail, cost=COST_BY_TICKER,
                   days=[str(days[0]), str(days[-1])]), open(os.path.join(d, "results.json"), "w"), indent=1)
    print(f"\nwrote {d}/results.json")


if __name__ == "__main__":
    main()
