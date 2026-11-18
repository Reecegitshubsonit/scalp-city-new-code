# Exit-shape test: live V2 trail vs Fischer's give-back-half

Run 2026-11-17. Script: `backtest/trail_grid.py`. Raw output: `results.csv`, `results.json`.

Data: `backtest/data/{SPY,QQQ,IWM}_1m.json`, 90 trading days, 2026-06-01 to 2026-10-07.
Entries are held fixed; only the exit varies. Everything is measured on the underlying in ATR units at
entry (1 R = 1 ATR at entry). 76 configurations.

## What was compared

| Exit | Shape |
|---|---|
| `stop_target 1.0/2.0` | Scalp City V1: 1 ATR stop, 2 ATR target |
| `live_v2 stop1.0 arm0.5 trail1.5` | current live: 1 ATR stop, no target, trail 1.5 x current ATR behind best close once 0.5 ATR in favour |
| `giveback stopS armA giveG` | Fischer's shape: S ATR stop, no target, and once a close is A ATR in favour the exit level sits G of the way back from the best close toward entry |

Fischer's stated configuration is `stop10 arm4 give0.5` (`research/nick-fisher/rules.md`, S07).

## Headline: his exact shape is not an improvement, and what looks like one is noise

Baseline entries (the set that mirrors live rules):

| Exit | Trades | Win% | avgR | t | after 0.2 cost | 30-day blocks > 0 | Median hold |
|---|---:|---:|---:|---:|---:|---:|---:|
| `stop_target 1.0/2.0` (V1) | 6290 | 32.1 | -0.036 | -2.02 | -0.236 | 0/3 | 4 min |
| `live_v2` (current) | 6672 | 31.4 | -0.022 | -1.11 | -0.222 | 0/3 | 5 min |
| `giveback stop1 arm0.5 give0.5` | 7132 | 53.3 | +0.006 | +0.33 | -0.194 | 2/3 | 3 min |
| `giveback stop1 arm1 give0.5` | 6515 | 42.2 | +0.006 | +0.29 | -0.194 | 2/3 | 4 min |
| **`giveback stop10 arm4 give0.5` (Fischer exact)** | **1244** | **61.4** | **+0.017** | **+0.10** | **-0.183** | **2/3** | **159 min** |

Fischer's exact shape posts the best raw avgR of the three, and it means nothing: t = +0.10. The sample
is 1,244 trades instead of 6,672 because a 10 ATR stop keeps positions open for hours, so the bot is in a
trade instead of taking the next signal. Median hold goes from 5 minutes to 159 minutes.

Two reasons not to read that as a win:

1. **It is trade reduction.** 81% of the trades disappear, and this project's standing rule is that fewer
   trades is a workaround, not a fix. The remaining trades are not better, they are just longer.
2. **The model does not charge for the hold.** This is an underlying-price simulation. There is no theta,
   no convexity and no spread beyond a flat 0.2 R sensitivity. Carrying a 1-3 DTE option for 159 minutes
   instead of 5 is a real bill that does not appear anywhere in these numbers. The true ranking of
   `stop10 arm4` is therefore worse than printed, by an unknown amount.

## The wide stop manufactures the win rate

This is the cleanest result in the grid. Hold arm and give fixed at 0.5 and widen only the stop:

| Stop | Trades | Win% | avgR | t |
|---:|---:|---:|---:|---:|
| 1 ATR | 7132 | 53.3 | +0.006 | +0.33 |
| 2 ATR | 5926 | 68.4 | -0.026 | -1.12 |
| 10 ATR | 3477 | 88.5 | -0.057 | -1.08 |

Win rate climbs from 53% to 88% while expectancy falls. An 88% win rate here buys nothing. This is direct
evidence for the reading of Fischer's reported 79% in `research/nick-fisher/rules.md` section 3.3: at his
stop width a high win rate is an artefact of the exit geometry, not a measure of edge.

## The one candidate worth keeping

`giveback stop1 arm0.5 give0.5` is the only variant that beats `live_v2` without cutting trade count or
extending holds: 7,132 trades against 6,672, median hold 3 minutes against 5, avgR +0.006 against -0.022,
and 2 of 3 thirty-day blocks positive against 0 of 3. The whole improvement is 0.028 R per trade at
t = +0.33, which is not significant. It is a candidate, not a result.

Mechanically it is a reasonable idea: it keeps our 1 ATR stop, arms at the same 0.5 ATR we already use,
and replaces the fixed 1.5 ATR trail distance with one proportional to how far the trade has run. Small
runs get a tight exit, large runs get room.

## Secondary entry set

The grid also ran against the research filter set (`buffer 0.2 + trend + chop_all`), which is NOT the live
entry rule. There, `giveback stop1 arm0.5 give0.25` reaches avgR +0.057 at t = +2.63 and 3 of 3 blocks
positive, and `giveback stop1 arm1 give0.25` reaches +0.060 at t = +2.33.

Do not act on those two numbers. 76 configurations were tested, so roughly four t-statistics above 2 are
expected from chance alone, and these are two of exactly four. They are worth a pre-registered re-test on
out-of-sample days, nothing more.

## Model limits

- Underlying only. No option pricing, no theta, no convexity, no spread beyond the flat 0.2 R constant.
- The hard stop is checked intrabar on the bar high/low and fills exactly at the stop price, which
  flatters tight stops. Real stops slip, so the 1 ATR rows are optimistic relative to the 10 ATR rows.
- Trail levels are evaluated on bar closes, matching the live engine.
- 90 days, one regime. The three 30-day block counts are the only stability check here.
- No daily loss cap, no daily goal lock, no per-ticker loss room, no profit brake.

## What would settle it

`backtest/replay_harness.py` prices real option bars through the live engine and would charge the hold
time properly. Running the give-back shape there requires adding the exit to `scalpcity/engine.py`, which
is a live-code change and has not been made.

No engine change, no config change, no commit has been made on the basis of this run.
