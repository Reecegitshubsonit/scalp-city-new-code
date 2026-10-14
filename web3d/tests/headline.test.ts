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
  })
  it('managing shows open P&L from the engine, never the day P&L', () => {
    const held = { entry_und: 776.2, stop: 776.6, target: 775.4, open_pnl: 180 }
    expect(badgeFor(row({ state: 'managing', side: 'PUT', pnl_day: 0, held }), undefined)).toEqual({ text: 'PUT +$180.00', tone: 'PUT' })
    expect(badgeFor(row({ state: 'managing', side: 'PUT', held: { ...held, open_pnl: -45.5 } }), undefined)).toEqual({ text: 'PUT -$45.50', tone: 'PUT' })
  })
  it('managing without open P&L shows progress from entry toward target or stop', () => {
    const held = { entry_und: 776.2, stop: 776.6, target: 775.4, open_pnl: null }
    const at = (price: number) => badgeFor(row({ state: 'managing', side: 'PUT', inputs: { price }, held }), undefined)
    expect(at(775.704)).toEqual({ text: 'PUT +62% TO TARGET', tone: 'PUT' })
    expect(at(776.2)).toEqual({ text: 'PUT +0% TO TARGET', tone: 'PUT' })
    expect(at(776.36)).toEqual({ text: 'PUT 40% TO STOP', tone: 'PUT' })
    const call = { entry_und: 100, stop: 99, target: 102, open_pnl: null }
    expect(badgeFor(row({ state: 'managing', side: 'CALL', inputs: { price: 101 }, held: call }), undefined)).toEqual({ text: 'CALL +50% TO TARGET', tone: 'CALL' })
  })
  it('managing with nothing known says holding, not a day P&L', () => {
    expect(badgeFor(row({ state: 'managing', side: 'CALL', pnl_day: 44 }), undefined)).toEqual({ text: 'CALL HOLDING', tone: 'CALL' })
    expect(badgeFor(row({ state: 'managing', pnl_day: -3 }), undefined)).toEqual({ text: 'IN TRADE', tone: 'NEUTRAL' })
    const noEntry = { entry_und: null, stop: 776.6, target: 775.4, open_pnl: null }
    expect(badgeFor(row({ state: 'managing', side: 'PUT', inputs: { price: 776 }, held: noEntry }), undefined)).toEqual({ text: 'PUT HOLDING', tone: 'PUT' })
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
