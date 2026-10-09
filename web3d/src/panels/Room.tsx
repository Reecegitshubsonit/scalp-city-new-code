import { useEffect, useRef } from 'react'
import type { BotEvent, BotRow } from '../model/types'
import type { Series } from '../model/history'
import { formatNum, formatPct, formatPnl, formatTime } from '../model/format'
import { headline } from '../model/headline'
import { plainReason } from '../model/reasons'
import { thoughtText } from '../model/thoughts'
import { stateIcon, stateLabel } from '../model/visual'
import { CandleChart } from './CandleChart'
import { idOf } from './Feed'

interface Props {
  row: BotRow
  events: BotEvent[]
  series: Series
  tickerTrades: number
  pending: boolean
  onClose: () => void
  onPause: (bot: string, paused: boolean) => void
  onInside?: () => void
}

const SIDE_NOTE = { explicit: 'from engine', signal: 'inferred from signal text', inferred: 'inferred from price vs level', none: '' } as const

export function Room({ row, events, series, tickerTrades, pending, onClose, onPause, onInside }: Props) {
  const closeRef = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    closeRef.current?.focus()
  }, [row.bot])
  const i = row.inputs
  const mine = events.filter(e => e.bot === row.bot).slice(0, 12)
  const pct = Math.min(100, Math.max(0, row.charge_pct ?? 0))
  return (
    <aside className="room" role="dialog" aria-label={`${row.bot} scanner`}>
      <header>
        <h2>{row.bot}</h2>
        <button ref={closeRef} onClick={onClose} aria-label="Close scanner">✕</button>
      </header>
      <CandleChart series={series} trades={tickerTrades} height={240} />
      {onInside && <button className="stepin" onClick={onInside}>Step inside the tower (3D room)</button>}
      <div className="scanner">
        <div className="sctitle">SIGNAL SCANNER</div>
        <div className="schead">{headline(row)}</div>
        <div className="scbar" aria-label={`charge ${formatPct(row.charge_pct)}`}>
          <span className={`fill ${row.side ?? 'none'}`} style={{ width: `${pct}%` }} />
          <b>{row.charge_pct == null ? 'NOT CHARGING' : `${Math.round(pct)}% CHARGED`}</b>
        </div>
        <p><span className="chip"><span aria-hidden="true">{stateIcon(row.state)}</span> {stateLabel(row.state)}</span> {plainReason(row.reason_code)}</p>
        <p className="muted">{row.reason_text} ({row.reason_code || '-'})</p>
        <h3>Thoughts</h3>
        <ol className="feed small">
          {mine.length === 0 && <li className="muted">No events for this bot yet.</li>}
          {mine.map(e => (
            <li key={idOf(e)} className={e.kind === 'trade_closed' ? ((e.pnl ?? 0) >= 0 ? 'win' : 'loss') : ''}><time>{formatTime(e.time)}</time> {thoughtText(e)}</li>
          ))}
        </ol>
      </div>
      <dl>
        <dt>Side</dt><dd>{row.side ?? '-'} {row.side && <small className="muted">({SIDE_NOTE[row.sideSource]})</small>}</dd>
        <dt>Day P&amp;L</dt><dd className={row.pnl_day > 0 ? 'pos' : row.pnl_day < 0 ? 'neg' : ''}>{formatPnl(row.pnl_day)}</dd>
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
      <button className="pause wide" disabled={pending} onClick={() => onPause(row.bot, !row.paused)}>
        {pending ? '...' : row.paused ? 'Resume' : 'Pause'} {row.bot}
      </button>
    </aside>
  )
}
