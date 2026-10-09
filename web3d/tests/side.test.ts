import { describe, it, expect } from 'vitest'
import { inferSide, parseSignalSide } from '../src/model/side'

describe('inferSide', () => {
  it('VWAP: price below level = CALL, above = PUT', () => {
    expect(inferSide('QQQ-VWAP', { price: 99, vwap: 100 })).toBe('CALL')
    expect(inferSide('QQQ-VWAP', { price: 101, vwap: 100 })).toBe('PUT')
  })
  it('EMA50 uses ema50', () => {
    expect(inferSide('SPY-EMA50', { price: 99, ema50: 100, vwap: 50 })).toBe('CALL')
  })
  it('RANGE, missing inputs and equality give null', () => {
    expect(inferSide('IWM-RANGE', { price: 99, vwap: 100 })).toBeNull()
    expect(inferSide('QQQ-VWAP', { price: 99 })).toBeNull()
    expect(inferSide('QQQ-VWAP', { price: 100, vwap: 100 })).toBeNull()
  })
})
describe('parseSignalSide', () => {
  it('finds CALL or PUT', () => {
    expect(parseSignalSide('CALL signal at 123.45')).toBe('CALL')
    expect(parseSignalSide('PUT signal at 9.1')).toBe('PUT')
    expect(parseSignalSide('holding')).toBeNull()
  })
})
