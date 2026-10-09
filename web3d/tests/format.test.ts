import { describe, it, expect } from 'vitest'
import { formatPnl, formatPct, formatTime, marketPhase, freshness } from '../src/model/format'

describe('format', () => {
  it('formats pnl with sign', () => {
    expect(formatPnl(1234.5)).toBe('+$1,234.50')
    expect(formatPnl(-80)).toBe('-$80.00')
    expect(formatPnl(0)).toBe('$0.00')
  })
  it('formats null charge as dash', () => {
    expect(formatPct(null)).toBe('-')
    expect(formatPct(undefined)).toBe('-')
    expect(formatPct(61.7)).toBe('62%')
  })
  it('formats ISO time as HH:MM:SS as given', () => {
    expect(formatTime('2026-10-08T09:45:30-04:00')).toBe('09:45:30')
    expect(formatTime(null)).toBe('-')
  })
  it('knows market phases (EDT in October)', () => {
    expect(marketPhase(new Date('2026-10-08T13:00:00Z')).phase).toBe('pre')    // 09:00 ET
    expect(marketPhase(new Date('2026-10-08T14:30:00Z')).phase).toBe('open')   // 10:30 ET
    expect(marketPhase(new Date('2026-10-08T20:00:00Z')).phase).toBe('closed') // 16:00 ET
    expect(marketPhase(new Date('2026-10-10T15:00:00Z')).phase).toBe('closed') // Saturday
    expect(marketPhase(new Date('2026-10-08T15:00:00Z')).seconds).toBe(3600 * 5) // 11:00 ET to 16:00
  })
  it('grades freshness', () => {
    expect(freshness(5, { phase: 'open' })).toBe('live')
    expect(freshness(100, { phase: 'open' })).toBe('slow')
    expect(freshness(200, { phase: 'open' })).toBe('stale')
    expect(freshness(200, { phase: 'closed' })).toBe('closed')
    expect(freshness(null, { phase: 'open' })).toBe('none')
  })
})
