import type { Series } from '../model/history'
import { markLabel } from '../model/history'
import { lineTone } from '../model/lab'
import { fullView, priceRange, type ChartView } from '../model/viewport'
import { COLORS } from '../model/visual'

export const CHART_COLORS = { bg: '#0b0830', grid: '#2a2570', text: '#c9c6ee', vwap: '#ff9d3b', ema50: '#ffe14d', ema9: '#7d6bff', ema21: '#4fb8ff' }

export interface DrawOptions {
  labels: boolean
  axis: boolean
  view?: ChartView
  /** index (into candles) of the hovered candle: draws a crosshair */
  cross?: number | null
  /** 'line': glowing close-price line coloured by performance (wall screens); default candles */
  style?: 'candles' | 'line'
  /** multiplies font sizes (wall textures are large, so their text needs to scale) */
  fontScale?: number
}

export interface ChartGeometry {
  start: number; span: number; n: number
  padL: number; padR: number; padT: number; padB: number
  plotW: number; plotH: number; lo: number; hi: number
  x: (i: number) => number
  y: (v: number) => number
}

export function chartGeometry(w: number, h: number, candles: Series['candles'], o: DrawOptions): ChartGeometry {
  const n = candles.length
  const view = o.view ?? fullView()
  const fs = o.fontScale ?? 1
  const padL = 8 * fs, padR = o.axis ? 62 * fs : 8 * fs, padT = o.labels ? 26 * fs : 10 * fs, padB = o.axis ? 24 * fs : 8 * fs
  const plotW = Math.max(1, w - padL - padR), plotH = Math.max(1, h - padT - padB)
  const span = Math.max(1, Math.min(view.span, n))
  const start = Math.min(Math.max(0, view.start), Math.max(0, n - span))
  const { lo, hi } = priceRange(candles, { ...view, start, span })
  return {
    start, span, n, padL, padR, padT, padB, plotW, plotH, lo, hi,
    x: i => padL + ((i - start + 0.5) / span) * plotW,
    y: v => padT + (1 - (v - lo) / (hi - lo)) * plotH,
  }
}

const niceStep = (min: number) => [1, 2, 5, 10, 15, 30, 60, 120].find(s => s >= min) ?? 120

