import { describe, it, expect } from 'vitest'
import { hudCards } from '../src/model/hud'
import type { DaySummary } from '../src/model/summary'

const sum = (o: Partial<DaySummary> = {}): DaySummary => ({
  total: 1250.5, byTicker: {}, top: { bot: 'QQQ-VWAP', pnl: 800 }, trades: 12, closed: 10, wins: 7, winRate: 70, goal: 5000, goalPct: 25, ...o,
})

describe('hudCards', () => {
  it('gives four cards: day P&L, win rate, trades, best bot', () => {
    const c = hudCards(sum())
    expect(c.map(x => x.id)).toEqual(['pnl', 'win', 'trades', 'best'])
    expect(c[0]).toMatchObject({ value: '+$1,250.50', tone: 'pos', sub: '25% of $5,000 goal' })
    expect(c[1]).toMatchObject({ value: '70%', sub: '7 of 10 closed' })
    expect(c[2].value).toBe('12')
    expect(c[3]).toMatchObject({ value: 'QQQ-VWAP', sub: '+$800.00' })
  })
  it('shows dashes when there is nothing yet, and a negative day as neg', () => {
    const c = hudCards(sum({ total: -300, winRate: null, closed: 0, wins: 0, trades: 0, top: null }))
    expect(c[0].tone).toBe('neg')
    expect(c[1].value).toBe('-'); expect(c[1].sub).toBe('no closed trades')
    expect(c[3]).toMatchObject({ value: '-', sub: 'no winner yet' })
  })
})
