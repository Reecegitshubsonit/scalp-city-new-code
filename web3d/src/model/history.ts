import type { Mark, Side, TickPoint } from './types'
import { formatPnl } from './format'
import type { TradeLevel } from './tradeLevels'

export interface Candle { time: string; open: number; high: number; low: number; close: number }
export interface Level { time: string; vwap?: number | null; ema9?: number | null; ema21?: number | null; ema50?: number | null }
export interface HMark { time: string; bot: string; type: 'entry' | 'exit'; side: Side | null; pnl?: number | null }
/** Shape of GET /history?ticker=... */
export interface History { ticker: string; bars: Candle[]; levels: Level[]; marks: HMark[] }
export interface Series {
  ticker: string; candles: Candle[]; levels: Level[]; marks: HMark[]
  /** open positions on this ticker, with the engine's stop and target on the underlying */
  positions?: OpenPos[]
  /** every trade on this ticker with its own stop and target, entry candle to exit candle */
  trades?: TradeLevel[]
  /** latest ATR of this ticker (1-minute bars), as the bots use it */
  atr?: number | null
}
/** One bot's open trade, drawn as stop and target lines. */
export interface OpenPos { bot: string; side: Side | null; stop: number; target: number }

/** History from the engine plus whatever arrived live since: newer ticks become candles (close price only), marks are merged. */
export function mergeSeries(ticker: string, history: History | null, ticks: TickPoint[], liveMarks: Mark[]): Series {
  const candles = history ? [...history.bars] : []
  const levels = history ? [...history.levels] : []
  const marks = history ? [...history.marks] : []
  let lastCandle = candles.length ? candles[candles.length - 1].time : ''
  let lastLevel = levels.length ? levels[levels.length - 1].time : ''
  for (const t of ticks) {
    if (t.time > lastCandle) {
      const prev = candles.length ? candles[candles.length - 1].close : t.price
      candles.push({ time: t.time, open: prev, high: Math.max(prev, t.price), low: Math.min(prev, t.price), close: t.price })
      lastCandle = t.time
    }
    if (t.time > lastLevel && (t.vwap != null || t.ema50 != null)) {
      levels.push({ time: t.time, vwap: t.vwap, ema9: t.ema9, ema21: t.ema21, ema50: t.ema50 })
      lastLevel = t.time
    }
  }
  for (const m of liveMarks) {
    if (marks.some(h => h.time === m.time && h.bot === m.bot && h.type === m.type)) continue
    marks.push({ time: m.time, bot: m.bot, type: m.type, side: m.side, pnl: m.pnl ?? null })
  }
  marks.sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0))
  return { ticker, candles, levels, marks }
}

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

export interface ChartHeader { ticker: string; date: string | null; time: string | null; price: number | null; changePct: number | null; trades: number }

/** Header text data like "QQQ . Fri 10/9 . 12:40 . 750.46 +0.53% . 9 trades". */
export function chartHeader(s: Series, trades: number): ChartHeader {
  const first = s.candles[0], last = s.candles[s.candles.length - 1]
  if (!first || !last) return { ticker: s.ticker, date: null, time: null, price: null, changePct: null, trades }
  const [y, m, d] = last.time.slice(0, 10).split('-').map(Number)
  const date = `${DAYS[new Date(Date.UTC(y, m - 1, d)).getUTCDay()]} ${m}/${d}`
  const changePct = first.open ? Math.round(((last.close - first.open) / first.open) * 10000) / 100 : null
  return { ticker: s.ticker, date, time: last.time.slice(11, 16), price: last.close, changePct, trades }
}

export function markLabel(m: HMark): string {
  if (m.type === 'entry') return m.side ?? 'ENTRY'
  return typeof m.pnl === 'number' ? formatPnl(m.pnl) : 'EXIT'
}

