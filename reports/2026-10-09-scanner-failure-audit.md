# Scanner failure audit - 2026-10-09

Source files:
- `logs/2026-10-09-live.jsonl` through 15:27 ET
- `reports/2026-10-09-trade-review.csv`
- `reports/analysis-2026-10-09/output.txt`

## Counts

The user-referenced 47 trades were the first 47 closed trades in the current log. The scanner kept trading after that snapshot and ended with 51 closed trades, 4 entry no-fills, and 35 squeeze skips.

| scope | closed trades | wins | net P&L |
|---|---:|---:|---:|
| first 47 closed | 47 | 15 / 47, 31.9% | -$2,230 |
| full current log | 51 | 16 / 51, 31.4% | -$2,490 |

## First 47 closed trades

By ticker:
- QQQ: 19 trades, -$1,370
- IWM: 20 trades, -$750
- SPY: 8 trades, -$110

By trigger:
- EMA50: 29 trades, -$1,580
- VWAP: 8 trades, -$550
- RANGE: 10 trades, -$100

By direction:
- PUT: 30 trades, -$2,880
- CALL: 17 trades, +$650

By exit:
- STOP: 34 trades, -$5,020
- TARGET: 13 trades, +$2,790

Main issue tags:
- NO_FOLLOW: 16 trades, -$2,040
- REENTRY: 9 trades, -$930
- EXIT_RETRY: 6 trades, -$760
- QUICK_STOP: 9 trades, -$680
- DUP: 8 trades, -$480

## Full current log

By ticker:
- QQQ: 21 trades, -$1,660
- IWM: 22 trades, -$720
- SPY: 8 trades, -$110

By trigger:
- EMA50: 33 trades, -$1,840
- VWAP: 8 trades, -$550
- RANGE: 10 trades, -$100

By direction:
- PUT: 34 trades, -$3,140
- CALL: 17 trades, +$650

By exit:
- STOP: 37 trades, -$5,340
- TARGET: 14 trades, +$2,850

Main issue tags:
- NO_FOLLOW: 17 trades, -$2,070
- REENTRY: 9 trades, -$930
- EXIT_RETRY: 6 trades, -$760
- QUICK_STOP: 10 trades, -$710
- DUP: 8 trades, -$480

## Where the scanner went wrong

1. It traded a negative-expectancy baseline.
   The 90-session replay of the live rules showed 5,352 trades with net -0.554 R/trade at the 2% spread assumption. The day was not an isolated accident; it matched a system that already tests negative after realistic option costs.

2. EMA50 generated too much low-quality traffic.
   EMA50 was 29 of the first 47 trades and lost -$1,580. In the full log it was 33 trades and lost -$1,840. That was the largest trigger-level loss center.

3. QQQ PUTs were the largest directional/ticker failure.
   QQQ lost -$1,370 in the first 47 and -$1,660 by the current log. PUT trades overall lost -$2,880 in the first 47 and -$3,140 in the full log, while CALL trades were positive.

4. Entries often had no follow-through.
   NO_FOLLOW trades lost -$2,040 in the first 47 and -$2,070 in the full log. These were signals where the underlying never moved even 0.25 ATR in favor after entry. That points to entries firing on level touches/crosses without enough momentum confirmation.

5. The bot kept re-entering after stops.
   REENTRY trades lost -$930. The sequence around 13:23-13:48 ET is especially bad: repeated IWM/QQQ EMA50 PUT attempts after fresh stops. This is a cooldown/state-management failure, not just bad market direction.

6. Duplicate bots double-counted the same idea.
   DUP trades lost -$480. Examples include QQQ EMA50 and QQQ RANGE firing together at 10:02, and IWM VWAP/EMA50 firing together around 10:32 and 10:52. The scanner treated correlated signals as independent opportunities.

7. Exit retry behavior is unsafe.
   EXIT_RETRY tagged trades lost -$760. Prior audit found at least one case where an exit decision was not preserved after a failed target/exit attempt, allowing the trade to continue and later stop. Exit intent should persist until broker-confirmed flat.

8. Option costs turn weak gross edge into a clear loser.
   Full-log recorded P&L was -$2,490, but quote-normalized scenarios were worse: mid-to-mid -$3,350 and ask-in/bid-out -$4,040. The scanner needs a stronger underlying edge than it currently has to overcome spreads/theta/fees.

## Filter replay on today's actual trades

These filters can only remove trades that happened; they cannot add trades that would have appeared if earlier positions had been filtered out.

| filter | kept | recorded P&L | ask-in/bid-out P&L |
|---|---:|---:|---:|
| live rules | 51 | -$2,490 | -$4,040 |
| chop filter all bots | 31 | -$180 | -$1,550 |
| dedupe | 35 | -$1,110 | -$2,000 |
| buffer + trend + chop | 13 | -$90 | -$740 |
| buffer + trend + chop + dedupe + stopcool | 11 | +$120 | -$510 |

The best-looking live-day filter still loses under realistic ask-in/bid-out pricing, so this is not ready to trade by simply adding filters.

## Recommendation

Do not keep paper-running the current rules as if they are close. First fix the plumbing:

1. Preserve exit decisions until broker-confirmed flat.
2. Add durable broker/order/position reconciliation before retry/restart.
3. Enforce real stop cooldowns after failed trades.
4. Dedupe same-ticker/same-direction entries across bots.
5. Add entry confirmation: trend alignment, chop filter for all bots, and minimum distance/momentum after crossing.
6. Re-run a forward-only options backtest with bid/ask, fees, latency, no-fill behavior, and the same engine used by paper trading.

The scanner went wrong mainly because it was allowed to trade many marginal level-cross signals in a negative-cost environment, then repeatedly re-entered and duplicated them after stops.
