# Range bots: when to stop new entries (run 2026-10-20, morning)

Source: `logs/*-live.jsonl` (Webull paper days 2026-10-09 to 2026-10-20). 10-20 was still in progress
when this ran, so its numbers cover the morning only. Range bots: IWM-RANGE, QQQ-RANGE, SPY-RANGE.
Script: `analyze.py`. Tables: `buckets.csv`, `cutoffs.csv`, `cutoffs_by_day.csv`, `trades.csv`.

- 56 range trades, total P&L +120. 10-20's morning makes up +1770 of that, so the 7 finished days
  total -1650.
- Entries start in the 07:45 MDT bucket. That bucket is +870 over 17 trades, but it swings by day:
  +1990 (10-14) and +1770 (10-20) against -1670 (10-15) and -1180 (10-16). It has 3 positive days
  and 4 negative ones. Without 10-20 it is -900.
- 08:00-08:29 MDT is the most consistently bad window: 12 trades, -1880, losses on 4 days and
  a gain on 1 (all within the 7 finished days).
- After 10:45 MDT: 10 trades, -560, 2 wins.
- Best single cutoff with 10-20 included: 08:00 MDT (keeps +870 over 17 trades). The 2-hour idea
  (09:30) keeps -150, which is worse than no cutoff.
- With 10-20 excluded, every cutoff still loses money (08:00 keeps -900; no cutoff gives -1650).
  The time of day does not turn the range bots profitable on the finished days.

## Entry conditions (criteria.py, criteria.txt, crosstab.txt, range_trades_features.csv)

- Break direction is the largest split. Breaks below the 9:30-9:44 ET range: 40 trades, -3840,
  28% wins, 5 losing days of 6. Breaks above: 16 trades, +3960, 56% wins, 4 winning days of 5.
- The time effect is mostly break direction. Up breaks in the first 30 minutes: 6 trades, +3320,
  5 wins. Down breaks in the first 30 minutes: 11 trades, -2450, 3 wins. Down breaks in minutes
  30-60: 11 trades, -1750, 2 wins.
- 30-60 minutes after the open: 12 trades, -1880, 0 winning days, 4 losing days.
- The 2nd trade of the day per bot: 13 trades, -1030, 23% wins.
- Wide opening range (>= 8.02 x 1-minute ATR): 19 trades, -830, 21% wins.
- By bot: IWM-RANGE -1400 (25 trades, 24% wins), QQQ-RANGE +650, SPY-RANGE +870.
- Hindsight check: trades where price at 15:55 ET was further in the traded direction made +3590;
  the rest lost -3470. The losses are trades taken against the way the day went.
- Caveat: the up/down split may be the market's direction over these two weeks, not a property of
  the bot. 6 first-30-minute up breaks is a small sample.
