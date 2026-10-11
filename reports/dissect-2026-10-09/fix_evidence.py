"""Evidence for each proposed fix: today's 52 closed trades and 90 historical days, with the side rule that actually ran (raw cross).
Research only. Run from repo root: python3 reports/dissect-2026-10-09/fix_evidence.py -> reports/dissect-2026-10-09/fix_evidence.txt

Today: each entry replayed alone on the logged 1-minute closes (bar-close exits), in R (1 R = signal-time ATR on the underlying).
History: same simulator as side_test.py (live rules, bar-close exits, 2 min cooldown); dev = first 70 days, holdout = last 20.
net$ = option model from reports/analysis-2026-10-09 with today's quoted spread per ticker.
"""
import collections, statistics as st, sys
sys.path.insert(0, "reports/analysis-2026-10-09"); sys.path.insert(0, "reports/dissect-2026-10-09"); sys.argv = ["x"]
import analyze as A, dissect as X, side_test as ST

OUT = "reports/dissect-2026-10-09/fix_evidence.txt"
lines = []
def P(*a):
    s = " ".join(str(x) for x in a); print(s); lines.append(s)

X.P = lambda *a: None
series, state, trades, failed, orphans = X.read_log()
allc = X.part1(series, state, trades, failed, orphans)
C = [c for c in allc if not c.get("orphan")]
for i, c in enumerate(C, 1): c["k"] = i


def side_of(rule, c, S):
    """Side for today's entry c under a rule. Trend-day rules look back over the logged closes."""
    if rule == "cross": return c["dir"]
    vw = "CALL" if c["sig_px"] > c["vwap"] else "PUT"
    if rule == "vwap": return vw
    t0 = c["sig_t"]
    if rule.startswith("hold"):          # VWAP side only if price closed on that side of VWAP for each of the last N minutes, else cross
        n = int(rule[4:]); ok = all(t in S and (S[t]["p"] > S[t]["vwap"]) == (vw == "CALL") for t in range(t0 - n, t0 + 1))
        return vw if ok else c["dir"]
    if rule.startswith("dist"):          # VWAP side only if price is at least D ATR from VWAP, else cross
        d = float(rule[4:]); return vw if abs(c["sig_px"] - c["vwap"]) / c["atr"] >= d else c["dir"]


