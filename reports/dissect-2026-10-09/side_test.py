"""Direction-rule test, same entries as live: side from EMA9/21 (live), from price vs VWAP, or from price vs EMA50.
Research only. Run from repo root: python3 reports/dissect-2026-10-09/side_test.py  -> reports/dissect-2026-10-09/side_test.txt"""
import collections, sys
sys.path.insert(0, "reports/analysis-2026-10-09"); sys.path.insert(0, "reports/dissect-2026-10-09")
import analyze as A, dissect as X

_orig = A.prepare
def prepare(bars):
    """Same as analyze.prepare, plus the VWAP and EMA50 value on each bar (needed to pick a side from them)."""
    days = _orig(bars)
    e50 = A.Ema(50); day = None; pv = vv = 0.0; i = 0
    flat = [r for d in days.values() for r in d]
    for (s, o, h, l, c, v), r in zip(bars, flat):
        if s.date() != day: day = s.date(); pv = vv = 0.0
        tp = (h + l + c) / 3; pv += tp * v; vv += v
        r["vwap"] = pv / vv if vv else tp; r["e50"] = e50.u(c)
    return days

def simulate(D, side):
    """X.simulate with the side chosen by `side` instead of EMA9/21."""
    v = dict(stop=1, tgt=2)
    trades = []
    for t in A.TICKERS:
        for day, xs in D[t].items():
            pos = {}; free = {b: None for b in A.BOTS}
            for k, x in enumerate(xs):
                end = x["end"]
                for b in list(pos):
                    p = pos[b]
                    if k <= p["k"]: continue
                    p["held"] += 1
                    why, R = X.exit_check(p, x["c"], end.time(), v)
                    if why is None and k == len(xs) - 1: why = "EOD"
                    if why:
                        dS = p["sg"] * (x["c"] - p["ent"])
                        trades.append(dict(t=t, bot=b, day=day, R=dS / p["atr"], why=why, et=p["et"], hold=(end - p["et"]).total_seconds() / 60, atr=p["atr"], S=p["ent"], dS=dS))
                        del pos[b]; free[b] = end + A.timedelta(minutes=2)
                if end.time() < A.T(9, 31) or end.time() > A.T(15, 30): continue
                chop = abs(x["e9"] - x["e21"]) < 0.15 * x["atr"]
                for b in A.BOTS:
                    if b in pos or (free[b] and end < free[b]): continue
                    sig = x["sig"].get(b)
                    if not sig or (b == "vwap" and chop): continue
                    if b == "range" and end.time() < A.T(9, 46): continue
                    if side == "ema9/21": d = "CALL" if x["e9"] > x["e21"] else "PUT" if x["e9"] < x["e21"] else sig
                    elif side == "vwap": d = "CALL" if x["c"] > x["vwap"] else "PUT"
                    else: d = "CALL" if x["c"] > x["e50"] else "PUT"
                    pos[b] = X.open_pos(d, x["c"], x["atr"], v, end, k)
    return trades

def main():
    D = {t: prepare(A.load(t)) for t in A.TICKERS}
    days = sorted(set(D["SPY"]) & set(D["QQQ"]) & set(D["IWM"]))
    for t in A.TICKERS: D[t] = collections.OrderedDict((d, v) for d, v in D[t].items() if d in days)
    byday, bytk = A.premium_model()
    dev, hold = set(days[:70]), set(days[70:])
    out = []
    for side in ("ema9/21", "vwap", "ema50"):
        tr = simulate(D, side); X.dollars(tr, byday, bytk)
        for split, ds in (("dev", dev), ("holdout", hold)):
            out.append(f"{split:8s} " + X.fmt(X.row(f"side from {side}", [x for x in tr if x["day"] in ds], len(ds), ci=split == "holdout")))
    # today: replay actual entries with the side from VWAP / EMA50 at the signal
    series, state, trades, failed, orphans = X.read_log()
    X.P = lambda *a: None
    allc = X.part1(series, state, trades, failed, orphans)
    for side in ("live", "vwap", "ema50"):
        tot = 0; n = 0; wins = 0; puts = 0
        for c in allc:
            S = series[c["tk"]]
            d = c["dir"] if side == "live" else ("CALL" if c["sig_px"] > (c["vwap"] if side == "vwap" else c["e50"]) else "PUT")
            p = X.open_pos(d, c["sig_px"], c["atr"], dict(stop=1, tgt=2), None, 0)
            for t in range(c["sig_t"] + 1, 960):
                if t not in S: continue
                p["held"] += 1
                why, R = X.exit_check(p, S[t]["p"], A.T(t // 60, t % 60), dict(stop=1, tgt=2))
                if why: break
            tot += R; n += 1; wins += R > 0; puts += d == "PUT"
        out.append(f"today    side from {side:6s} entries={n} puts={puts} win={wins} total R={tot:+.1f}")
    open("reports/dissect-2026-10-09/side_test.txt", "w").write("\n".join(out) + "\n"); print("\n".join(out))


if __name__ == "__main__":
    main()
