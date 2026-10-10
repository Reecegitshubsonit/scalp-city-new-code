import { describe, it, expect } from 'vitest'
import { fullView, zoomTime, panTime, zoomPrice, panPrice, priceRange, visibleRange, MIN_SPAN } from '../src/model/viewport'
import type { Candle } from '../src/model/history'

const candles = (n: number): Candle[] => Array.from({ length: n }, (_, i) => ({ time: `t${i}`, open: 100 + i, high: 102 + i, low: 98 + i, close: 101 + i }))

describe('time zoom and pan', () => {
  it('full view shows everything', () => {
    expect(fullView()).toEqual({ start: 0, span: Infinity, priceZoom: 1, priceShift: 0 })
    expect(visibleRange(candles(100), fullView())).toEqual({ i0: 0, i1: 100 })
  })
  it('zooming in halves the span and keeps the anchor candle under the cursor', () => {
    const n = 200
    const v = zoomTime(fullView(), n, 2, 0.5)
    expect(v.span).toBe(100)
    // anchor index before: 0.5*200 = 100; after: start + 0.5*span = 100
    expect(v.start + 0.5 * v.span).toBeCloseTo(100)
  })
  it('zoom out is capped at all candles, zoom in at MIN_SPAN', () => {
    const n = 200
    let v = zoomTime(fullView(), n, 1000, 0.5)
    expect(v.span).toBe(MIN_SPAN)
    v = zoomTime(v, n, 0.0001, 0.5)
    expect(v.span).toBe(n); expect(v.start).toBe(0)
  })
  it('start stays inside the data', () => {
    const n = 200
    let v = zoomTime(fullView(), n, 4, 1)         // anchored at the right edge
    expect(v.start + v.span).toBeCloseTo(n)
    v = panTime(v, n, 1000); expect(v.start + v.span).toBe(n)
    v = panTime(v, n, -1000); expect(v.start).toBe(0)
  })
  it('few candles: span never exceeds n', () => {
    const v = zoomTime(fullView(), 5, 2, 0.5)
    expect(v.span).toBe(5)
  })
})

describe('price zoom and range', () => {
  it('auto range covers the visible highs and lows with padding', () => {
    const r = priceRange(candles(10), fullView())
    expect(r.lo).toBeLessThan(98); expect(r.hi).toBeGreaterThan(111)
  })
  it('only visible candles count', () => {
    const c = candles(100)
    const v = { start: 0, span: 10, priceZoom: 1, priceShift: 0 }
    expect(priceRange(c, v).hi).toBeLessThan(120)
  })
  it('price zoom shrinks the range around its centre, capped', () => {
    const c = candles(10)
    const base = priceRange(c, fullView())
    const z = priceRange(c, zoomPrice(fullView(), 2))
    expect(z.hi - z.lo).toBeCloseTo((base.hi - base.lo) / 2)
    expect((z.hi + z.lo) / 2).toBeCloseTo((base.hi + base.lo) / 2)
    expect(zoomPrice(fullView(), 1e9).priceZoom).toBeLessThanOrEqual(20)
    expect(zoomPrice(fullView(), 0.0001).priceZoom).toBe(1)
  })
  it('price pan shifts the range by a fraction of the visible range', () => {
    const c = candles(10)
    const v = panPrice(zoomPrice(fullView(), 2), 0.25)
    const r = priceRange(c, v), r0 = priceRange(c, zoomPrice(fullView(), 2))
    expect(r.lo - r0.lo).toBeCloseTo((r0.hi - r0.lo) * 0.25)
  })
})
