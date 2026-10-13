import { describe, it, expect } from 'vitest'
import { headline } from '../src/model/headline'
import { badgeFor } from '../src/model/badge'
import type { BotRow, TradeRec } from '../src/model/types'

const row = (o: Partial<BotRow> = {}): BotRow => ({
  bot: 'QQQ-VWAP', ticker: 'QQQ', state: 'idle', reason_code: 'WATCHING', reason_text: '', charge_pct: null,
  inputs: {}, time: null, pnl_day: 0, trades: 0, paused: false, side: null, sideSource: 'none', exit_code: null, ...o,
})
const trade = (o: Partial<TradeRec> = {}): TradeRec => ({ time: 't', bot: 'QQQ-VWAP', ticker: 'QQQ', pnl: 118, exit_code: 'EXIT_LOCK', side: 'CALL', ...o })

describe('headline', () => {
  it('trigger, direction and distance', () => {
    expect(headline(row({ side: 'PUT', inputs: { distance_atr: 0.52 } }))).toBe('VWAP cross ▼ PUT · 0.52 ATR away')
    expect(headline(row({ bot: 'SPY-EMA50', side: 'CALL', inputs: { distance_atr: 1.2 } }))).toBe('EMA50 cross ▲ CALL · 1.20 ATR away')
  })
  it('no side, no distance', () => {
    expect(headline(row({ bot: 'IWM-RANGE' }))).toBe('Range break')
    expect(headline(row({ inputs: { distance_atr: 0.5 } }))).toBe('VWAP cross · 0.50 ATR away')
  })
  it('unknown trigger shows the raw name', () => {
    expect(headline(row({ bot: 'QQQ-NEW' }))).toBe('NEW')
  })
})

describe('badgeFor', () => {
  it('no badge for a plain idle bot', () => {
    expect(badgeFor(row(), undefined)).toBeNull()
  })
  it('forming shows direction and charge', () => {
    expect(badgeFor(row({ state: 'forming', side: 'CALL', charge_pct: 62 }), undefined)).toEqual({ text: 'CALL 62% CHARGED', tone: 'CALL' })
    expect(badgeFor(row({ state: 'forming', charge_pct: null }), undefined)).toEqual({ text: 'CHARGING', tone: 'NEUTRAL' })
  })
  it('fired and managing', () => {
    expect(badgeFor(row({ state: 'fired', side: 'PUT' }), undefined)).toEqual({ text: 'FIRE PUT', tone: 'PUT' })
    expect(badgeFor(row({ state: 'managing', side: 'CALL', pnl_day: 44 }), undefined)).toEqual({ text: 'CALL +$44.00', tone: 'CALL' })
    expect(badgeFor(row({ state: 'managing', pnl_day: -3 }), undefined)).toEqual({ text: 'IN TRADE -$3.00', tone: 'NEUTRAL' })
  })
  it('after a trade, cooldown shows the outcome', () => {
    expect(badgeFor(row({ state: 'cooldown' }), trade())).toEqual({ text: 'PROFIT LOCKED +$118.00', tone: 'WIN' })
    expect(badgeFor(row({ state: 'cooldown' }), trade({ pnl: -48, exit_code: 'EXIT_STOP' }))).toEqual({ text: 'STOPPED OUT -$48.00', tone: 'LOSS' })
    expect(badgeFor(row({ state: 'cooldown' }), trade({ pnl: 0, exit_code: 'EXIT_TIME' }))).toEqual({ text: 'CLOSED FLAT', tone: 'NEUTRAL' })
    expect(badgeFor(row({ state: 'cooldown' }), undefined)).toBeNull()
  })
  it('locked, paused, stale', () => {
    expect(badgeFor(row({ state: 'locked', reason_code: 'DAILY_GOAL' }), undefined)).toEqual({ text: 'DAILY GOAL', tone: 'GOAL' })
    expect(badgeFor(row({ state: 'locked', reason_code: 'DAILY_LOSS' }), undefined)).toEqual({ text: 'LOSS LIMIT', tone: 'LOSS_LIMIT' })
    expect(badgeFor(row({ state: 'paused' }), undefined)).toEqual({ text: 'PAUSED', tone: 'PAUSED' })
    expect(badgeFor(row({ state: 'stale' }), undefined)).toEqual({ text: 'STALE DATA', tone: 'STALE' })
  })
})