/** Draws candles, VWAP/EMA lines and trade markers. Used for the HTML charts and for the 3D wall screens. */
export function drawChart(ctx: CanvasRenderingContext2D, w: number, h: number, s: Series, o: DrawOptions): ChartGeometry {
  const fs = o.fontScale ?? 1
  ctx.fillStyle = CHART_COLORS.bg
  ctx.fillRect(0, 0, w, h)
  const g = chartGeometry(w, h, s.candles, o)
  if (g.n < 2) {
    ctx.fillStyle = CHART_COLORS.text
    ctx.font = `${Math.round(14 * fs)}px system-ui, sans-serif`
    ctx.textAlign = 'center'
    ctx.fillText('waiting for prices...', w / 2, h / 2)
    return g
  }
  const font = Math.max(10, Math.round(11 * fs))
  const slot = g.plotW / g.span
  const i0 = Math.max(0, Math.floor(g.start) - 1), i1 = Math.min(g.n, Math.ceil(g.start + g.span) + 1)

  if (o.axis) {
    ctx.strokeStyle = CHART_COLORS.grid; ctx.fillStyle = CHART_COLORS.text
    ctx.font = `${font}px system-ui, sans-serif`; ctx.lineWidth = 1; ctx.textAlign = 'left'
    for (let k = 0; k <= 5; k++) {
      const v = g.lo + ((g.hi - g.lo) * k) / 5, yy = Math.round(g.y(v)) + 0.5
      ctx.beginPath(); ctx.moveTo(g.padL, yy); ctx.lineTo(w - g.padR, yy); ctx.stroke()
      ctx.fillText(v.toFixed(2), w - g.padR + 5, yy + font * 0.35)
    }
    ctx.textAlign = 'center'
    const step = niceStep(Math.ceil((font * 5) / slot))
    for (let i = i0; i < i1; i++) {
      if (i % step !== 0 || g.x(i) < g.padL || g.x(i) > w - g.padR) continue
      const xx = Math.round(g.x(i)) + 0.5
      ctx.beginPath(); ctx.moveTo(xx, g.padT); ctx.lineTo(xx, h - g.padB); ctx.stroke()
      ctx.fillText(s.candles[i].time.slice(11, 16), xx, h - g.padB + font + 4 * fs)
    }
  }

  ctx.save()
  ctx.beginPath(); ctx.rect(g.padL, g.padT - 2, g.plotW, g.plotH + 4); ctx.clip()

  const line = (key: 'vwap' | 'ema9' | 'ema21' | 'ema50', color: string, width: number, dash: number[]) => {
    const byTime = new Map(s.levels.map(l => [l.time, l[key]]))
    ctx.strokeStyle = color; ctx.lineWidth = width * Math.max(1, fs * 0.8); ctx.setLineDash(dash.map(d => d * fs)); ctx.beginPath()
    let started = false
    for (let i = i0; i < i1; i++) {
      const v = byTime.get(s.candles[i].time)
      if (typeof v !== 'number') continue
      if (!started) { ctx.moveTo(g.x(i), g.y(v)); started = true } else ctx.lineTo(g.x(i), g.y(v))
    }
    ctx.stroke(); ctx.setLineDash([])
  }
  line('vwap', CHART_COLORS.vwap, 1.6, [])
  line('ema50', CHART_COLORS.ema50, 1.4, [5, 4])

  if (o.style === 'line') {
    const tone = lineTone(s.candles)
    const col = tone === 'up' ? COLORS.CALL : tone === 'down' ? COLORS.PUT : COLORS.NEUTRAL
    const grad = ctx.createLinearGradient(0, g.padT, 0, g.padT + g.plotH)
    grad.addColorStop(0, col + '55'); grad.addColorStop(1, col + '00')
    ctx.beginPath()
    let first = true
    for (let i = i0; i < i1; i++) { const x = g.x(i), y = g.y(s.candles[i].close); if (first) { ctx.moveTo(x, y); first = false } else ctx.lineTo(x, y) }
    ctx.lineTo(g.x(i1 - 1), g.padT + g.plotH); ctx.lineTo(g.x(i0), g.padT + g.plotH); ctx.closePath()
    ctx.fillStyle = grad; ctx.fill()
    ctx.beginPath(); first = true
    for (let i = i0; i < i1; i++) { const x = g.x(i), y = g.y(s.candles[i].close); if (first) { ctx.moveTo(x, y); first = false } else ctx.lineTo(x, y) }
    ctx.strokeStyle = col; ctx.lineWidth = 2.4 * fs; ctx.shadowColor = col; ctx.shadowBlur = 10 * fs; ctx.lineJoin = 'round'; ctx.stroke(); ctx.shadowBlur = 0
  } else {
    const bw = Math.max(1, Math.min(14 * fs, slot * 0.72))
    for (let i = i0; i < i1; i++) {
      const c = s.candles[i]
      const up = c.close >= c.open
      ctx.strokeStyle = ctx.fillStyle = up ? COLORS.CALL : COLORS.PUT
      ctx.lineWidth = Math.max(1, fs * 0.9)
      ctx.beginPath(); ctx.moveTo(Math.round(g.x(i)) + 0.5, g.y(c.high)); ctx.lineTo(Math.round(g.x(i)) + 0.5, g.y(c.low)); ctx.stroke()
      const top = g.y(Math.max(c.open, c.close)), hgt = Math.max(1, Math.abs(g.y(c.open) - g.y(c.close)))
      ctx.fillRect(Math.round(g.x(i) - bw / 2), top, Math.max(1, Math.round(bw)), hgt)
    }
  }

  const idx = new Map(s.candles.map((c, i) => [c.time, i]))
  const mfs = Math.max(10, Math.round(11 * fs))
  ctx.font = `bold ${mfs}px system-ui, sans-serif`; ctx.textAlign = 'center'
  const tri = 6 * fs
  for (const m of s.marks) {
    const i = idx.get(m.time)
    if (i === undefined || i < i0 || i >= i1) continue
    const c = s.candles[i]
    const col = m.type === 'entry' ? (m.side === 'PUT' ? COLORS.PUT : m.side === 'CALL' ? COLORS.CALL : COLORS.NEUTRAL)
      : typeof m.pnl === 'number' ? (m.pnl >= 0 ? COLORS.CALL : COLORS.PUT) : COLORS.locked
    ctx.fillStyle = col
    const px = g.x(i)
    if (m.type === 'entry') {
      const put = m.side === 'PUT'
      const py = put ? g.y(c.high) - 4 * fs : g.y(c.low) + 4 * fs
      const dir = put ? 1 : -1
      ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(px - tri, py - dir * tri * 1.7); ctx.lineTo(px + tri, py - dir * tri * 1.7); ctx.closePath(); ctx.fill()
      if (o.labels) ctx.fillText(markLabel(m), px, put ? py - tri * 1.7 - 3 * fs : py + tri * 1.7 + mfs)
    } else {
      const py = g.y(c.close)
      ctx.fillRect(px - 4 * fs, py - 4 * fs, 8 * fs, 8 * fs)
      if (o.labels) ctx.fillText(markLabel(m), px, py - 8 * fs)
    }
  }
  ctx.restore()

  if (o.cross != null && o.cross >= 0 && o.cross < g.n) {
    const c = s.candles[o.cross]
    const cx = Math.round(g.x(o.cross)) + 0.5, cy = Math.round(g.y(c.close)) + 0.5
    ctx.strokeStyle = '#ffffffaa'; ctx.lineWidth = 1; ctx.setLineDash([4, 4])
    ctx.beginPath(); ctx.moveTo(cx, g.padT); ctx.lineTo(cx, h - g.padB); ctx.moveTo(g.padL, cy); ctx.lineTo(w - g.padR, cy); ctx.stroke(); ctx.setLineDash([])
    if (o.axis) {
      ctx.fillStyle = '#ffffff'; ctx.fillRect(w - g.padR, cy - font * 0.8, g.padR, font * 1.6)
      ctx.fillStyle = '#0b0830'; ctx.textAlign = 'left'; ctx.font = `bold ${font}px system-ui, sans-serif`
      ctx.fillText(c.close.toFixed(2), w - g.padR + 5, cy + font * 0.35)
    }
  }
  return g
}
