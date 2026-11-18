"""Do option-market states predict underlying direction? Five features, 24 days.

This is the one feature family the 1-minute OHLC scans could not reach: implied volatility,
skew, option volume and quoted liquidity, from data/webull/<day>/snapshots.jsonl.

POWER WARNING, stated before any result. There are 24 usable days. Bars within a day are
heavily autocorrelated, so the effective sample is nearer 24 than the ~9,000 bar-level
observations. A day-level sign test needs 17 of 24 days to reach p<0.05 one-sided. Anything
weaker than that is not evidence, whatever the bar-level t-statistic says.

Features are fixed before running and the list is not extended afterwards:
  iv_atm        ATM implied vol (mean |delta| nearest 0.5)
  iv_skew       IV of the ~25-delta put minus IV of the ~25-delta call
  iv_chg15      change in ATM IV over the last 15 minutes
  pc_volume     put volume / (put + call volume) across the chain so far today
  rel_spread    volume-weighted (ask-bid)/mid across the chain

Judged on: day-level sign consistency first, bar-level t second.

    .venv/bin/python backtest/greek_hunt.py
"""
import json
import math
import os
import statistics as st
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = os.path.join(ROOT, "data", "webull")
HORIZONS = (15, 30)
TICKERS = ("QQQ", "SPY", "IWM")


def parse_day(day):
    """Per ticker, per minute: option-chain features."""
    p = os.path.join(W, day, "snapshots.jsonl")
    if not os.path.exists(p):
        return {}
    permin = defaultdict(lambda: defaultdict(list))
    for line in open(p):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = datetime.fromisoformat(rec["recorded_at"])
        minute = ts.replace(second=0, microsecond=0)
        for s in rec.get("snapshots", []):
            sym = s.get("symbol", "")
            tkr = "".join(c for c in sym[:3] if c.isalpha())
            if tkr not in TICKERS:
                continue
            try:
                d = dict(delta=float(s["delta"]), iv=float(s["imp_vol"]),
                         bid=float(s["bid"]), ask=float(s["ask"]),
                         vol=float(s.get("volume") or 0))
            except (KeyError, ValueError, TypeError):
                continue
            if d["iv"] <= 0 or d["bid"] <= 0 or d["ask"] <= d["bid"]:
                continue
            d["right"] = "P" if sym[9] == "P" else "C"
            permin[tkr][minute].append(d)
    out = {}
    for tkr, mins in permin.items():
        cum_c = cum_p = 0.0
        series = {}
        for m in sorted(mins):
            ch = mins[m]
            if len(ch) < 6:
                continue
            atm = sorted(ch, key=lambda x: abs(abs(x["delta"]) - 0.5))[:4]
            iv_atm = st.mean(x["iv"] for x in atm)
            puts = [x for x in ch if x["right"] == "P"]
            calls = [x for x in ch if x["right"] == "C"]
            skew = None
            if puts and calls:
                p25 = sorted(puts, key=lambda x: abs(abs(x["delta"]) - 0.25))[0]
                c25 = sorted(calls, key=lambda x: abs(abs(x["delta"]) - 0.25))[0]
                skew = p25["iv"] - c25["iv"]
            cum_c += sum(x["vol"] for x in calls)
            cum_p += sum(x["vol"] for x in puts)
            tot = cum_c + cum_p
            rs = [(x["ask"] - x["bid"]) / ((x["ask"] + x["bid"]) / 2) for x in ch]
            series[m] = dict(iv_atm=iv_atm, iv_skew=skew,
                             pc_volume=(cum_p / tot if tot else None),
                             rel_spread=st.mean(rs))
        out[tkr] = series
    return out


def stock_bars(day, tkr):
    p = os.path.join(W, day, f"stock-{tkr}.json")
    if not os.path.exists(p):
        return None
    bars = []
    for b in json.load(open(p)):
        t = datetime.fromisoformat(b["time"].replace("Z", "+00:00"))
        bars.append((t, float(b["high"]), float(b["low"]), float(b["close"])))
    bars.sort()
    return bars


def atr_of(bars, period=14):
    out, atr, pc = [], None, None
    for i, (t, h, l, c) in enumerate(bars):
        tr = (h - l) if pc is None else max(h - l, abs(h - pc), abs(l - pc))
        pc = c
        n = i + 1
        atr = tr if atr is None else ((atr * (period - 1) + tr) / period if n > period else (atr * (n - 1) + tr) / n)
        out.append(atr)
    return out


