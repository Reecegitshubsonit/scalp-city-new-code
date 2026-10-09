import { describe, it, expect } from 'vitest'
import { reduce, initialState, totalPnl, leaderboard } from '../src/model/reducer'
import type { BotEvent, ServerMsg, SnapshotBot } from '../src/model/types'

const snapBot = (bot: string, o: Partial<SnapshotBot> = {}): SnapshotBot => ({
  bot, ticker: bot.split('-')[0], state: 'idle', reason_code: 'NO_DATA', reason_text: 'no events yet',
  charge_pct: null, inputs: {}, time: null, pnl_day: 0, trades: 0, paused: false, ...o,
})
const snap = (last_seq = 0, bots: SnapshotBot[] = [snapBot('QQQ-VWAP'), snapBot('SPY-RANGE')]): ServerMsg => ({
  type: 'snapshot', last_seq, bots: Object.fromEntries(bots.map(b => [b.bot, b])),
})
const ev = (seq: number, o: Partial<BotEvent> = {}): ServerMsg => ({
  type: 'event', event: {
    seq, time: '2026-10-08T09:45:00-04:00', bot: 'QQQ-VWAP', ticker: 'QQQ', kind: 'tick', state: 'idle',
    reason_code: 'WATCHING', reason_text: 'watching', inputs: { price: 100 }, charge_pct: null, ...o,
  },
})
const run = (...msgs: ServerMsg[]) => msgs.reduce((s, m, i) => reduce(s, m, 1000 + i), initialState)

describe('snapshot', () => {
  it('seeds rows, handles null time and empty inputs', () => {
    const s = run(snap(7))
    expect(Object.keys(s.bots)).toEqual(['QQQ-VWAP', 'SPY-RANGE'])
    expect(s.lastSeq).toBe(7); expect(s.bots['QQQ-VWAP'].time).toBeNull()
  })
  it('re-applying a snapshot (reconnect) replaces rows and resets lastSeq, keeps feed', () => {
    let s = run(snap(0), ev(5, { kind: 'state_change', state: 'fired' }))
    expect(s.feed).toHaveLength(1)
    s = reduce(s, snap(7, [snapBot('QQQ-VWAP', { state: 'managing' })]), 5000)
    expect(s.lastSeq).toBe(7); expect(s.bots['QQQ-VWAP'].state).toBe('managing'); expect(s.feed).toHaveLength(1)
    expect(Object.keys(s.bots)).toEqual(['QQQ-VWAP'])
    s = reduce(s, ev(8, { state: 'cooldown' }), 5001)
    expect(s.bots['QQQ-VWAP'].state).toBe('cooldown')
  })
  it('clears the feed when the snapshot shows seq went backwards (engine restarted)', () => {
    let s = run(snap(0), ev(5, { kind: 'state_change', state: 'fired' }), ev(6, { kind: 'fill' }))
    expect(s.feed).toHaveLength(2)
    s = reduce(s, snap(1), 9000)
    expect(s.feed).toHaveLength(0); expect(s.lastSeq).toBe(1)
  })
  it('snapshot side is explicit', () => {
    const s = run(snap(0, [snapBot('QQQ-VWAP', { state: 'managing', side: 'PUT' })]))
    expect(s.bots['QQQ-VWAP'].side).toBe('PUT'); expect(s.bots['QQQ-VWAP'].sideSource).toBe('explicit')
  })
})

describe('seq handling', () => {
  it('ignores duplicate and out-of-order events', () => {
    let s = run(snap(0), ev(3, { state: 'forming', charge_pct: 40 }))
    s = reduce(s, ev(3, { state: 'idle' }), 2000)
    s = reduce(s, ev(2, { state: 'idle' }), 2001)
    expect(s.bots['QQQ-VWAP'].state).toBe('forming'); expect(s.lastSeq).toBe(3)
  })
  it('ignores events at or below the snapshot last_seq', () => {
    const s = run(snap(10), ev(10, { state: 'forming' }), ev(9, { state: 'forming' }))
    expect(s.bots['QQQ-VWAP'].state).toBe('idle')
  })
  it('unknown bot only advances lastSeq', () => {
    const s = run(snap(0), ev(1, { bot: 'XYZ-VWAP' }))
    expect(s.lastSeq).toBe(1); expect(s.bots['XYZ-VWAP']).toBeUndefined()
  })
})

