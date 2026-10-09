import type { AppState, BotEvent, BotRow, Mark, ServerMsg, Side, SideSource, SnapshotBot, TickPoint } from './types'
import { inferSide, parseSignalSide } from './side'

export const FEED_MAX = 200
export const TICKS_MAX = 390
export const MARKS_MAX = 100
export const TRADES_MAX = 100

export const initialState: AppState = { bots: {}, lastSeq: 0, feed: [], ticks: {}, marks: {}, trades: [], mode: null, lastEventAt: null }

interface SideState { side: Side | null; sideSource: SideSource }
const NONE: SideState = { side: null, sideSource: 'none' }
const CLEARING = new Set(['idle', 'cooldown', 'locked', 'paused', 'stale'])

function applySide(prev: SideState, ev: BotEvent): SideState {
  if (ev.side === 'CALL' || ev.side === 'PUT') return { side: ev.side, sideSource: 'explicit' }
  if (ev.side === null) return NONE
  if (ev.reason_code === 'SIGNAL') {
    const s = parseSignalSide(ev.reason_text)
    if (s) return { side: s, sideSource: 'signal' }
  }
  if (CLEARING.has(ev.state)) return NONE
  if (ev.state === 'forming') {
    const s = inferSide(ev.bot, ev.inputs ?? {})
    return s ? { side: s, sideSource: 'inferred' } : NONE
  }
  return prev
}

function rowFromSnapshot(b: SnapshotBot): BotRow {
  const explicit = b.side === 'CALL' || b.side === 'PUT'
  let side: SideState = explicit ? { side: b.side as Side, sideSource: 'explicit' } : NONE
  if (!explicit && b.state === 'forming') {
    const s = inferSide(b.bot, b.inputs ?? {})
    if (s) side = { side: s, sideSource: 'inferred' }
  }
  return {
    bot: b.bot, ticker: b.ticker ?? b.bot.split('-')[0], state: b.state ?? 'idle', reason_code: b.reason_code ?? '',
    reason_text: b.reason_text ?? '', charge_pct: b.charge_pct ?? null, inputs: b.inputs ?? {}, time: b.time ?? null,
    pnl_day: typeof b.pnl_day === 'number' ? b.pnl_day : 0, trades: typeof b.trades === 'number' ? b.trades : 0,
    paused: !!b.paused, ...side, exit_code: null,
  }
}

function addMark(marks: Record<string, Mark[]>, ev: BotEvent, side: Side | null): Record<string, Mark[]> {
  let type: Mark['type'] | null = null
  if (ev.kind === 'fill' || ev.kind === 'order_sent') {
    if (ev.reason_code === 'ENTRY_FILL') type = 'entry'
    else if (ev.reason_code === 'EXIT_FILL' || ev.reason_code === 'PARTIAL_FILL') type = 'exit'
  } else if (ev.kind === 'trade_closed') type = 'exit'
  const price = ev.fill_price ?? ev.inputs?.price
  if (!type || typeof price !== 'number') return marks
  const list = marks[ev.ticker] ?? []
  const last = list[list.length - 1]
  if (type === 'exit' && last && last.type === 'exit' && last.bot === ev.bot && last.time === ev.time) {
    // trade_closed right after its exit fill: same exit, just add the result
    if (ev.kind !== 'trade_closed' || typeof ev.pnl !== 'number') return marks
    return { ...marks, [ev.ticker]: [...list.slice(0, -1), { ...last, pnl: ev.pnl }] }
  }
  const mark: Mark = { time: ev.time, price, type, bot: ev.bot, side, ...(ev.kind === 'trade_closed' && typeof ev.pnl === 'number' ? { pnl: ev.pnl } : {}) }
  return { ...marks, [ev.ticker]: [...list, mark].slice(-MARKS_MAX) }
}

