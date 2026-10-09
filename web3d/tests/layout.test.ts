import { describe, it, expect } from 'vitest'
import { ALL_BOTS, botId, parseBotId, towerPosition } from '../src/model/layout'

describe('layout', () => {
  it('has 9 bot ids in ticker-major order', () => {
    expect(ALL_BOTS).toHaveLength(9)
    expect(ALL_BOTS[0]).toBe('QQQ-VWAP')
    expect(ALL_BOTS[8]).toBe('IWM-RANGE')
    expect(botId('SPY', 'EMA50')).toBe('SPY-EMA50')
  })
  it('parses ids', () => {
    expect(parseBotId('SPY-EMA50')).toEqual({ ticker: 'SPY', trigger: 'EMA50' })
    expect(parseBotId('junk')).toBeNull()
  })
  it('places 9 distinct towers around the centre', () => {
    const seen = new Set<string>()
    for (let t = 0; t < 3; t++) for (let k = 0; k < 3; k++) {
      const [x, y, z] = towerPosition(t, k)
      expect(y).toBe(0)
      expect(Math.hypot(x, z)).toBeGreaterThan(4)
      seen.add(`${x.toFixed(2)},${z.toFixed(2)}`)
    }
    expect(seen.size).toBe(9)
  })
})
