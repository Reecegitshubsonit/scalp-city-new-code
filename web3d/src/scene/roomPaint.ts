import type { BotEvent, BotRow } from '../model/types'
import { formatPnl, formatTime, marketPhase } from '../model/format'
import { headline } from '../model/headline'
import { plainReason } from '../model/reasons'
import { thoughtText } from '../model/thoughts'
import { stateLabel } from '../model/visual'
import { COLORS } from '../model/visual'
import { TICKERS, TRIGGERS } from '../model/layout'
import { CHART_COLORS } from '../panels/drawChart'

type Ctx = CanvasRenderingContext2D
const FONT = 'system-ui, sans-serif'

function text(ctx: Ctx, s: string, x: number, y: number, size: number, color: string, align: CanvasTextAlign = 'left', bold = false) {
  ctx.fillStyle = color; ctx.textAlign = align; ctx.font = `${bold ? 'bold ' : ''}${size}px ${FONT}`
  ctx.fillText(s, x, y)
}

function clip(ctx: Ctx, s: string, maxW: number): string {
  if (ctx.measureText(s).width <= maxW) return s
  let t = s
  while (t.length > 1 && ctx.measureText(t + '...').width > maxW) t = t.slice(0, -1)
  return t + '...'
}

/** "SIGNAL SCANNER" monitor: headline, charge bar and the bot's latest thoughts. */
export function paintScanner(ctx: Ctx, w: number, h: number, row: BotRow | null, events: BotEvent[], highlight = false): void {
  ctx.fillStyle = CHART_COLORS.bg; ctx.fillRect(0, 0, w, h)
  if (highlight) { ctx.strokeStyle = '#ffffff'; ctx.lineWidth = Math.max(4, h * 0.012); ctx.strokeRect(2, 2, w - 4, h - 4) }
  if (!row) { text(ctx, 'Select a tower', w / 2, h / 2, h / 14, CHART_COLORS.text, 'center'); return }
  const m = w * 0.04
  text(ctx, 'SIGNAL SCANNER', m, h * 0.09, h * 0.055, CHART_COLORS.text, 'left', true)
  text(ctx, row.bot, w - m, h * 0.09, h * 0.055, '#fff', 'right', true)
  ctx.font = `bold ${h * 0.075}px ${FONT}`
  text(ctx, clip(ctx, headline(row), w - 2 * m), m, h * 0.19, h * 0.075, '#fff', 'left', true)
  const pct = Math.min(100, Math.max(0, row.charge_pct ?? 0))
  ctx.fillStyle = '#1b1666'; ctx.fillRect(m, h * 0.23, w - 2 * m, h * 0.08)
  ctx.fillStyle = row.side === 'PUT' ? COLORS.PUT : row.side === 'CALL' ? COLORS.CALL : COLORS.NEUTRAL
  ctx.fillRect(m, h * 0.23, ((w - 2 * m) * pct) / 100, h * 0.08)
  text(ctx, row.charge_pct == null ? 'NOT CHARGING' : `${Math.round(pct)}% CHARGED`, w / 2, h * 0.287, h * 0.055, '#fff', 'center', true)
  ctx.font = `${h * 0.05}px ${FONT}`
  text(ctx, clip(ctx, `${stateLabel(row.state)} - ${plainReason(row.reason_code)}`, w * 0.62), m, h * 0.37, h * 0.05, CHART_COLORS.text)
  text(ctx, `Day ${formatPnl(row.pnl_day)} · ${row.trades} trades`, w - m, h * 0.37, h * 0.05, row.pnl_day >= 0 ? COLORS.CALL : COLORS.PUT, 'right', true)
  text(ctx, 'THOUGHTS', m, h * 0.44, h * 0.05, CHART_COLORS.text, 'left', true)
  const mine = events.filter(e => e.bot === row.bot).slice(0, 9)
  mine.forEach((e, i) => {
    const y = h * 0.51 + i * h * 0.052
    ctx.font = `${h * 0.043}px ${FONT}`
    const col = e.kind === 'trade_closed' ? ((e.pnl ?? 0) >= 0 ? COLORS.CALL : COLORS.PUT) : '#d9d4ff'
    text(ctx, clip(ctx, `${formatTime(e.time).slice(0, 5)}  ${thoughtText(e)}`, w - 2 * m), m, y, h * 0.043, col)
  })
  if (!mine.length) text(ctx, 'no events for this bot yet', m, h * 0.51, h * 0.043, CHART_COLORS.text)
}

