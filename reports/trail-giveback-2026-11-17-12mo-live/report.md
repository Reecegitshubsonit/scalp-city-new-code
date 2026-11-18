# Exit-shape test over 12 months: should the new bot get a give-back trail?

Run 2026-11-17. Script `backtest/trail_grid.py`, data fetched by `backtest/fetch_stock_range.py`.
Raw output in this folder (`results.csv`, `results.json`) and in
`reports/trail-giveback-2026-11-17-12mo-1530/` for the robustness run.

Data: SPY, QQQ, IWM 1-minute bars, **2025-11-17 to 2026-11-13, 250 trading days, 13 calendar months**.
Entries are held fixed; only the exit varies. Measured on the underlying in ATR units at entry
(1 R = 1 ATR at entry). 76 configurations per run.

Primary run uses the **live entry cutoff of 10:59**. A second run at 15:30 (the legacy harness cutoff)
is the robustness check, and it matters — see "Fragility" below.

## Why this is an exit-only question

`diff scalp-city-ema5/scalpcity/config.py scalp-city/scalpcity/config.py` differs in exactly one thing:

- **new Scalp City** (`~/scalp-city-ema5`, port 8011, feeds `new-scalp-city-paper`): 1 ATR stop, 2 ATR target.
- **Scalp City V2** (`~/scalp-city`, port 8010, feeds `scalp-city-v2-paper`): 1 ATR stop, no target,
  trail 1.5 x current ATR behind the best close once 0.5 ATR in favour.

Same tickers, same three bots, same entry times, same stop, same caps. So the grid below maps directly
onto the live difference between the two engines.

## Results, live 10:59 cutoff, baseline entries

| Exit | Trades | Win% | avgR | t | Months > 0 | Last 6 mo avgR | Median hold |
|---|---:|---:|---:|---:|---:|---:|---:|
| `stop_target 1.0/2.0` — **what the new bot runs today** | 5859 | 33.2 | -0.003 | -0.14 | 8/13 | -0.003 | 4 min |
| `live_v2 trail 1.5 arm 0.5` — **what V2 runs today** | 6150 | 32.3 | +0.008 | +0.39 | 7/13 | +0.030 | 5 min |
| `giveback stop1 arm0.5 give0.5` | 6585 | 53.5 | +0.041 | +1.89 | 8/13 | +0.056 | 3 min |
| **`giveback stop1 arm0.5 give0.75`** | **6297** | **53.3** | **+0.106** | **+3.20** | **8/13** | **+0.094** | **4 min** |
| `giveback stop1 arm1 give0.75` | 5929 | 42.1 | +0.082 | +2.25 | 8/13 | +0.067 | 5 min |
| `giveback stop1 arm4 give0.75` | 5063 | 18.7 | +0.107 | +2.13 | 8/13 | +0.112 | 6 min |
| `giveback stop10 arm4 give0.5` — **Fischer's exact config** | 2368 | 61.9 | +0.128 | +0.98 | 9/13 | +0.276 | 232 min |

## The finding is not Fischer's configuration. It is "trail looser."

Across every stop width and every arm threshold, average R rises with `give` — the fraction of the run
handed back before exiting. At stop 1, arm 0.5: +0.010 (give 0.25), +0.041 (give 0.50), +0.106 (give 0.75).
At arm 1: -0.001, +0.026, +0.082. At arm 2: +0.007, +0.019, +0.087. At arm 4: +0.042, +0.080, +0.107.

Twelve of twelve stop/arm cells rank give 0.75 above give 0.25. A smooth monotone response across a
parameter is much harder to get from noise than an isolated spike, and this is the one pattern that
holds in every slice of the grid.

The mechanism is the same thing the 2026-11-13 dissection found by hand: both RANGE puts that day were
stopped out by under five cents and both would have run 5-10 points. Our exits leave winners on the
table. Fischer's give-back shape is one way to stop doing that; it is not the only way, and his
particular numbers are not what wins here.

**Fischer's exact config (stop 10, arm 4, give 0.5) is still not the answer.** avgR +0.128 looks like the
best cell in the table, and t = +0.98 says it is noise. It holds trades for 232 minutes against 4-5, and
this model charges nothing for that time. It also cuts the trade count from 6,150 to 2,368.

## Fragility: the headline number does not survive the entry window

Same config, same 12 months, entries allowed to 15:30 instead of 10:59:

| Exit | Trades | avgR | t | Last 6 mo |
|---|---:|---:|---:|---:|
| `live_v2 trail 1.5 arm 0.5` | 18635 | +0.007 | +0.53 | -0.011 |
| `giveback stop1 arm0.5 give0.75` | 17610 | +0.016 | +0.96 | -0.007 |

The 10:59 trades are a subset of the 15:30 trades, so this says the afternoon entries do badly under the
same exit and drag the average to nothing. Two readings, and the evidence here cannot separate them:

1. **Structural.** Morning moves trend and afternoon moves chop, so a loose trail pays before 11:00 and
   not after. This fits the engine's existing 11:00 cutoff, which was chosen for other reasons.
2. **Sample luck.** t = +3.20 is the best of 76 configurations; the 5% family-wise threshold for 76 tests
   is about t = 3.2. It clears that bar by nothing at all.

The monotone give-pattern survives both cutoffs. The specific magnitude of +0.106 does not.

## Your premise about the two engines does not hold up in the data I can see

The claim was that the new bot is doing worse and V2's trail is doing pretty good. What the records show:

- `scalp-city-ceo-feed-extract/manifest.json`, snapshot 2026-11-11: V2 640 trades, -$21,920
  (-$34.3/trade). New bot 93 trades, -$2,404 (-$25.8/trade). Per trade the new bot was **better**.
  That snapshot shows only EXIT_STOP and EXIT_TARGET for V2, so it predates the trail going in.
- `reports/dissect-2026-11-13`: V2 -1,850 on 3 trades, new bot -1,820 on 4 trades. A dead heat, same
  signals, differences down to sandbox fills and which loss cap tripped.
- This grid: V2's trail beats stop/target by 0.011 R per trade at t = +0.39. Real but small.

So "the new bot is worse" may be true from days I have not seen, but nothing in the logs, the feed
extract, the 11-13 dissection or this backtest establishes it. If the belief is resting on a handful of
recent sessions, that is a sample of a few dozen trades against a per-trade difference of about 0.01 R.

## Model limits

- Underlying only. No option pricing, no theta, no convexity, no spread beyond a flat 0.2 R constant.
  Every row is negative after that constant; only the ranking is meaningful.
- Hard stops fill exactly at the stop price intrabar, which flatters tight stops.
- Trail levels evaluated on bar closes, matching the live engine.
- No daily loss cap, no daily goal lock, no per-ticker loss room. The 11-13 dissection shows the shared
  SPY/IWM cap can dominate a day's result, and none of that is modelled here.
- 76 configurations per run. Treat any single t-statistic accordingly.

## What would settle it

`backtest/replay_harness.py` prices real option bars through the live engine and would charge hold time
properly. Running a give-back exit there needs the exit added to `scalpcity/engine.py`.

No engine change, no config change, no commit has been made.
