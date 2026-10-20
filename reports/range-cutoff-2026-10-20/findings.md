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
