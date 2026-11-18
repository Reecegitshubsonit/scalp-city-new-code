# Entry hunt: searching for a state that predicts direction

Run 2026-11-17. Script `backtest/entry_hunt.py`, raw output `results.json`.
SPY/QQQ/IWM 1-minute bars, 2025-11-17 to 2026-11-13, 250 trading days, entries to 10:59.

`entry_quality.py` showed Scalp City's three triggers carry no directional information. Those
are *events*. This tests *states*: given where the market is now, what is the expected signed
move over the next 5, 15 or 30 minutes? Every eligible bar is an observation (~250k) rather
than only the 11k bars a trigger fires on, which is a far more powerful test.

**Result: nothing durable was found.** Details below, including two methodology bugs caught
during the run that would have produced false positives.

## 1. Two bugs caught before the result was believed

**Look-ahead.** The first version computed `atr_rel` and `gap` against the *median ATR of the
whole day*, which is not known at the time of entry. That leak produced t-statistics of +39
and bucket means of 1.8 ATR. Fixed to use the **previous** day's median ATR, strictly prior
information. Any figure from the first run is void.

**No drift control.** Forward returns are signed long, so in a rising market every long-signed
bucket looks profitable. Fixed by subtracting the unconditional in-sample drift per ticker and
horizon, so all numbers below are excess over drift.

In-sample drift, for reference: QQQ +0.005 / +0.009 / +0.060 R at 5 / 15 / 30 minutes;
IWM +0.047 / +0.086 / +0.143.

## 2. What the split-sample test said

Nine features, three horizons, five quantile buckets: 135 cells. First 60% of days rank, last
40% judge. A survivor needs |t_in| > 3, the same sign out of sample, and |t_oos| > 2.

Eleven cells survived, and all eleven cleared the measured QQQ round-trip cost of 0.094 R. On
that evidence alone it looks like a result. It is not.

Almost every survivor is the same thing seen through correlated features — price below the
opening range, price far below the open, price down hard in the last 15 minutes — all
predicting further downside. 49% of the `mom15 < −1.96` bars are also below the opening range.
Four features, one phenomenon: **downside continuation**.

## 3. The month-by-month test kills it

Excess return at 30 minutes, by calendar month, for the three strongest candidates:

| Month | mom15 < −1.96 | range_pos < −0.13 | from_open < −3.84 |
|---|---:|---:|---:|
| 2025-11 | **−1.430** | +0.386 | +0.773 |
| 2025-12 | +0.059 | −0.923 | −0.801 |
| 2026-01 | −0.060 | −0.392 | −0.523 |
| 2026-02 | −1.106 | −1.164 | −1.210 |
| 2026-03 | **+0.728** | **+0.675** | **+1.045** |
| 2026-04 | −0.240 | +0.556 | +0.560 |
| 2026-05 | **+0.549** | +0.235 | +0.416 |
| 2026-06 | −0.244 | +0.010 | +0.041 |
| 2026-07 | −0.656 | −0.379 | −0.247 |
| 2026-08 | −0.054 | +0.129 | +0.138 |
| 2026-09 | −0.642 | −0.688 | −0.727 |
| 2026-10 | **+0.421** | **+0.455** | **+0.458** |
| 2026-11 | **−2.232** | **−1.775** | **−1.915** |
| **Months with the pooled sign** | **9/13** | **6/13** | **6/13** |

Two of the three hold their sign in six months out of thirteen — a coin flip. The pooled
out-of-sample numbers looked strong because the test window happened to contain more down
months, and because November 2026, a partial month, contributes −1.8 to −2.2 R and dominates
the average.

Within individual months the t-statistics are large in *both* directions (+10.3 in March,
−14.4 in November). The conditional mean is genuinely non-zero. Its **sign is regime-dependent**,
and nothing here identifies the regime in advance. "Price is falling, so it will keep falling"
works in falling months and reverses in rising ones, which is another way of saying it is not
a signal.

This is why the split-sample test alone is not enough. All eleven survivors passed it.

## 4. Per ticker, for completeness

| Candidate | Ticker | n | mean excess | Cost | Net |
|---|---|---:|---:|---:|---:|
| mom15 < −1.96 | SPY | 3726 | −0.314 | 0.079 | +0.235 |
| | QQQ | 3777 | −0.207 | 0.094 | +0.113 |
| | IWM | 4232 | −0.306 | 0.313 | **−0.007** |
| range_pos < −0.13 | QQQ | 3794 | −0.338 | 0.094 | +0.244 |
| | IWM | 4310 | −0.201 | 0.313 | **−0.112** |
| from_open < −3.84 | IWM | 4847 | −0.133 | 0.313 | **−0.180** |

Even taking the pooled numbers at face value, IWM is net negative on all three because its
cost is 0.313 R. That is the fourth independent test today pointing the same way about IWM.

## 5. Where this leaves things

- Scalp City's three triggers have no directional edge (`entry-quality-2026-11-17`).
- No exit shape can fix that; excursions are symmetric (same report, section 2).
- A 135-cell scan over nine market-state features found no state whose predictive sign is
  stable across months.
- Everything that looked like an edge was either a look-ahead leak, uncontrolled drift, or a
  regime effect that reverses.

What has **not** been tested, and is the honest next frontier: features this scan did not
include because they are not derivable from 1-minute OHLC bars. We hold per-minute option
greeks, bid/ask and volume in `data/webull/<day>/snapshots.jsonl` for 28 paper days — implied
volatility, delta skew and quoted spread dynamics are a genuinely different feature family
from price and ATR. 28 days is thin for a hunt, and the multiple-comparison risk demonstrated
above applies with full force, but it is new information rather than a rearrangement of the
same prices.

The alternative worth stating plainly: a 1-minute intraday directional edge on large-cap index
ETFs is among the most heavily competed signals in the market, and the result above is the
result most such searches produce. The null here is not a bug.

No engine change, no config change, no commit has been made.
