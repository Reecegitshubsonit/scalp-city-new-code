import type { BotRow, TradeRec } from './types'

export const DAY_GOAL = 5000

export interface DaySummary {
  total: number; byTicker: Record<string, number>; top: { bot: string; pnl: number } | null
  trades: number; closed: number; wins: number; winRate: number | null; goal: number; goalPct: number
}

export function daySummary(rows: BotRow[], trades: TradeRec[]): DaySummary {
  const byTicker: Record<string, number> = { QQQ: 0, SPY: 0, IWM: 0 }
  let total = 0, count = 0
  let top: DaySummary['top'] = null
  for (const r of rows) {
    total += r.pnl_day
    count += r.trades
    byTicker[r.ticker] = (byTicker[r.ticker] ?? 0) + r.pnl_day
    if (r.pnl_day > 0 && (!top || r.pnl_day > top.pnl)) top = { bot: r.bot, pnl: r.pnl_day }
  }
  const wins = trades.filter(t => t.pnl > 0).length
  return {
    total, byTicker, top, trades: count, closed: trades.length, wins,
    winRate: trades.length ? (wins / trades.length) * 100 : null,
    goal: DAY_GOAL, goalPct: Math.min(100, Math.max(0, (total / DAY_GOAL) * 100)),
  }
}
