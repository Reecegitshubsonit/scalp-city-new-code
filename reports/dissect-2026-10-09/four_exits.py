"""Backtest of the four exit designs discussed on 2026-10-09, same entries as live (raw cross side), 10 contracts, 1R stop.
  A  0.5R target: sell all 10 at +0.5R
  B  split: sell 5 at +0.5R, 5 at +1R
  C  user ladder: 2 at +0.5R, 3 at +1R, 2 at +1.5R, 3 at +2R; after +1R the rest exits at 0R
  D  ladder on trend setups only: C when price closed on the trade's side of VWAP for each of the last 30 minutes, else A
     (30 minutes fixed in advance, not tuned)
Each run with bar-close exits (live today) and touch fills (stop and targets fill at their level when the bar's high/low reaches it; best case).
Today: 52 entries on logged closes (bar-close only; the log has no highs/lows). History: 90 days, first 70 / last 20.
Research only. Run from repo root: python3 reports/dissect-2026-10-09/four_exits.py -> reports/dissect-2026-10-09/four_exits.txt"""
import collections, sys
sys.path.insert(0, "reports/analysis-2026-10-09"); sys.path.insert(0, "reports/dissect-2026-10-09"); sys.argv = ["x"]
import fix_evidence as F, scale_out as SO, analyze as A
X = F.X
out = []
def P(s): print(s); out.append(s)

LIVE = (((2.0, 10),), None)
A_ = (((0.5, 10),), None)
B_ = (((0.5, 5), (1.0, 5)), None)
C_ = (SO.PLAN, 1.0)
DESIGNS = {"live 2R target": lambda trend: LIVE, "A 0.5R target": lambda trend: A_, "B 5@0.5R + 5@1R": lambda trend: B_,
           "C ladder 2/3/2/3 + BE": lambda trend: C_, "D ladder on trend setups, else A": lambda trend: C_ if trend else A_}


def trend_today(c, S):
    vw = c["sig_px"] > c["vwap"]
    return (vw == (c["dir"] == "CALL")) and all(t in S and (S[t]["p"] > S[t]["vwap"]) == vw for t in range(c["sig_t"] - 30, c["sig_t"] + 1))


def today(pick):
    res = []
    for c in F.C:
        S = F.series[c["tk"]]; lad, be = pick(trend_today(c, S))
        p = SO.Pos(c["sgn"], c["sig_px"], c["atr"], 1.0, lad, be)
        for t in range(c["sig_t"] + 1, 960):
            if t not in S: continue
            p.bar(S[t]["p"], flat=t >= 15 * 60 + 55)
            if p.done: break
        if not p.done: p.sell(p.left, S[max(S)]["p"]); p.why = "EOD"
        res.append(dict(R=p.dS / c["atr"], why=p.why, t=c["tk"], day="2026-10-09", S=c["sig_px"], dS=p.dS, hold=p.cmin, atr=c["atr"],
                        et=X.datetime(2026, 10, 9, c["sig_t"] // 60, c["sig_t"] % 60, tzinfo=A.ET), trend=trend_today(c, S)))
    X.dollars(res, {}, {"SPY": 0.00009, "QQQ": 0.00014, "IWM": 0.00014})
    return res


def hist(pick, touch):
    trades = []
    for t in A.TICKERS:
        for day, xs in F.D[t].items():
            pos = {}; free = {b: None for b in A.BOTS}
            for k, x in enumerate(xs):
                end = x["end"]
                for b in list(pos):
                    p = pos[b]
                    if k <= p.k: continue
                    p.bar(x["c"], x["h"] if touch else None, x["l"] if touch else None, flat=end.time() >= A.T(15, 55) or k == len(xs) - 1)
                    if p.done:
                        trades.append(dict(t=t, bot=b, day=day, R=p.dS / p.atr, why=p.why, et=p.et, hold=p.cmin, atr=p.atr, S=p.ent, dS=p.dS, trend=p.trend))
                        del pos[b]; free[b] = end + A.timedelta(minutes=2)
                if end.time() < A.T(9, 31) or end.time() > A.T(15, 30): continue
                chop = abs(x["e9"] - x["e21"]) < 0.15 * x["atr"]
                for b in A.BOTS:
                    if b in pos or (free[b] and end < free[b]): continue
                    sig = x["sig"].get(b)
                    if not sig or (b == "vwap" and chop): continue
                    if b == "range" and end.time() < A.T(9, 46): continue
                    vw = x["c"] > x["vwap"]
                    trend = (vw == (sig == "CALL")) and k >= 30 and all((xs[j]["c"] > xs[j]["vwap"]) == vw for j in range(k - 30, k + 1))
                    lad, be = pick(trend)
                    p = SO.Pos(1 if sig == "CALL" else -1, x["c"], x["atr"], 1.0, lad, be); p.k, p.et, p.trend = k, end, trend; pos[b] = p
    X.dollars(trades, F.byday, F.bytk)
    return trades


P("TODAY: 52 live entries, bar-close exits on logged closes")
for name, pick in DESIGNS.items():
    r = today(pick)
    P(f"  {name:34s} total {sum(x['R'] for x in r):+6.1f}R  winners {sum(x['R'] > 0 for x in r):2d}  model net ${sum(x['net$'] for x in r):+6.0f}  exits {dict(collections.Counter(x['why'] for x in r))}")
P(f"  trend setups today (D uses the ladder): {sum(trend_today(c, F.series[c['tk']]) for c in F.C)} of {len(F.C)}")

rows = []
for touch in (False, True):
    P(f"\nHISTORY, {'touch fills (best case)' if touch else 'bar-close exits (live today)'}. dev = first 70 days, holdout = last 20. net$ per 10-contract position.")
    for name, pick in DESIGNS.items():
        tr = hist(pick, touch)
        for split, ds in (("dev", F.dev), ("holdout", F.hold)):
            r = X.row(name, [x for x in tr if x["day"] in ds], len(ds), ci=split == "holdout"); r.update(split=split, fills="touch" if touch else "close"); rows.append(r)
            P(f"  {split:8s}" + X.fmt(r))
        if name.startswith("D"):
            tt = [x for x in tr if x["trend"]]
            P(f"           D: trend setups {len(tt)} of {len(tr)} ({100*len(tt)/len(tr):.1f}%)")
import csv
with open("reports/dissect-2026-10-09/four_exits.csv", "w", newline="") as f:
    w = csv.DictWriter(f, ["fills", "split", "variant", "n", "per_day", "win", "grossR", "gross_usd", "net_usd", "net2_usd", "usd_day", "hold", "ci_lo", "ci_hi", "p_pos"], extrasaction="ignore")
    w.writeheader(); [w.writerow(r) for r in rows]
open("reports/dissect-2026-10-09/four_exits.txt", "w").write("\n".join(out) + "\n")
