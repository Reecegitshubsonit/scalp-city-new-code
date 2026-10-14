import type { AppState, BotEvent, BotRow, Held, Mark, ServerMsg, Side, SideSource, SnapshotBot, TickPoint } from './types'
import { inferSide, parseSignalSide } from './side'
import { parseStopTarget } from './history'

export const FEED_MAX = 200
export const TICKS_MAX = 390
export const MARKS_MAX = 100
export const TRADES_MAX = 100

const LEVEL_KEYS = ['vwap', 'ema9', 'ema21', 'ema50'] as const

export const initialState: AppState = { bots: {}, lastSeq: 0, feed: [], ticks: {}, marks: {}, trades: [], mode: null, lastEventAt: null, fires: {} }

interface SideState { side: Side | null; sideSource: SideSource }
const NONE: SideState = { side: null, sideSource: 'none' }
const CLEARING = new Set(['idle', 'cooldown', 'locked', 'paused', 'stale'])
const HOLDING = new Set(['managing', 'exiting'])
const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null)

/** Open position after an event or snapshot row: engine fields first, else stop/target from "PUT held, stop X, target Y". */
function heldFrom(prev: Held | null | undefined, src: Partial<BotEvent> | SnapshotBot, isTick: boolean): Held | null {
  if (!HOLDING.has(src.state ?? '')) return null
  const stop = num(src.stop_und), target = num(src.target_und)
  const st = stop !== null && target !== null ? { stop, target } : parseStopTarget(src.reason_text ?? '')
  const base = st ? { entry_und: num(src.entry_und) ?? prev?.entry_und ?? null, ...st, open_pnl: prev?.open_pnl ?? null } : prev ?? null
  if (!base) return null
  // open P&L comes only on ticks: a tick without it means no live quote this bar, so the old number is dropped
  return isTick ? { ...base, open_pnl: num(src.open_pnl) } : base
}

function applySide(prev: SideState, ev: BotEvent): SideState {
  if (ev.side === 'CALL' || ev.side === 'PUT') return { side: ev.side, sideSource: 'explicit' }
  if (ev.side === null) return NONE
  if (ev.reason_code === 'SIGNAL') {
    const s = parseSignalSide(ev.reason_text)
    if (s) return { side: s, sideSource: 'signal' }
  }
  if (CLEARING.has(ev.state)) return NONE
  if (HOLDING.has(ev.state) && !prev.side) {
    const s = parseSignalSide(ev.reason_text)   // "PUT held, ...", "PUT filled 10 at ...": a page loaded mid-trade
    if (s) return { side: s, sideSource: 'signal' }
  }
  if (ev.state === 'forming') {
    const s = inferSide(ev.bot, ev.inputs ?? {})
    return s ? { side: s, sideSource: 'inferred' } : NONE
  }
  return { side: prev.side, sideSource: prev.sideSource }   // not the whole row: Object.assign(r, row) would revert state, charge and inputs to the previous event's
}

function rowFromSnapshot(b: SnapshotBot): BotRow {
  const explicit = b.side === 'CALL' || b.side === 'PUT'
  let side: SideState = explicit ? { side: b.side as Side, sideSource: 'explicit' } : NONE
  if (!explicit && b.state === 'forming') {
    const s = inferSide(b.bot, b.inputs ?? {})
    if (s) side = { side: s, sideSource: 'inferred' }
  }
  if (!explicit && HOLDING.has(b.state)) {
    const s = parseSignalSide(b.reason_text)
    if (s) side = { side: s, sideSource: 'signal' }
  }
  return {
    bot: b.bot, ticker: b.ticker ?? b.bot.split('-')[0], state: b.state ?? 'idle', reason_code: b.reason_code ?? '',
    reason_text: b.reason_text ?? '', charge_pct: b.charge_pct ?? null, inputs: b.inputs ?? {}, time: b.time ?? null,
    pnl_day: typeof b.pnl_day === 'number' ? b.pnl_day : 0, trades: typeof b.trades === 'number' ? b.trades : 0,
    paused: !!b.paused, ...side, exit_code: null, held: heldFrom(null, b, true),
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
      for (const k of LEVEL_KEYS) if (typeof r.inputs[k] === 'number') levels[k] = r.inputs[k]
      ticks = { ...ticks, [r.ticker]: [...pts, { time: r.time, price: r.inputs.price, ...levels }].slice(-TICKS_MAX) }
    }
    const lastSeq = typeof msg.last_seq === 'number' ? msg.last_seq : 0
    // seq going backwards means the engine restarted: old feed and chart history no longer belong to this run
    const restarted = lastSeq < state.lastSeq
    return {
      ...state, bots, lastSeq, lastEventAt: nowMs, ticks,
      ...(restarted ? { feed: [], ticks: {}, marks: {}, trades: [], fires: {} } : {}),
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
    r.held = heldFrom(row.held, ev, ev.kind === 'tick')
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
      for (const k of LEVEL_KEYS) if (typeof ev.inputs[k] === 'number') levels[k] = ev.inputs[k]
    }
    if (!last || last.time !== ev.time)
      next.ticks = { ...state.ticks, [ev.ticker]: [...pts, { time: ev.time, price: ev.inputs.price, ...levels }].slice(-TICKS_MAX) }
    else if (last.vwap === undefined && levels.vwap !== undefined)
      next.ticks = { ...state.ticks, [ev.ticker]: [...pts.slice(0, -1), { ...last, ...levels }] }
  }
  if (ev.kind === 'trade_closed' && typeof ev.pnl === 'number')
    next.trades = [...state.trades, { time: ev.time, bot: ev.bot, ticker: ev.ticker, pnl: ev.pnl, exit_code: row.exit_code, side: row.side }].slice(-TRADES_MAX)
  next.marks = addMark(state.marks, ev, row.side)
  // entry effect: triggered by the event, not by the 'fired' state, which the engine can leave within the same bar
  const old = state.fires[ev.bot]
  if (ev.reason_code === 'SIGNAL') next.fires = { ...state.fires, [ev.bot]: { seq: ev.seq, side: r.side, time: ev.time, filled: false } }
  else if (ev.reason_code === 'ENTRY_FILL') {
    next.fires = old && !old.filled ? { ...state.fires, [ev.bot]: { ...old, filled: true } }
      : { ...state.fires, [ev.bot]: { seq: ev.seq, side: r.side, time: ev.time, filled: true } }
  }
  return next
}

export const totalPnl = (s: AppState) => Object.values(s.bots).reduce((a, b) => a + b.pnl_day, 0)
export const leaderboard = (s: AppState): BotRow[] =>
  Object.values(s.bots).sort((a, b) => b.pnl_day - a.pnl_day || a.bot.localeCompare(b.bot))
