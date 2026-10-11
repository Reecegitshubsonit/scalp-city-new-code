"""User's scale-out plan vs live rules, today's 52 entries and 90 days of history (raw cross side, same entries).
Plan: 10 contracts. Sell 2 at +0.5R, 3 at +1R, 2 at +1.5R, the last 3 at +2R. Once +1R is reached, the stop on what is left moves to 0R.
Stop before +1R: 1.0 / 0.75 / 0.5 R (tested). Levels checked on the 1-minute close (live parity); 'touch' = fills at the level when the bar's high/low reaches it (history only, best case).
Option dollars: same model as fix_evidence (spread and fees once per contract, time decay per contract-minute held).
Research only. Run from repo root: python3 reports/dissect-2026-10-09/scale_out.py -> reports/dissect-2026-10-09/scale_out.txt"""
import collections, statistics as st, sys
sys.path.insert(0, "reports/analysis-2026-10-09"); sys.path.insert(0, "reports/dissect-2026-10-09"); sys.argv = ["x"]
import fix_evidence as F, analyze as A
X = F.X
out = []
def P(s): print(s); out.append(s)

PLAN = ((0.5, 2), (1.0, 3), (1.5, 2), (2.0, 3))


class Pos:
    """One 10-contract position managed by a ladder. Tracks contract-weighted underlying move and contract-minutes."""
    def __init__(s, sg, ent, atr, stop, ladder, be_at):
        s.sg, s.ent, s.atr, s.stop0, s.ladder, s.be_at = sg, ent, atr, stop, list(ladder), be_at
        s.left, s.stopR, s.peak, s.held, s.dS, s.cmin = 10, -stop, 0.0, 0, 0.0, 0.0
        s.done = False; s.why = None

    def sell(s, q, px):
        s.dS += q / 10 * s.sg * (px - s.ent); s.cmin += q / 10 * s.held; s.left -= q
        if s.left <= 0: s.done = True

    def bar(s, close, hi=None, lo=None, flat=False):
        s.held += 1
        R = lambda px: s.sg * (px - s.ent) / s.atr
        lvl = lambda r: s.ent + s.sg * r * s.atr
        if flat: s.why = "TIME"; s.sell(s.left, close); return
        if hi is not None:                                  # touch mode: adverse side first (conservative within the bar)
            adv = lo if s.sg > 0 else hi; fav = hi if s.sg > 0 else lo
            if R(adv) <= s.stopR: s.why = s.why or "STOP"; s.sell(s.left, lvl(s.stopR)); return
            for r, q in list(s.ladder):
                if R(fav) >= r: s.sell(q, lvl(r)); s.ladder.remove((r, q)); s.peak = max(s.peak, r)
            if s.be_at is not None and s.peak >= s.be_at: s.stopR = max(s.stopR, 0.0)
            if not s.ladder and s.left > 0: s.sell(s.left, lvl(2.0))
            if s.done and not s.why: s.why = "TARGET"
            return
        r = R(close); s.peak = max(s.peak, r)
        if r <= s.stopR:
            s.why = "STOP" if s.stopR < 0 else "BREAKEVEN"; s.sell(s.left, close); return
        for lv, q in list(s.ladder):
            if r >= lv: s.sell(q, close); s.ladder.remove((lv, q))
        if s.be_at is not None and s.peak >= s.be_at: s.stopR = max(s.stopR, 0.0)
        if s.done: s.why = "TARGET"


def ladder_for(name):
    if name == "live 1R stop / 2R target": return ((2.0, 10),), None, 1.0
    stop = {"plan, stop 1R": 1.0, "plan, stop 0.75R": 0.75, "plan, stop 0.5R": 0.5}.get(name, 1.0)
    be = None if "no breakeven" in name else 1.0
    return PLAN, be, stop


NAMES = ("live 1R stop / 2R target", "plan, stop 1R", "plan, stop 0.75R", "plan, stop 0.5R", "plan, stop 1R, no breakeven")


