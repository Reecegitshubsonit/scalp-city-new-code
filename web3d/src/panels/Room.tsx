import { useEffect, useRef } from 'react'
import type { BotEvent, BotRow } from '../model/types'
import type { Series } from '../model/history'
import { formatNum, formatPnl, formatTime } from '../model/format'
import { CandleChart } from './CandleChart'
import { ScannerView } from './ScannerView'
import { stateIcon, stateLabel } from '../model/visual'
import type { Trade } from '../model/trades'

interface Props {
  row: BotRow
  events: BotEvent[]
  series: Series
  tickerTrades: number
  pending: boolean
  onClose: () => void
  onPause: (bot: string, paused: boolean) => void
  onInside?: () => void
  siblings: BotRow[]
  recent: Trade[]
  onSelectBot: (bot: string) => void
}

const SIDE_NOTE = { explicit: 'from engine', signal: 'inferred from signal text', inferred: 'inferred from price vs level', none: '' } as const

export function Room({ row, events, series, tickerTrades, pending, onClose, onPause, onInside, siblings, recent, onSelectBot }: Props) {
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
      <section className="tickerbots" aria-label={`${row.ticker} bots today`}>
        <h3>{row.ticker} bots today</h3>
        <ul>
          {siblings.map(b => (
            <li key={b.bot}>
              <button className={b.bot === row.bot ? 'active' : ''} aria-pressed={b.bot === row.bot} onClick={() => onSelectBot(b.bot)}>
                <span>{b.bot.split('-')[1]} <small className="muted">{stateIcon(b.state)} {stateLabel(b.state)}</small></span>
                <b className={b.pnl_day > 0 ? 'pos' : b.pnl_day < 0 ? 'neg' : ''}>{formatPnl(b.pnl_day)}</b>
              </button>
            </li>
          ))}
        </ul>
        <h3>{row.ticker} recent trades</h3>
        <ul className="earnedlines">
          {recent.length === 0 && <li className="muted">No closed trades yet.</li>}
          {recent.slice(-6).reverse().map((t, i) => (
            <li key={i} className={t.pnl >= 0 ? 'win' : 'loss'}>{formatTime(t.exit_time).slice(0, 5)} {t.bot.split('-')[1]} {formatPnl(t.pnl)}</li>
          ))}
        </ul>
      </section>
      <ScannerView row={row} events={events} />
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
