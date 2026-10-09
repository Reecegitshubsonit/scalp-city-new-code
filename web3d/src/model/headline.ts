import type { BotRow } from './types'

const TRIGGER_TEXT: Record<string, string> = { VWAP: 'VWAP cross', EMA50: 'EMA50 cross', RANGE: 'Range break' }

/** Scanner headline, e.g. "VWAP cross ▼ PUT · 0.52 ATR away". */
export function headline(row: BotRow): string {
  const trigger = row.bot.split('-')[1] ?? row.bot
  let s = TRIGGER_TEXT[trigger] ?? trigger
  if (row.side) s += ` ${row.side === 'CALL' ? '▲' : '▼'} ${row.side}`
  const d = row.inputs.distance_atr
  if (typeof d === 'number') s += ` · ${d.toFixed(2)} ATR away`
  return s
}