def today(name):
    lad, be, stop = ladder_for(name); res = []
    for c in F.C:
        S = F.series[c["tk"]]; p = Pos(c["sgn"], c["sig_px"], c["atr"], stop, lad, be)
        for t in range(c["sig_t"] + 1, 960):
            if t not in S: continue
            p.bar(S[t]["p"], flat=t >= 15 * 60 + 55)
            if p.done: break
        if not p.done: p.sell(p.left, S[max(k for k in S)]["p"]); p.why = "EOD"
        res.append(dict(k=c["k"], R=p.dS / c["atr"], why=p.why, t=c["tk"], day="2026-10-09", S=c["sig_px"], dS=p.dS, hold=p.cmin, atr=c["atr"],
                        et=X.datetime(2026, 10, 9, c["sig_t"] // 60, c["sig_t"] % 60, tzinfo=A.ET), pnl=c["pnl"]))
    X.dollars(res, {}, {"SPY": 0.00009, "QQQ": 0.00014, "IWM": 0.00014})
    return res


def hist(name, touch=False):
    lad, be, stop = ladder_for(name); trades = []
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
                        trades.append(dict(t=t, bot=b, day=day, R=p.dS / p.atr, why=p.why, et=p.et, hold=p.cmin, atr=p.atr, S=p.ent, dS=p.dS))
                        del pos[b]; free[b] = end + A.timedelta(minutes=2)
                if end.time() < A.T(9, 31) or end.time() > A.T(15, 30): continue
                chop = abs(x["e9"] - x["e21"]) < 0.15 * x["atr"]
                for b in A.BOTS:
                    if b in pos or (free[b] and end < free[b]): continue
                    sig = x["sig"].get(b)
                    if not sig or (b == "vwap" and chop): continue
                    if b == "range" and end.time() < A.T(9, 46): continue
                    p = Pos(1 if sig == "CALL" else -1, x["c"], x["atr"], stop, lad, be); p.k, p.et = k, end; pos[b] = p
    X.dollars(trades, F.byday, F.bytk)
    return trades


def main():
    # ---- stop width evidence: how deep did eventual winners go first? ----
    P("STOP WIDTH: worst close before the exit, for trades that ended at the 2R target (live rules)")
    tg = [c for c in F.C if c["why"] == "TARGET"]
    P(f"  today ({len(tg)} targets): worst closes {sorted(round(c['mae'], 2) for c in tg)}")
    for s in (0.5, 0.75):
        P(f"    a {s}R stop would have killed {sum(c['mae'] <= -s for c in tg)} of {len(tg)} winners first")
    import inspect
    src = inspect.getsource(F.hsim).replace("trades.append(dict(t=t, bot=b, day=day, R=dS / p[\"atr\"], why=why,", "trades.append(dict(trough=p.get(\"trough\", 0), t=t, bot=b, day=day, R=dS / p[\"atr\"], why=why,")
    src = src.replace("p[\"held\"] += 1", "p[\"held\"] += 1; p[\"trough\"] = min(p.get(\"trough\", 0), p[\"sg\"] * (x[\"c\"] - p[\"ent\"]) / p[\"R\"])")
    ns = dict(F.__dict__); exec(src, ns)
    ht = [x for x in ns["hsim"]("cross") if x["why"] == "TARGET"]
    for s in (0.5, 0.75):
        P(f"  history ({len(ht)} targets): worst close at or below -{s}R before reaching target: {sum(x['trough'] <= -s for x in ht)} ({100*sum(x['trough'] <= -s for x in ht)/len(ht):.1f}%)")

    P("\nTODAY: same 52 entries, each replayed alone on logged closes")
    for name in NAMES:
        r = today(name); w = collections.Counter(x["why"] for x in r)
        P(f"  {name:30s} total {sum(x['R'] for x in r):+6.1f}R  model net ${sum(x['net$'] for x in r):+6.0f}  positive {sum(x['R'] > 0 for x in r):2d}  exits {dict(w)}")

    P("\nHISTORY: dev = first 70 days, holdout = last 20 days. R and $ are per 10-contract position.")
    for name in NAMES:
        tr = hist(name)
        for split, ds in (("dev", F.dev), ("holdout", F.hold)):
            P(f"  {split:8s}" + X.fmt(X.row(name, [x for x in tr if x["day"] in ds], len(ds), ci=split == "holdout")))
    for name in ("live 1R stop / 2R target", "plan, stop 1R"):
        tr = hist(name, touch=True)
        for split, ds in (("dev", F.dev), ("holdout", F.hold)):
            P(f"  {split:8s}" + X.fmt(X.row(name + " (touch fills)", [x for x in tr if x["day"] in ds], len(ds), ci=split == "holdout")))
    open("reports/dissect-2026-10-09/scale_out.txt", "w").write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
