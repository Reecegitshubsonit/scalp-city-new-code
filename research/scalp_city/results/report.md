# Friday research baseline — October 9, 2026

**Scope:** 52 supplied closed trades only. The three restart positions are excluded by user instruction. This is not complete account P&L.

Reported P&L: **$-2,270**. 17/52 positive outcomes (**32.7%**); 15/52 target exits. Average reported P&L **$-43.65** per trade; profit factor **0.61**.

## What this session establishes

PUT trades account for $-2,920, versus $+650 for CALLs. The strongest observed interaction is squeezed PUT entries: 18 trades, $-2,770. This is a concentration of losses, not proof that squeeze or direction alone caused them. Both squeezed CALLs won, illustrating the danger of generalizing one aggregate filter.

QQQ-VWAP and SPY-EMA50 together contribute $-2,050 over 9 trades. Those are priorities for review, not sufficient evidence to disable the bots permanently.

Average positive outcome is $205.29; average negative outcome magnitude is $164.57. Their observed payoff ratio is 1.25:1. Holding these averages fixed would require a 44.5% positive-outcome rate to break even, versus the observed 32.7%. This is arithmetic on reported P&L, not a forecast or cost-adjusted required win rate.

The table contains 27 trades whose side opposes the reported fast-EMA direction. That differs from the intended trend_side=True rule, but filtering to aligned trades still loses $1,390. The data does not support the claim that alignment alone fixes the strategy; reversing historical trades is a different, untested experiment.

The only positive full-sample entry screen leaves $40 across 32 trades; excluding flagged fills turns it negative. None of the six screens demonstrates a robust profitable strategy. Most stop exits have little favorable movement or path overshoot; the exact contribution of stop timing versus execution needs ordered data.

## Definitions and evidence boundaries

Reported P&L is the supplied dollar column; fee inclusion, size and option entry premium are unknown. Profit factor = sum of positive P&L / absolute sum of negative P&L. Average loss is expressed as a positive magnitude. A winning dollar result and a target exit are different measures. No option-premium return, actual R-multiple, annualized result or account drawdown is inferred.

The existing table generator identifies distances and excursions as underlying-price movement in signal-time ATR units, signed in the trade direction. Best/worst summarize observed closes during the trade, not executable option prices or necessarily intrabar extrema. The post-exit column is measured relative to the original signal price, not the exit price. EMA50 slope is a 20-minute change divided by signal ATR. The above-VWAP lookback uses available observations in an inclusive 31-minute window; early-session percentages can represent much shorter history. Treat rounded zeros and 0.15 gap boundary values cautiously; use supplied squeeze labels.

One session supplies one market-day observation. Trades within a ticker/session are dependent. No confidence interval or significance claim based on 52 independent trades is justified here. Prior settings were already explored in backtests; existing history cannot automatically be called untouched holdout data.

## Fill-flag sensitivity

| Group | Trades | Positive P&L | Target exits | Reported P&L | Avg/trade | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| All supplied | 52 | 32.7% | 15 | $-2,270 | $-43.7 | 0.61 |
| Three flagged rows | 3 | 66.7% | 0 | $+160 | $53.3 | 1.62 |
| Exclude flagged rows | 49 | 30.6% | 15 | $-2,430 | $-49.6 | 0.56 |

Flagged rows remain in the primary sample. Their asterisks come from the supplied table; local generator metadata labels them off-market fills. They are not the three excluded restart positions. Exclusion is a sensitivity check, not a corrected execution result.

## Performance decomposition

### Nine bots

| Group | Trades | Positive P&L | Target exits | Reported P&L | Avg/trade | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| IWM-EMA50 | 13 | 30.8% | 4 | $-390 | $-30.0 | 0.52 |
| IWM-RANGE | 6 | 16.7% | 1 | $-510 | $-85.0 | 0.09 |
| IWM-VWAP | 3 | 66.7% | 2 | $+180 | $60.0 | 1.78 |
| QQQ-EMA50 | 16 | 37.5% | 5 | $-270 | $-16.9 | 0.85 |
| QQQ-RANGE | 2 | 50.0% | 0 | $-80 | $-40.0 | 0.70 |
| QQQ-VWAP | 4 | 0.0% | 0 | $-1,090 | $-272.5 | 0.00 |
| SPY-EMA50 | 5 | 0.0% | 0 | $-960 | $-192.0 | 0.00 |
| SPY-RANGE | 2 | 100.0% | 2 | $+490 | $245.0 | n/a |
| SPY-VWAP | 1 | 100.0% | 1 | $+360 | $360.0 | n/a |

### Side

| Group | Trades | Positive P&L | Target exits | Reported P&L | Avg/trade | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| CALL | 17 | 52.9% | 9 | $+650 | $38.2 | 1.55 |
| PUT | 35 | 22.9% | 6 | $-2,920 | $-83.4 | 0.36 |

### Trigger

