"""How often trades reached +1.5R (bar close) before exiting, today and in 90 days of history; plus a 1.5R-target replay.
Research only. Run from repo root: python3 reports/dissect-2026-10-09/hit_1_5R.py -> reports/dissect-2026-10-09/hit_1_5R.txt"""
import sys
sys.path.insert(0, "reports/analysis-2026-10-09"); sys.path.insert(0, "reports/dissect-2026-10-09"); sys.argv = ["x"]
import fix_evidence as F, dissect as X
out = []
def P(s): print(s); out.append(s)
C, base = F.C, F.base
for lvl in (1.0, 1.5, 2.0):
    hit = [c for c in C if c["mfe"] >= lvl]
    P(f"today: reached +{lvl}R before exit: {len(hit)} of {len(C)} ({100*len(hit)/len(C):.0f}%); of those, ended at stop: {sum(c['why']=='STOP' for c in hit)} {[c['k'] for c in hit if c['why']=='STOP']}")
P("today: trades reaching +1.5R: " + ", ".join(f"#{c['k']} {c['bot']} {c['dir']} best {c['mfe']:+.2f} -> {c['why']} {c['pnl']:+.0f}" for c in C if c["mfe"] >= 1.5))
T15 = dict(stop=1, tgt=1.5)
r15 = {c["k"]: F.replay(c, c["dir"], T15)[0] for c in C}
P(f"today replay: live 2R target {sum(base.values()):+.1f}R ({sum(r>0 for r in base.values())} winners); 1.5R target {sum(r15.values()):+.1f}R ({sum(r>0 for r in r15.values())} winners); "
  f"1R target {sum(F.replay(c, c['dir'], F.T1)[0] for c in C):+.1f}R")
# history: share of live-rule trades whose path reached 1.5R before exit
for name, v in (("2R target (live)", F.BASE), ("1.5R target", T15), ("1R target", F.T1)):
    tr = F.hsim("cross", v)
    if name.startswith("2R"):
        pass
    F.show(f"cross, {name}", tr)
    for split, ds in (("dev", F.dev), ("holdout", F.hold)):
        xs = [x for x in tr if x["day"] in ds]
        P(f"  {split}: exits at target {sum(x['why']=='TARGET' for x in xs)} of {len(xs)} ({100*sum(x['why']=='TARGET' for x in xs)/len(xs):.1f}%)")
P("\n".join(F.lines[-12:]))
open("reports/dissect-2026-10-09/hit_1_5R.txt", "w").write("\n".join(out) + "\n")