def replay(c, d, v):
    S = series[c["tk"]]; p = X.open_pos(d, c["sig_px"], c["atr"], v, None, 0); R = 0.0; why = "EOD"
    for t in range(c["sig_t"] + 1, 960):
        if t not in S: continue
        p["held"] += 1; w, R = X.exit_check(p, S[t]["p"], X.T(t // 60, t % 60), v)
        if w: why = w; break
    return R, why


BASE = dict(stop=1, tgt=2)
base = {c["k"]: replay(c, c["dir"], BASE)[0] for c in C}
P(f"TODAY: {len(C)} closed trades replayed on logged closes. Live rules total {sum(base.values()):+.1f}R, {sum(r > 0 for r in base.values())} winners. Logged P&L {sum(c['pnl'] for c in C):+.0f}")

# ---------- Fix 1: side from VWAP ----------
P("\n=== FIX 1: choose side from VWAP ===")
for rule in ("vwap", "hold15", "hold30", "hold60", "dist1", "dist2"):
    res = {c["k"]: replay(c, side_of(rule, c, series[c["tk"]]), BASE)[0] for c in C}
    changed = [c for c in C if side_of(rule, c, series[c["tk"]]) != c["dir"]]
    l2w = [c["k"] for c in changed if base[c["k"]] <= 0 < res[c["k"]]]
    w2l = [c["k"] for c in changed if base[c["k"]] > 0 >= res[c["k"]]]
    P(f"  today {rule:7s}: side changed on {len(changed):2d} trades; loser->winner {len(l2w)} {l2w}; winner->loser {len(w2l)} {w2l}; "
      f"total {sum(res.values()):+.1f}R (live {sum(base.values()):+.1f}R), winners {sum(r > 0 for r in res.values())}")
P("  Today's split by price vs VWAP at the signal (live side):")
for lab, f in (("with VWAP", lambda c: c["vwap_side"] >= 0), ("against VWAP", lambda c: c["vwap_side"] < 0)):
    xs = [c for c in C if f(c)]
    P(f"    {lab:12s} n={len(xs):2d} targets={sum(c['why'] == 'TARGET' for c in xs):2d} logged ${sum(c['pnl'] for c in xs):+.0f} replay {sum(base[c['k']] for c in xs):+.1f}R")

# ---------- history simulator with side rules and exit options ----------
D = {t: ST.prepare(A.load(t)) for t in A.TICKERS}
days = sorted(set(D["SPY"]) & set(D["QQQ"]) & set(D["IWM"]))
for t in A.TICKERS: D[t] = collections.OrderedDict((d, v) for d, v in D[t].items() if d in days)
byday, bytk = A.premium_model()
dev, hold = set(days[:70]), set(days[70:])


def hsim(side, v=BASE, intrabar=False):
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
                    if intrabar:      # stop fills at the stop line when the bar's high/low touches it (best case for a resting stop)
                        lvl = p["ent"] + p["stopR"] * p["R"] * p["sg"]
                        if (x["l"] <= lvl if p["sg"] > 0 else x["h"] >= lvl):
                            dS = p["sg"] * (lvl - p["ent"]); why = "STOP"
                            trades.append(dict(t=t, bot=b, day=day, R=dS / p["atr"], why=why, et=p["et"], hold=(end - p["et"]).total_seconds() / 60, atr=p["atr"], S=p["ent"], dS=dS))
                            del pos[b]; free[b] = end + A.timedelta(minutes=2); continue
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
                    vw = "CALL" if x["c"] > x["vwap"] else "PUT"
                    if side == "cross": d = sig
                    elif side == "vwap": d = vw
                    elif side.startswith("hold"):
                        n = int(side[4:]); d = vw if k >= n and all((xs[j]["c"] > xs[j]["vwap"]) == (vw == "CALL") for j in range(k - n, k + 1)) else sig
                    elif side.startswith("dist"):
                        d = vw if abs(x["c"] - x["vwap"]) / x["atr"] >= float(side[4:]) else sig
                    pos[b] = X.open_pos(d, x["c"], x["atr"], v, end, k)
    X.dollars(trades, byday, bytk)
    return trades


def show(name, tr):
    for split, ds in (("dev", dev), ("holdout", hold)):
        P(f"  {split:8s}" + X.fmt(X.row(name, [x for x in tr if x["day"] in ds], len(ds), ci=split == "holdout")))


P(f"\nHISTORY {days[0]}..{days[-1]} ({len(days)} days), dev {len(dev)} / holdout {len(hold)} ({min(hold)}..{max(hold)}). Live side rule = raw cross.")
H = {}
for side in ("cross", "vwap", "hold15", "hold30", "hold60", "dist1", "dist2"):
    H[side] = hsim(side); show(f"side={side}", H[side])

# ---------- Fix 2: 1R take-profit ----------
P("\n=== FIX 2: take profit at 1R (stop stays 1R) ===")
T1 = dict(stop=1, tgt=1)
t1 = {c["k"]: replay(c, c["dir"], T1)[0] for c in C}
gave = [c for c in C if c["why"] == "STOP" and c["mfe"] >= 1]
cut = [c for c in C if c["why"] == "TARGET"]
P(f"  today: stops that first reached +1R: {len(gave)} {[c['k'] for c in gave]} -> each banks +1R or better instead of the stop")
P(f"  today: targets that would be cut to 1R: {len(cut)}; their replay R live {sum(base[c['k']] for c in cut):+.1f} vs 1R rule {sum(t1[c['k']] for c in cut):+.1f}")
P(f"  today total: live {sum(base.values()):+.1f}R -> 1R target {sum(t1.values()):+.1f}R; winners {sum(r > 0 for r in base.values())} -> {sum(r > 0 for r in t1.values())}")
show("cross, 1R target", hsim("cross", T1))
show("hold30, 1R target", hsim("hold30", T1))

# ---------- Fix 3: exit at the stop line ----------
P("\n=== FIX 3: exits fill at the stop line ===")
stops = [c for c in C if c["why"] == "STOP"]
past = [c for c in stops if c["out_R"] < -1.0]
P(f"  today: {len(stops)} stops; {len(past)} filled beyond -1R; R lost beyond the line {sum(-1 - c['out_R'] for c in past):.2f}R; "
  f"beyond -1.25R: {sum(c['out_R'] < -1.25 for c in stops)}")
for lab, ks in (("feed gap 11:09-11:16", lambda c: 11 * 60 + 9 <= c["out_t"] <= 11 * 60 + 16), ("exit order failed first", lambda c: c["retries"] > 0)):
    xs = [c for c in past if ks(c)]
    P(f"    of which {lab}: {[c['k'] for c in xs]} = {sum(-1 - c['out_R'] for c in xs):.2f}R")
P(f"  distribution of stop fills (R): {sorted(round(c['out_R'], 2) for c in stops)}")
show("cross, bar-close stop (live)", H["cross"])
show("cross, stop at the line (touch)", hsim("cross", BASE, intrabar=True))

# ---------- Fix 4: stop wider than noise ----------
P("\n=== FIX 4: minimum stop width (ATR floor) ===")
for lo, hi in ((0, 3), (3, 5), (5, 99)):
    xs = [c for c in C if lo <= c["atr_bp"] < hi]
    if xs: P(f"  today ATR {lo}-{hi} bp: n={len(xs)} targets={sum(c['why'] == 'TARGET' for c in xs)} logged ${sum(c['pnl'] for c in xs):+.0f} "
             f"replay {sum(base[c['k']] for c in xs):+.1f}R, stops filled past -1.25R {sum(1 for c in xs if c['why'] == 'STOP' and c['out_R'] < -1.25)}")
for bp in (3, 4):
    v = dict(stop=1, tgt=2, floor_bp=bp)
    res = {c["k"]: replay(c, c["dir"], v)[0] for c in C}
    P(f"  today ATR floor {bp} bp: total {sum(res.values()):+.1f}R (live {sum(base.values()):+.1f}R)")
    show(f"cross, ATR floor {bp}bp", hsim("cross", v))

# ---------- Fix 5: bugs ----------
P("\n=== FIX 5: execution bugs, today's dollars ===")
c29 = next(c for c in C if c["bot"] == "QQQ-VWAP" and c["sig_t"] == 11 * 60 + 48)
P(f"  exit retry reverts a target: #{c29['k']} QQQ-VWAP CALL, target hit 11:58 at {base[c29['k']]:+.2f}R in replay; logged {c29['pnl']:+.0f}")
fake = [c for c in C if not (c["in_bid"] - .011 <= c["in_px"] <= c["in_ask"] + .011) or not (c["out_bid"] - .011 <= c["out_px"] <= c["out_ask"] + .011)]
P(f"  fills outside the quote: {[c['k'] for c in fake]} logged ${sum(c['pnl'] for c in fake):+.0f}, at quote mids "
  f"${sum(((c['out_bid'] + c['out_ask']) / 2 - (c['in_bid'] + c['in_ask']) / 2) * 1000 for c in fake):+.0f}")
gap = [c for c in C if c["in_t"] <= 11 * 60 + 9 and c["out_t"] >= 11 * 60 + 16]
P(f"  held through the 11:09-11:16 feed gap: {[(c['k'], c['bot'], round(c['out_R'], 2)) for c in gap]}")
P(f"  lost at restart: {[(c['bot'], c['dir'], X.hm(c['in_t'])) for c in orphans]} (broker showed -$5,900 unrealized at 17:16 MDT)")

# ---------- combined ----------
P("\n=== COMBINED: hold30 side + 1R target ===")
res = {c["k"]: replay(c, side_of("hold30", c, series[c["tk"]]), T1)[0] for c in C}
P(f"  today total {sum(res.values()):+.1f}R, winners {sum(r > 0 for r in res.values())} (live {sum(base.values()):+.1f}R, {sum(r > 0 for r in base.values())})")
open(OUT, "w").write("\n".join(lines) + "\n")

P("\n=== COMBINED: 1R target + stop at the line (history only; today's log has closes, no highs/lows) ===")
show("cross, 1R target, stop at line", hsim("cross", T1, intrabar=True))
open(OUT, "w").write("\n".join(lines) + "\n")
