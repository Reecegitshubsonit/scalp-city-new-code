import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { Series } from '../model/history'
import { chartHeader, markLabel, relVolume } from '../model/history'
import { fullView, panPrice, panTime, zoomPrice, zoomTime, type ChartView } from '../model/viewport'
import { drawChart, CHART_COLORS, type ChartGeometry } from './drawChart'
import { formatPnl } from '../model/format'

interface Props { series: Series; trades: number; height?: number }

/** Interactive chart: wheel = zoom time at the cursor, Shift+wheel = zoom price, drag = pan, double-click = reset. */
export function ZoomChart({ series, trades, height = 460 }: Props) {
  const ref = useRef<HTMLCanvasElement>(null)
  const geo = useRef<ChartGeometry | null>(null)
  const drag = useRef<{ x: number; y: number } | null>(null)
  const [view, setView] = useState<ChartView>(fullView())
  const [hover, setHover] = useState<number | null>(null)
  const n = series.candles.length
  const prevN = useRef(n)

  // follow the newest candle when the view was already at the right edge
  useEffect(() => {
    setView(v => {
      if (v.span === Infinity || n === prevN.current) return v
      const atEdge = v.start + Math.min(v.span, prevN.current) >= prevN.current - 0.5
      return atEdge ? { ...v, start: Math.max(0, n - Math.min(v.span, n)) } : v
    })
    prevN.current = n
  }, [n])

  useEffect(() => {
    const cv = ref.current
    if (!cv) return
    const paint = () => {
      const w = cv.clientWidth, dpr = Math.min(3, window.devicePixelRatio || 1)
      if (!w) return
      cv.width = Math.round(w * dpr); cv.height = Math.round(height * dpr)
      const ctx = cv.getContext('2d')!
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      geo.current = drawChart(ctx, w, height, series, { labels: true, axis: true, view, cross: hover, fontScale: 1.15 })
    }
    paint()
    const ro = new ResizeObserver(paint)
    ro.observe(cv)
    return () => ro.disconnect()
  }, [series, view, hover, height])

  const apply = useCallback((f: (v: ChartView) => ChartView) => setView(f), [])
  const timeZoom = useCallback((factor: number, anchor = 0.5) => apply(v => zoomTime(v, n, factor, anchor)), [apply, n])

  useEffect(() => {
    const cv = ref.current
    if (!cv) return
    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      const g = geo.current
      const factor = Math.exp(-e.deltaY * 0.0018)
      if (e.shiftKey && !e.ctrlKey) { setView(v => zoomPrice(v, factor)); return }
      const rect = cv.getBoundingClientRect()
      const anchor = g ? Math.min(1, Math.max(0, (e.clientX - rect.left - g.padL) / g.plotW)) : 0.5
      setView(v => zoomTime(v, n, factor, anchor))
    }
    cv.addEventListener('wheel', onWheel, { passive: false })
    return () => cv.removeEventListener('wheel', onWheel)
  }, [n])

  const idxAt = (clientX: number): number | null => {
    const g = geo.current, cv = ref.current
    if (!g || !cv || !g.n) return null
    const rect = cv.getBoundingClientRect()
    const i = Math.round(g.start + ((clientX - rect.left - g.padL) / g.plotW) * g.span - 0.5)
    return Math.min(g.n - 1, Math.max(0, i))
  }

  const onPointerDown = (e: React.PointerEvent) => { drag.current = { x: e.clientX, y: e.clientY }; (e.target as HTMLElement).setPointerCapture(e.pointerId) }
  const onPointerMove = (e: React.PointerEvent) => {
    const g = geo.current
    if (drag.current && g) {
      const dx = e.clientX - drag.current.x, dy = e.clientY - drag.current.y
      drag.current = { x: e.clientX, y: e.clientY }
      setView(v => panPrice(panTime(v, n, -dx / (g.plotW / g.span)), dy / g.plotH))
    } else setHover(idxAt(e.clientX))
  }
  const onPointerUp = () => { drag.current = null }
  const onKey = (e: React.KeyboardEvent) => {
    const g = geo.current
    const step = g ? Math.max(1, g.span / 10) : 5
    const handled = { '+': () => timeZoom(1.4), '=': () => timeZoom(1.4), '-': () => timeZoom(1 / 1.4), '0': () => setView(fullView()),
      ArrowLeft: () => apply(v => panTime(v, n, -step)), ArrowRight: () => apply(v => panTime(v, n, step)),
      ArrowUp: () => apply(v => zoomPrice(v, 1.3)), ArrowDown: () => apply(v => zoomPrice(v, 1 / 1.3)) }[e.key]
    if (handled) { e.preventDefault(); handled() }
  }

  const head = chartHeader(series, trades)
  const c = hover != null ? series.candles[hover] : series.candles[n - 1]
  const lv = useMemo(() => (c ? series.levels.find(l => l.time === c.time) : undefined), [series.levels, c])
  const marksHere = c ? series.marks.filter(m => m.time === c.time) : []
  const rel = c ? relVolume(series.candles, hover ?? n - 1) : null
  const zoomed = view.span < n || view.priceZoom > 1

  return (
    <figure className="zoomchart">
      <figcaption className="charthead big">
        <b>{head.ticker}</b>
        {head.date && <span className="muted"> · {head.date}</span>}
        {head.price != null && <span> · {head.price.toFixed(2)}</span>}
        {head.changePct != null && <span className={head.changePct >= 0 ? 'pos' : 'neg'}> {head.changePct >= 0 ? '+' : ''}{head.changePct.toFixed(2)}%</span>}
        <span className="muted"> · {head.trades} trades</span>
      </figcaption>
      <div className="zoombar" role="toolbar" aria-label="Chart zoom">
        <button onClick={() => timeZoom(1.5)} aria-label="Zoom in time">Time +</button>
        <button onClick={() => timeZoom(1 / 1.5)} aria-label="Zoom out time">Time −</button>
        <button onClick={() => setView(v => zoomPrice(v, 1.4))} aria-label="Zoom in price">Price +</button>
        <button onClick={() => setView(v => zoomPrice(v, 1 / 1.4))} aria-label="Zoom out price">Price −</button>
        <button onClick={() => setView(v => (v.span === Infinity ? v : { ...v, start: Math.max(0, n - Math.min(v.span, n)) }))}>Latest</button>
        <button onClick={() => setView(fullView())} disabled={!zoomed}>Reset</button>
        <small className="muted">{`${Math.round(Math.min(view.span, n))} of ${n} candles`} · wheel = zoom time, Shift+wheel = zoom price, drag = pan, double-click = reset</small>
      </div>
      <canvas ref={ref} tabIndex={0} role="img" className="zoomcanvas" style={{ height }}
        aria-label={`${head.ticker} one-minute chart, ${n} candles. Plus and minus zoom, arrow keys pan, 0 resets.`}
        onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerLeave={() => { setHover(null); onPointerUp() }}
        onDoubleClick={() => setView(fullView())} onKeyDown={onKey} />
      <div className="readout" aria-live="off">
        {c ? <>
          <b>{c.time.slice(11, 16)}</b> O {c.open.toFixed(2)} H {c.high.toFixed(2)} L {c.low.toFixed(2)} C <b>{c.close.toFixed(2)}</b>
          {c.volume ? <span> V {Math.round(c.volume).toLocaleString('en-US')}{rel != null && <span className="muted"> ({rel.toFixed(1)}× avg of prior 20)</span>}</span> : <span className="muted"> V -</span>}
          {lv?.vwap != null && <span style={{ color: CHART_COLORS.vwap }}> VWAP {lv.vwap.toFixed(2)}</span>}
          {lv?.ema50 != null && <span style={{ color: CHART_COLORS.ema50 }}> EMA50 {lv.ema50.toFixed(2)}</span>}
          {marksHere.map((m, i) => <span key={i} className={m.type === 'entry' ? '' : (m.pnl ?? 0) >= 0 ? 'pos' : 'neg'}> · {m.bot} {m.type} {markLabel(m)}{m.type === 'exit' && typeof m.pnl === 'number' ? ` (${formatPnl(m.pnl)})` : ''}</span>)}
        </> : <span className="muted">no candles yet</span>}
      </div>
    </figure>
  )
}
