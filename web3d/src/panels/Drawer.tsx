import { useEffect, useRef } from 'react'
import type { BotRow, Mark, TickPoint } from '../model/types'
import { formatNum, formatPct, formatPnl, formatTime } from '../model/format'
import { plainReason } from '../model/reasons'
import { stateIcon, stateLabel } from '../model/visual'
import { Chart } from './Chart'

interface Props {
  row: BotRow
  ticks: TickPoint[]
  marks: Mark[]
  pending: boolean
  onClose: () => void
  onPause: (bot: string, paused: boolean) => void
}

const SIDE_NOTE = { explicit: 'from engine', signal: 'inferred from signal text', inferred: 'inferred from price vs level', none: '' } as const

export function Drawer({ row, ticks, marks, pending, onClose, onPause }: Props) {
  const closeRef = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    closeRef.current?.focus()
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [row.bot, onClose])
  const i = row.inputs
  return (
    <aside className="drawer" role="dialog" aria-label={`${row.bot} details`}>
      <header>
        <h2>{row.bot}</h2>
        <button ref={closeRef} onClick={onClose} aria-label="Close details">✕</button>
      </header>
      <p><span className="chip"><span aria-hidden="true">{stateIcon(row.state)}</span> {stateLabel(row.state)}</span></p>
      <p>{plainReason(row.reason_code)}</p>
      <p className="muted">{row.reason_text} ({row.reason_code || '-'})</p>
      <dl>
        <dt>Charge</dt><dd>{formatPct(row.charge_pct)}</dd>
        <dt>Side</dt><dd>{row.side ?? '-'} {row.side && <small className="muted">({SIDE_NOTE[row.sideSource]})</small>}</dd>
        <dt>Day P&amp;L</dt><dd>{formatPnl(row.pnl_day)}</dd>
        <dt>Trades</dt><dd>{row.trades}</dd>
        <dt>Updated</dt><dd>{formatTime(row.time)}</dd>
      </dl>
      <h3>Inputs</h3>
      <dl>
        <dt>Price</dt><dd>{formatNum(i.price)}</dd>
        <dt>VWAP</dt><dd>{formatNum(i.vwap)}</dd>
        <dt>EMA9</dt><dd>{formatNum(i.ema9)}</dd>
        <dt>EMA21</dt><dd>{formatNum(i.ema21)}</dd>
        <dt>EMA50</dt><dd>{formatNum(i.ema50)}</dd>
        <dt>ATR</dt><dd>{formatNum(i.atr, 3)}</dd>
        <dt>Distance (ATR)</dt><dd>{formatNum(i.distance_atr, 3)}</dd>
      </dl>
      <h3>{row.ticker} chart</h3>
      <Chart points={ticks} marks={marks} ticker={row.ticker} />
      <button className="pause wide" disabled={pending} onClick={() => onPause(row.bot, !row.paused)}>
        {pending ? '...' : row.paused ? 'Resume' : 'Pause'} {row.bot}
      </button>
    </aside>
  )
}
