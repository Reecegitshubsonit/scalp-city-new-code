import { describe, it, expect } from 'vitest'
import { visualFor, beamFraction, sideColor, COLORS, stateLabel } from '../src/model/visual'
import type { BotRow } from '../src/model/types'

const row = (o: Partial<BotRow> = {}): BotRow => ({
  bot: 'QQQ-VWAP', ticker: 'QQQ', state: 'idle', reason_code: 'WATCHING', reason_text: '', charge_pct: null,
  inputs: {}, time: null, pnl_day: 0, trades: 0, paused: false, side: null, sideSource: 'none', exit_code: null, ...o,
})

describe('colours', () => {
  it('CALL green, PUT red, none neutral', () => {
    expect(sideColor('CALL')).toBe(COLORS.CALL)
    expect(sideColor('PUT')).toBe(COLORS.PUT)
    expect(sideColor(null)).toBe(COLORS.NEUTRAL)
    expect(COLORS.CALL).not.toBe(COLORS.PUT)
  })
})
describe('beamFraction', () => {
  it('maps 0-100 to 0-1, clamps, null is 0', () => {
    expect(beamFraction(50)).toBe(0.5)
    expect(beamFraction(150)).toBe(1)
    expect(beamFraction(-5)).toBe(0)
    expect(beamFraction(null)).toBe(0)
    expect(beamFraction(NaN)).toBe(0)
  })
})
describe('visualFor', () => {
  it('idle is dim with no beam', () => {
    const v = visualFor(row(), false)
    expect(v.beam).toBe(0); expect(v.glow).toBeLessThan(0.3); expect(v.effect).toBe('none')
  })
  it('forming: beam follows charge, colour follows side', () => {
    const c = visualFor(row({ state: 'forming', charge_pct: 60, side: 'CALL' }), false)
    const p = visualFor(row({ state: 'forming', charge_pct: 60, side: 'PUT' }), false)
    expect(c.beam).toBeCloseTo(0.6); expect(c.color).toBe(COLORS.CALL); expect(p.color).toBe(COLORS.PUT)
  })
  it('forming with null charge has no beam', () => {
    expect(visualFor(row({ state: 'forming', charge_pct: null }), false).beam).toBe(0)
  })
  it('fired rings; reduced motion makes the ring static', () => {
    expect(visualFor(row({ state: 'fired', side: 'PUT' }), false).effect).toBe('ring')
    expect(visualFor(row({ state: 'fired', side: 'PUT' }), true).effect).toBe('ring-static')
  })
  it('managing glows steady and labels pnl', () => {
    const v = visualFor(row({ state: 'managing', side: 'CALL', pnl_day: 120 }), false)
    expect(v.effect).toBe('none'); expect(v.label).toBe('+$120.00'); expect(v.glow).toBeGreaterThan(0.6)
  })
  it('exiting pulses, stale flickers, but not with reduced motion', () => {
    expect(visualFor(row({ state: 'exiting' }), false).effect).toBe('pulse')
    expect(visualFor(row({ state: 'stale' }), false).effect).toBe('flicker')
    expect(visualFor(row({ state: 'exiting' }), true).effect).toBe('none')
    expect(visualFor(row({ state: 'stale' }), true).effect).toBe('none')
    expect(visualFor(row({ state: 'stale' }), true).color).toBe(COLORS.stale)
  })
  it('cooldown blue, locked amber, paused hatched', () => {
    expect(visualFor(row({ state: 'cooldown' }), false).color).toBe(COLORS.cooldown)
    expect(visualFor(row({ state: 'locked' }), false).color).toBe(COLORS.locked)
    expect(visualFor(row({ state: 'locked', reason_code: 'DAILY_GOAL' }), false)).toMatchObject({ color: COLORS.goal, label: 'GOAL HIT' })
    expect(visualFor(row({ state: 'locked', reason_code: 'DAILY_LOSS' }), false)).toMatchObject({ color: COLORS.lossLimit, label: 'LOSS LIMIT' })
    expect(visualFor(row({ state: 'paused' }), false).hatched).toBe(true)
  })
  it('unknown state degrades to idle look', () => {
    const v = visualFor(row({ state: 'wat' }), false)
    expect(v.color).toBe(COLORS.idle); expect(stateLabel('wat')).toBe('wat')
  })
})
