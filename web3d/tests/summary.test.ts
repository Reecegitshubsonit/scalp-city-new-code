import { describe, it, expect } from 'vitest'
import { daySummary, DAY_GOAL } from '../src/model/summary'
import type { BotRow, TradeRec } from '../src/model/types'

const row = (bot: string, pnl_day: number, trades = 1): BotRow => ({
  bot, ticker: bot.split('-')[0], state: 'idle', reason_code: '', reason_text: '', charge_pct: null,
  inputs: {}, time: null, pnl_day, trades, paused: false, side: null, sideSource: 'none', exit_code: null,
})
const tr = (pnl: number): TradeRec => ({ time: 't', bot: 'QQQ-VWAP', ticker: 'QQQ', pnl, exit_code: null, side: null })

describe('daySummary', () => {
  it('totals, per ticker, top worker, goal', () => {
    const s = daySummary([row('QQQ-VWAP', 1000), row('QQQ-EMA50', 500), row('SPY-RANGE', -200), row('IWM-VWAP', 0)], [tr(10), tr(-5), tr(20)])
    expect(s.total).toBe(1300)
    expect(s.byTicker).toEqual({ QQQ: 1500, SPY: -200, IWM: 0 })
    expect(s.top).toEqual({ bot: 'QQQ-VWAP', pnl: 1000 })
    expect(s.trades).toBe(4)
    expect(s.wins).toBe(2); expect(s.closed).toBe(3); expect(s.winRate).toBeCloseTo(66.67, 1)
    expect(s.goal).toBe(DAY_GOAL); expect(DAY_GOAL).toBe(5000)
    expect(s.goalPct).toBeCloseTo(26, 5)
  })
  it('empty and losing days', () => {
    const s = daySummary([], [])
    expect(s.total).toBe(0); expect(s.top).toBeNull(); expect(s.winRate).toBeNull(); expect(s.goalPct).toBe(0)
    expect(daySummary([row('QQQ-VWAP', -300)], []).goalPct).toBe(0)
    expect(daySummary([row('QQQ-VWAP', 9000)], []).goalPct).toBe(100)
  })
})
