import { memo } from 'react'
import type { Mark, TickPoint } from '../model/types'
import { TICKERS } from '../model/layout'
import { formatNum } from '../model/format'
import { COLORS } from '../model/visual'

interface ChartProps { ticker: string; points: TickPoint[]; marks: Mark[]; big?: boolean }

export function TickerChart({ ticker, points, marks, big }: ChartProps) {
  const W = 320, H = big ? 150 : 110, P = 8
  const last = points[points.length - 1]
  const first = points[0]
  const chg = last && first && first.price ? ((last.price - first.price) / first.price) * 100 : null
  const header = (
    <figcaption className="charthead">
      <b>{ticker}</b> <span>{last ? formatNum(last.price) : '-'}</span>{' '}
      <span className={chg == null ? 'muted' : chg >= 0 ? 'pos' : 'neg'}>{chg == null ? '-' : `${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%`}</span>
      <small className="muted"> since load</small>
    </figcaption>
  )
  if (points.length < 2) return <figure className="chart">{header}<p className="muted pad">Fills as prices arrive.</p></figure>

  const vals = points.flatMap(p => [p.price, p.vwap, p.ema50]).filter((v): v is number => typeof v === 'number')
  const lo = Math.min(...vals), hi = Math.max(...vals), span = hi - lo || 1
  const x = (i: number) => P + (i / (points.length - 1)) * (W - 2 * P)
  const y = (v: number) => H - P - ((v - lo) / span) * (H - 2 * P)
  const line = (key: 'price' | 'vwap' | 'ema50') => {
    const pts = points.map((p, i) => (typeof p[key] === 'number' ? `${x(i).toFixed(1)},${y(p[key] as number).toFixed(1)}` : null)).filter(Boolean)
    return pts.length > 1 ? pts.join(' ') : null
  }
  const idx = new Map(points.map((p, i) => [p.time, i]))
  const vwap = line('vwap'), ema = line('ema50')
  return (
    <figure className="chart">
      {header}
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${ticker} price chart, ${points.length} points, ${lo.toFixed(2)} to ${hi.toFixed(2)}`}>
        {vwap && <polyline fill="none" stroke="#ff9d3b" strokeWidth="1.2" points={vwap} />}
        {ema && <polyline fill="none" stroke="#ffe14d" strokeWidth="1.2" strokeDasharray="3 3" points={ema} />}
        <polyline fill="none" stroke="#9fb3ff" strokeWidth="1.6" points={line('price') ?? ''} />
        {marks.filter(m => idx.has(m.time)).map((m, i) => {
          const cx = x(idx.get(m.time)!), cy = y(m.price)
          const col = m.type === 'entry' ? (m.side === 'PUT' ? COLORS.PUT : m.side === 'CALL' ? COLORS.CALL : COLORS.NEUTRAL)
            : m.pnl == null ? COLORS.locked : m.pnl >= 0 ? COLORS.CALL : COLORS.PUT
          return m.type === 'entry'
            ? <polygon key={i} points={`${cx},${cy - 6} ${cx - 5},${cy + 4} ${cx + 5},${cy + 4}`} fill={col} stroke="#0b0830" />
            : <rect key={i} x={cx - 4} y={cy - 4} width="8" height="8" fill={col} stroke="#0b0830" />
        })}
      </svg>
      <div className="legend muted"><span style={{ color: '#9fb3ff' }}>price</span> <span style={{ color: '#ff9d3b' }}>VWAP</span> <span style={{ color: '#ffe14d' }}>EMA50</span> ▲ entry ■ exit</div>
    </figure>
  )
}

interface RowProps { ticks: Record<string, TickPoint[]>; marks: Record<string, Mark[]> }
function ChartsImpl({ ticks, marks }: RowProps) {
  return (
    <section className="charts" aria-label="Price charts">
      {TICKERS.map(t => <TickerChart key={t} ticker={t} points={ticks[t] ?? []} marks={marks[t] ?? []} />)}
    </section>
  )
}
export const Charts = memo(ChartsImpl)
