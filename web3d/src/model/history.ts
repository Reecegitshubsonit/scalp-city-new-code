import type { Mark, Side, TickPoint } from './types'
import { formatPnl } from './format'

export interface Candle { time: string; open: number; high: number; low: number; close: number }
export interface Level { time: string; vwap?: number | null; ema9?: number | null; ema21?: number | null; ema50?: number | null }
export interface HMark { time: string; bot: string; type: 'entry' | 'exit'; side: Side | null; pnl?: number | null }
/** Shape of GET /history?ticker=... */
export interface History { ticker: string; bars: Candle[]; levels: Level[]; marks: HMark[] }
export interface Series { ticker: string; candles: Candle[]; levels: Level[]; marks: HMark[] }

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
      levels.push({ time: t.time, vwap: t.vwap, ema50: t.ema50 })
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
