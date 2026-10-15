import type { Series } from '../model/history'
import { atrSeries, groupMarks, openingRange, squeezed } from '../model/history'
import { lineTone } from '../model/lab'
import { fullView, priceRange, type ChartView } from '../model/viewport'
import { COLORS } from '../model/visual'

/** Every color on the chart is a different hue (checked with the dataviz palette validator: each pair at least 15 ΔE apart).
 *  Candles keep green/red; the stop and target lines reuse them on purpose (loss side / profit side) and carry STOP / TARGET tags. */
export const CHART_COLORS = {
  bg: '#0b0830', grid: '#2a2570', text: '#c9c6ee', label: '#05031aee', session: '#8a90a8',
  vwap: '#ff8c1a',   // orange
  ema50: '#ff4fd8',  // magenta
  ema9: '#00e5ff',   // cyan
  ema21: '#3d7bff',  // blue
  range: '#ffffff',  // white
  atr: '#fff23a',    // yellow
}

/** Session rules the bots follow, drawn as dashed vertical lines. */
const SESSION_TIMES = [
  { hm: '09:40', text: 'RANGE arms', color: CHART_COLORS.session },
  { hm: '09:45', text: 'OR set', color: CHART_COLORS.session },
  { hm: '15:30', text: 'last entry', color: CHART_COLORS.session },
  { hm: '15:55', text: 'flat by', color: CHART_COLORS.session },
]

/** Line styles: VWAP thick solid, EMA50 dashed, EMA9 and EMA21 thin. Shared by the chart legend. */
export const LEVEL_LINES = [
  { key: 'ema21', name: 'EMA21', color: CHART_COLORS.ema21, width: 1.1, dash: [] as number[] },
  { key: 'ema9', name: 'EMA9', color: CHART_COLORS.ema9, width: 1, dash: [] as number[] },
  { key: 'ema50', name: 'EMA50', color: CHART_COLORS.ema50, width: 1.6, dash: [6, 4] },
  { key: 'vwap', name: 'VWAP', color: CHART_COLORS.vwap, width: 2.2, dash: [] as number[] },
] as const

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
  /** ATR panel under the price plot (0 high on the tower sparklines) */
  atrTop: number; atrH: number
  x: (i: number) => number
  y: (v: number) => number
}

