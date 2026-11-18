# Disconnected replay: exit retries, portfolio coordination and entries

Session: October 9, 2026. Research only; no broker connection, production edits or deployment. The three specifically excluded restart entries remain excluded in every variant.

## What the replay established

The current exit-intent logic fixes the historical target-to-stop retry decision in the reproduced trace. A shared ticker-direction reservation prototype prevents opposite positions and pending entries under the tested conditions. Neither control change by itself establishes profitability. The signal-selection result depends strongly on whether direction follows the original cross or the current EMA9/EMA21 rule.

The cross-direction squeeze-plus-VWAP variant is a candidate for further evidence, not an approved strategy. Current EMA-direction variants were generally negative; the ATR-floor variant was only slightly positive before costs at zero delay. Do not assume changing direction fixes the problem, and do not equate improved control correctness with improved profitability.

## Three distinct evidence layers

1. **Actual Friday ledger:** 52 selected closed paper trades, reported -$2,270. The expanded audit already reconciled all 104 fills to their log records. This factual reference remains unchanged.
2. **Isolated exit replay:** seed each of the six retry trades from its actual entry; inject its recorded failure time; compare earlier re-evaluation logic against the current latched-exit logic on observed underlying closes. Later success is hypothetical, and no alternative option dollar P&L is assigned.
3. **Stateful signal replay:** regenerate entry opportunities from recorded indicator snapshots and run the production Bot decision/fill/cooldown transitions with research-only controls. Changing entries/exits changes subsequent bot availability. This is more than filtering the original 52 rows, but it is not an exact account replay.

The replay uses 1109 ticker-minute snapshots (IWM 370, QQQ 370, SPY 369), starting 09:40 and ending 15:59 Eastern. There are 64 recorded variants, including stress checks. All finish without simulated open positions; coordinated runs have zero observed opposing-position steps.

## What was and was not simulated

- Input closes, EMAs, VWAP and ATR are the rounded values actually logged. Missing minutes are not interpolated. EMA warmup is inherited from the recorded snapshots, not recomputed from missing prior OHLC.
- Opening-range limits use the existing reconstructed constants: IWM 277.71–278.86, QQQ 749.03–752.86, SPY 775.35–776.84. The missing original opening OHLC prevents independent reconstruction. All coordinated entry variants include a +/-$0.01 level sensitivity; this does not eliminate uncertainty in reconstruction.
- Use 1 ATR stop, 2 ATR target, 120-second cooldown, 15:30 last entry and 15:55 flatten attempt. Simulated fills occur on available observed underlying closes, never assumed exactly at the stop or target. Entry positions use the signal price and ATR.
- Six logged retry bot/minute/side combinations are scenario injections when a variant has a matching open position. Their occurrence in a different trade is an imposed stress condition, not a factual broker outcome. Remaining attempts are assumed to succeed at the observed underlying close.
- Entry rejections, no-outcome orders, exact option liquidity, monetary risk gates, daily dollar locks, account equity, commissions and broker reconciliation are not simulated in the signal study. Alternative option quotes are unavailable. The code uses a constant unit fill value solely to exercise Bot state transitions, ignores its dollar bookkeeping, and reports no synthetic option P&L.
- Consequently the raw-cross replay has 64 trades, versus the factual 52. Different exits, omitted monetary/admission restrictions, absent exact runtime settings and partial startup information prevent an exact Friday account reproduction. Treat -0.462 mean ATR as the modeled baseline, not a reproduction of -$2,270.
- A summed ATR result is the sum of directional underlying move divided by each entry ATR. It is not dollar profit, option-premium return or portfolio R. Position-minutes measure aggregate holding duration and can overlap across bots. Positive rate is underlying-positive outcomes, not paper option win rate.

## Exit retries: actual trace comparisons