| Group | Trades | Positive P&L | Target exits | Reported P&L | Avg/trade | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| EMA50 | 34 | 29.4% | 9 | $-1,620 | $-47.6 | 0.55 |
| RANGE | 10 | 40.0% | 3 | $-100 | $-10.0 | 0.88 |
| VWAP | 8 | 37.5% | 3 | $-550 | $-68.8 | 0.58 |

### Ticker

| Group | Trades | Positive P&L | Target exits | Reported P&L | Avg/trade | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| IWM | 22 | 31.8% | 7 | $-720 | $-32.7 | 0.55 |
| QQQ | 22 | 31.8% | 5 | $-1,440 | $-65.5 | 0.55 |
| SPY | 8 | 37.5% | 3 | $-110 | $-13.8 | 0.89 |

### Time of signal

| Group | Trades | Positive P&L | Target exits | Reported P&L | Avg/trade | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| 11:00–11:59 | 12 | 16.7% | 2 | $-1,620 | $-135.0 | 0.18 |
| 12:00 onward | 23 | 26.1% | 6 | $-910 | $-39.6 | 0.52 |
| Before 11:00 | 17 | 52.9% | 7 | $+260 | $15.3 | 1.14 |

### EMA9/21 alignment

| Group | Trades | Positive P&L | Target exits | Reported P&L | Avg/trade | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| Agrees | 25 | 24.0% | 5 | $-1,390 | $-55.6 | 0.48 |
| Opposes | 27 | 40.7% | 10 | $-880 | $-32.6 | 0.71 |

### Squeeze

| Group | Trades | Positive P&L | Target exits | Reported P&L | Avg/trade | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| Labeled squeeze | 20 | 15.0% | 3 | $-2,310 | $-115.5 | 0.18 |
| Not labeled squeeze | 32 | 43.8% | 12 | $+40 | $1.2 | 1.01 |

### Persistent VWAP conflict

| Group | Trades | Positive P&L | Target exits | Reported P&L | Avg/trade | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| Against persistent side | 27 | 25.9% | 7 | $-1,150 | $-42.6 | 0.58 |
| No persistent conflict | 25 | 40.0% | 8 | $-1,120 | $-44.8 | 0.63 |

### ATR

| Group | Trades | Positive P&L | Target exits | Reported P&L | Avg/trade | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| At least 3 bp | 28 | 39.3% | 9 | $-1,060 | $-37.9 | 0.71 |
| Below 3 bp | 24 | 25.0% | 6 | $-1,210 | $-50.4 | 0.41 |

### Side and squeeze

| Group | Trades | Positive P&L | Target exits | Reported P&L | Avg/trade | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| CALL / no squeeze | 15 | 46.7% | 7 | $+190 | $12.7 | 1.16 |
| CALL / squeeze | 2 | 100.0% | 2 | $+460 | $230.0 | n/a |
| PUT / no squeeze | 17 | 41.2% | 5 | $-150 | $-8.8 | 0.91 |
| PUT / squeeze | 18 | 5.6% | 1 | $-2,770 | $-153.9 | 0.02 |

### Opening range and side

| Group | Trades | Positive P&L | Target exits | Reported P&L | Avg/trade | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| CALL / above | 7 | 42.9% | 3 | $+230 | $32.9 | 1.74 |
| CALL / inside | 10 | 60.0% | 6 | $+420 | $42.0 | 1.48 |
| PUT / above | 8 | 12.5% | 1 | $-550 | $-68.8 | 0.10 |
| PUT / below | 5 | 40.0% | 0 | $-420 | $-84.0 | 0.50 |
| PUT / inside | 22 | 22.7% | 5 | $-1,950 | $-88.6 | 0.38 |

### Prior five-minute move

| Group | Trades | Positive P&L | Target exits | Reported P&L | Avg/trade | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| 0 to less than 1 ATR | 10 | 30.0% | 2 | $-410 | $-41.0 | 0.61 |
| Against trade direction | 6 | 33.3% | 2 | $-20 | $-3.3 | 0.97 |
| At least 1 ATR | 32 | 34.4% | 11 | $-1,290 | $-40.3 | 0.62 |
| Missing | 4 | 25.0% | 0 | $-550 | $-137.5 | 0.26 |

### EMA50 slope alignment

| Group | Trades | Positive P&L | Target exits | Reported P&L | Avg/trade | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| Agrees | 10 | 50.0% | 5 | $+360 | $36.0 | 1.46 |
| Missing | 12 | 25.0% | 1 | $-1,140 | $-95.0 | 0.36 |
| Opposes | 27 | 33.3% | 9 | $-1,140 | $-42.2 | 0.60 |
| Rounded flat | 3 | 0.0% | 0 | $-350 | $-116.7 | 0.00 |

## Exit-path diagnostics

