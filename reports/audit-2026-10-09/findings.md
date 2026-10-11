# Independent audit — October 9, 2026

Scope: local source code, 2,592 event records through 13:29 ET (11:29 MDT), original 40-trade review, cached historical data and rerun research scripts. No broker reconciliation, trading changes, or restart. Existing uncommitted code was preserved.

## Results

- Original review: 40 closed trades, -$1,560 recorded. Replacing only exits #2, #3, #4 with their recorded bids yields -$2,450. Repricing every entry at its recorded ask and every exit at its recorded bid yields -$3,000. These are scenarios using submission quotes, not executable-price guarantees or broker accounting.
- Latest local snapshot: 41 closed trades, -$1,720 recorded, -$3,190 all-quote scenario; two positions remain open in the log. The additional QQQ-EMA50 exit at 13:28 ET lost $160. This is a partial session, not end-of-day P&L.
- Stop-tagged trades in the original review averaged -1.539 ATR sampled adverse excursion. This is not an average of realized losing trades, nor true intrabar MAE.
- 90 historical sessions, June 1–October 7: underlying baseline 6,290 trades, -0.0356 ATR/trade gross. Filtered version (0.2 ATR buffer, EMA9/21 direction, chop filter on all bots) 2,742 trades, +0.0449 gross. At the script's assumed 0.2 ATR cost these become -0.236 and -0.155. Costs are sensitivity assumptions, not reconciled current option costs.
- Forward 60/30-day split: selected filtered version +0.030 ATR gross on 947 test trades, hence -0.170 after assumed 0.2 cost. Three-block validation uses later data to select variants for earlier blocks and is not a forward-only trading simulation. Trade-level t statistics ignore common-day and cross-bot dependence.
- All 24 stop/target grid combinations are negative under the grid's 0.24 ATR cost assumption. Best filtered gross result +0.054 at 1 ATR stop/3 ATR target; after assumed costs -0.186. The grid itself is tuning on the full sample.
- Controlled change to historical exit semantics only: baseline bar-close exits 5,357 trades, -0.0737 ATR gross; filtered bar-close exits 2,542 trades, +0.0410. This is a sensitivity experiment, not a complete production replay; latency, outages, option prices and daily limits remain absent.
- Existing morning option artifact: 1,473 trades, -$51,280 across 90 days. All three trigger families negative. Artifact was aggregated, not refetched/regenerated. Its simulator uses option trade-bar closes with fixed spread adjustments, potentially stale marks and different trading windows/daily lockouts; it is not a current executable options backtest.

## Confirmed implementation defects and priorities

1. Preserve an exit decision until broker-confirmed flat. bot.on_order_failed clears pending and subsequent bars re-test price conditions. QQQ-VWAP #29 triggered TARGET at 11:58, got NO_FILL, and changed back to HOLDING at 11:59. Recorded bid at the target attempt was $3.06 versus $2.79 entry: a hypothetical +$270, not +$170; later realized -$310. No guarantee the hypothetical bid was fillable.
2. Reconcile broker orders/positions before retry or restart. Timeout cancellation is not verified; partial fills are not accounted for; broker order IDs are not persisted in events. A late fill can diverge from local position state. Placement exceptions can invoke modeled fills despite uncertainty whether a broker accepted an order. These are code-path risks, not proven occurrences today.
3. Separate risk monitoring from blocking execution. Engine holds a shared lock while synchronous order handling polls; a nominal 15-second timeout can delay other bots and exceed 15 seconds with network latency. Monitor underlying prices for existing underlying-ATR rules, and use fresh option quotes for orders. Polling only option prices changes the exit rule unless a distinct premium-risk rule is specified.
4. Add outage/restart protection and wall-clock telemetry. Events use bar.end as the fill/order timestamp, so they cannot establish actual execution latency. Seven-minute tick gap 11:09–11:16 confirms missing observations, not the exact outage cause or counterfactual loss. Trade #8's 37-minute hold was not 37 minutes without observations: ticks are present during that interval.
5. Align backtest and paper engines/configuration before evaluating filters. High/low checks at completed-bar time cannot deliver historic touch prices; exact stops remain optimistic and same-bar stop/target ordering is ambiguous. Current defaults impose a $100 per-bot daily loss lock, but the day's repeated entries after deeper losses imply settings/version differences; effective historical configuration is not recorded in these events.

## Interpretation limits

NO_FOLLOW uses minute-close samples, not true maximum favorable excursion, and is known only after the trade. It is not an entry-time filter. Tags overlap; their P&Ls cannot be added as separate causes or promised recoverable savings. DUP labels both trades in each duplicate pair, so eliminating duplication cannot be credited with the entire tagged loss. Opposite options are not guaranteed to be delta-neutral; their net loss cannot be attributed solely to spread. Out-of-quote fills compared against submission-time quotes are suspicious, not conclusively invalid without broker fills and contemporaneous market quotes. Paper results are simulated, not actual lost money.

## Recommended next move

Prioritize durable exits, order reconciliation, independent risk monitoring and telemetry. Validate timeout/late-fill, partial-fill, target-reversal, restart, and simultaneous-bot scenarios before a controlled paper restart. Then rerun a shared-engine, forward-only options test with actual bid/ask, timestamps, fees and latency sensitivity. Keep candidate filters in research: existing evidence does not demonstrate positive net expectancy. Do not tighten stops or deploy filters based on this single session.

External reference: SEC Investor.gov, Types of Orders, explains limit non-execution and that stop prices do not guarantee execution prices: https://www.investor.gov/introduction-investing/investing-basics/how-stock-markets-work/types-orders