/** A past day's history cut at the replay position: nothing after `ms` (the replay must not show the future). */
export function truncateHistory(h: History, ms: number): History {
  const ok = (t: string) => Date.parse(t) <= ms
  return { ticker: h.ticker, bars: h.bars.filter(b => ok(b.time)), levels: h.levels.filter(l => ok(l.time)), marks: h.marks.filter(m => ok(m.time)) }
}

/** Stop and target from the engine's holding text, e.g. "PUT held, stop 740.83, target 738.87". */
export function parseStopTarget(text: string): { stop: number; target: number } | null {
  const m = /stop (-?\d+(?:\.\d+)?), target (-?\d+(?:\.\d+)?)/.exec(text ?? '')
  return m ? { stop: Number(m[1]), target: Number(m[2]) } : null
}

/** Opening range as the RANGE bots build it: high and low of the latest day's bars starting 9:30..9:44 ET. Null before its first bar. */
export function openingRange(candles: Candle[]): { hi: number; lo: number; complete: boolean } | null {
  let hi = -Infinity, lo = Infinity, complete = false
  const day = candles.length ? candles[candles.length - 1].time.slice(0, 10) : ''
  for (const c of candles) {
    if (c.time.slice(0, 10) !== day) continue   // the chart starts with a few bars of the previous session
    const hm = c.time.slice(11, 16)
    if (hm < '09:30') continue
    if (hm >= '09:45') { complete = true; break }
    hi = Math.max(hi, c.high); lo = Math.min(lo, c.low)
  }
  return hi === -Infinity ? null : { hi, lo, complete }
}

/** EMA9 and EMA21 closer than 0.15 ATR: the chop filter skips VWAP entries (engine: IndicatorSet.squeezed). */
export const SQUEEZE_ATR = 0.15
export function squeezed(level: Level | undefined, atr: number | null | undefined): boolean {
  if (!level || typeof level.ema9 !== 'number' || typeof level.ema21 !== 'number' || !atr) return false
  return Math.abs(level.ema9 - level.ema21) < SQUEEZE_ATR * atr
}

/** Bot name without its ticker: "QQQ-EMA50" -> "EMA50". */
const shortBot = (bot: string) => bot.split('-').slice(1).join('-') || bot

/** One label line: the mark's side or P&L, or the bot under it (`mark` indexes the group's marks). */
export interface MarkLine { text: string; mark: number; bot: boolean }

/** Marks grouped per candle and type, so two exits on one candle get one stacked label instead of overwriting each other.
 *  Each mark gets two lines, its side or P&L with the bot under it ("PUT" / "VWAP"), so the label grows taller, not wider. */
export function groupMarks(marks: HMark[]): { time: string; type: HMark['type']; marks: HMark[]; lines: MarkLine[] }[] {
  const groups = new Map<string, { time: string; type: HMark['type']; marks: HMark[]; lines: MarkLine[] }>()
  for (const m of marks) {
    const key = `${m.time}|${m.type}`
    let g = groups.get(key)
    if (!g) groups.set(key, (g = { time: m.time, type: m.type, marks: [], lines: [] }))
    g.marks.push(m)
  }
  for (const g of groups.values())
    g.lines = g.marks.flatMap((m, k) => [{ text: markLabel(m), mark: k, bot: false }, { text: shortBot(m.bot), mark: k, bot: true }])
  return [...groups.values()]
}

/** ATR per candle, as the engine computes it (scalpcity/indicators.py Atr): Wilder, plain average of true ranges for the first `period` bars. */
export function atrSeries(candles: Candle[], period = 14): number[] {
  const out: number[] = []
  let prev: number | null = null, value = 0, sum = 0
  candles.forEach((c, n) => {
    const tr = prev === null ? c.high - c.low : Math.max(c.high - c.low, Math.abs(c.high - prev), Math.abs(c.low - prev))
    prev = c.close
    if (n < period) { sum += tr; value = sum / (n + 1) } else value = (value * (period - 1) + tr) / period
    out.push(value)
  })
  return out
}
