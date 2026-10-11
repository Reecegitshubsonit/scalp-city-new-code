import { formatPnl } from './format'
import type { DaySummary } from './summary'

export interface HudCard { id: 'pnl' | 'win' | 'trades' | 'best'; label: string; value: string; sub: string; tone: 'pos' | 'neg' | 'flat' }

/** The four small cards at the top-left of the city view. */
export function hudCards(s: DaySummary): HudCard[] {
  return [
    { id: 'pnl', label: 'DAY P&L', value: formatPnl(s.total), sub: `${s.goalPct.toFixed(0)}% of $${s.goal.toLocaleString('en-US')} goal`, tone: s.total > 0 ? 'pos' : s.total < 0 ? 'neg' : 'flat' },
    { id: 'win', label: 'WIN RATE', value: s.winRate == null ? '-' : `${Math.round(s.winRate)}%`, sub: s.closed ? `${s.wins} of ${s.closed} closed` : 'no closed trades', tone: 'flat' },
    { id: 'trades', label: 'TRADES', value: String(s.trades), sub: 'today, all bots', tone: 'flat' },
    { id: 'best', label: 'BEST BOT', value: s.top?.bot ?? '-', sub: s.top ? formatPnl(s.top.pnl) : 'no winner yet', tone: s.top ? 'pos' : 'flat' },
  ]
}
