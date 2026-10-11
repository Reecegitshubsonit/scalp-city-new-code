"""Setup check on the 49 clean trades of 2026-10-09 (all closed trades except #2, #4, #5 whose fills were off-market):
PUTs vs CALLs, what the market was doing when each signal fired, and whether the same pattern holds in 90 days of history.
Research only. Run from repo root: python3 reports/dissect-2026-10-09/setup_puts.py -> reports/dissect-2026-10-09/setup_puts.txt"""
import collections, statistics as st, sys
sys.path.insert(0, "reports/analysis-2026-10-09"); sys.path.insert(0, "reports/dissect-2026-10-09"); sys.argv = ["x"]
import fix_evidence as F, analyze as A
X = F.X
out = []
def P(s): print(s); out.append(s)
C = [c for c in F.C if c["k"] not in (2, 4, 5)]
S_ = F.series

def ctx(c):
    S = S_[c["tk"]]; t0 = c["sig_t"]; first = min(S)
    e50_20 = S.get(t0 - 20, {}).get("e50")
    c["slope50"] = (c["e50"] - e50_20) / c["atr"] if e50_20 else None          # EMA50 change over 20 min, ATR (+ = rising)
    c["day_move"] = (c["sig_px"] - S[first]["p"]) / c["atr"]                    # price vs 09:40, ATR
    c["above_vwap_30"] = sum(S[t]["p"] > S[t]["vwap"] for t in range(t0 - 30, t0 + 1) if t in S) / max(1, sum(1 for t in range(t0 - 30, t0 + 1) if t in S))
    # trend in the trade's terms: + means the bigger trend agrees with the trade's side
    s = c["sgn"]
    c["with_slope"] = None if c["slope50"] is None else (c["slope50"] * s > 0)
    c["with_vwap30"] = (c["above_vwap_30"] >= 0.8 and s > 0) or (c["above_vwap_30"] <= 0.2 and s < 0)
    c["against_vwap30"] = (c["above_vwap_30"] >= 0.8 and s < 0) or (c["above_vwap_30"] <= 0.2 and s > 0)
for c in C: ctx(c)

def line(lab, xs):
    if not xs: return P(f"  {lab:46s} none")
    P(f"  {lab:46s} n={len(xs):2d} targets={sum(c['why']=='TARGET' for c in xs):2d} ({100*sum(c['why']=='TARGET' for c in xs)/len(xs):3.0f}%) "
      f"logged ${sum(c['pnl'] for c in xs):+6.0f} replay {sum(F.base[c['k']] for c in xs):+6.1f}R  avg best {st.mean(c['mfe'] for c in xs):+.2f}R")

P("DAY: each ticker 09:40 -> 15:59 close, and share of minutes above VWAP")
for tk, S in S_.items():
    ts = sorted(S); P(f"  {tk}: {S[ts[0]]['p']:.2f} -> {S[ts[-1]]['p']:.2f} ({S[ts[-1]]['p']-S[ts[0]]['p']:+.2f}), above VWAP {100*sum(S[t]['p']>S[t]['vwap'] for t in ts)/len(ts):.0f}% of minutes")

P("\nTODAY, 49 clean trades")
line("all", C)
for d in ("PUT", "CALL"):
    xs = [c for c in C if c["dir"] == d]; line(d, xs)
    for tk in ("SPY", "QQQ", "IWM"): line(f"  {d} {tk}", [c for c in xs if c["tk"] == tk])
P("\nBY TRIGGER x SIDE")
for tr in ("VWAP", "EMA50", "RANGE"):
    for d in ("PUT", "CALL"): line(f"{tr} {d}", [c for c in C if c["trig"] == tr and c["dir"] == d])
