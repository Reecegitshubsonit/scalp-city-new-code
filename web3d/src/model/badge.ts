import type { BotRow, TradeRec } from './types'
import { formatPnl } from './format'

export type Tone = 'CALL' | 'PUT' | 'NEUTRAL' | 'WIN' | 'LOSS' | 'LOCKED' | 'PAUSED' | 'STALE'
export interface Badge { text: string; tone: Tone }

/** Short floating tag for a tower, from the bot's state and its last closed trade. */
export function badgeFor(row: BotRow, lastTrade: TradeRec | undefined): Badge | null {
  const tone: Tone = row.side ?? 'NEUTRAL'
  switch (row.state) {
    case 'paused': return { text: 'PAUSED', tone: 'PAUSED' }
    case 'stale': return { text: 'STALE DATA', tone: 'STALE' }
    case 'locked': return { text: row.reason_code === 'DAILY_LOSS' ? 'LOSS LIMIT' : 'DAILY GOAL', tone: 'LOCKED' }
    case 'forming':
      if (row.charge_pct == null) return { text: 'CHARGING', tone: 'NEUTRAL' }
      return { text: `${row.side ? row.side + ' ' : ''}${Math.round(row.charge_pct)}% CHARGED`, tone }
    case 'fired': return { text: row.side ? `FIRE ${row.side}` : 'FIRE', tone }
    case 'exiting': return { text: 'EXITING', tone }
    case 'managing': return { text: `${row.side ?? 'IN TRADE'} ${formatPnl(row.pnl_day)}`, tone }
    case 'cooldown':
      if (!lastTrade) return null
      if (lastTrade.pnl > 0) return { text: `PROFIT LOCKED ${formatPnl(lastTrade.pnl)}`, tone: 'WIN' }
      if (lastTrade.pnl < 0) return { text: `STOPPED OUT ${formatPnl(lastTrade.pnl)}`, tone: 'LOSS' }
      return { text: 'CLOSED FLAT', tone: 'NEUTRAL' }
    default: return null
  }
}
