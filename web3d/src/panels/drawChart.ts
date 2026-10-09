import type { Series } from '../model/history'
import { markLabel } from '../model/history'
import { COLORS } from '../model/visual'

export const CHART_COLORS = { bg: '#0b0830', grid: '#241f6a', text: '#9a97c8', vwap: '#ff9d3b', ema50: '#ffe14d', ema9: '#7d6bff', ema21: '#4fb8ff' }

export interface DrawOptions { labels: boolean; axis: boolean }

/** Draws candles, VWAP/EMA lines and trade markers. Used for the HTML chart and for the 3D wall monitors. */
export function drawChart(ctx: CanvasRenderingContext2D, w: number, h: number, s: Series, o: DrawOptions): void {
  ctx.fillStyle = CHART_COLORS.bg
  ctx.fillRect(0, 0, w, h)
  const n = s.candles.length
  if (n < 2) {
    ctx.fillStyle = CHART_COLORS.text
    ctx.font = `${Math.round(h / 12)}px system-ui, sans-serif`
    ctx.textAlign = 'center'
    ctx.fillText('waiting for prices...', w / 2, h / 2)
    return
  }
  const padL = 6, padR = o.axis ? 48 : 6, padT = o.labels ? 22 : 8, padB = o.axis ? 18 : 6
  let lo = Infinity, hi = -Infinity
  for (const c of s.candles) { if (c.low < lo) lo = c.low; if (c.high > hi) hi = c.high }
  const pad = (hi - lo) * 0.06 || 0.01
  lo -= pad; hi += pad
  const x = (i: number) => padL + ((i + 0.5) / n) * (w - padL - padR)
  const y = (v: number) => padT + (1 - (v - lo) / (hi - lo)) * (h - padT - padB)
  const slot = (w - padL - padR) / n

  if (o.axis) {
    ctx.strokeStyle = CHART_COLORS.grid; ctx.fillStyle = CHART_COLORS.text
    ctx.font = `${Math.max(9, Math.round(h / 22))}px system-ui, sans-serif`; ctx.lineWidth = 1; ctx.textAlign = 'left'
    for (let k = 0; k <= 4; k++) {
      const v = lo + ((hi - lo) * k) / 4, yy = y(v)
      ctx.beginPath(); ctx.moveTo(padL, yy); ctx.lineTo(w - padR, yy); ctx.stroke()
      ctx.fillText(v.toFixed(2), w - padR + 4, yy + 3)
    }
    ctx.textAlign = 'center'
    let lastHour = ''
    s.candles.forEach((c, i) => {
      const hr = c.time.slice(11, 13)
      if (hr !== lastHour) { lastHour = hr; ctx.fillText(`${hr}:00`, x(i), h - 4) }
    })
  }

  const line = (key: 'vwap' | 'ema9' | 'ema21' | 'ema50', color: string, width: number, dash: number[]) => {
    const byTime = new Map(s.levels.map(l => [l.time, l[key]]))
    ctx.strokeStyle = color; ctx.lineWidth = width; ctx.setLineDash(dash); ctx.beginPath()
    let started = false
    s.candles.forEach((c, i) => {
      const v = byTime.get(c.time)
      if (typeof v !== 'number') return
      if (!started) { ctx.moveTo(x(i), y(v)); started = true } else ctx.lineTo(x(i), y(v))
    })
    ctx.stroke(); ctx.setLineDash([])
  }
  line('vwap', CHART_COLORS.vwap, 1.4, [])
  line('ema50', CHART_COLORS.ema50, 1.2, [4, 3])

  const bw = Math.max(1, Math.min(8, slot * 0.7))
  s.candles.forEach((c, i) => {
    const up = c.close >= c.open
    ctx.strokeStyle = ctx.fillStyle = up ? COLORS.CALL : COLORS.PUT
    ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(x(i), y(c.high)); ctx.lineTo(x(i), y(c.low)); ctx.stroke()
    const top = y(Math.max(c.open, c.close)), hgt = Math.max(1, Math.abs(y(c.open) - y(c.close)))
    ctx.fillRect(x(i) - bw / 2, top, bw, hgt)
  })

  const idx = new Map(s.candles.map((c, i) => [c.time, i]))
  const fs = Math.max(9, Math.round(h / 20))
  ctx.font = `bold ${fs}px system-ui, sans-serif`; ctx.textAlign = 'center'
  for (const m of s.marks) {
    const i = idx.get(m.time)
    if (i === undefined) continue
    const c = s.candles[i]
    const col = m.type === 'entry' ? (m.side === 'PUT' ? COLORS.PUT : m.side === 'CALL' ? COLORS.CALL : COLORS.NEUTRAL)
      : typeof m.pnl === 'number' ? (m.pnl >= 0 ? COLORS.CALL : COLORS.PUT) : COLORS.locked
    ctx.fillStyle = col
    const px = x(i)
    if (m.type === 'entry') {
      const py = m.side === 'PUT' ? y(c.high) - 4 : y(c.low) + 4
      const dir = m.side === 'PUT' ? 1 : -1   // PUT: marker above pointing down; CALL: below pointing up
      ctx.beginPath(); ctx.moveTo(px, py + dir * 0); ctx.lineTo(px - 5, py - dir * 9); ctx.lineTo(px + 5, py - dir * 9); ctx.closePath(); ctx.fill()
      if (o.labels) ctx.fillText(markLabel(m), px, py - dir * 12 + (dir > 0 ? -2 : fs))
    } else {
      const py = y(c.close)
      ctx.fillRect(px - 4, py - 4, 8, 8)
      if (o.labels) ctx.fillText(markLabel(m), px, py - 8)
    }
  }
}