/** Heatmap tiles plus leaderboard. */
export function paintBoard(ctx: Ctx, w: number, h: number, rows: BotRow[]): void {
  ctx.fillStyle = CHART_COLORS.bg; ctx.fillRect(0, 0, w, h)
  const m = w * 0.04
  text(ctx, 'WORKER HEATMAP', m, h * 0.08, h * 0.05, CHART_COLORS.text, 'left', true)
  const by = new Map(rows.map(r => [r.bot, r]))
  const scale = Math.max(300, ...rows.map(r => Math.abs(r.pnl_day)))
  const gw = w * 0.56, tw = gw / 3, th = h * 0.2
  TICKERS.forEach((t, ti) => TRIGGERS.forEach((k, ki) => {
    const r = by.get(`${t}-${k}`), pnl = r?.pnl_day ?? 0
    const a = Math.min(0.8, 0.15 + (Math.abs(pnl) / scale) * 0.6)
    ctx.fillStyle = pnl > 0 ? `rgba(25,245,160,${a})` : pnl < 0 ? `rgba(255,59,107,${a})` : 'rgba(120,120,180,0.2)'
    const x = m + ki * tw, y = h * 0.12 + ti * (th + 6)
    ctx.fillRect(x, y, tw - 6, th)
    text(ctx, `${t} ${k}`, x + 6, y + th * 0.34, h * 0.04, '#e8e6ff')
    text(ctx, formatPnl(pnl), x + 6, y + th * 0.75, h * 0.055, '#fff', 'left', true)
  }))
  const lx = m + gw + w * 0.04
  text(ctx, 'LEADERBOARD', lx, h * 0.08, h * 0.05, CHART_COLORS.text, 'left', true)
  const board = [...rows].sort((a, b) => b.pnl_day - a.pnl_day)
  board.forEach((r, i) => {
    const y = h * 0.15 + i * h * 0.075
    text(ctx, `${i + 1}. ${r.bot}`, lx, y, h * 0.045, '#e8e6ff')
    text(ctx, formatPnl(r.pnl_day), w - m, y, h * 0.045, r.pnl_day >= 0 ? COLORS.CALL : COLORS.PUT, 'right', true)
  })
}

/** "MARKET OPEN, time to close" plaque and the day's total. */
export function paintPlaque(ctx: Ctx, w: number, h: number, nowMs: number, total: number, label = 'DAY'): void {
  ctx.fillStyle = '#05031e'; ctx.fillRect(0, 0, w, h)
  const p = marketPhase(new Date(nowMs))
  const dot = p.phase === 'open' ? COLORS.CALL : COLORS.locked
  ctx.fillStyle = dot; ctx.beginPath(); ctx.arc(w * 0.07, h * 0.3, h * 0.07, 0, Math.PI * 2); ctx.fill()
  text(ctx, p.phase === 'open' ? 'MARKET OPEN' : p.phase === 'pre' ? 'PRE-MARKET' : 'MARKET CLOSED', w * 0.13, h * 0.37, h * 0.17, '#fff', 'left', true)
  const et = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', hour12: false }).format(nowMs)
  const left = p.seconds ? `${Math.floor(p.seconds / 3600)}h ${String(Math.floor((p.seconds % 3600) / 60)).padStart(2, '0')}m ${p.phase === 'open' ? 'to close' : 'to open'}` : p.label
  text(ctx, `${et} ET - ${left}`, w * 0.07, h * 0.62, h * 0.13, CHART_COLORS.text)
  text(ctx, `${label} ${formatPnl(total)}`, w * 0.07, h * 0.9, h * 0.2, total >= 0 ? COLORS.CALL : COLORS.PUT, 'left', true)
}