def main():
    days = sorted(d for d in os.listdir(W) if d[0].isdigit())
    recs = []
    used = []
    for day in days:
        feats = parse_day(day)
        if not feats:
            continue
        got = 0
        for tkr in TICKERS:
            series = feats.get(tkr) or {}
            bars = stock_bars(day, tkr)
            if not bars or not series:
                continue
            atrs = atr_of(bars)
            idx = {t.replace(tzinfo=None): i for i, (t, h, l, c) in enumerate(bars)}
            closes = [c for (t, h, l, c) in bars]
            hist = sorted(series)
            for j, m in enumerate(hist):
                key = m.astimezone(bars[0][0].tzinfo).replace(tzinfo=None)
                i = idx.get(key)
                if i is None or not atrs[i]:
                    continue
                f = series[m]
                if f["iv_skew"] is None or f["pc_volume"] is None:
                    continue
                prev = None
                for back in hist[:j][::-1]:
                    if (m - back).total_seconds() >= 15 * 60:
                        prev = series[back]
                        break
                fwd = {}
                for h in HORIZONS:
                    if i + h < len(closes):
                        fwd[h] = (closes[i + h] - closes[i]) / atrs[i]
                if len(fwd) < len(HORIZONS):
                    continue
                recs.append(dict(day=day, t=tkr, fwd=fwd,
                                 iv_atm=f["iv_atm"], iv_skew=f["iv_skew"],
                                 iv_chg15=(f["iv_atm"] - prev["iv_atm"]) if prev else None,
                                 pc_volume=f["pc_volume"], rel_spread=f["rel_spread"]))
                got += 1
        if got:
            used.append(day)
    print(f"usable days {len(used)}  observations {len(recs):,}")
    print(f"  day-level bar for p<0.05 one-sided: {math.ceil(0.5*len(used) + 0.98*math.sqrt(len(used)))} of {len(used)}\n")

    # drift control per ticker/horizon
    drift = {}
    for t in TICKERS:
        for h in HORIZONS:
            v = [r["fwd"][h] for r in recs if r["t"] == t]
            drift[(t, h)] = float(np.mean(v)) if v else 0.0
    for r in recs:
        r["exc"] = {h: r["fwd"][h] - drift[(r["t"], h)] for h in HORIZONS}

    FEATS = ["iv_atm", "iv_skew", "iv_chg15", "pc_volume", "rel_spread"]
    print(f"{'feature':11s} {'h':>3s} {'bkt':>3s} {'n':>6s} {'mean exc':>9s} {'t':>7s} "
          f"{'days same sign':>15s}")
    rows = []
    for feat in FEATS:
        vals = [r for r in recs if r.get(feat) is not None]
        if len(vals) < 500:
            continue
        arr = np.array([r[feat] for r in vals], dtype=float)
        qs = [np.quantile(arr, q) for q in (0, 1 / 3, 2 / 3, 1)]
        qs[0], qs[-1] = -np.inf, np.inf
        for h in HORIZONS:
            for b in range(3):
                g = [r for r in vals if qs[b] <= r[feat] < qs[b + 1]]
                if len(g) < 300:
                    continue
                y = np.array([r["exc"][h] for r in g])
                m = float(np.mean(y))
                se = float(np.std(y, ddof=1)) / math.sqrt(len(y))
                tt = m / se if se else 0.0
                byday = defaultdict(list)
                for r in g:
                    byday[r["day"]].append(r["exc"][h])
                dd = [d for d in byday if len(byday[d]) >= 20]
                same = sum(1 for d in dd if (np.mean(byday[d]) > 0) == (m > 0))
                print(f"{feat:11s} {h:3d} {b:3d} {len(g):6d} {m:+9.4f} {tt:+7.2f} "
                      f"{same:>8d}/{len(dd):<6d}")
                rows.append(dict(feat=feat, h=h, bucket=b, n=len(g), mean=m, t=tt,
                                 days_same=same, days=len(dd)))
    need = math.ceil(0.5 * len(used) + 0.98 * math.sqrt(len(used)))
    win = [r for r in rows if abs(r["t"]) > 3 and r["days_same"] >= need and abs(r["mean"]) > 0.094]
    print(f"\ncells passing |t|>3 AND day-sign >= {need} AND |mean| > 0.094 R: {len(win)}")
    for r in win:
        print(f"  {r['feat']} h={r['h']} bucket={r['bucket']} mean {r['mean']:+.4f} "
              f"t {r['t']:+.2f} days {r['days_same']}/{r['days']}")
    d = os.path.join(ROOT, "reports", f"greek-hunt-{date.today():%Y-%m-%d}")
    os.makedirs(d, exist_ok=True)
    json.dump(dict(days=used, n=len(recs), cells=rows, passed=len(win), need_days=need),
              open(os.path.join(d, "results.json"), "w"), indent=1)
    print(f"wrote {d}/results.json")


if __name__ == "__main__":
    main()
