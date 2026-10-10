import { ALL_BOTS } from './layout'
import { initialState, reduce } from './reducer'
import type { AppState, BotEvent, ServerMsg } from './types'

/** One row of GET /days. */
export interface Day { day: string; mode: string; events: number; first: string | null; last: string | null }

export function placeholderSnapshot(): ServerMsg {
  const bots = Object.fromEntries(ALL_BOTS.map(bot => [bot, {
    bot, ticker: bot.split('-')[0], state: 'idle', reason_code: 'NO_DATA', reason_text: 'replay not started',
    charge_pct: null, inputs: {}, time: null, pnl_day: 0, trades: 0, paused: false,
  }]))
  return { type: 'snapshot', bots, last_seq: 0 }
}

export const eventTimes = (events: BotEvent[]): number[] => events.map(e => Date.parse(e.time))

/** How many events have happened at or before `tMs` (times must be ascending). */
export function countAt(times: number[], tMs: number): number {
  let lo = 0, hi = times.length
  while (lo < hi) { const mid = (lo + hi) >> 1; if (times[mid] <= tMs) lo = mid + 1; else hi = mid }
  return lo
}

/** View state after the first `count` events, rebuilt from scratch (cheap enough to scrub backwards). */
export function replayStateAt(events: BotEvent[], count: number): AppState {
  let s = reduce(initialState, placeholderSnapshot(), 0)
  for (let i = 0; i < count; i++) s = reduce(s, { type: 'event', event: events[i] }, 0)
  return s
}
