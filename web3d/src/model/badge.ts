import type { BotRow, TradeRec } from './types'
import { formatPnl } from './format'

export type Tone = 'CALL' | 'PUT' | 'NEUTRAL' | 'WIN' | 'LOSS' | 'LOCKED' | 'GOAL' | 'LOSS_LIMIT' | 'PAUSED' | 'STALE'
export interface Badge { text: string; tone: Tone }

/** Short floating tag for a tower, from the bot's state and its last closed trade. */
export function badgeFor(row: BotRow, lastTrade: TradeRec | undefined): Badge | null {
  const tone: Tone = row.side ?? 'NEUTRAL'
  switch (row.state) {
    case 'paused': return { text: 'PAUSED', tone: 'PAUSED' }
    case 'stale': return { text: 'STALE DATA', tone: 'STALE' }
    case 'locked':
      if (row.reason_code === 'DAILY_LOSS') return { text: 'LOSS LIMIT', tone: 'LOSS_LIMIT' }
      if (row.reason_code === 'DAILY_GOAL') return { text: 'DAILY GOAL', tone: 'GOAL' }
      return { text: 'LOCKED', tone: 'LOCKED' }
    case 'forming':
      if (row.charge_pct == null) return { text: 'CHARGING', tone: 'NEUTRAL' }
      return { text: `${row.side ? row.side + ' ' : ''}${Math.round(row.charge_pct)}% CHARGED`, tone }
    case 'fired': return { text: row.side ? `FIRE ${row.side}` : 'FIRE', tone }
    case 'exiting': return { text: 'EXITING', tone }
    case 'managing': return { text: holdingText(row), tone }
    case 'cooldown':
      if (!lastTrade) return null
      if (lastTrade.pnl > 0) return { text: `PROFIT LOCKED ${formatPnl(lastTrade.pnl)}`, tone: 'WIN' }
      if (lastTrade.pnl < 0) return { text: `STOPPED OUT ${formatPnl(lastTrade.pnl)}`, tone: 'LOSS' }
      return { text: 'CLOSED FLAT', tone: 'NEUTRAL' }
    default: return null
  }
}

/** "PUT +$180.00" from the engine's open P&L; else "PUT +62% TO TARGET" / "PUT 40% TO STOP" from the underlying; else "PUT HOLDING". */
function holdingText(row: BotRow): string {
  const label = row.side ?? 'IN TRADE'
  const h = row.held
  if (h && h.open_pnl !== null) return `${label} ${formatPnl(h.open_pnl)}`
  const price = row.inputs.price
  if (!h || h.entry_und === null || typeof price !== 'number' || h.target === h.entry_und || h.stop === h.entry_und) return row.side ? `${label} HOLDING` : label
  const toTarget = (price - h.entry_und) / (h.target - h.entry_und)
  if (toTarget >= 0) return `${label} +${Math.round(toTarget * 100)}% TO TARGET`
  return `${label} ${Math.round(((price - h.entry_und) / (h.stop - h.entry_und)) * 100)}% TO STOP`
}
