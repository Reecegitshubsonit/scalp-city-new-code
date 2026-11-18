# Expanded Friday paper-trade investigation

Actual paper session: October 9, 2026. All 52 original closed trades retained; the three excluded restart positions remain out of scope. This report supersedes the original report’s missing-timeline limitations. Dollar results describe this selected sample, not complete account performance.

## Conclusions

There are both strategy-selection weaknesses and execution/control defects. Fixing opposing holdings is required by the intended behavior, but does not by itself establish profitability. Friday followed cross directions rather than the currently intended EMA9/EMA21 side rule. The existing six screens do not become convincing after replacing logged fill prices with order-quote benchmarks.

## Reconciliation and provenance

All 52 row numbers, bots, sides, signal times and logged P&L match; signal prices match within cent-display rounding against the supplied table. All 104 fill records match their raw log sequence IDs, contract, quantity, fill price and minute. Recomputed fill P&L and quote-mid P&L match every row. All 622 path rows match raw-log bar values and pass ordering and ATR-movement arithmetic checks. The 47 displayed stop/target pairs match reconstructed values within cent-display rounding; they are not literally equal at full precision.

CSV copies are frozen in data/expanded; the originals are unchanged. The raw log is used only for verification and ordered event evidence for these 52 trades. Raw-log mode labels are not used to reclassify the user-confirmed paper session as real-money trading.

## Paper fills versus execution benchmarks

| Population | Trades | Logged paper P&L | Midpoint benchmark | Buy-ask/sell-bid benchmark |
|---|---:|---:|---:|---:|
| All 52 | 52 | $-2,270 | $-3,130 | $-3,840 |
| Originally starred #2/#4/#5 | 3 | $+160 | $-875 | $-920 |
| Rebooked #7/#8 | 2 | $-590 | $-565 | $-590 |

Logged P&L is the application’s paper-trade ledger. Quote mids are a sensitivity benchmark, not corrected actual fills. Buy-ask/sell-bid uses the entry order quote and the final exit order quote, with the observed quantity, and is also hypothetical. These quotes are timestamped by bar minute; their true age and wall-clock fill timing are unknown. None of these figures includes unlogged fees, market impact or uncertain quote/fill latency. Mids may overstate achievable results; ask/bid is not a guaranteed worst case.

Rows #7/#8 carry broker_offmarket fill sources: application booking may differ from broker-account prices. This is still actual paper trading, but the log alone cannot establish reconciled broker-account P&L. Do not infer broker positions from an order whose outcome is missing.

## Actual contract and direction behavior

Every recorded option symbol expires October 12, 2026: these were Monday-expiring contracts traded Friday, not same-day-expiring contracts. That matters for option-price response; underlying ATR return is not option-premium return. Symbols alone do not establish that the chosen strike was the closest available ATM strike.

Prior/current logged indicator snapshots confirm cross-direction agreement for 42/42 VWAP/EMA50 entries. 27/52 entries oppose their signal-time EMA9/EMA21 direction. This supports a Friday raw-cross baseline. The exact startup configuration and claimed 15:16 code-change time are not authenticated by these CSVs; some settings evidence is hard-coded by the exporter.

## Opposing positions

Verified 10 opposing position pairs involving 16 distinct trades, grouped into 6 connected sets: [[1, 6], [9, 14], [16, 18], [23, 24, 28], [29, 30], [37, 39, 40, 42, 45]]. The supplied README’s ‘8 groups’ is inconsistent with the independently computed pair and component counts. Same-side overlap involves 18 trades across 11 pairs. Overlap is measured from fill bar-minute intervals; same-minute details require sequence ordering, and these are not wall-clock durations.

| Population | Trades | Logged paper P&L | Midpoint benchmark | Buy-ask/sell-bid benchmark |
|---|---:|---:|---:|---:|
| Trades involved in opposing overlap | 16 | $-210 | $-105 | $-310 |
| No-opposing historical-entry sensitivity: retained | 44 | $-2,280 | $-3,190 | $-3,800 |
| No-opposing historical-entry sensitivity: blocked | 8 | $+10 | $+60 | $-40 |

Sensitivity rule: process logged entry-fill sequence order; reject a later opposite-side entry while an earlier retained same-ticker position remains open; preserve retained original exits. Blocked IDs: [6, 14, 18, 24, 30, 39, 42, 45]. This respects the user’s intended direction constraint but is not a full replay. It omits missing/rejected candidate signals, pending-entry states, altered cooldowns and account risk locks. Its dollar difference is not proven avoidable loss. Same-side duplication remains allowed.