| Trade | Earlier next attempt after failure | Current latched next attempt | Recorded outcome |
|---|---|---|---|
| #2 | 09:55 STOP | 09:55 STOP | 09:55, $-260 |
| #3 | 09:52 STOP | 09:52 STOP | 09:52, $-250 |
| #16 | 11:16 TARGET | 11:04 TARGET | 11:16, $+220 |
| #29 | 12:01 STOP | 11:59 TARGET | 12:01, $-310 |
| #42 | 13:33 STOP | 13:33 STOP | 13:33, $-20 |
| #46 | 13:48 STOP | 13:48 STOP | 13:48, $-140 |

For #29, the current code retries TARGET at 11:59 after the 11:58 failure; earlier logic waits until STOP at 12:01. For #16 it retries at 11:04 instead of waiting until 11:16. These verify persistent exit decisions, not guaranteed fills or saved dollars. A TARGET reason means why liquidation began, not that the eventual price still meets the target.

The earlier exit-safety README describes a “current bot drops target” defect that no longer reproduces in today’s Bot: the current code already contains the latch. This study explicitly reconstructs the earlier behavior in an isolated subclass, rather than changing production to reintroduce it.

## Portfolio coordination

The prototype atomically reserves ticker direction before entry and retains ownership for pending, partially filled, unknown and held exposure. Same-side entries are allowed. Opposite entries wait until both pending and held quantities are cleared. Exits remain available during an entry freeze. State restoration blocks new entries until quantities and pending reservations reconcile.

No-opposing policy is evaluated separately from profit. Unexpected broker fills after an authoritative terminal state are accounted and freeze new entries for reconciliation; they cannot be wished away. This is an isolated research component, not wired into the production risk gate or broker adapter.

Entry decisions use deterministic production bot order within each ticker. Reversing that priority is a stress test because a direction conflict can otherwise give one bot preferential access. Replay checks compare positions at each observed update; synthetic tests separately cover simultaneous/pending-order cases.

## Controls followed by entry changes

| Variant | Trades | Mean entry ATR | Sum entry ATR | Positive | Worst trade ATR | Position-minutes |
|---|---:|---:|---:|---:|---:|---:|
| cross_legacy | 64 | -0.462 | -29.54 | 28.1% | -3.154 | 669 |
| cross_latched | 65 | -0.471 | -30.63 | 29.2% | -3.154 | 664 |
| cross_coordinated_unchanged | 62 | -0.356 | -22.07 | 32.3% | -3.154 | 625 |
| cross_coordinated_squeeze | 51 | +0.226 | +11.50 | 45.1% | -2.582 | 573 |
| cross_coordinated_vwap | 60 | +0.105 | +6.29 | 40.0% | -2.582 | 546 |
| cross_coordinated_squeeze_vwap | 48 | +0.289 | +13.89 | 45.8% | -2.582 | 485 |
| cross_coordinated_atr3 | 31 | -0.250 | -7.75 | 35.5% | -3.154 | 337 |
| ema_legacy | 68 | -0.395 | -26.83 | 27.9% | -2.875 | 594 |
| ema_latched | 68 | -0.351 | -23.85 | 29.4% | -2.875 | 592 |
| ema_coordinated_unchanged | 62 | -0.316 | -19.59 | 30.6% | -2.875 | 550 |
| ema_coordinated_squeeze | 53 | -0.491 | -26.03 | 26.4% | -2.875 | 503 |
| ema_coordinated_vwap | 41 | -0.101 | -4.15 | 36.6% | -2.875 | 357 |
| ema_coordinated_squeeze_vwap | 33 | -0.491 | -16.19 | 27.3% | -2.875 | 295 |
| ema_coordinated_atr3 | 30 | +0.063 | +1.89 | 40.0% | -2.048 | 298 |

The squeeze rule applies the existing <0.15 ATR EMA-gap filter to every bot. The VWAP rule vetoes trades against persistent VWAP positioning only with at least 25 observations in the trailing inclusive 30-clock-minute window. This differs from the first table-only screen, which could use short early-session lookbacks. ATR3 rejects signals with ATR below 3 basis points of underlying price.

Both direction modes retain independent baselines. The cross-direction combined filter had 48 trades and 45.8% positive underlying outcomes, still below the aspirational 65% target. No variant was selected on a fresh holdout. Friday and prior historical studies have already been examined.

