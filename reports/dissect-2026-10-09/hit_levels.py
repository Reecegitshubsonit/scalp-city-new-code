"""Ladder: how many trades reached +0.25R .. +2R (bar close) before exiting, and how many of those still ended at the stop.
Today's 52 trades and 90 days of history, live rules (raw cross, 1R stop / 2R target). Also a 0.5R-target replay.
Research only. Run from repo root: python3 reports/dissect-2026-10-09/hit_levels.py -> reports/dissect-2026-10-09/hit_levels.txt"""
import inspect, sys
sys.path.insert(0, "reports/analysis-2026-10-09"); sys.path.insert(0, "reports/dissect-2026-10-09"); sys.argv = ["x"]
import fix_evidence as F
out = []
def P(s): print(s); out.append(s)
LV = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0)
C = F.C
P("TODAY (52 closed trades)")
for lv in LV:
    a = [c for c in C if c["mfe"] >= lv]; b = [c for c in a if c["why"] == "STOP"]
    P(f"  reached +{lv}R: {len(a):2d} ({100*len(a)/len(C):3.0f}%)  then stopped: {len(b):2d} ({100*len(b)/max(1,len(a)):3.0f}% of those)  logged ${sum(c['pnl'] for c in b):+.0f}  {[c['k'] for c in b]}")
P(f"  never reached +0.5R: {sum(c['mfe'] < 0.5 for c in C)} {[c['k'] for c in C if c['mfe'] < 0.5]}")
src = inspect.getsource(F.hsim).replace("trades.append(dict(t=t, bot=b, day=day, R=dS / p[\"atr\"], why=why,", "trades.append(dict(peak=p[\"peak\"], t=t, bot=b, day=day, R=dS / p[\"atr\"], why=why,")
ns = dict(F.__dict__); exec(src, ns); hsim = ns["hsim"]
tr = hsim("cross")
for split, ds in (("FIRST 70 DAYS", F.dev), ("LAST 20 DAYS", F.hold)):
    xs = [x for x in tr if x["day"] in ds]; P(f"HISTORY {split} ({len(xs)} trades)")
    for lv in LV:
        a = [x for x in xs if x["peak"] >= lv]; b = [x for x in a if x["why"] == "STOP"]
        P(f"  reached +{lv}R: {len(a):5d} ({100*len(a)/len(xs):4.1f}%)  then stopped: {len(b):5d} ({100*len(b)/max(1,len(a)):4.1f}% of those)")
P("TARGET REPLAY (stop 1R)")
for tg in (0.5, 1.0, 2.0):
    v = dict(stop=1, tgt=tg); r = {c["k"]: F.replay(c, c["dir"], v)[0] for c in C}
    P(f"  today target {tg}R: total {sum(r.values()):+.1f}R, winners {sum(x > 0 for x in r.values())}")
    t2 = hsim("cross", v)
    for split, ds in (("first 70", F.dev), ("last 20", F.hold)):
        P("   " + split + " " + F.X.fmt(F.X.row(f"target {tg}R", [x for x in t2 if x["day"] in ds], len(ds))))
open("reports/dissect-2026-10-09/hit_levels.txt", "w").write("\n".join(out) + "\n")
