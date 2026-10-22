/** Hand-written "biggest downfall" per logged day, from reports/ and the day's trades. New days have no note until one is written here. */
export interface DayNote { short: string; detail: string; source: string }

export const DAY_NOTES: Record<string, DayNote> = {
  '2026-10-07': {
    short: 'Simulated day: range stop in 2 min',
    detail: 'Replay day, not paper. Worst trade: QQQ-RANGE PUT on the 09:48 down-break, stopped at 09:50 for -$420. SPY-RANGE and QQQ-EMA50 were also stopped once each.',
    source: 'day trades',
  },
  '2026-10-09': {
    short: 'Failed exit went back to HOLDING',
    detail: 'A TARGET exit that got NO_FILL was dropped and the bot went back to HOLDING instead of retrying: QQQ-VWAP had a +$270 bid at the target and closed -$310. EMA50 bots took 34 trades for -$1,620, the 11:00 hour lost -$1,620, and a 7-minute data gap (11:09-11:16) hit SPY-EMA50. An engine restart also reset three bots\' day P&L, so their loss locks counted from zero.',
    source: 'reports/audit-2026-10-09/findings.md',
  },
  '2026-10-12': {
    short: 'IWM-RANGE re-entered 10 times',
    detail: 'Best day of the first week, but IWM-RANGE kept taking new breaks: 10 trades, 8 stops, -$560. Nothing stops a range bot after its first range trade. Across six days, range trades after the first one lost -$2,060.',
    source: 'reports/range-then-trend-2026-10-20/findings.md',
  },
  '2026-10-13': {
    short: 'Entries on the first 9:31 bar',
    detail: 'Six bots entered at 09:31-09:32 on the first bars of the day and netted -$590; the 09:00 hour lost -$1,360 on 12 trades. VWAP bots lost -$1,160 on 14 trades, and 3 exits needed retries.',
    source: 'reports/morning-losses-2026-10-13/output.txt',
  },
  '2026-10-14': {
    short: 'EMA50 traded the raw cross',
    detail: 'EMA50 bots lost -$1,650 on 17 trades. Trades that followed the raw EMA cross lost -$1,880, while trades the trend side flipped made +$2,680. The range bots (+$1,450) carried the day.',
    source: 'reports/five-day-review-2026-10-15/output.txt',
  },
  '2026-10-15': {
    short: 'One -$900 stop + VWAP chasing',
    detail: 'SPY-RANGE lost -$900 on one PUT (09:54-10:02), about 3x the day\'s average loss. 14 trades entered 2+ ATR from VWAP in the trade\'s direction and lost -$1,100. The 09:00 hour lost -$2,450.',
    source: 'reports/five-day-review-2026-10-15/output.txt',
  },
  '2026-10-16': {
    short: 'Range bots shorted down-breaks',
    detail: 'QQQ-RANGE took two PUTs on down-breaks (09:52 and 10:06) and lost -$1,480; range bots lost -$1,660 in total. Across all paper days, down-breaks lost -$3,840 (28% wins) while up-breaks made +$3,960. The 13:00 hour added -$1,610.',
    source: 'reports/range-cutoff-2026-10-20/findings.md',
  },
  '2026-10-19': {
    short: 'Engine did not run (DNS failure)',
    detail: 'The engine could not resolve api.sandbox.webull.com and did not trade. Only 6 minutes after 15:54 were logged.',
    source: 'logs/engine-2026-10-19.out',
  },
  '2026-10-20': {
    short: 'First-bar entry and late VWAP PUT',
    detail: 'Small losses on a strong up day: IWM-EMA50 entered on the 09:31 bar and lost -$280, and SPY-VWAP took a PUT at 09:50 against the trend for -$380. Range up-breaks made +$1,770.',
    source: 'day trades',
  },
  '2026-10-21': {
    short: 'Stacked PUTs stopped together',
    detail: 'SPY-VWAP, SPY-RANGE and IWM-VWAP all held PUTs and were all stopped at 10:31 on the same bounce, -$1,150 together. No rule limits several bots on the same side at once. QQQ-EMA50 lost -$590 on a PUT held 13 minutes.',
    source: 'day trades',
  },
}
