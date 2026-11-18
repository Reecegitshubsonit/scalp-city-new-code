"""Before vs after commit fd474e0 (trend_side + exit stickiness), 90-day engine replay outputs in old/ and new/.
Run from repo root: python3 reports/compare-before-after-fd474e0/compare.py -> compare.txt"""
import csv, collections, statistics as st, random
O = "reports/compare-before-after-fd474e0/"
out = []
def P(s): print(s); out.append(s)
T = {v: list(csv.DictReader(open(O + v + "/trades.csv"))) for v in ("old", "new")}
days = sorted({t["entry_time"][:10] for v in T.values() for t in v}); dev, hold = set(days[:70]), set(days[70:])
P(f"days {days[0]}..{days[-1]} ({len(days)}); first 70 = {days[0]}..{days[69]}, last 20 = {days[70]}..{days[-1]}")
def stat(xs, nd):
    if not xs: return "none"
    p = [float(t["pnl"]) for t in xs]
    byd = collections.defaultdict(float)
    for t in xs: byd[t["entry_time"][:10]] += float(t["pnl"])
    rng = random.Random(3); keys = list(byd); ms = []
    for _ in range(2000): ms.append(sum(byd[rng.choice(keys)] for _ in keys) / len(keys))
    ms.sort()
    return (f"n={len(p):4d} win={100*sum(x>0 for x in p)/len(p):4.1f}% net=${sum(p):+8.0f} per trade ${st.mean(p):+6.1f} per day ${sum(p)/nd:+6.0f} "
            f"(95% CI per day {ms[50]:+.0f} to {ms[1950]:+.0f})")
for lab, ds in (("ALL 90 DAYS", set(days)), ("FIRST 70 DAYS", dev), ("LAST 20 DAYS", hold)):
    P(f"\n{lab}")
    for v, name in (("old", "before (cross side)"), ("new", "after (EMA9/21 side)")):
        P(f"  {name:22s} " + stat([t for t in T[v] if t["entry_time"][:10] in ds], len(ds)))
P("\nBY TRIGGER, all 90 days")
for trig in ("VWAP", "EMA50", "RANGE"):
    for v, name in (("old", "before"), ("new", "after ")):
        P(f"  {trig:5s} {name} " + stat([t for t in T[v] if t["bot"].endswith(trig)], len(days)))
P("\nBY TICKER, all 90 days")
for tk in ("SPY", "QQQ", "IWM"):
    for v, name in (("old", "before"), ("new", "after ")):
        P(f"  {tk} {name} " + stat([t for t in T[v] if t["ticker"] == tk], len(days)))
# daily head-to-head
dd = {v: collections.defaultdict(float) for v in T}
for v in T:
    for t in T[v]: dd[v][t["entry_time"][:10]] += float(t["pnl"])
better = sum(1 for d in days if dd["new"][d] > dd["old"][d]); worse = sum(1 for d in days if dd["new"][d] < dd["old"][d])
P(f"\nDAY BY DAY: after beat before on {better} days, lost on {worse}, tied {len(days)-better-worse}")
# how often the side differs (same signal minute and bot)
ko = {(t["bot"], t["entry_time"]): t for t in T["old"]}; kn = {(t["bot"], t["entry_time"]): t for t in T["new"]}
both = set(ko) & set(kn)
flip = [k for k in both if ko[k]["contract"][len(ko[k]["ticker"]) + 6] != kn[k]["contract"][len(kn[k]["ticker"]) + 6]]
P(f"SAME ENTRY (bot + minute) in both runs: {len(both)}; side flipped by trend_side on {len(flip)} ({100*len(flip)/len(both):.0f}%)")
P(f"  on flipped entries: before ${sum(float(ko[k]['pnl']) for k in flip):+.0f}, after ${sum(float(kn[k]['pnl']) for k in flip):+.0f}")
P(f"  on unflipped entries: before ${sum(float(ko[k]['pnl']) for k in both if k not in flip):+.0f}, after ${sum(float(kn[k]['pnl']) for k in both if k not in flip):+.0f}")
open(O + "compare.txt", "w").write("\n".join(out) + "\n")
