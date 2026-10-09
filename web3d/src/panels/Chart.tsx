import type { Mark, TickPoint } from '../model/types'

export function Chart({ points, marks, ticker }: { points: TickPoint[]; marks: Mark[]; ticker: string }) {
  if (points.length < 2) return <p className="muted">Chart fills as prices arrive (since page load).</p>
  const W = 300, H = 120, P = 6
  const prices = points.map(p => p.price)
  const lo = Math.min(...prices), hi = Math.max(...prices)
  const span = hi - lo || 1
  const x = (i: number) => P + (i / (points.length - 1)) * (W - 2 * P)
  const y = (v: number) => H - P - ((v - lo) / span) * (H - 2 * P)
  const idxOf = (t: string) => { const i = points.findIndex(p => p.time === t); return i < 0 ? points.length - 1 : i }
  const visible = marks.filter(m => points.some(p => p.time === m.time))
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${ticker} price, ${points.length} points, ${lo.toFixed(2)} to ${hi.toFixed(2)}`}>
        <polyline fill="none" stroke="#9fb3ff" strokeWidth="1.5" points={points.map((p, i) => `${x(i)},${y(p.price)}`).join(' ')} />
        {visible.map((m, i) => (
          <g key={i}>
            {m.type === 'entry'
              ? <polygon points={`${x(idxOf(m.time))},${y(m.price) - 6} ${x(idxOf(m.time)) - 5},${y(m.price) + 4} ${x(idxOf(m.time)) + 5},${y(m.price) + 4}`} fill="#19f5a0" />
              : <rect x={x(idxOf(m.time)) - 4} y={y(m.price) - 4} width="8" height="8" fill="#ffb020" />}
          </g>
        ))}
      </svg>
      <figcaption className="muted">{ticker} {lo.toFixed(2)} - {hi.toFixed(2)} · ▲ entry ■ exit</figcaption>
    </figure>
  )
}
