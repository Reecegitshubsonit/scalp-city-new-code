import { memo, useEffect, useRef } from 'react'
import type { Series } from '../model/history'
import { chartHeader } from '../model/history'
import { drawChart, CHART_COLORS } from './drawChart'

interface Props { series: Series; trades: number; height?: number; labels?: boolean; compact?: boolean }

function CandleChartImpl({ series, trades, height = 220, labels = true, compact = false }: Props) {
  const ref = useRef<HTMLCanvasElement>(null)
  const head = chartHeader(series, trades)
  useEffect(() => {
    const cv = ref.current
    if (!cv) return
    const paint = () => {
      const w = cv.clientWidth, dpr = Math.min(2, window.devicePixelRatio || 1)
      if (!w) return
      cv.width = Math.round(w * dpr); cv.height = Math.round(height * dpr)
      const ctx = cv.getContext('2d')!
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      drawChart(ctx, w, height, series, { labels, axis: !compact })
    }
    paint()
    const ro = new ResizeObserver(paint)
    ro.observe(cv)
    return () => ro.disconnect()
  }, [series, height, labels, compact])
  const chg = head.changePct
  return (
    <figure className="chart">
      <figcaption className="charthead">
        <b>{head.ticker}</b>
        {head.date && <span className="muted"> · {head.date} · {head.time}</span>}
        {head.price != null && <span> · {head.price.toFixed(2)}</span>}
        {chg != null && <span className={chg >= 0 ? 'pos' : 'neg'}> {chg >= 0 ? '+' : ''}{chg.toFixed(2)}%</span>}
        <span className="muted"> · {head.trades} trades</span>
      </figcaption>
      <canvas ref={ref} style={{ width: '100%', height, display: 'block', background: CHART_COLORS.bg, borderRadius: 6 }} role="img"
        aria-label={`${head.ticker} one-minute chart, ${series.candles.length} candles${head.price != null ? `, last price ${head.price.toFixed(2)}` : ''}`} />
      {!compact && <div className="legend muted"><span style={{ color: CHART_COLORS.vwap }}>VWAP</span> <span style={{ color: CHART_COLORS.ema50 }}>EMA50</span> ▲ entry ■ exit · candles: green up, red down</div>}
    </figure>
  )
}
export const CandleChart = memo(CandleChartImpl)
