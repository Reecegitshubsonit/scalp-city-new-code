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
export function paintScanner(ctx: Ctx, w: number, h: number, row: BotRow | null, events: BotEvent[]): void {
  ctx.fillStyle = CHART_COLORS.bg; ctx.fillRect(0, 0, w, h)
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
  text(ctx, `${stateLabel(row.state)} - ${plainReason(row.reason_code)}`, m, h * 0.37, h * 0.05, CHART_COLORS.text)
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
export function paintPlaque(ctx: Ctx, w: number, h: number, nowMs: number, total: number): void {
  ctx.fillStyle = '#05031e'; ctx.fillRect(0, 0, w, h)
  const p = marketPhase(new Date(nowMs))
  const dot = p.phase === 'open' ? COLORS.CALL : COLORS.locked
  ctx.fillStyle = dot; ctx.beginPath(); ctx.arc(w * 0.07, h * 0.3, h * 0.07, 0, Math.PI * 2); ctx.fill()
  text(ctx, p.phase === 'open' ? 'MARKET OPEN' : p.phase === 'pre' ? 'PRE-MARKET' : 'MARKET CLOSED', w * 0.13, h * 0.37, h * 0.17, '#fff', 'left', true)
  const et = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', hour12: false }).format(nowMs)
  const left = p.seconds ? `${Math.floor(p.seconds / 3600)}h ${String(Math.floor((p.seconds % 3600) / 60)).padStart(2, '0')}m ${p.phase === 'open' ? 'to close' : 'to open'}` : p.label
  text(ctx, `${et} ET - ${left}`, w * 0.07, h * 0.62, h * 0.13, CHART_COLORS.text)
  text(ctx, `DAY ${formatPnl(total)}`, w * 0.07, h * 0.9, h * 0.2, total >= 0 ? COLORS.CALL : COLORS.PUT, 'left', true)
}