## Delay, ordering and range sensitivity

| Variant | Trades | Mean entry ATR | Sum entry ATR | Positive | Worst trade ATR | Position-minutes |
|---|---:|---:|---:|---:|---:|---:|
| cross_coordinated_squeeze_vwap | 48 | +0.289 | +13.89 | 45.8% | -2.582 | 485 |
| cross_coordinated_squeeze_vwap_delay1 | 46 | +0.155 | +7.15 | 41.3% | -2.971 | 523 |
| cross_coordinated_squeeze_vwap_delay2 | 49 | +0.152 | +7.44 | 40.8% | -2.771 | 533 |
| cross_coordinated_squeeze_vwap_reverse_priority | 48 | +0.289 | +13.89 | 45.8% | -2.582 | 485 |
| cross_coordinated_squeeze_vwap_range_shift-0.01 | 48 | +0.289 | +13.89 | 45.8% | -2.582 | 485 |
| cross_coordinated_squeeze_vwap_range_shift0.01 | 47 | +0.323 | +15.16 | 46.8% | -2.582 | 483 |
| ema_coordinated_atr3 | 30 | +0.063 | +1.89 | 40.0% | -2.048 | 298 |
| ema_coordinated_atr3_delay1 | 29 | +0.216 | +6.26 | 41.4% | -2.099 | 337 |
| ema_coordinated_atr3_delay2 | 29 | +0.211 | +6.10 | 44.8% | -2.696 | 351 |
| ema_coordinated_atr3_reverse_priority | 30 | +0.063 | +1.89 | 40.0% | -2.048 | 298 |
| ema_coordinated_atr3_range_shift-0.01 | 30 | +0.063 | +1.89 | 40.0% | -2.048 | 298 |
| ema_coordinated_atr3_range_shift0.01 | 29 | +0.109 | +3.15 | 41.4% | -2.048 | 296 |

Exit delays are clock-minute minimum waits followed by the next observed bar; no fills are invented inside data gaps. A better result at a slower delay is path-dependent, not evidence that slower execution is preferable.

An arbitrary 0.2 ATR burden per completed trade would reduce the cross combined-filter mean from +0.289 to +0.089 in the zero-delay case and from +0.152 to -0.048 with a two-minute delay. Its positive gross result is therefore not strong evidence after execution frictions. The current EMA/ATR3 zero-delay result becomes -0.137 under that same burden. These are sensitivity scales, not estimated option spreads or fees. All variants include both 0.1 and 0.2 burdens in summary.csv.

## Validation and reproducibility

- 14 new offline tests pass: atomic competing reservations, unknown order handling, partial and duplicate fills, excess exits, stale status updates, unexpected late fills, state restoration/reconciliation, same-side policy, exit retries, historical #29, causal-prefix replay, and no fills in unobserved gaps.
- 36 pre-existing isolated-candidate integration tests pass against the separately copied candidate engine and fake broker. They provide additional evidence for retry/partial-fill plumbing, not proof that this new portfolio prototype is deployed or integrated with that candidate.
- All production Python source hashes are unchanged, recorded in manifest.json. The run imports no broker client or credentials and performs no network requests.
- Full trade lists, veto counts, attempted exits and unclosed-position lists are retained in replay.json; summary.csv, trades.csv and by_bot.csv support independent review. Every evaluated variant is retained.

Run from repository root:

```bash
python3 research/scalp_city/replay/run.py
python3 research/scalp_city/replay/report.py
python3 -m pytest research/scalp_city/replay/test_replay.py -q
python3 -m pytest simulations/exit_safety/integration_tests -q
```

## Decision

Keep the current exit-intent fix, and carry the ticker-direction reservation design forward for separate integration review. Do not deploy this research prototype or promote an entry rule from Friday alone. Prioritize testing the cross/squeeze/VWAP hypothesis and the current EMA baseline on fresh chronological evidence with complete option quotes, realistic risk limits and costs. The current evidence supports improved control behavior and candidate hypotheses; it does not establish profitable option trading.
