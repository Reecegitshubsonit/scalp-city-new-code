import { memo } from 'react'
import type { TradeRec } from '../model/types'
import { formatPnl, formatTime } from '../model/format'

function TapeImpl({ trades }: { trades: TradeRec[] }) {
  const recent = trades.slice(-14).reverse()
  return (
    <section className="tape" aria-label="Recent trades">
      <span className="muted">Trades</span>
      {recent.length === 0 && <span className="muted">none yet</span>}
      {recent.map((t, i) => (
        <span key={`${t.time}-${t.bot}-${i}`} className={`tchip ${t.pnl >= 0 ? 'win' : 'loss'}`}>
          {formatTime(t.time).slice(0, 5)} {t.bot} <b>{formatPnl(t.pnl)}</b>
        </span>
      ))}
    </section>
  )
}
export const Tape = memo(TapeImpl)