Of 37 stop-labeled trades, 17 never reached +0.25 ATR in the summarized path, 10 reached at least +1 ATR, and 1 reached at least +2 ATR (rounded). These are overlapping diagnostic counts, not additive categories.

37 stop trades have a worst observed close below -1 ATR. This identifies path overshoot; it does not quantify option slippage or prove the fill occurred at the worst point. 3 stopped trades show a post-exit best of at least +2 ATR relative to entry.

Extrema lack event ordering. A +1 ATR favorable excursion does not prove a tighter target would have filled before the original stop. Neither a trailing-stop backtest nor a side-flipped return can be reconstructed from these summary fields. Do not use best/worst or post-exit movement as entry features.

## Duplicate signals and opposing positions

There are 48 unique ticker/time/side/price clusters. Same-signal groups: [[7, 8], [12, 13], [15, 16], [19, 20]]. Keeping the first listed row per cluster gives $-2,110; keeping the last gives $-1,950. Both are bookkeeping sensitivities with less exposure, not replay results or evidence of an optimal bot priority.

Opposing simultaneous holdings cannot be counted from entry times alone. The table has no exit timestamps or pending-order state. Alternating directions do not establish overlap. The user confirms opposing holdings are unintended: the proposed portfolio invariant is no new opposing exposure for a ticker while an existing position or pending entry remains, with exit/reduction orders still available. Test this offline using ordered order/fill events before operational adoption. Do not automatically close an existing position on a new opposite signal.

## Exploratory entry screens

These screens retain actual historical rows and their unchanged reported outcomes. They are not backtests: skipping trades changes cooldowns, capital, risk locks and available subsequent signals. Every evaluated screen is retained, including failures. Thresholds are exploratory and already exposed to this data.

| Group | Trades | Positive P&L | Target exits | Reported P&L | Avg/trade | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| E01 EMA9/21 direction agrees | 25 | 24.0% | 5 | $-1,390 | $-55.6 | 0.48 |
| E02 Skip labeled squeezes | 32 | 43.8% | 12 | $+40 | $1.2 | 1.01 |
| E03 Skip trades against persistent VWAP side | 25 | 40.0% | 8 | $-1,120 | $-44.8 | 0.63 |
| E04 EMA agreement and no squeeze | 16 | 31.2% | 4 | $-240 | $-15.0 | 0.84 |
| E05 No squeeze and no persistent VWAP conflict | 20 | 45.0% | 7 | $-100 | $-5.0 | 0.95 |
| E06 ATR at least 3 basis points | 28 | 39.3% | 9 | $-1,060 | $-37.9 | 0.71 |

### Same screens excluding flagged rows

| Group | Trades | Positive P&L | Target exits | Reported P&L | Avg/trade | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| E01 EMA9/21 direction agrees | 24 | 20.8% | 5 | $-1,620 | $-67.5 | 0.40 |
| E02 Skip labeled squeezes | 30 | 40.0% | 12 | $-380 | $-12.7 | 0.87 |
| E03 Skip trades against persistent VWAP side | 22 | 36.4% | 8 | $-1,280 | $-58.2 | 0.53 |
| E04 EMA agreement and no squeeze | 15 | 26.7% | 4 | $-470 | $-31.3 | 0.68 |
| E05 No squeeze and no persistent VWAP conflict | 18 | 38.9% | 7 | $-520 | $-28.9 | 0.72 |
| E06 ATR at least 3 basis points | 25 | 36.0% | 9 | $-1,220 | $-48.8 | 0.65 |

Per-screen retained/removed IDs and complementary P&L are in experiments.csv and metrics.json. Do not combine dollar improvements across screens; their excluded trades overlap.

## Research sequence

1. Freeze this table and the intended configuration. Audit the direction mismatch against the actual Friday run configuration before interpreting today's trend-side code as Friday's behavior.
2. Test a shared ticker-direction entry gate in disconnected replay; include pending orders, partial fills, concurrent signals and persistence. Measure same-direction duplication separately; the user has not prohibited it.
3. Compare the fixed entry screens on fresh chronological sessions. Replay the complete bot state, not just retained rows. Track performance by bot and market day at comparable risk and exposure.
4. Test exits only with ordered underlying paths and option quote/order data. Separate signal failure, late entry, stop overshoot and exit execution failure.
5. Evaluate realistic option costs and account risk constraints, including existing stricter bot limits. The supplied table cannot reconstruct realized-plus-unrealized equity, loss-streak timing, concurrent risk, or 50–100% premium returns.

## Reproduce and validate

`python3 research/scalp_city/analyze.py` (Python 3 standard library; offline). Outputs are deterministic apart from environment metadata in manifest.json. Parser enforces row identity, valid outcomes and excursion signs; every partition and screen reconciles to the supplied total. No production files or broker state are changed.

See README.md for the source contract and decisions, experiments.json for hypotheses and failure criteria, and results/manifest.json for hashes. This baseline supplies diagnosis and candidate experiments; profitable improvements remain unproven.