// ---------- backtest-room screens ----------
import type { Series } from '../model/history'
import { chartHeader } from '../model/history'
import { earnedLines, lineTone, standingLabel } from '../model/lab'
import type { Trade } from '../model/trades'
import { drawChart } from '../panels/drawChart'
import { formatNum } from '../model/format'
import { fullView } from '../model/viewport'

/** Wall chart in the video's style: glowing close line, green when up on the day and red when down, VWAP in orange, header with price and %. */
export function paintWallLine(ctx: Ctx, w: number, h: number, ticker: string, s: Series, trades: number): void {
  drawChart(ctx, w, h, s, { labels: false, axis: false, style: 'line', fontScale: 2.2 })
  const hd = chartHeader(s, trades)
  const up = lineTone(s.candles)
  const col = up === 'up' ? COLORS.CALL : up === 'down' ? COLORS.PUT : '#fff'
  text(ctx, ticker, w * 0.03, h * 0.12, h * 0.09, '#fff', 'left', true)
  text(ctx, `${formatNum(hd.price)}   ${hd.changePct == null ? '' : (hd.changePct >= 0 ? '+' : '') + hd.changePct.toFixed(2) + '%'}`, w * 0.97, h * 0.12, h * 0.09, col, 'right', true)
  text(ctx, `${hd.time ?? ''} · ${hd.trades} trades`, w * 0.03, h * 0.2, h * 0.05, CHART_COLORS.text)
}

/** Selected ticker's last 90 one-minute candles with VWAP/EMA50 and the WINNING / LOSING standing. */
export function paintChart1m(ctx: Ctx, w: number, h: number, ticker: string, s: Series, tickerPnl: number): void {
  const n = s.candles.length
  drawChart(ctx, w, h, s, { labels: true, axis: true, fontScale: 1.9, view: { ...fullView(), span: Math.min(90, Math.max(2, n)), start: Math.max(0, n - 90) } })
  const hd = chartHeader(s, 0)
  text(ctx, `${ticker} · 1-MIN · ${hd.time ?? ''}`, w * 0.02, h * 0.075, h * 0.062, '#fff', 'left', true)
  text(ctx, standingLabel(tickerPnl), w * 0.62, h * 0.075, h * 0.062, tickerPnl >= 0 ? COLORS.CALL : COLORS.PUT, 'left', true)
  text(ctx, 'VWAP', w * 0.9, h * 0.075, h * 0.045, CHART_COLORS.vwap, 'right', true)
  text(ctx, 'EMA50', w * 0.98, h * 0.075, h * 0.045, CHART_COLORS.ema50, 'right', true)
}

/** "EARNED · Wed 10/7": big P&L with the latest trades under it. */
export function paintEarned(ctx: Ctx, w: number, h: number, e: { label: string; pnl: number; count: number; wins: number; trades: Trade[] }): void {
  ctx.fillStyle = '#05031e'; ctx.fillRect(0, 0, w, h)
  const m = w * 0.06
  text(ctx, `EARNED · ${e.label}`, m, h * 0.1, h * 0.065, CHART_COLORS.text, 'left', true)
  text(ctx, formatPnl(e.pnl), m, h * 0.3, h * 0.2, e.pnl >= 0 ? COLORS.CALL : COLORS.PUT, 'left', true)
  text(ctx, `${e.count} trades · ${e.wins} wins · ${e.count ? Math.round((e.wins / e.count) * 100) : 0}% win rate`, m, h * 0.39, h * 0.05, '#e8e6ff')
  earnedLines(e.trades, 9).forEach((l, i) => {
    ctx.font = `${h * 0.045}px ${FONT}`
    text(ctx, clip(ctx, l, w - 2 * m), m, h * 0.5 + i * h * 0.056, h * 0.045, l.includes('-$') ? COLORS.PUT : COLORS.CALL)
  })
  if (!e.trades.length) text(ctx, 'no closed trades yet', m, h * 0.5, h * 0.05, CHART_COLORS.text)
}

