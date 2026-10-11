import { describe, it, expect } from 'vitest'
import { mergeTrades, tradeStats, tradesToCsv, filterTrades, toTradeRecs, type Trade } from '../src/model/trades'
import type { TradeRec } from '../src/model/types'

const tr = (o: Partial<Trade> = {}): Trade => ({
  bot: 'QQQ-VWAP', ticker: 'QQQ', side: 'CALL', contract: 'QQQ261012C00750000', qty: 10,
  entry_time: '2026-10-09T09:43:00-04:00', entry_price: 1.2, exit_time: '2026-10-09T09:50:00-04:00', exit_price: 1.5,
  exit_code: 'EXIT_TARGET', pnl: 300, pnl_day: 300, source: 'broker', ...o,
})
const rec = (o: Partial<TradeRec> = {}): TradeRec => ({ time: '2026-10-09T10:20:00-04:00', bot: 'SPY-RANGE', ticker: 'SPY', pnl: -50, exit_code: 'EXIT_STOP', side: 'PUT', ...o })

describe('mergeTrades', () => {
  it('keeps fetched trades, adds live-only trades, dedupes by bot and exit time, sorts by exit time', () => {
    const fetched = [tr(), tr({ bot: 'IWM-VWAP', ticker: 'IWM', exit_time: '2026-10-09T10:05:00-04:00', pnl: 100 })]
    const live = [rec({ time: fetched[0].exit_time, bot: 'QQQ-VWAP', pnl: 300 }), rec()]
    const m = mergeTrades(fetched, live)
    expect(m.map(t => [t.bot, t.exit_time.slice(11, 16)])).toEqual([['QQQ-VWAP', '09:50'], ['IWM-VWAP', '10:05'], ['SPY-RANGE', '10:20']])
    expect(m[2].entry_time).toBeNull(); expect(m[2].side).toBe('PUT'); expect(m[2].pnl).toBe(-50)
  })
  it('works with only one side', () => {
    expect(mergeTrades([], [rec()])).toHaveLength(1)
    expect(mergeTrades([tr()], [])).toHaveLength(1)
    expect(mergeTrades([], [])).toEqual([])
  })
})

describe('tradeStats', () => {
  it('count, wins, win rate, total, best and worst', () => {
    const s = tradeStats([tr({ pnl: 300 }), tr({ pnl: -100 }), tr({ pnl: 50 }), tr({ pnl: 0 })])
    expect(s).toMatchObject({ count: 4, wins: 2, winRate: 50, pnl: 250 })
    expect(s.best?.pnl).toBe(300); expect(s.worst?.pnl).toBe(-100)
  })
  it('empty', () => { expect(tradeStats([])).toEqual({ count: 0, wins: 0, winRate: null, pnl: 0, best: null, worst: null }) })
})

describe('filterTrades', () => {
  const all = [tr(), tr({ bot: 'SPY-RANGE', ticker: 'SPY', pnl: -20 }), tr({ bot: 'SPY-VWAP', ticker: 'SPY', pnl: 40 })]
  it('by bot, ticker and result', () => {
    expect(filterTrades(all, { bot: 'SPY-RANGE' })).toHaveLength(1)
    expect(filterTrades(all, { ticker: 'SPY' })).toHaveLength(2)
    expect(filterTrades(all, { result: 'loss' }).map(t => t.pnl)).toEqual([-20])
    expect(filterTrades(all, { result: 'win' })).toHaveLength(2)
    expect(filterTrades(all, {})).toHaveLength(3)
  })
})

describe('tradesToCsv and toTradeRecs', () => {
  it('csv has a header and one quoted line per trade', () => {
    const csv = tradesToCsv([tr(), tr({ entry_time: null, exit_code: null })])
    const lines = csv.trim().split('\n')
    expect(lines[0]).toBe('exit_time,entry_time,bot,ticker,side,contract,qty,entry_price,exit_price,exit_reason,pnl,pnl_day')
    expect(lines[1]).toContain('QQQ-VWAP'); expect(lines[1]).toContain('Exit: target hit'); expect(lines[1]).toContain('300')
    expect(lines[2].split(',')[1]).toBe('')
    expect(lines).toHaveLength(3)
  })
  it('toTradeRecs maps to the shape the tape and badges use', () => {
    expect(toTradeRecs([tr()])[0]).toEqual({ time: '2026-10-09T09:50:00-04:00', bot: 'QQQ-VWAP', ticker: 'QQQ', pnl: 300, exit_code: 'EXIT_TARGET', side: 'CALL' })
  })
})
