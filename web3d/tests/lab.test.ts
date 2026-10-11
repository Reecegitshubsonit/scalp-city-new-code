import { describe, it, expect } from 'vitest'
import { standingLabel, lineTone, replayClockLabel, nextSpeed, earnedLines } from '../src/model/lab'
import type { Candle } from '../src/model/history'
import type { Trade } from '../src/model/trades'

const c = (open: number, close: number): Candle => ({ time: 't', open, high: Math.max(open, close), low: Math.min(open, close), close })
const trade = (o: Partial<Trade> = {}): Trade => ({
  bot: 'QQQ-VWAP', ticker: 'QQQ', side: 'CALL', contract: null, qty: null, entry_time: null, entry_price: null,
  exit_time: '2026-10-09T09:50:00-04:00', exit_price: null, exit_code: 'EXIT_STOP', pnl: -50, pnl_day: null, source: null, ...o,
})

describe('standingLabel', () => {
  it('WINNING, LOSING and FLAT with the amount', () => {
    expect(standingLabel(329)).toBe('WINNING +$329.00')
    expect(standingLabel(-2072)).toBe('LOSING -$2,072.00')
    expect(standingLabel(0)).toBe('FLAT $0.00')
  })
})

describe('lineTone', () => {
  it('green when the last close is above the first open, red below, neutral when flat or empty', () => {
    expect(lineTone([c(100, 101), c(101, 103)])).toBe('up')
    expect(lineTone([c(100, 99), c(99, 98)])).toBe('down')
    expect(lineTone([c(100, 100)])).toBe('flat')
    expect(lineTone([])).toBe('flat')
  })
})

describe('replayClockLabel', () => {
  it('weekday, date and ET time of the replay position', () => {
    expect(replayClockLabel(Date.parse('2026-10-07T15:04:00Z'))).toBe('Wed 10/7 · 11:04 AM ET')
  })
})

describe('nextSpeed', () => {
  it('cycles through the speeds and wraps', () => {
    expect(nextSpeed(1)).toBe(5); expect(nextSpeed(60)).toBe(300); expect(nextSpeed(300)).toBe(1); expect(nextSpeed(7)).toBe(1)
  })
})

describe('earnedLines', () => {
  it('latest trades first, in words, with signed pnl', () => {
    const l = earnedLines([trade({ pnl: -50, exit_time: '2026-10-09T09:50:00-04:00' }), trade({ pnl: 120, exit_code: 'EXIT_TARGET', exit_time: '2026-10-09T10:05:00-04:00' })], 5)
    expect(l[0]).toBe('10:05 QQQ-VWAP profit locked +$120.00')
    expect(l[1]).toBe('09:50 QQQ-VWAP stop hit -$50.00')
    expect(earnedLines([trade(), trade(), trade()], 2)).toHaveLength(2)
  })
})

import { deskKey } from '../src/model/lab'
describe('deskKey', () => {
  it('maps keys to the three desk buttons', () => {
    expect(deskKey(' ')).toBe('play'); expect(deskKey('p')).toBe('play')
    expect(deskKey('l')).toBe('stop'); expect(deskKey('L')).toBe('stop')
    expect(deskKey('s')).toBe('speed')
    expect(deskKey('x')).toBeNull(); expect(deskKey('Escape')).toBeNull()
  })
})