/** Neon sign. */
export function paintSign(ctx: Ctx, w: number, h: number, label: string): void {
  ctx.clearRect(0, 0, w, h)
  ctx.textAlign = 'center'; ctx.font = `bold ${h * 0.7}px ${FONT}`
  ctx.shadowColor = '#ff3bd4'; ctx.shadowBlur = h * 0.25; ctx.fillStyle = '#ff9bea'
  ctx.fillText(label, w / 2, h * 0.75)
  ctx.shadowColor = '#3de0ff'; ctx.shadowBlur = h * 0.12; ctx.strokeStyle = '#3de0ff'; ctx.lineWidth = h * 0.02
  ctx.strokeText(label, w / 2, h * 0.75)
  ctx.shadowBlur = 0
}

/** Purple hexagon tiles with a few pink ones. */
export function paintHex(ctx: Ctx, w: number, h: number): void {
  ctx.fillStyle = '#1a1058'; ctx.fillRect(0, 0, w, h)
  const r = h / 9, dx = r * 1.5, dy = Math.sqrt(3) * r
  let seed = 5
  const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296 }
  for (let col = -1; col * dx < w + r; col++) {
    for (let row = -1; row * dy < h + dy; row++) {
      const cx = col * dx, cy = row * dy + (col % 2 ? dy / 2 : 0)
      ctx.beginPath()
      for (let k = 0; k < 6; k++) { const a = (Math.PI / 3) * k; ctx.lineTo(cx + (r - 3) * Math.cos(a), cy + (r - 3) * Math.sin(a)) }
      ctx.closePath()
      const v = rnd()
      ctx.fillStyle = v < 0.07 ? '#ff3bd4' : v < 0.2 ? '#3a1d8f' : '#2a1678'
      ctx.fill()
    }
  }
}

/** Label under a desk button. */
export function paintDiscLabel(ctx: Ctx, w: number, h: number, label: string, color: string): void {
  ctx.clearRect(0, 0, w, h)
  ctx.fillStyle = '#0b0830cc'; ctx.fillRect(0, 0, w, h)
  text(ctx, label, w / 2, h * 0.68, h * 0.55, color, 'center', true)
}


/** One ticker's bots: a P&L tile per bot (heatmap) next to the ranking (leaderboard). */
export function paintTickerBoard(ctx: Ctx, w: number, h: number, ticker: string, rows: BotRow[]): void {
  ctx.fillStyle = CHART_COLORS.bg; ctx.fillRect(0, 0, w, h)
  const m = w * 0.04
  text(ctx, `${ticker} BOTS TODAY`, m, h * 0.09, h * 0.06, CHART_COLORS.text, 'left', true)
  const scale = Math.max(300, ...rows.map(r => Math.abs(r.pnl_day)))
  const tw = w * 0.58, th = h * 0.24
  rows.forEach((r, i) => {
    const a = Math.min(0.8, 0.15 + (Math.abs(r.pnl_day) / scale) * 0.6)
    ctx.fillStyle = r.pnl_day > 0 ? `rgba(25,245,160,${a})` : r.pnl_day < 0 ? `rgba(255,59,107,${a})` : 'rgba(120,120,180,0.2)'
    const y = h * 0.14 + i * (th + 8)
    ctx.fillRect(m, y, tw, th)
    text(ctx, `${r.bot.split('-')[1]} · ${stateLabel(r.state)}`, m + 10, y + th * 0.33, h * 0.052, '#e8e6ff')
    text(ctx, formatPnl(r.pnl_day), m + 10, y + th * 0.78, h * 0.085, '#fff', 'left', true)
    text(ctx, `${r.trades} trades`, m + tw - 10, y + th * 0.78, h * 0.05, '#e8e6ff', 'right')
  })
  const lx = m + tw + w * 0.04
  text(ctx, 'LEADERBOARD', lx, h * 0.09, h * 0.05, CHART_COLORS.text, 'left', true)
  ;[...rows].sort((a, b) => b.pnl_day - a.pnl_day).forEach((r, i) => {
    const y = h * 0.2 + i * h * 0.17
    text(ctx, `${i + 1}. ${r.bot.split('-')[1]}`, lx, y, h * 0.06, '#e8e6ff', 'left', true)
    text(ctx, formatPnl(r.pnl_day), w - m, y + h * 0.075, h * 0.06, r.pnl_day >= 0 ? COLORS.CALL : COLORS.PUT, 'right', true)
  })
}