export function reduce(state: AppState, msg: ServerMsg, nowMs: number): AppState {
  if (msg.type === 'snapshot') {
    const bots: Record<string, BotRow> = {}
    const IN_TRADE = new Set(['fired', 'managing', 'exiting'])
    for (const [id, b] of Object.entries(msg.bots ?? {})) {
      const row = rowFromSnapshot({ ...b, bot: b.bot ?? id })
      const old = state.bots[id]
      // the snapshot has no side for a trade we already know the direction of: keep what we knew
      if (!row.side && IN_TRADE.has(row.state) && old?.side) { row.side = old.side; row.sideSource = old.sideSource }
      bots[id] = row
    }
    // snapshots also feed the chart, so the view works when only polling /snapshot (no websocket)
    let ticks = state.ticks
    for (const r of Object.values(bots)) {
      if (typeof r.inputs.price !== 'number' || !r.time) continue
      const pts = ticks[r.ticker] ?? []
      if (pts.length && pts[pts.length - 1].time === r.time) continue
      const levels: Partial<TickPoint> = {}
      if (typeof r.inputs.vwap === 'number') levels.vwap = r.inputs.vwap
      if (typeof r.inputs.ema50 === 'number') levels.ema50 = r.inputs.ema50
      ticks = { ...ticks, [r.ticker]: [...pts, { time: r.time, price: r.inputs.price, ...levels }].slice(-TICKS_MAX) }
    }
    const lastSeq = typeof msg.last_seq === 'number' ? msg.last_seq : 0
    // seq going backwards means the engine restarted: old feed and chart history no longer belong to this run
    const restarted = lastSeq < state.lastSeq
    return {
      ...state, bots, lastSeq, lastEventAt: nowMs, ticks,
      ...(restarted ? { feed: [], ticks: {}, marks: {}, trades: [] } : {}),
    }
  }
  const ev = msg.event
  if (!ev || typeof ev.seq !== 'number' || ev.seq <= state.lastSeq) return state
  const row = state.bots[ev.bot]
  const base: AppState = { ...state, lastSeq: ev.seq, lastEventAt: nowMs, mode: typeof ev.mode === 'string' ? ev.mode : state.mode }
  if (!row) return base

  const r: BotRow = { ...row }
  if (typeof ev.state === 'string' && ev.state !== '') {
    r.state = ev.state
    r.reason_code = ev.reason_code ?? ''
    r.reason_text = ev.reason_text ?? ''
    r.charge_pct = ev.charge_pct ?? null
    r.time = ev.time ?? r.time
    if (ev.inputs && Object.keys(ev.inputs).length) r.inputs = ev.inputs
    Object.assign(r, applySide(row, ev))
    if (ev.state === 'exiting' && ev.reason_code?.startsWith('EXIT_')) r.exit_code = ev.reason_code
    else if (ev.state === 'fired') r.exit_code = null
  }
  if (typeof ev.pnl_day === 'number') r.pnl_day = ev.pnl_day
  if (typeof ev.trades === 'number') r.trades = ev.trades
  if (typeof ev.paused === 'boolean') r.paused = ev.paused

  const next: AppState = { ...base, bots: { ...state.bots, [ev.bot]: r } }
  if (ev.kind !== 'tick') next.feed = [{ ...ev, prev_state: row.state }, ...state.feed].slice(0, FEED_MAX)
  if (ev.kind === 'tick' && typeof ev.inputs?.price === 'number') {
    const pts = state.ticks[ev.ticker] ?? []
    const last = pts[pts.length - 1]
    const levels: Partial<TickPoint> = {}
    if (r.state !== 'forming') {
      if (typeof ev.inputs.vwap === 'number') levels.vwap = ev.inputs.vwap
      if (typeof ev.inputs.ema50 === 'number') levels.ema50 = ev.inputs.ema50
    }
    if (!last || last.time !== ev.time)
      next.ticks = { ...state.ticks, [ev.ticker]: [...pts, { time: ev.time, price: ev.inputs.price, ...levels }].slice(-TICKS_MAX) }
    else if (last.vwap === undefined && levels.vwap !== undefined)
      next.ticks = { ...state.ticks, [ev.ticker]: [...pts.slice(0, -1), { ...last, ...levels }] }
  }
  if (ev.kind === 'trade_closed' && typeof ev.pnl === 'number')
    next.trades = [...state.trades, { time: ev.time, bot: ev.bot, ticker: ev.ticker, pnl: ev.pnl, exit_code: row.exit_code, side: row.side }].slice(-TRADES_MAX)
  next.marks = addMark(state.marks, ev, row.side)
  return next
}

export const totalPnl = (s: AppState) => Object.values(s.bots).reduce((a, b) => a + b.pnl_day, 0)
export const leaderboard = (s: AppState): BotRow[] =>
  Object.values(s.bots).sort((a, b) => b.pnl_day - a.pnl_day || a.bot.localeCompare(b.bot))
