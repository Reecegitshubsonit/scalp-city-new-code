import { describe, it, expect } from 'vitest'
import { atrSeries, groupMarks, mergeSeries, relVolume, volumeCap, openingRange, parseStopTarget, squeezed, type Candle, type HMark } from '../src/model/history'

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
  const texts = (g: ReturnType<typeof groupMarks>) => g[0].lines.map(l => l.text)
  it('stacks two exits on one candle instead of overlapping, each with its bot under it', () => {
    const g = groupMarks([exit('QQQ-VWAP', -180), exit('QQQ-EMA50', -120)])
    expect(g).toHaveLength(1)
    expect(texts(g)).toEqual(['-$180.00', 'VWAP', '-$120.00', 'EMA50'])
  })
  it('a lone exit names its bot on the line under the P&L', () => {
    expect(texts(groupMarks([exit('QQQ-VWAP', -180)]))).toEqual(['-$180.00', 'VWAP'])
  })
  it('an entry shows the side with the bot under it', () => {
    const g = groupMarks([{ time: T(9, 46), bot: 'SPY-RANGE', type: 'entry', side: 'CALL', pnl: null }])
    expect(g[0].lines).toEqual([{ text: 'CALL', mark: 0, bot: false }, { text: 'RANGE', mark: 0, bot: true }])
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

describe('volumeCap', () => {
  it('caps at the 95th percentile so the opening spike does not flatten the day', () => {
    const vols = [5_000_000, ...Array.from({ length: 99 }, (_, i) => 100_000 + i * 1000)]
    const cap = volumeCap(vols)!
    expect(cap).toBeLessThan(5_000_000)
    expect(cap).toBeGreaterThanOrEqual(190_000)
  })
  it('ignores missing volumes and is null when none', () => {
    expect(volumeCap([null, undefined, 0])).toBeNull()
    expect(volumeCap([null, 200])).toBe(200)
  })
})

describe('mergeSeries volume', () => {
  it('keeps the volume of history bars; tick candles have none', () => {
    const h = { ticker: 'QQQ', bars: [{ time: T(9, 31), open: 1, high: 2, low: 1, close: 2, volume: 129870 }], levels: [], marks: [] }
    const s = mergeSeries('QQQ', h, [{ time: T(9, 32), price: 2.1, vwap: 2, ema9: 2, ema21: 2, ema50: 2 }], [])
    expect(s.candles[0].volume).toBe(129870)
    expect(s.candles[1].volume).toBeUndefined()
  })
})

describe('relVolume', () => {
  const vc = (volume: number | null): Candle => ({ time: '', open: 1, high: 1, low: 1, close: 1, volume })
  it('compares a bar with the average of the bars before it', () => {
    expect(relVolume([vc(100), vc(300), vc(400)], 2)).toBe(2)
  })
  it('uses at most n prior bars and skips bars without volume', () => {
    expect(relVolume([vc(1000), vc(100), vc(null), vc(100), vc(150)], 4, 3)).toBe(1.5)
  })
  it('null for the first bar or a bar without volume', () => {
    expect(relVolume([vc(100)], 0)).toBeNull()
    expect(relVolume([vc(100), vc(null)], 1)).toBeNull()
  })
})
