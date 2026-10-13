import { describe, it, expect } from 'vitest'
import { atrSeries, groupMarks, mergeSeries, openingRange, parseStopTarget, squeezed, type Candle, type HMark } from '../src/model/history'

const T = (h: number, m: number) => `2026-10-13T${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:00-04:00`
const bar = (h: number, m: number, high: number, low: number): Candle => ({ time: T(h, m), open: low, high, low, close: high })

describe('parseStopTarget', () => {
  it('reads the engine holding text', () => {
    expect(parseStopTarget('PUT held, stop 740.83, target 738.87')).toEqual({ stop: 740.83, target: 738.87 })
    expect(parseStopTarget('CALL recovered, stop 777.50, target 778.16')).toEqual({ stop: 777.5, target: 778.16 })
  })
  it('null for other text', () => { expect(parseStopTarget('PUT filled 10 at 1.36')).toBeNull() })
})

describe('openingRange', () => {
  it('uses bars 9:30..9:44 only, like RangeBreak', () => {
    const r = openingRange([bar(9, 30, 101, 99), bar(9, 44, 103, 100), bar(9, 45, 110, 90)])
    expect(r).toEqual({ hi: 103, lo: 99, complete: true })
  })
  it('ignores the previous session bars at the start of the chart', () => {
    const prev: Candle = { time: '2026-10-12T15:58:00-04:00', open: 1, high: 999, low: 1, close: 1 }
    expect(openingRange([prev, bar(9, 30, 101, 99), bar(9, 45, 110, 90)])).toEqual({ hi: 101, lo: 99, complete: true })
  })
  it('is forming before 9:45 and null before the open', () => {
    expect(openingRange([bar(9, 31, 101, 99)])).toEqual({ hi: 101, lo: 99, complete: false })
    expect(openingRange([])).toBeNull()
  })
})

describe('squeezed', () => {
  it('EMA9 and EMA21 closer than 0.15 ATR', () => {
    expect(squeezed({ time: '', ema9: 100, ema21: 100.01 }, 0.1)).toBe(true)
    expect(squeezed({ time: '', ema9: 100, ema21: 100.02 }, 0.1)).toBe(false)
    expect(squeezed({ time: '', ema9: 100, ema21: 100 }, null)).toBe(false)
  })
})

describe('groupMarks', () => {
  const exit = (bot: string, pnl: number): HMark => ({ time: T(9, 34), bot, type: 'exit', side: 'PUT', pnl })
  it('stacks two exits on one candle instead of overlapping', () => {
    const g = groupMarks([exit('QQQ-VWAP', -180), exit('QQQ-EMA50', -120)])
    expect(g).toHaveLength(1)
    expect(g[0].lines).toEqual(['VWAP -$180.00', 'EMA50 -$120.00'])
  })
  it('a lone exit keeps its plain label', () => {
    expect(groupMarks([exit('QQQ-VWAP', -180)])[0].lines).toEqual(['-$180.00'])
  })
})

describe('mergeSeries levels', () => {
  it('keeps EMA9 and EMA21 from live ticks', () => {
    const s = mergeSeries('QQQ', null, [{ time: T(9, 31), price: 100, vwap: 100, ema9: 100.1, ema21: 100.2, ema50: 100.3 }], [])
    expect(s.levels[0]).toMatchObject({ ema9: 100.1, ema21: 100.2 })
  })
})

describe('atrSeries', () => {
  it('matches the engine: plain average for the first bars, then Wilder', () => {
    const c = (h: number, l: number, cl: number) => ({ time: '', open: cl, high: h, low: l, close: cl })
    const v = atrSeries([c(2, 1, 1.5), c(3, 1.5, 2.5), c(2.6, 2.4, 2.5)], 2)
    expect(v[0]).toBeCloseTo(1)          // first bar: high - low
    expect(v[1]).toBeCloseTo(1.25)       // average of 1 and 1.5
    expect(v[2]).toBeCloseTo((1.25 + 0.2) / 2)   // Wilder: (prev * (n-1) + tr) / n
  })
})
