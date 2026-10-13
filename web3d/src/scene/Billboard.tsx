import { memo } from 'react'
import type { Badge, Tone } from '../model/badge'
import { formatPnl } from '../model/format'
import { COLORS, stateLabel } from '../model/visual'

const TONE_COLOR: Record<Tone, string> = {
  CALL: COLORS.CALL, PUT: COLORS.PUT, WIN: COLORS.CALL, LOSS: COLORS.PUT, NEUTRAL: COLORS.NEUTRAL,
  LOCKED: COLORS.locked, GOAL: COLORS.goal, LOSS_LIMIT: COLORS.lossLimit, PAUSED: COLORS.paused, STALE: COLORS.stale,
}

interface Props { closes: number[]; badge: Badge | null; state: string; pnl: number }

/** Small floating card on a tower: sparkline of the ticker, current status and the bot's day P&L. */
function BillboardImpl({ closes, badge, state, pnl }: Props) {
  const W = 104, H = 30
  const pts = closes.slice(-40)
  let path = ''
  if (pts.length > 1) {
    const lo = Math.min(...pts), hi = Math.max(...pts), span = hi - lo || 1
    path = pts.map((v, i) => `${((i / (pts.length - 1)) * (W - 4) + 2).toFixed(1)},${(H - 3 - ((v - lo) / span) * (H - 6)).toFixed(1)}`).join(' ')
  }
  const up = pts.length > 1 && pts[pts.length - 1] >= pts[0]
  const color = badge ? TONE_COLOR[badge.tone] : '#8a90c8'
  return (
    <div className="bb" style={{ borderColor: color }}>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} aria-hidden="true">
        {path && <polyline fill="none" stroke={up ? COLORS.CALL : COLORS.PUT} strokeWidth="1.6" points={path} />}
      </svg>
      <div className="bbtext" style={{ color }}>{badge ? badge.text : stateLabel(state).toUpperCase()}</div>
      <div className={`bbpnl ${pnl > 0 ? 'pos' : pnl < 0 ? 'neg' : ''}`}>{formatPnl(pnl)}</div>
    </div>
  )
}
export const Billboard = memo(BillboardImpl)