export function chartGeometry(w: number, h: number, candles: Series['candles'], o: DrawOptions): ChartGeometry {
  const n = candles.length
  const view = o.view ?? fullView()
  const fs = o.fontScale ?? 1
  const padL = 8 * fs, padR = o.axis ? 62 * fs : 8 * fs, padT = o.style === 'line' ? 10 * fs : 26 * fs, padB = o.axis ? 24 * fs : 8 * fs
  const plotW = Math.max(1, w - padL - padR), full = Math.max(1, h - padT - padB)
  const atrH = o.style === 'line' ? 0 : Math.round(full * 0.2), atrGap = atrH ? 6 * fs : 0
  const plotH = Math.max(1, full - atrH - atrGap), atrTop = padT + plotH + atrGap
  const span = Math.max(1, Math.min(view.span, n))
  const start = Math.min(Math.max(0, view.start), Math.max(0, n - span))
  const { lo, hi } = priceRange(candles, { ...view, start, span })
  return {
    start, span, n, padL, padR, padT, padB, plotW, plotH, lo, hi, atrTop, atrH,
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
  // opening range (RANGE bots): shaded while it forms, then its high and low carry on as lines
  const orng = openingRange(s.candles)
  if (orng) {
    let a = -1, b = -1
    const day = s.candles[g.n - 1].time.slice(0, 10)
    for (let i = 0; i < g.n; i++) { const t = s.candles[i].time, hm = t.slice(11, 16); if (t.slice(0, 10) === day && hm >= '09:30' && hm < '09:45') { if (a < 0) a = i; b = i } }
    const yh = g.y(orng.hi), yl = g.y(orng.lo)
    if (a >= 0) { ctx.fillStyle = CHART_COLORS.range + '12'; ctx.fillRect(g.x(a) - slot / 2, yh, (b - a + 1) * slot, yl - yh) }
    ctx.strokeStyle = CHART_COLORS.range + 'cc'; ctx.lineWidth = Math.max(1, fs * 0.8); ctx.setLineDash([2 * fs, 3 * fs])
    ctx.beginPath(); ctx.moveTo(g.x(Math.max(a, 0)) - slot / 2, yh); ctx.lineTo(w - g.padR, yh); ctx.moveTo(g.x(Math.max(a, 0)) - slot / 2, yl); ctx.lineTo(w - g.padR, yl); ctx.stroke(); ctx.setLineDash([])
  }

  // the bots' clock: RANGE arms 9:40 and trades from 9:45, no new entries after 15:30, flat by 15:55 (scalpcity/config.py)
  ctx.font = `${Math.max(9, Math.round(9 * fs))}px system-ui, sans-serif`; ctx.textAlign = 'left'
  for (let i = i0; i < i1; i++) {
    const hm = s.candles[i].time.slice(11, 16)
    const rule = SESSION_TIMES.find(r => r.hm === hm)
    if (!rule) continue
    const xx = Math.round(g.x(i) - slot / 2) + 0.5
    ctx.strokeStyle = rule.color + '99'; ctx.lineWidth = 1; ctx.setLineDash([3 * fs, 3 * fs])
    ctx.beginPath(); ctx.moveTo(xx, g.padT); ctx.lineTo(xx, g.padT + g.plotH); ctx.stroke(); ctx.setLineDash([])
    if (o.labels) { ctx.fillStyle = rule.color; ctx.fillText(rule.text, xx + 3 * fs, g.padT + g.plotH - 4 * fs) }
  }

  // every trade: red box entry->stop, green box entry->target, from its entry candle to its exit candle (open trades run to the right edge)
  const at = (t: string) => { let k = 0; while (k < g.n - 1 && s.candles[k].time < t) k++; return k }
  for (const tr of s.trades ?? []) {
    const a = at(tr.entry), b = tr.exit ? at(tr.exit) : g.n - 1
    if (b < i0 || a >= i1) continue
    const xa = g.x(a) - slot / 2, xb = tr.exit ? g.x(b) + slot / 2 : w - g.padR
    const ent = tr.entryPrice ?? s.candles[a].close
    const ys = g.y(tr.stop), yt = g.y(tr.target), ye = g.y(ent)
    ctx.fillStyle = COLORS.PUT + (tr.exit ? '1c' : '30'); ctx.fillRect(xa, Math.min(ye, ys), xb - xa, Math.abs(ys - ye))
    ctx.fillStyle = COLORS.CALL + (tr.exit ? '1c' : '30'); ctx.fillRect(xa, Math.min(ye, yt), xb - xa, Math.abs(yt - ye))
    ctx.lineWidth = (tr.exit ? 1.2 : 1.8) * Math.max(1, fs * 0.8); ctx.setLineDash([5 * fs, 3 * fs])
    ctx.strokeStyle = COLORS.PUT; ctx.beginPath(); ctx.moveTo(xa, ys); ctx.lineTo(xb, ys); ctx.stroke()
    ctx.strokeStyle = COLORS.CALL; ctx.beginPath(); ctx.moveTo(xa, yt); ctx.lineTo(xb, yt); ctx.stroke()
    ctx.setLineDash([])
    if (o.labels && xb - xa > 26 * fs) {
      ctx.font = `bold ${Math.max(9, Math.round(9 * fs))}px system-ui, sans-serif`; ctx.textAlign = 'left'
      ctx.fillStyle = COLORS.PUT; ctx.fillText('STOP', xa + 2 * fs, ys + (ys > ye ? 10 * fs : -3 * fs))
      ctx.fillStyle = COLORS.CALL; ctx.fillText('TGT', xa + 2 * fs, yt + (yt > ye ? 10 * fs : -3 * fs))
    }
  }

  for (const l of LEVEL_LINES) line(l.key, l.color, l.width, [...l.dash])

  // open positions: the engine's stop and target on the underlying
  for (const p of s.positions ?? []) {
    for (const [v, col] of [[p.stop, COLORS.PUT], [p.target, COLORS.CALL]] as const) {
      const yy = g.y(v)
      ctx.strokeStyle = col; ctx.lineWidth = 1.4 * Math.max(1, fs * 0.8); ctx.setLineDash([7 * fs, 4 * fs])
      ctx.beginPath(); ctx.moveTo(g.padL, yy); ctx.lineTo(w - g.padR, yy); ctx.stroke(); ctx.setLineDash([])
    }
    if (o.labels) {
      ctx.font = `bold ${Math.max(9, Math.round(9 * fs))}px system-ui, sans-serif`; ctx.textAlign = 'left'
      ctx.fillStyle = COLORS.PUT; ctx.fillText(`STOP ${p.bot.split('-').slice(1).join('-')}`, g.padL + 4 * fs, g.y(p.stop) - 3 * fs)
      ctx.fillStyle = COLORS.CALL; ctx.fillText(`TARGET ${p.bot.split('-').slice(1).join('-')}`, g.padL + 4 * fs, g.y(p.target) - 3 * fs)
    }
  }

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
  const markColor = (m: Series['marks'][number]) => m.type === 'entry' ? (m.side === 'PUT' ? COLORS.PUT : m.side === 'CALL' ? COLORS.CALL : COLORS.NEUTRAL)
    : typeof m.pnl === 'number' ? (m.pnl >= 0 ? COLORS.CALL : COLORS.PUT) : COLORS.locked
  const placed: { x0: number; x1: number; y0: number; y1: number }[] = []
  const lineH = mfs + 3 * fs, padX = 4 * fs
  // stacked labels on a dark pill; moved up or down when they would cover another label
  const label = (px: number, anchorY: number, up: boolean, lines: string[], cols: string[]) => {
    const bw = Math.max(...lines.map(t => ctx.measureText(t).width)) + padX * 2, bh = lines.length * lineH + 2 * fs
    let y0 = up ? anchorY - bh : anchorY
    const hit = (y: number) => placed.some(r => px - bw / 2 < r.x1 && px + bw / 2 > r.x0 && y < r.y1 && y + bh > r.y0)
    for (let k = 0; k < 12 && hit(y0); k++) y0 += up ? -(lineH / 2) : lineH / 2
    y0 = Math.min(Math.max(y0, g.padT - 2), g.padT + g.plotH - bh)
    placed.push({ x0: px - bw / 2, x1: px + bw / 2, y0, y1: y0 + bh })
    ctx.fillStyle = CHART_COLORS.label
    ctx.beginPath(); ctx.roundRect(px - bw / 2, y0, bw, bh, 3 * fs); ctx.fill()
    lines.forEach((t, k) => { ctx.fillStyle = cols[k]; ctx.fillText(t, px, y0 + 1 * fs + (k + 1) * lineH - 3 * fs) })
  }
  for (const grp of groupMarks(s.marks)) {
    const i = idx.get(grp.time)
    if (i === undefined || i < i0 || i >= i1) continue
    const c = s.candles[i]
    const px = g.x(i)
    const cols = grp.marks.map(markColor)
    const lines = grp.lines.map(l => l.text)
    const lineCols = grp.lines.map(l => (l.bot ? CHART_COLORS.text : cols[l.mark]))   // side or P&L in its color, bot name under it in plain text
    if (grp.type === 'entry') {
      for (const m of grp.marks) {
        const put = m.side === 'PUT'
        const py = put ? g.y(c.high) - 4 * fs : g.y(c.low) + 4 * fs
        const dir = put ? 1 : -1
        ctx.fillStyle = markColor(m)
        ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(px - tri, py - dir * tri * 1.7); ctx.lineTo(px + tri, py - dir * tri * 1.7); ctx.closePath(); ctx.fill()
      }
      if (o.labels) {
        const put = grp.marks[0].side === 'PUT'
        label(px, put ? g.y(c.high) - 4 * fs - tri * 1.7 - 2 * fs : g.y(c.low) + 4 * fs + tri * 1.7 + 2 * fs, put, lines, lineCols)
      }
    } else {
      const py = g.y(c.close)
      for (const col of cols) { ctx.fillStyle = col; ctx.fillRect(px - 4 * fs, py - 4 * fs, 8 * fs, 8 * fs) }
      if (o.labels) label(px, py - 7 * fs, true, lines, lineCols)
    }
  }
  ctx.restore()

  if (g.atrH) drawAtrPanel(ctx, s, g, w, fs, font, i0, i1, o.axis)
  if (o.style !== 'line') drawLegend(ctx, s, g, fs)   // every value the bots use, on every price chart (not the tower sparklines)

  if (o.axis) {
    // price tags for stop, target and the opening range on the right axis
    const tag = (v: number, col: string, dark: boolean) => {
      if (v < g.lo || v > g.hi) return
      const yy = g.y(v)
      ctx.fillStyle = col; ctx.fillRect(w - g.padR, yy - font * 0.75, g.padR, font * 1.5)
      ctx.fillStyle = dark ? '#0b0830' : '#ffffff'; ctx.textAlign = 'left'; ctx.font = `bold ${font}px system-ui, sans-serif`
      ctx.fillText(v.toFixed(2), w - g.padR + 5, yy + font * 0.35)
    }
    if (orng) { tag(orng.hi, CHART_COLORS.range, true); tag(orng.lo, CHART_COLORS.range, true) }
    for (const p of [...(s.positions ?? []), ...(s.trades ?? []).filter(t => t.exit === null)]) { tag(p.stop, COLORS.PUT, false); tag(p.target, COLORS.CALL, true) }
  }

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

/** Top-left legend: each line with its latest value, then ATR, opening range, open stop/target and the squeeze flag. */
function drawLegend(ctx: CanvasRenderingContext2D, s: Series, g: ChartGeometry, fs: number) {
  const last = [...s.levels].reverse().find(l => typeof l.vwap === 'number' || typeof l.ema50 === 'number')
  const f = Math.max(9, Math.round(10 * fs))
  ctx.font = `bold ${f}px system-ui, sans-serif`; ctx.textAlign = 'left'
  const items: { text: string; color: string; swatch?: { dash: readonly number[]; width: number } }[] = []
  for (const l of [...LEVEL_LINES].reverse()) {
    const v = last?.[l.key]
    items.push({ text: `${l.name} ${typeof v === 'number' ? v.toFixed(2) : '-'}`, color: l.color, swatch: { dash: l.dash, width: l.width } })
  }
  if (s.atr) items.push({ text: `ATR ${s.atr.toFixed(2)}`, color: CHART_COLORS.atr, swatch: { dash: [], width: 1.6 } })
  const orng = openingRange(s.candles)
  if (orng) items.push({ text: `OR ${orng.lo.toFixed(2)}-${orng.hi.toFixed(2)}${orng.complete ? '' : ' forming'}`, color: CHART_COLORS.range, swatch: { dash: [2, 3], width: 1 } })
  for (const p of [...(s.positions ?? []), ...(s.trades ?? []).filter(t => t.exit === null)])
    items.push({ text: `${p.bot.split('-').slice(1).join('-')} ${p.side ?? ''} stop ${p.stop.toFixed(2)} tgt ${p.target.toFixed(2)}`, color: p.side === 'PUT' ? COLORS.PUT : p.side === 'CALL' ? COLORS.CALL : CHART_COLORS.text })
  if (squeezed(last, s.atr)) items.push({ text: 'SQUEEZE: VWAP chop filter on', color: CHART_COLORS.text })
  const sw = 16 * fs, gap = 10 * fs
  let x = g.padL + 4 * fs, y = 4 * fs + f
  const rowH = f + 5 * fs, maxX = g.padL + g.plotW
  const widths = items.map(it => (it.swatch ? sw + 4 * fs : 0) + ctx.measureText(it.text).width)
  let rows = 1, cx = x
  for (const wd of widths) { if (cx + wd > maxX && cx > x) { rows++; cx = x } cx += wd + gap }
  ctx.fillStyle = CHART_COLORS.label
  ctx.fillRect(g.padL, 0, g.plotW, rows * rowH + 4 * fs)
  items.forEach((it, k) => {
    if (x + widths[k] > maxX && x > g.padL + 4 * fs) { x = g.padL + 4 * fs; y += rowH }
    if (it.swatch) {
      ctx.strokeStyle = it.color; ctx.lineWidth = it.swatch.width * Math.max(1, fs * 0.8); ctx.setLineDash(it.swatch.dash.map(d => d * fs))
      ctx.beginPath(); ctx.moveTo(x, y - f * 0.35); ctx.lineTo(x + sw, y - f * 0.35); ctx.stroke(); ctx.setLineDash([])
      x += sw + 4 * fs
    }
    ctx.fillStyle = it.color; ctx.fillText(it.text, x, y)
    x += ctx.measureText(it.text).width + gap
  })
}

/** ATR(14) of the 1-minute bars in its own panel under the price (its own scale, not a second price axis).
 *  The bots set stop = 1 ATR and target = 2 ATR from entry, and the squeeze test uses 0.15 ATR. */
function drawAtrPanel(ctx: CanvasRenderingContext2D, s: Series, g: ChartGeometry, w: number, fs: number, font: number, i0: number, i1: number, axis: boolean) {
  // latest session only: the chart opens with a few bars of the previous day, and the overnight gap would read as one huge bar
  const day = s.candles[g.n - 1].time.slice(0, 10)
  const first = s.candles.findIndex(c => c.time.slice(0, 10) === day)
  const vals: (number | null)[] = [...Array(first).fill(null), ...atrSeries(s.candles.slice(first))]
  let lo = Infinity, hi = -Infinity
  for (let i = Math.max(0, Math.floor(g.start)); i < Math.min(g.n, Math.ceil(g.start + g.span)); i++) { const v = vals[i]; if (v != null) { lo = Math.min(lo, v); hi = Math.max(hi, v) } }
  if (!isFinite(lo)) return
  if (hi - lo < 1e-6) { hi += 0.01; lo = Math.max(0, lo - 0.01) }
  const y = (v: number) => g.atrTop + (1 - (v - lo) / (hi - lo)) * g.atrH
  ctx.fillStyle = '#ffffff08'; ctx.fillRect(g.padL, g.atrTop, g.plotW, g.atrH)
  ctx.save(); ctx.beginPath(); ctx.rect(g.padL, g.atrTop, g.plotW, g.atrH); ctx.clip()
  ctx.strokeStyle = CHART_COLORS.atr; ctx.lineWidth = 1.6 * Math.max(1, fs * 0.8); ctx.beginPath()
  let started = false
  for (let i = i0; i < i1; i++) {
    const v = vals[i]
    if (v == null) continue
    if (!started) { ctx.moveTo(g.x(i), y(v)); started = true } else ctx.lineTo(g.x(i), y(v))
  }
  ctx.stroke(); ctx.restore()
  const f = Math.max(9, Math.round(9 * fs))
  ctx.font = `bold ${f}px system-ui, sans-serif`; ctx.textAlign = 'left'; ctx.fillStyle = CHART_COLORS.atr
  const now = s.atr ?? vals[vals.length - 1] ?? 0
  ctx.fillText(g.atrH >= 40 ? `ATR(14) ${now.toFixed(2)}   stop 1 ATR, target 2 ATR` : `ATR ${now.toFixed(2)}`, g.padL + 4 * fs, g.atrTop + f + 2 * fs)
  if (axis) {
    ctx.font = `${font}px system-ui, sans-serif`
    ctx.fillText(hi.toFixed(2), w - g.padR + 5, g.atrTop + font)
    ctx.fillText(lo.toFixed(2), w - g.padR + 5, g.atrTop + g.atrH)
  }
}
