import { describe, it, expect } from 'vitest'
import { mergeSeries, chartHeader, markLabel, type History } from '../src/model/history'
import type { Mark, TickPoint } from '../src/model/types'

const T = (m: number) => `2026-10-09T09:${String(m).padStart(2, '0')}:00-04:00`
const hist = (): History => ({
  ticker: 'QQQ',
  bars: [
    { time: T(30), open: 100, high: 101, low: 99, close: 100.5 },
    { time: T(31), open: 100.5, high: 102, low: 100, close: 101.5 },
  ],
  levels: [{ time: T(30), vwap: 100, ema9: 100.1, ema21: 100.2, ema50: 100.3 }, { time: T(31), vwap: 100.2, ema9: 100.4, ema21: 100.3, ema50: 100.3 }],
  marks: [{ time: T(31), bot: 'QQQ-VWAP', type: 'entry', side: 'CALL', pnl: null }],
})
const tick = (m: number, price: number, extra: Partial<TickPoint> = {}): TickPoint => ({ time: T(m), price, ...extra })

describe('mergeSeries', () => {
  it('uses history as is when there are no newer ticks', () => {
    const s = mergeSeries('QQQ', hist(), [tick(30, 100.5), tick(31, 101.5)], [])
    expect(s.candles).toHaveLength(2); expect(s.levels).toHaveLength(2); expect(s.marks).toHaveLength(1)
  })
  it('appends candles for ticks newer than the last bar, open = previous close', () => {
    const s = mergeSeries('QQQ', hist(), [tick(31, 101.5), tick(32, 103, { vwap: 101, ema50: 100.4 }), tick(33, 102.5)], [])
    expect(s.candles.map(c => c.time)).toEqual([T(30), T(31), T(32), T(33)])
    expect(s.candles[2]).toEqual({ time: T(32), open: 101.5, high: 103, low: 101.5, close: 103 })
    expect(s.candles[3]).toEqual({ time: T(33), open: 103, high: 103, low: 102.5, close: 102.5 })
    expect(s.levels[2]).toMatchObject({ time: T(32), vwap: 101, ema50: 100.4 })
    expect(s.levels).toHaveLength(3)   // tick without levels adds none
  })
  it('without history, builds candles from ticks alone', () => {
    const s = mergeSeries('QQQ', null, [tick(30, 100), tick(31, 101)], [])
    expect(s.candles).toEqual([{ time: T(30), open: 100, high: 100, low: 100, close: 100 }, { time: T(31), open: 100, high: 101, low: 100, close: 101 }])
  })
  it('merges live marks without duplicating history marks', () => {
    const live: Mark[] = [
      { time: T(31), price: 101.5, type: 'entry', bot: 'QQQ-VWAP', side: 'CALL' },
      { time: T(33), price: 102, type: 'exit', bot: 'QQQ-VWAP', side: 'CALL', pnl: 40 },
    ]
    const s = mergeSeries('QQQ', hist(), [], live)
    expect(s.marks.map(m => [m.type, m.time])).toEqual([['entry', T(31)], ['exit', T(33)]])
    expect(s.marks[1].pnl).toBe(40)
  })
  it('empty everything', () => {
    expect(mergeSeries('QQQ', null, [], [])).toEqual({ ticker: 'QQQ', candles: [], levels: [], marks: [] })
  })
})

describe('chartHeader', () => {
  it('ticker, date, time, price, change vs day open, trades', () => {
    const s = mergeSeries('QQQ', hist(), [], [])
    expect(chartHeader(s, 9)).toEqual({ ticker: 'QQQ', date: 'Fri 10/9', time: '09:31', price: 101.5, changePct: 1.5, trades: 9 })
  })
  it('empty series', () => {
    expect(chartHeader(mergeSeries('QQQ', null, [], []), 0)).toEqual({ ticker: 'QQQ', date: null, time: null, price: null, changePct: null, trades: 0 })
  })
})

describe('markLabel', () => {
  it('entry shows side, exit shows pnl', () => {
    expect(markLabel({ time: T(1), bot: 'a', type: 'entry', side: 'PUT' })).toBe('PUT')
    expect(markLabel({ time: T(1), bot: 'a', type: 'entry', side: null })).toBe('ENTRY')
    expect(markLabel({ time: T(1), bot: 'a', type: 'exit', side: 'CALL', pnl: 140 })).toBe('+$140.00')
    expect(markLabel({ time: T(1), bot: 'a', type: 'exit', side: 'CALL', pnl: -48 })).toBe('-$48.00')
    expect(markLabel({ time: T(1), bot: 'a', type: 'exit', side: null })).toBe('EXIT')
  })
})
