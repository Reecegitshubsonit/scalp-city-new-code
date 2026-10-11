"""Stop/target size grid on the underlying, for the baseline entries and the best filter set. Research script, paper only.
Results are in ATR units per trade (1 ATR = the old R). Cost: ~0.24 ATR/trade measured from the option backtest (spread alone ~0.09).
Also reports in how many of 3 consecutive 30-day blocks the average is positive. Stops fill exactly at the stop price here,
so tight stops are flattered (real stops slip)."""
import sys, os, statistics as st, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import filters as F

COST = 0.24
FILT = dict(buffer=0.2, trend=True, chop_all=True)


def main():
    allrows = {}
    for t in F.TICKERS:
        bars = F.load(t)
        for i, (s, o, h, l, c, v) in enumerate(bars): F.bars_hl[(t, i)] = (h, l, c)
        allrows[t] = F.prepare(bars)
    days = sorted({r["t"].date() for r in allrows["SPY"]})
    blocks = [set(days[i * 30:(i + 1) * 30]) for i in range(3)]
    for label, base in (("BASELINE entries", {}), ("FILTERED entries (buffer 0.2 + trend + chop all)", FILT)):
        print(f"\n{label}\n stop  target |  trades  win%   avgATR  t     after-cost | blocks>0  | break-even win%")
        for sa in (0.5, 0.75, 1.0):
            for ta in (1.5, 2.0, 3.0, 4.0):
                tr = [x for t in F.TICKERS for x in F.run(t, allrows[t], dict(base, stop=sa, tgt=ta))]
                R = [x["R"] for x in tr]; m = st.mean(R); se = st.stdev(R) / math.sqrt(len(R))
                w = 100 * sum(1 for r in R if r > 0) / len(R)
                pos = sum(1 for b in blocks if st.mean([x["R"] for x in tr if x["day"] in b]) > 0)
                be = 100 * (sa + COST) / (sa + ta)   # win rate needed after cost for a stop/target-only trade
                print(f" {sa:4.2f}  {ta:4.1f}   | {len(R):6d}  {w:4.1f}  {m:+.3f}  {m/se:+5.2f}  {m-COST:+.3f}     |  {pos}/3      | {be:4.1f}")


if __name__ == "__main__":
    main()
