import { formatPnl, formatTime } from '../model/format'
import { plainReason } from '../model/reasons'
import type { Trade } from '../model/trades'

interface Props { label: string; pnl: number; count: number; wins: number; lines?: Trade[]; active?: boolean; onClick?: () => void }

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
export function dayLabel(day: string): string {
  const [y, m, d] = day.split('-').map(Number)
  return `${DAYS[new Date(Date.UTC(y, m - 1, d)).getUTCDay()]} ${m}/${d}`
}

/** "EARNED · Fri 10/9, +$1,016, 3 trades, 100% win rate" with the latest trades underneath. */
export function EarnedCard({ label, pnl, count, wins, lines = [], active, onClick }: Props) {
  const body = (
    <>
      <div className="earnedhead">EARNED · {label}</div>
      <div className={`earnedpnl ${pnl > 0 ? 'pos' : pnl < 0 ? 'neg' : ''}`}>{formatPnl(pnl)}</div>
      <div className="muted">{count} trades · {wins} wins · {count ? Math.round((wins / count) * 100) : 0}% win rate</div>
      {lines.length > 0 && (
        <ul className="earnedlines">
          {lines.slice(-4).reverse().map((t, i) => (
            <li key={i} className={t.pnl >= 0 ? 'win' : 'loss'}>{formatTime(t.exit_time).slice(0, 5)} {t.bot} {t.pnl >= 0 ? 'profit locked' : plainReason(t.exit_code ?? '').replace('Exit: ', '').toLowerCase()} {formatPnl(t.pnl)}</li>
          ))}
        </ul>
      )}
    </>
  )
  return onClick
    ? <button className={`earned${active ? ' active' : ''}`} onClick={onClick} aria-pressed={active}>{body}</button>
    : <div className="earned">{body}</div>
}
