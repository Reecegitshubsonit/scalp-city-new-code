# Do Scalp City entries predict anything?

Run 2026-11-17. Script `backtest/entry_quality.py`, raw output `results.json`.
SPY/QQQ/IWM 1-minute bars, 2025-11-17 to 2026-11-13, 250 trading days, live 10:59 entry cutoff.

No exits are involved anywhere in this test. For every bar a bot would fire on, it measures
what the underlying actually did next, in ATR units at entry, signed so positive is in the
trade's favour. Each mean is reported against a drift benchmark — the same horizon measured
from every eligible bar, signed the same way — so a rising tape cannot pass as edge.

## 1. The live entry rules have no directional edge

11,243 signals, CALL share 50.7%, so the drift adjustment is negligible.

| Horizon | Mean forward return (ATR) | t | Drift-adjusted excess |
|---:|---:|---:|---:|
| 1 min | −0.0114 | −1.81 | −0.0114 |
| 2 min | −0.0165 | −1.87 | −0.0165 |
| 3 min | −0.0259 | **−2.44** | −0.0260 |
| 5 min | −0.0234 | −1.74 | −0.0234 |
| 10 min | −0.0063 | −0.34 | −0.0062 |
| 15 min | −0.0018 | −0.08 | −0.0017 |
| 30 min | −0.0069 | −0.22 | −0.0068 |

**Every horizon is negative.** The only result that approaches significance is at 3 minutes,
and it points the wrong way: after a signal fires, price drifts slightly *against* the trade
for the first few minutes, then the effect decays to nothing.

That is the signature of buying strength that immediately fades — entering on a breakout or a
cross and getting mild mean reversion in return.

## 2. The excursion distribution is symmetric, which caps every possible exit

Over the 30 minutes after entry:

| | Mean | Median |
|---|---:|---:|
| Maximum favourable excursion | +2.563 ATR | +2.097 ATR |
| Maximum adverse excursion | −2.580 ATR | −2.128 ATR |

Favourable and adverse excursions are the same size. A signal with edge would push MFE above
MAE; these are indistinguishable, and MAE is marginally the larger of the two.

**This is the whole explanation for the exit grid.** Every exit shape tested on 2026-11-17 —
stop/target, the live 1.5 ATR trail, 36 give-back variants — was drawing from a symmetric
distribution. No exit rule can manufacture positive expectancy from symmetric excursions, and
after the measured spread cost every configuration was negative. The exits were never the
problem.

## 3. No entry filter fixes it

Seven filter sets were tested on the same forward returns. The five largest absolute
t-statistics in the entire sweep, across all sets and horizons:

| Filter set | Horizon | Mean | t |
|---|---:|---:|---:|
| trend align (EMA9 vs EMA21) | 1 min | −0.0244 | −2.84 |
| chop filter on all bots | 3 min | −0.0330 | −2.79 |
| buffer 0.2 + trend + chop all | 3 min | −0.0489 | −2.45 |
| buffer 0.4 | 3 min | −0.0425 | −2.44 |
| none (live rules) | 3 min | −0.0259 | −2.44 |

Every one is negative. The filters that were supposed to improve entry quality make the
short-horizon drift slightly *more* adverse, because they select harder for the same
buy-strength pattern. Nothing in the sweep produces a positive excess return with a
t-statistic above 2.

## 4. Per bot and ticker, against each ticker's measured cost

15-minute forward return, live rules, against the round-trip spread cost measured in
`reports/premium-fit-2026-11-17/report.md`:

| Ticker | Bot | n | fwd 15m | t | Cost | Net | Median MFE | Median MAE |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| SPY | vwap | 1472 | +0.0246 | +0.40 | 0.079 | −0.054 | +2.059 | −2.040 |
| SPY | ema50 | 1494 | −0.0440 | −0.70 | 0.079 | −0.123 | +2.075 | −2.128 |
| SPY | range | 886 | −0.0155 | −0.20 | 0.079 | −0.095 | +1.982 | −2.191 |
| QQQ | vwap | 1430 | −0.0127 | −0.19 | 0.094 | −0.107 | +2.105 | −2.198 |
| QQQ | ema50 | 1500 | −0.0330 | −0.54 | 0.094 | −0.127 | +2.049 | −2.056 |
| QQQ | range | 827 | −0.0939 | −1.22 | 0.094 | −0.188 | +1.829 | −2.050 |
| IWM | vwap | 1357 | +0.0160 | +0.24 | 0.313 | −0.297 | +2.224 | −2.176 |
| IWM | ema50 | 1507 | +0.0444 | +0.66 | 0.313 | −0.269 | +2.257 | −2.032 |
| IWM | range | 770 | +0.1034 | +1.20 | 0.313 | −0.210 | +2.236 | −1.951 |

Nine bot-ticker combinations. Not one has a forward return distinguishable from zero, and
every one is net negative after cost. IWM has the least-bad raw numbers and the worst net,
which is the same conclusion the per-ticker exit grid reached.

## 5. What this means

The three triggers — VWAP cross, 5-minute EMA50 cross, opening-range break — carry no
measurable information about the next 1 to 30 minutes on SPY, QQQ or IWM over 250 days. The
engine is paying a real spread to take positions whose outcome distribution is symmetric.

That reframes everything tested today:

- Exit shape is not the bottleneck. Section 2 shows why no exit could have worked.
- Per-ticker cost matters for *how much* is lost, not whether.
- Dropping IWM is still correct, but it reduces the loss rate rather than creating an edge.

The open question is no longer which exit or which ticker. It is whether any entry rule
available to this engine predicts direction at all. Nothing tested here does.

## 6. Caveats

- Underlying only. A signal could in principle be profitable through option convexity while
  the underlying forward return is flat, but not at these symmetric excursions.
- 1-minute closes; intrabar paths beyond MFE/MAE are not modelled.
- Forward returns ignore the engine's own position management, caps and locks entirely, which
  is the point.
- 250 days, one regime. A signal that works only in a regime absent from this window would not
  show up.

No engine change, no config change, no commit has been made.