P("\nBIGGER TREND AT THE SIGNAL (in the trade's terms)")
line("EMA50 rising for a CALL / falling for a PUT", [c for c in C if c["with_slope"] is True])
line("EMA50 against the side", [c for c in C if c["with_slope"] is False])
line("price held trade's side of VWAP 80%+ of last 30m", [c for c in C if c["with_vwap30"]])
line("price held OTHER side of VWAP 80%+ of last 30m", [c for c in C if c["against_vwap30"]])
line("VWAP mixed in last 30m", [c for c in C if not c["with_vwap30"] and not c["against_vwap30"]])
P("\nPUTS ONLY: the pullback question")
pu = [c for c in C if c["dir"] == "PUT"]
line("PUT while EMA50 rising (shorting an uptrend)", [c for c in pu if c["slope50"] is not None and c["slope50"] > 0])
line("PUT while EMA50 falling", [c for c in pu if c["slope50"] is not None and c["slope50"] <= 0])
line("PUT while price above VWAP 80%+ of last 30m", [c for c in pu if c["above_vwap_30"] >= 0.8])
line("PUT after a 1+ ATR drop in the prior 5 min", [c for c in pu if (c["pre5"] or 0) >= 1])
stopped = [c for c in pu if c["why"] == "STOP"]
P(f"  stopped PUTs: {len(stopped)}; after the exit, price kept rising (30-min worst <= -2R for the PUT): {sum((c['post_mae'] or 0) <= -2 for c in stopped)}")
P("  per stopped PUT: #  bot  signal  EMA50 slope20(ATR)  above-VWAP share 30m  prior-5m drop(ATR)  30m after exit worst(R)")
for c in stopped:
    P(f"    #{c['k']:2d} {c['bot']:10s} {X.hm(c['sig_t'])}  slope {c['slope50'] if c['slope50'] is None else round(c['slope50'],2)!s:>6}  aboveVWAP {c['above_vwap_30']:.0%}  drop {c['pre5']!s:>5}  after {c['post_mae']}")

# ---------------- history: same split, 90 days ----------------
import inspect
src = inspect.getsource(F.hsim)
src = src.replace("pos[b] = X.open_pos(d, x[\"c\"], x[\"atr\"], v, end, k)",
  "pos[b] = X.open_pos(d, x[\"c\"], x[\"atr\"], v, end, k); pos[b][\"slope\"] = (x[\"e50\"] - xs[k-20][\"e50\"]) / x[\"atr\"] if k >= 20 else None; "
  "pos[b][\"av30\"] = sum(xs[j][\"c\"] > xs[j][\"vwap\"] for j in range(max(0,k-30), k+1)) / (k - max(0,k-30) + 1)")
src = src.replace("trades.append(dict(t=t, bot=b, day=day, R=dS / p[\"atr\"], why=why,", "trades.append(dict(slope=p.get(\"slope\"), av30=p.get(\"av30\"), dir=p[\"dir\"], t=t, bot=b, day=day, R=dS / p[\"atr\"], why=why,")
ns = dict(F.__dict__); exec(src, ns)
H = ns["hsim"]("cross")
def hl(lab, xs):
    if not xs: return P(f"  {lab:46s} none")
    P(f"  {lab:46s} n={len(xs):5d} win={100*sum(x['R']>0 for x in xs)/len(xs):4.1f}% grossR={st.mean(x['R'] for x in xs):+.3f} net$={st.mean(x['net$'] for x in xs):+6.1f}")
for split, ds in (("FIRST 70 DAYS", F.dev), ("LAST 20 DAYS", F.hold)):
    xs = [x for x in H if x["day"] in ds]; P(f"\nHISTORY {split}, live rules")
    for d in ("PUT", "CALL"): hl(d, [x for x in xs if x["dir"] == d])
    sg = lambda x: 1 if x["dir"] == "CALL" else -1
    hl("EMA50 slope agrees with side", [x for x in xs if x["slope"] is not None and x["slope"] * sg(x) > 0])
    hl("EMA50 slope against side", [x for x in xs if x["slope"] is not None and x["slope"] * sg(x) <= 0])
    hl("held trade's side of VWAP 80%+ last 30m", [x for x in xs if (x["av30"] >= .8 and sg(x) > 0) or (x["av30"] <= .2 and sg(x) < 0)])
    hl("held OTHER side of VWAP 80%+ last 30m", [x for x in xs if (x["av30"] >= .8 and sg(x) < 0) or (x["av30"] <= .2 and sg(x) > 0)])
open("reports/dissect-2026-10-09/setup_puts.txt", "w").write("\n".join(out) + "\n")