## Ordered exit evidence

10 of the 37 final STOP trades first reached +1 ATR on an observed close before the first observed -1 ATR close: [1, 19, 20, 26, 29, 35, 36, 37, 39, 49]. This resolves the ordering ambiguity in the initial table, but missing minutes and lack of option quotes at hypothetical exits still prevent a validated option-P&L result for a +1 ATR target.

All 37 final STOP trades exited with underlying movement below -1 signal ATR; summed excess beyond -1 across those trades is 18.439 ATR units. This sum is a trade-normalized diagnostic, not portfolio R, dollars, or pure execution slippage. Bar-close evaluation, gaps and retries can all contribute. The 1 ATR stop was a close-based trigger, not a guaranteed fill level.

Trade #29: first exit trigger TARGET at 11:58, an EXIT_RETRY, then a STOP outcome at 12:01 for -$310 logged. The expanded exit_trigger column means first trigger; the original result means final outcome. It is not a row mismatch. The raw event sequence is saved in exit_diagnostics.csv. This is direct evidence for preserving a pending exit decision through retries, subject to valid executable orders.

Six trades have an exit retry: [2, 3, 16, 29, 42, 46]. Trade #16 spans 13 bar minutes from target trigger to fill and finishes profitable. A retry does not automatically mean it caused a loss. Trades #18/#21 exit at -2.582/-3.154 underlying ATR after the 11:09–11:16 missing-event interval. The log establishes a gap, not its cause or what could have filled inside it.

## Original screens under quote benchmarks

| Population | Trades | Logged paper P&L | Midpoint benchmark | Buy-ask/sell-bid benchmark |
|---|---:|---:|---:|---:|
| E01 EMA9/21 direction agrees | 25 | $-1,390 | $-1,760 | $-2,090 |
| E02 Skip labeled squeezes | 32 | $+40 | $-910 | $-1,350 |
| E03 Skip trades against persistent VWAP side | 25 | $-1,120 | $-2,040 | $-2,380 |
| E04 EMA agreement and no squeeze | 16 | $-240 | $-695 | $-910 |
| E05 No squeeze and no persistent VWAP conflict | 20 | $-100 | $-1,040 | $-1,310 |
| E06 ATR at least 3 basis points | 28 | $-1,060 | $-1,970 | $-2,370 |

These are the same frozen six exploratory screens and retained IDs as the initial research, with no parameter tuning. Filtering actual rows is not a strategy rerun. Compare both average outcomes and exposure before declaring improvement; skipping losers discovered after the fact is not evidence of a tradable rule.

## Export corrections and unresolved fields

- Use 10 opposing pairs / 16 trades / 6 connected sets, with the unit stated explicitly.
- stop_und_logged and target_und_logged are cent-rounded displays; use rounding tolerance, not an exact-match claim.
- settings_used.csv contains hard-coded claims derived partly from code or inference, despite its log-only framing. Treat exact version/change time, threshold values and flat cutoff accordingly.
- The post-restart daily-loss evidence includes an unlocked -$780 and a locked -$960. Under a shared fixed loss threshold with inclusive locking, this implies a threshold greater than $780 and at most $960, not the exported $720 lower bound. Per-bot or changing limits would invalidate that shared-threshold inference.
- A +$490 unlocked observation implies a shared inclusive goal threshold greater than $490, not merely the exported $310. Before-restart observations do not establish the exported $130 lower bound.
- Fee values, actual submitted limit prices and execution wall-clock timestamps are missing. Order quotes do not prove limit prices; current code is not a versioned Friday order record.
- One entry order has no logged outcome. Treat it as unresolved; no broker-account quantity or fill can be established from that absence.

## Next reproducible experiments

1. Reproduce Friday with raw-cross direction and actual Monday expiry. Keep a separate EMA-direction variant; do not silently replace the historical baseline.
2. Test the no-opposing-entry invariant at shared ticker scope with atomic pending-order reservations and position reconciliation. Preserve exits and do not automatically flip existing positions.
3. Test persistent exit intent through retries and gap handling in disconnected event replay; distinguish exit-trigger price, order price and fill price.
4. Compare entry and exit variants on new chronological sessions with option quotes, fees and portfolio limits. All already-examined Friday outcomes and historical trials remain development evidence.

Run `python3 research/scalp_city/analyze.py` then `python3 research/scalp_city/analyze_expanded.py`. All source hashes and validation counts are in expanded_manifest.json. No broker calls or production mutations are performed.
