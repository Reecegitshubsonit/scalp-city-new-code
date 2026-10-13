import type { BotEvent, Side } from './types'
import { parseStopTarget } from './history'
import { parseSignalSide } from './side'

/** One trade's stop and target on the underlying, from its entry candle to its exit candle (exit null while open). */
export interface TradeLevel { bot: string; ticker: string; side: Side | null; entry: string; exit: string | null; entryPrice: number | null; stop: number; target: number }

/** Every trade of a day with the stop and target the engine set for it, read from the event log ("PUT held, stop X, target Y"). */
export function tradeLevels(events: BotEvent[]): TradeLevel[] {
  const out: TradeLevel[] = []
  const side: Record<string, Side | null> = {}
  const open: Record<string, Omit<TradeLevel, 'stop' | 'target'> & { stop: number | null; target: number | null }> = {}
  for (const e of events) {
    if (e.reason_code === 'SIGNAL') side[e.bot] = parseSignalSide(e.reason_text)
    if (e.kind === 'fill' && e.reason_code === 'ENTRY_FILL') {
      open[e.bot] = { bot: e.bot, ticker: e.ticker, side: side[e.bot] ?? parseSignalSide(e.reason_text), entry: e.time, exit: null,
        entryPrice: typeof e.inputs?.price === 'number' ? e.inputs.price : null, stop: null, target: null }
      continue
    }
    const t = open[e.bot]
    if (!t) {
      // engine restart mid-trade: the position comes back as "PUT recovered, stop X, target Y"
      const st = parseStopTarget(e.reason_text)
      if (st && e.state === 'managing') open[e.bot] = { bot: e.bot, ticker: e.ticker, side: parseSignalSide(e.reason_text), entry: e.time, exit: null, entryPrice: null, ...st }
      continue
    }
    if (t.stop === null) {
      const st = parseStopTarget(e.reason_text)
      if (st) { t.stop = st.stop; t.target = st.target }
    }
    if (e.kind === 'trade_closed') {
      if (t.stop !== null && t.target !== null) out.push({ ...t, stop: t.stop, target: t.target, exit: e.time })
      delete open[e.bot]
    }
  }
  for (const t of Object.values(open)) if (t.stop !== null && t.target !== null) out.push({ ...t, stop: t.stop, target: t.target })
  return out.sort((a, b) => (a.entry < b.entry ? -1 : a.entry > b.entry ? 1 : 0))
}

/** Levels as of a replay position: trades entered later are dropped, exits after it read as still open. */
export function levelsAt(levels: TradeLevel[], ms: number): TradeLevel[] {
  return levels.filter(t => Date.parse(t.entry) <= ms).map(t => (t.exit && Date.parse(t.exit) > ms ? { ...t, exit: null } : t))
}