describe('row updates', () => {
  it('applies tick fields, null charge allowed, unknown reason code kept verbatim', () => {
    const s = run(snap(0), ev(1, { state: 'forming', charge_pct: null, reason_code: 'BRAND_NEW', reason_text: 'x' }))
    const r = s.bots['QQQ-VWAP']
    expect(r.state).toBe('forming'); expect(r.charge_pct).toBeNull(); expect(r.reason_code).toBe('BRAND_NEW')
  })
  it('applies pnl_day, trades and paused whenever present', () => {
    const s = run(snap(0), ev(1, { kind: 'trade_closed', state: 'cooldown', pnl: 50, pnl_day: 50, trades: 1 }),
      ev(2, { kind: 'control', state: 'paused', paused: true }))
    const r = s.bots['QQQ-VWAP']
    expect(r.pnl_day).toBe(50); expect(r.trades).toBe(1); expect(r.paused).toBe(true); expect(r.state).toBe('paused')
  })
  it('keeps old inputs when an event has none', () => {
    const s = run(snap(0), ev(1, { inputs: { price: 101 } }), ev(2, { kind: 'order_sent', inputs: {} }))
    expect(s.bots['QQQ-VWAP'].inputs.price).toBe(101)
  })
  it('non-tick events go to the feed newest first, ticks do not; feed is capped', () => {
    let s = run(snap(0), ev(1), ev(2, { kind: 'state_change', state: 'forming' }), ev(3, { kind: 'fill' }))
    expect(s.feed.map(e => e.seq)).toEqual([3, 2])
    s = reduce(initialState, snap(0), 0)
    for (let i = 1; i <= 250; i++) s = reduce(s, ev(i, { kind: 'state_change' }), i)
    expect(s.feed).toHaveLength(200); expect(s.feed[0].seq).toBe(250)
  })
})

describe('side resolution', () => {
  it('explicit side wins', () => {
    const s = run(snap(0), ev(1, { state: 'forming', side: 'PUT', inputs: { price: 99, vwap: 100 } }))
    expect(s.bots['QQQ-VWAP'].side).toBe('PUT'); expect(s.bots['QQQ-VWAP'].sideSource).toBe('explicit')
  })
  it('forming infers from price vs vwap when side absent', () => {
    const s = run(snap(0), ev(1, { state: 'forming', inputs: { price: 99, vwap: 100 } }))
    expect(s.bots['QQQ-VWAP'].side).toBe('CALL'); expect(s.bots['QQQ-VWAP'].sideSource).toBe('inferred')
  })
  it('RANGE forming stays neutral without side', () => {
    const s = run(snap(0), ev(1, { bot: 'SPY-RANGE', ticker: 'SPY', state: 'forming', inputs: { price: 99, vwap: 100 } }))
    expect(s.bots['SPY-RANGE'].side).toBeNull()
  })
  it('SIGNAL text sets side, remembered through managing and exiting, cleared on cooldown', () => {
    let s = run(snap(0), ev(1, { kind: 'state_change', state: 'fired', reason_code: 'SIGNAL', reason_text: 'PUT signal at 99.1' }))
    expect(s.bots['QQQ-VWAP'].side).toBe('PUT'); expect(s.bots['QQQ-VWAP'].sideSource).toBe('signal')
    s = reduce(s, ev(2, { state: 'managing', reason_code: 'HOLDING' }), 10)
    s = reduce(s, ev(3, { state: 'exiting', reason_code: 'EXIT_TARGET' }), 11)
    expect(s.bots['QQQ-VWAP'].side).toBe('PUT')
    s = reduce(s, ev(4, { state: 'cooldown', reason_code: 'COOLDOWN' }), 12)
    expect(s.bots['QQQ-VWAP'].side).toBeNull(); expect(s.bots['QQQ-VWAP'].sideSource).toBe('none')
  })
})

describe('chart data', () => {
  it('records one price point per ticker per time, and entry/exit marks', () => {
    const s = run(snap(0, [snapBot('QQQ-VWAP'), snapBot('QQQ-EMA50')]),
      ev(1, { inputs: { price: 100 } }), ev(2, { bot: 'QQQ-EMA50', inputs: { price: 100 } }),
      ev(3, { kind: 'fill', reason_code: 'ENTRY_FILL', fill_price: 100.1 }),
      ev(4, { kind: 'trade_closed', state: 'cooldown', pnl: 10, pnl_day: 10, trades: 1 }))
    expect(s.ticks['QQQ']).toHaveLength(1)
    expect(s.marks['QQQ'].map(m => m.type)).toEqual(['entry', 'exit'])
  })
})

describe('aggregates', () => {
  it('total pnl and leaderboard order', () => {
    const s = run(snap(0, [snapBot('QQQ-VWAP', { pnl_day: 50 }), snapBot('SPY-RANGE', { pnl_day: -20 }), snapBot('IWM-VWAP', { pnl_day: 80 })]))
    expect(totalPnl(s)).toBe(110)
    expect(leaderboard(s).map(r => r.bot)).toEqual(['IWM-VWAP', 'QQQ-VWAP', 'SPY-RANGE'])
  })
})
