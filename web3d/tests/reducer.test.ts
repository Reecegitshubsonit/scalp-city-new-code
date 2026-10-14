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
  it('reconnect snapshot keeps a remembered side for a bot still in a trade, drops it otherwise', () => {
    let s = run(snap(0), ev(1, { kind: 'state_change', state: 'fired', reason_code: 'SIGNAL', reason_text: 'PUT signal at 99.1' }))
    s = reduce(s, snap(5, [snapBot('QQQ-VWAP', { state: 'managing' }), snapBot('SPY-RANGE', { state: 'managing' })]), 100)
    expect(s.bots['QQQ-VWAP'].side).toBe('PUT'); expect(s.bots['QQQ-VWAP'].sideSource).toBe('signal')
    expect(s.bots['SPY-RANGE'].side).toBeNull()
    s = reduce(s, snap(6, [snapBot('QQQ-VWAP', { state: 'cooldown' })]), 101)
    expect(s.bots['QQQ-VWAP'].side).toBeNull()
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

describe('round 2 data', () => {
  it('feed events carry the previous state', () => {
    const s = run(snap(0), ev(1, { kind: 'state_change', state: 'forming' }), ev(2, { kind: 'state_change', state: 'idle' }))
    expect(s.feed.map(e => e.prev_state)).toEqual(['forming', 'idle'])
  })
  it('records closed trades with exit code and side', () => {
    const s = run(snap(0),
      ev(1, { kind: 'state_change', state: 'fired', reason_code: 'SIGNAL', reason_text: 'CALL signal at 1' }),
      ev(2, { state: 'exiting', reason_code: 'EXIT_TARGET' }),
      ev(3, { kind: 'trade_closed', state: 'cooldown', reason_code: 'EXIT_FILL', pnl: 55, pnl_day: 55, trades: 1 }))
    expect(s.trades).toEqual([{ time: '2026-10-08T09:45:00-04:00', bot: 'QQQ-VWAP', ticker: 'QQQ', pnl: 55, exit_code: 'EXIT_TARGET', side: 'CALL' }])
    expect(s.bots['QQQ-VWAP'].exit_code).toBe('EXIT_TARGET')
  })
  it('a new fire clears the previous exit code', () => {
    const s = run(snap(0), ev(1, { state: 'exiting', reason_code: 'EXIT_STOP' }), ev(2, { state: 'fired', reason_code: 'SIGNAL', reason_text: 'PUT signal' }))
    expect(s.bots['QQQ-VWAP'].exit_code).toBeNull()
  })
  it('chart overlays come from a bot that is not forming', () => {
    const a = { price: 100, vwap: 105, ema50: 106 }, b = { price: 100, vwap: 100.1, ema50: 100.2 }
    let s = run(snap(0, [snapBot('QQQ-VWAP'), snapBot('QQQ-RANGE')]),
      ev(1, { state: 'forming', inputs: a }))
    expect(s.ticks['QQQ'][0].vwap).toBeUndefined()
    s = reduce(s, ev(2, { bot: 'QQQ-RANGE', state: 'idle', inputs: b }), 5)
    expect(s.ticks['QQQ']).toHaveLength(1)
    expect(s.ticks['QQQ'][0]).toMatchObject({ price: 100, vwap: 100.1, ema50: 100.2 })
  })
  it('marks carry side, exit marks are not duplicated, trades clear on engine restart', () => {
    let s = run(snap(0),
      ev(1, { kind: 'state_change', state: 'fired', reason_code: 'SIGNAL', reason_text: 'PUT signal' }),
      ev(2, { kind: 'fill', state: 'fired', reason_code: 'ENTRY_FILL', fill_price: 100 }),
      ev(3, { kind: 'fill', state: 'exiting', reason_code: 'EXIT_FILL', fill_price: 99 }),
      ev(4, { kind: 'trade_closed', state: 'cooldown', pnl: 9, pnl_day: 9, trades: 1 }))
    expect(s.marks['QQQ'].map(m => [m.type, m.side])).toEqual([['entry', 'PUT'], ['exit', 'PUT']])
    expect(s.marks['QQQ'][1].pnl).toBe(9)
    s = reduce(s, snap(0), 99)
    expect(s.trades).toEqual([])
  })
})

describe('snapshot price points (polling mode)', () => {
  it('adds one chart point per ticker per time from snapshot inputs', () => {
    const b = (bot: string, time: string, price: number) => snapBot(bot, { time, inputs: { price, vwap: price + 0.1, ema50: price + 0.2 } })
    let s = run(snap(1, [b('QQQ-VWAP', 't1', 100), b('QQQ-EMA50', 't1', 100), b('SPY-RANGE', 't1', 200)]))
    expect(s.ticks['QQQ']).toEqual([{ time: 't1', price: 100, vwap: 100.1, ema50: 100.2 }])
    expect(s.ticks['SPY']).toHaveLength(1)
    s = reduce(s, snap(2, [b('QQQ-VWAP', 't1', 100), b('QQQ-EMA50', 't2', 101)]), 9)
    expect(s.ticks['QQQ'].map(p => p.time)).toEqual(['t1', 't2'])
  })
  it('ignores bots without a price or time', () => {
    expect(run(snap(1)).ticks).toEqual({})
  })
})

describe('data mode', () => {
  it('tracks the mode of the latest event', () => {
    expect(initialState.mode).toBeNull()
    expect(run(snap(0), ev(1, { mode: 'mock' })).mode).toBe('mock')
    expect(run(snap(0), ev(1, { mode: 'live' })).mode).toBe('live')
  })
})

describe('aggregates', () => {
  it('total pnl and leaderboard order', () => {
    const s = run(snap(0, [snapBot('QQQ-VWAP', { pnl_day: 50 }), snapBot('SPY-RANGE', { pnl_day: -20 }), snapBot('IWM-VWAP', { pnl_day: 80 })]))
    expect(totalPnl(s)).toBe(110)
    expect(leaderboard(s).map(r => r.bot)).toEqual(['IWM-VWAP', 'QQQ-VWAP', 'SPY-RANGE'])
  })
})

describe('fire records', () => {
  const sig = (seq: number, side = 'CALL') => ev(seq, { kind: 'state_change', state: 'fired', reason_code: 'SIGNAL', reason_text: `${side} signal at 100.00` })
  it('records a fire on SIGNAL even when fired and managing arrive in the same batch', () => {
    const s = run(snap(0),
      sig(1),
      ev(2, { kind: 'state_change', state: 'fired', reason_code: 'BUY_OPEN' }),
      ev(3, { kind: 'fill', state: 'managing', reason_code: 'ENTRY_FILL' }))
    expect(s.bots['QQQ-VWAP'].state).toBe('managing')
    expect(s.fires['QQQ-VWAP']).toMatchObject({ seq: 1, side: 'CALL' })
  })
  it('records PUT side, and a new fire per trade', () => {
    let s = run(snap(0), sig(1, 'PUT'), ev(2, { kind: 'fill', state: 'managing', reason_code: 'ENTRY_FILL' }))
    expect(s.fires['QQQ-VWAP'].side).toBe('PUT')
    s = reduce(s, sig(3), 5000)
    expect(s.fires['QQQ-VWAP']).toMatchObject({ seq: 3, side: 'CALL' })
  })
  it('records a fire from ENTRY_FILL alone when no SIGNAL was seen', () => {
    const s = run(snap(0), ev(4, { kind: 'fill', state: 'managing', reason_code: 'ENTRY_FILL' }))
    expect(s.fires['QQQ-VWAP'].seq).toBe(4)
  })
  it('does not double-fire when ENTRY_FILL follows its SIGNAL', () => {
    const s = run(snap(0), sig(1), ev(2, { kind: 'fill', state: 'managing', reason_code: 'ENTRY_FILL' }))
    expect(s.fires['QQQ-VWAP'].seq).toBe(1)
  })
})

describe('open position', () => {
  const HELD = { side: 'PUT' as const, entry_und: 776.2, stop_und: 776.6, target_und: 775.4, entry_price: 1.96, option_mid: 2.05, open_pnl: 90 }
  it('snapshot carries the engine open position', () => {
    const s = run(snap(3, [snapBot('SPY-VWAP', { state: 'managing', reason_text: 'PUT held, stop 776.60, target 775.40', ...HELD })]))
    expect(s.bots['SPY-VWAP'].side).toBe('PUT')
    expect(s.bots['SPY-VWAP'].held).toEqual({ entry_und: 776.2, stop: 776.6, target: 775.4, open_pnl: 90 })
  })
  it('snapshot without side (old engine) recovers side and levels from the reason text', () => {
    let s = run(snap(3, [snapBot('SPY-VWAP', { state: 'managing', reason_text: 'PUT held, stop 776.60, target 775.40' })]))
    expect(s.bots['SPY-VWAP'].side).toBe('PUT'); expect(s.bots['SPY-VWAP'].sideSource).toBe('signal')
    expect(s.bots['SPY-VWAP'].held).toEqual({ entry_und: null, stop: 776.6, target: 775.4, open_pnl: null })
    s = run(snap(3, [snapBot('SPY-VWAP', { state: 'managing', reason_text: 'CALL filled 10 at 1.50' })]))
    expect(s.bots['SPY-VWAP'].side).toBe('CALL'); expect(s.bots['SPY-VWAP'].held ?? null).toBeNull()
  })
  it('ticks update open P&L, other events keep it, leaving the trade clears it', () => {
    let s = run(snap(0, [snapBot('QQQ-VWAP')]),
      ev(1, { kind: 'state_change', state: 'managing', reason_code: 'HOLDING', reason_text: 'CALL filled 10 at 1.50' }))
    expect(s.bots['QQQ-VWAP'].side).toBe('CALL')
    s = reduce(s, ev(2, { state: 'managing', reason_code: 'HOLDING', reason_text: 'CALL held, stop 99.00, target 102.00', side: 'CALL', entry_und: 100, stop_und: 99, target_und: 102, open_pnl: 40 }), 2000)
    expect(s.bots['QQQ-VWAP'].held).toEqual({ entry_und: 100, stop: 99, target: 102, open_pnl: 40 })
    s = reduce(s, ev(3, { kind: 'state_change', state: 'exiting', reason_code: 'EXIT_TARGET', reason_text: 'closing CALL: target' }), 2001)
    expect(s.bots['QQQ-VWAP'].held?.open_pnl).toBe(40)
    s = reduce(s, ev(4, { kind: 'state_change', state: 'cooldown', reason_code: 'COOLDOWN', reason_text: 'cooldown until 10:05:00' }), 2002)
    expect(s.bots['QQQ-VWAP'].held ?? null).toBeNull()
  })
  it('tick without a quote keeps levels but drops a stale open P&L', () => {
    let s = run(snap(0, [snapBot('QQQ-VWAP')]),
      ev(1, { state: 'managing', reason_text: 'CALL held, stop 99.00, target 102.00', side: 'CALL', entry_und: 100, stop_und: 99, target_und: 102, open_pnl: 40 }))
    s = reduce(s, ev(2, { state: 'managing', reason_text: 'CALL held, stop 99.00, target 102.00', side: 'CALL', entry_und: 100, stop_und: 99, target_und: 102 }), 2000)
    expect(s.bots['QQQ-VWAP'].held).toEqual({ entry_und: 100, stop: 99, target: 102, open_pnl: null })
  })
})
