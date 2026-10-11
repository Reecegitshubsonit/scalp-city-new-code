"""How often trades reached +1R (bar close) and then reversed to the stop: today's 52 trades and 90 days of history, live rules (raw cross, 1R stop / 2R target).
Research only. Run from repo root: python3 reports/dissect-2026-10-09/hit_1R_reverse.py -> reports/dissect-2026-10-09/hit_1R_reverse.txt"""
import inspect, sys
sys.path.insert(0, "reports/analysis-2026-10-09"); sys.path.insert(0, "reports/dissect-2026-10-09"); sys.argv = ["x"]
import fix_evidence as F
out = []
def P(s): print(s); out.append(s)
C = F.C
r1 = [c for c in C if c["mfe"] >= 1]; rev = [c for c in r1 if c["why"] == "STOP"]; stops = [c for c in C if c["why"] == "STOP"]
P(f"today: reached +1R: {len(r1)} of {len(C)}; then reversed to stop: {len(rev)} ({100*len(rev)/len(r1):.0f}% of those reaching 1R, {100*len(rev)/len(stops):.0f}% of all {len(stops)} stops, {100*len(rev)/len(C):.0f}% of all trades)")
P(f"today: logged P&L of the reversals {sum(c['pnl'] for c in rev):+.0f}; exit fills {sum(c['out_R'] for c in rev):+.2f}R total")
for c in rev:
    S = F.series[c["tk"]]; t1 = next(t for t in range(c["sig_t"] + 1, c["out_t"] + 1) if t in S and c["sgn"] * (S[t]["p"] - c["sig_px"]) / c["atr"] >= 1)
    P(f"  #{c['k']:2d} {c['bot']:10s} {c['dir']:4s} in {F.X.hm(c['in_t'])} +1R at {F.X.hm(t1)} best {c['mfe']:+.2f} stopped {F.X.hm(c['out_t'])} ({c['out_t']-t1} min after +1R) fill {c['out_R']:+.2f}R {c['pnl']:+.0f}")
# history: same simulator, record the best close before exit
src = inspect.getsource(F.hsim).replace("trades.append(dict(t=t, bot=b, day=day, R=dS / p[\"atr\"], why=why,", "trades.append(dict(peak=p[\"peak\"], t=t, bot=b, day=day, R=dS / p[\"atr\"], why=why,")
ns = dict(F.__dict__); exec(src, ns); hsim = ns["hsim"]
tr = hsim("cross")
for split, ds in (("dev (first 70 days)", F.dev), ("holdout (last 20 days)", F.hold)):
    xs = [x for x in tr if x["day"] in ds]; a = [x for x in xs if x["peak"] >= 1]; b = [x for x in a if x["why"] == "STOP"]; s = [x for x in xs if x["why"] == "STOP"]
    P(f"history {split}: {len(xs)} trades; reached +1R {len(a)} ({100*len(a)/len(xs):.1f}%); reversed to stop {len(b)} = {100*len(b)/len(a):.1f}% of those, "
      f"{100*len(b)/len(s):.1f}% of stops, {100*len(b)/len(xs):.1f}% of trades; mean net$ of reversals {sum(x['net$'] for x in b)/len(b):+.1f}")
open("reports/dissect-2026-10-09/hit_1R_reverse.txt", "w").write("\n".join(out) + "\n")
