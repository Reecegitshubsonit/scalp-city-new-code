import { describe, it, expect } from 'vitest'
import { thoughtText } from '../src/model/thoughts'
import type { BotEvent } from '../src/model/types'

const ev = (o: Partial<BotEvent> = {}): BotEvent => ({
  seq: 1, time: '2026-10-08T10:00:00-04:00', bot: 'QQQ-VWAP', ticker: 'QQQ', kind: 'state_change', state: 'idle',
  reason_code: 'WATCHING', reason_text: '', inputs: {}, charge_pct: null, prev_state: 'idle', ...o,
})

describe('thoughtText', () => {
  it('setup forming, with side and charge', () => {
    expect(thoughtText(ev({ state: 'forming', prev_state: 'idle', charge_pct: 56, side: 'PUT' }))).toBe('setup forming: PUT, 56% charged')
  })
  it('setup faded when forming drops back to idle', () => {
    expect(thoughtText(ev({ state: 'idle', prev_state: 'forming' }))).toBe('setup faded, standing down')
  })
  it('fire', () => {
    expect(thoughtText(ev({ state: 'fired', reason_code: 'SIGNAL', reason_text: 'CALL signal at 752.13', side: 'CALL' }))).toBe('FIRE CALL: CALL signal at 752.13')
    expect(thoughtText(ev({ state: 'fired', reason_code: 'SIGNAL', reason_text: 'signal' }))).toBe('FIRE: signal')
  })
  it('orders and fills', () => {
    expect(thoughtText(ev({ kind: 'order_sent', contract: 'QQQ261009C00620000', qty: 10 }))).toBe('order sent: QQQ261009C00620000 x10')
    expect(thoughtText(ev({ kind: 'order_sent' }))).toBe('order sent')
    expect(thoughtText(ev({ kind: 'order_rejected' }))).toBe('order rejected, standing down')
    expect(thoughtText(ev({ kind: 'fill', reason_code: 'ENTRY_FILL', fill_price: 3.48, fill_source: 'modeled' }))).toBe('entry filled @ 3.48 (modeled)')
    expect(thoughtText(ev({ kind: 'fill', reason_code: 'EXIT_FILL', fill_price: 4.1 }))).toBe('exit filled @ 4.10')
    expect(thoughtText(ev({ kind: 'fill', reason_code: 'PARTIAL_FILL' }))).toBe('partial fill')
  })
  it('trade closed: profit, loss, flat', () => {
    expect(thoughtText(ev({ kind: 'trade_closed', pnl: 740 }))).toBe('profit locked +$740.00')
    expect(thoughtText(ev({ kind: 'trade_closed', pnl: -48 }))).toBe('stopped out -$48.00')
    expect(thoughtText(ev({ kind: 'trade_closed', pnl: 0 }))).toBe('closed flat')
  })
  it('locks, cooldown, stale, control', () => {
    expect(thoughtText(ev({ state: 'locked', reason_code: 'DAILY_GOAL' }))).toBe('daily goal reached, clocking out')
    expect(thoughtText(ev({ state: 'locked', reason_code: 'DAILY_LOSS' }))).toBe('daily loss limit hit, standing down')
    expect(thoughtText(ev({ state: 'cooldown', reason_code: 'COOLDOWN' }))).toBe('cooling down before the next setup')
    expect(thoughtText(ev({ kind: 'feed_stale', state: 'stale' }))).toBe('data feed went stale, standing by')
    expect(thoughtText(ev({ kind: 'feed_fresh' }))).toBe('data is fresh again, resuming')
    expect(thoughtText(ev({ kind: 'control', state: 'paused', paused: true }))).toBe('paused by you')
    expect(thoughtText(ev({ kind: 'control', state: 'idle', paused: false }))).toBe('resumed')
  })
  it('exiting uses the plain exit reason; unknown falls back to the code', () => {
    expect(thoughtText(ev({ state: 'exiting', reason_code: 'EXIT_STOP' }))).toBe('Exit: stop hit')
    expect(thoughtText(ev({ state: 'idle', prev_state: 'idle', reason_code: 'BRAND_NEW', reason_text: 'x' }))).toBe('BRAND_NEW: x')
    expect(thoughtText(ev({ state: 'idle', prev_state: 'idle', reason_code: 'BRAND_NEW', reason_text: '' }))).toBe('BRAND_NEW')
  })
})
