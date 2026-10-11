import type { Side, TradeRec } from './types'
import { plainReason } from './reasons'

/** One closed trade as served by GET /trades (entry fields are null when the log only saw the close, e.g. after a restart). */
export interface Trade {
  bot: string; ticker: string; side: Side | null; contract: string | null; qty: number | null
  entry_time: string | null; entry_price: number | null; exit_time: string; exit_price: number | null
  exit_code: string | null; pnl: number; pnl_day: number | null; source: string | null
}

/** Trades fetched from the engine plus trade_closed events seen live since (deduped by bot and exit time), oldest first. */
export function mergeTrades(fetched: Trade[], live: TradeRec[]): Trade[] {
  const seen = new Set(fetched.map(t => `${t.bot}|${t.exit_time}`))
  const out = [...fetched]
  for (const r of live) {
    if (seen.has(`${r.bot}|${r.time}`)) continue
    out.push({
      bot: r.bot, ticker: r.ticker, side: r.side, contract: null, qty: null, entry_time: null, entry_price: null,
      exit_time: r.time, exit_price: null, exit_code: r.exit_code, pnl: r.pnl, pnl_day: null, source: null,
    })
  }
  return out.sort((a, b) => (a.exit_time < b.exit_time ? -1 : a.exit_time > b.exit_time ? 1 : 0))
}

export const toTradeRecs = (ts: Trade[]): TradeRec[] =>
  ts.map(t => ({ time: t.exit_time, bot: t.bot, ticker: t.ticker, pnl: t.pnl, exit_code: t.exit_code, side: t.side }))

export interface TradeStats { count: number; wins: number; winRate: number | null; pnl: number; best: Trade | null; worst: Trade | null }

export function tradeStats(ts: Trade[]): TradeStats {
  let pnl = 0, wins = 0
  let best: Trade | null = null, worst: Trade | null = null
  for (const t of ts) {
    pnl += t.pnl
    if (t.pnl > 0) wins++
    if (!best || t.pnl > best.pnl) best = t
    if (!worst || t.pnl < worst.pnl) worst = t
  }
  return { count: ts.length, wins, winRate: ts.length ? (wins / ts.length) * 100 : null, pnl: Math.round(pnl * 100) / 100, best, worst }
}

export interface TradeFilter { bot?: string; ticker?: string; result?: 'win' | 'loss' }

export const filterTrades = (ts: Trade[], f: TradeFilter): Trade[] =>
  ts.filter(t => (!f.bot || t.bot === f.bot) && (!f.ticker || t.ticker === f.ticker) &&
    (!f.result || (f.result === 'win' ? t.pnl > 0 : t.pnl < 0)))

const CSV_COLS = ['exit_time', 'entry_time', 'bot', 'ticker', 'side', 'contract', 'qty', 'entry_price', 'exit_price', 'exit_reason', 'pnl', 'pnl_day']
const cell = (v: unknown) => (v == null ? '' : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v))

export function tradesToCsv(ts: Trade[]): string {
  const lines = [CSV_COLS.join(',')]
  for (const t of ts) {
    lines.push([t.exit_time, t.entry_time, t.bot, t.ticker, t.side, t.contract, t.qty, t.entry_price, t.exit_price, t.exit_code ? plainReason(t.exit_code) : '', t.pnl, t.pnl_day].map(cell).join(','))
  }
  return lines.join('\n') + '\n'
}
