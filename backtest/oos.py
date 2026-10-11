"""Out-of-sample check of the entry-filter variants in backtest/filters.py. Research script, paper only, no network.
1) time split: pick the best variant on the first 60 days, report it on the last 30.
2) 3-block cross-validation: for each 30-day block, pick the best variant on the other two blocks, report it on the held-out block.
Metric: average R per trade (1R = 1 ATR stop) before costs; t = mean / standard error. Cost sensitivity in the last column."""
import sys, os, statistics as st, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import filters as F


def stats(tr):
    R = [x["R"] for x in tr]
    if len(R) < 2: return (len(R), 0.0, 0.0, 0.0)
    m = st.mean(R); se = st.stdev(R) / math.sqrt(len(R))
    return (len(R), m, m / se if se else 0.0, 100 * sum(1 for r in R if r > 0) / len(R))


def fmt(s): return f"{s[0]:5d} tr  avgR {s[1]:+.3f}  t {s[2]:+5.2f}  win {s[3]:4.1f}%"


def main():
    allrows = {}
    for t in F.TICKERS:
        bars = F.load(t)
        for i, (s, o, h, l, c, v) in enumerate(bars): F.bars_hl[(t, i)] = (h, l, c)
        allrows[t] = F.prepare(bars)
    days = sorted({r["t"].date() for r in allrows["SPY"]})
    trades = {name: [x for t in F.TICKERS for x in F.run(t, allrows[t], cfg)] for name, cfg in F.VARIANTS}
    blocks = [set(days[i * 30:(i + 1) * 30]) for i in range(3)]
    train60, test30 = set(days[:60]), set(days[60:])
    base = F.VARIANTS[0][0]
    print(f"{len(days)} days; blocks of 30; cost sensitivity {F.COST_R}R per trade\n")
    sel = lambda name, ds: [x for x in trades[name] if x["day"] in ds]
    # 1) time split
    ranked = sorted(F.VARIANTS, key=lambda v: -stats(sel(v[0], train60))[1])
    print("TIME SPLIT  (train = first 60 days, test = last 30)")
    for name, _ in ranked[:3] + [v for v in F.VARIANTS if v[0] == base]:
        print(f"  {name:34s} train {fmt(stats(sel(name, train60)))} | test {fmt(stats(sel(name, test30)))}")
    best = ranked[0][0]
    # 2) block cross-validation
    print("\n3-BLOCK CROSS-VALIDATION  (variant chosen on the other 2 blocks)")
    pooled_best, pooled_base = [], []
    for i, blk in enumerate(blocks):
        others = set().union(*[b for j, b in enumerate(blocks) if j != i])
        pick = max(F.VARIANTS, key=lambda v: stats(sel(v[0], others))[1])[0]
        tb, tbase = sel(pick, blk), sel(base, blk)
        pooled_best += tb; pooled_base += tbase
        print(f"  held-out block {i + 1} ({min(blk)}..{max(blk)}): picked '{pick}'\n      picked {fmt(stats(tb))}\n      base   {fmt(stats(tbase))}")
    sb, sbase = stats(pooled_best), stats(pooled_base)
    print(f"\n  POOLED out-of-sample  picked {fmt(sb)}  after {F.COST_R}R cost {sb[1]-F.COST_R:+.3f}\n  POOLED out-of-sample  base   {fmt(sbase)}  after {F.COST_R}R cost {sbase[1]-F.COST_R:+.3f}")


if __name__ == "__main__":
    main()
