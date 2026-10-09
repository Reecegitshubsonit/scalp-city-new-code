import { useEffect, useRef } from 'react'
import type { BotRow, TradeRec } from '../model/types'
import { daySummary } from '../model/summary'
import { formatPnl, formatTime } from '../model/format'

interface Props { rows: BotRow[]; trades: TradeRec[]; date: string | null; onClose: () => void }

export function Summary({ rows, trades, date, onClose }: Props) {
  const s = daySummary(rows, trades)
  const ref = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    ref.current?.focus()
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [onClose])
  const max = Math.max(1, ...Object.values(s.byTicker).map(Math.abs))
  return (
    <div className="modal" role="dialog" aria-label="Day summary">
      <div className="sumcard">
        <header>
          <span className="muted">{date ?? 'TODAY'} · day summary</span>
          <button ref={ref} onClick={onClose} aria-label="Close summary">Close</button>
        </header>
        <div className={`bigpnl ${s.total > 0 ? 'pos' : s.total < 0 ? 'neg' : ''}`}>{formatPnl(s.total)}</div>
        <div className="goal" aria-label={`Goal ${s.goalPct.toFixed(0)} percent`}>
          <div className="bar"><span className="fill CALL" style={{ width: `${s.goalPct}%` }} /></div>
          <small className="muted">{s.goalPct.toFixed(0)}% of {formatPnl(s.goal).replace('+', '')} goal</small>
        </div>
        <div className="tbars">
          {Object.entries(s.byTicker).map(([t, v]) => (
            <div key={t} className="tbar">
              <span className="tbv"><b className={v > 0 ? 'pos' : v < 0 ? 'neg' : ''}>{formatPnl(v)}</b></span>
              <span className="tbcol"><span className={v >= 0 ? 'up' : 'down'} style={{ height: `${Math.max(2, (Math.abs(v) / max) * 100)}%` }} /></span>
              <span>{t}</span>
            </div>
          ))}
        </div>
        <p>{s.top ? <>Top worker <b>{s.top.bot}</b> <b className="pos">{formatPnl(s.top.pnl)}</b></> : <span className="muted">No profitable bot yet</span>}</p>
        <p className="muted">{s.trades} trades · {s.closed ? `${s.wins} of ${s.closed} wins since page load (${s.winRate!.toFixed(0)}%)` : 'no closed trades since page load'}</p>
        <ol className="feed">
          {trades.slice(-8).reverse().map((t, i) => (
            <li key={i} className={t.pnl >= 0 ? 'win' : 'loss'}><time>{formatTime(t.time)}</time> <b>{t.bot}</b> {t.pnl >= 0 ? 'profit locked' : 'stopped out'} <b>{formatPnl(t.pnl)}</b></li>
          ))}
        </ol>
      </div>
    </div>
  )
}
