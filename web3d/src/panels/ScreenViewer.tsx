import { useEffect, useRef } from 'react'
import type { Series } from '../model/history'
import { formatPnl } from '../model/format'
import type { BotEvent, BotRow } from '../model/types'
import type { Trade } from '../model/trades'
import { earnedLines } from '../model/lab'
import { EarnedCard } from './EarnedCard'
import type { Status } from '../net/socket'
import { Clock } from './Clock'
import { Heatmap } from './Heatmap'
import { Leaderboard } from './Leaderboard'
import { ScannerView } from './ScannerView'
import { ZoomChart } from './ZoomChart'
import { botOfScreen } from '../model/tower'

export const screenTitle = (screen: string, ticker: string, bot?: string): string => ({
  scan0: `${bot ?? 'Bot'} scanner`, scan1: `${bot ?? 'Bot'} scanner`, scan2: `${bot ?? 'Bot'} scanner`,
  chart: `${ticker} chart with trades`, chart1m: `${ticker} 1-minute chart`, board: `${ticker} bots: heatmap and leaderboard`,
  plaque: `Market and ${ticker} day total`, earned: `${ticker} earned: closed trades`,
} as Record<string, string>)[screen] ?? screen

interface Props {
  screen: string
  ticker: string
  series: Series
  tradeCount: number
  tickerRows: BotRow[]
  feed: BotEvent[]
  earned: { label: string; pnl: number; count: number; wins: number; trades: Trade[] }
  tickerPnl: number
  lastEventAt: number | null
  dataTime: string | null
  status: Status
  onSelectBot: (bot: string) => void
  onClose: () => void
}

/** Full-size, crisp version of one wall screen of a tower room (one ticker only), opened by clicking that screen. */
export function ScreenViewer(p: Props) {
  const closeRef = useRef<HTMLButtonElement>(null)
  useEffect(() => { closeRef.current?.focus() }, [p.screen])
  const row = botOfScreen(p.screen, p.tickerRows)
  const ranked = [...p.tickerRows].sort((a, b) => b.pnl_day - a.pnl_day)
  const title = screenTitle(p.screen, p.ticker, row?.bot)
  const chartH = Math.max(300, Math.min(620, Math.round(window.innerHeight * 0.62)))
  return (
    <div className="modal screenmodal" role="dialog" aria-label={title}>
      <div className="sumcard bigcard">
        <header>
          <h2>{title}</h2>
          <button ref={closeRef} onClick={p.onClose} aria-label="Close screen (Esc)">Close (Esc)</button>
        </header>
        {(p.screen === 'chart' || p.screen === 'chart1m') && <ZoomChart series={p.series} trades={p.tradeCount} height={chartH} />}
        {p.screen === 'earned' && (
          <div className="twocol">
            <EarnedCard label={p.earned.label} pnl={p.earned.pnl} count={p.earned.count} wins={p.earned.wins} lines={p.earned.trades} />
            <ol className="feed small">
              {earnedLines(p.earned.trades, 200).map((l, i) => <li key={i} className={l.includes('-$') ? 'loss' : 'win'}>{l}</li>)}
              {p.earned.trades.length === 0 && <li className="muted">No closed trades yet.</li>}
            </ol>
          </div>
        )}
        {row && (
          <>
            <label className="muted">Bot{' '}
              <select value={row.bot} onChange={e => p.onSelectBot(e.target.value)}>
                {p.tickerRows.map(r => <option key={r.bot} value={r.bot}>{r.bot}</option>)}
              </select>
            </label>
            <ScannerView row={row} events={p.feed} limit={40} />
          </>
        )}
        {p.screen === 'board' && (
          <div className="twocol">
            <Heatmap rows={p.tickerRows} onSelect={p.onSelectBot} title={`${p.ticker} bots today`} />
            <Leaderboard rows={ranked} onSelect={p.onSelectBot} />
          </div>
        )}
        {p.screen === 'plaque' && (
          <div className="twocol">
            <Clock lastEventAt={p.lastEventAt} dataTime={p.dataTime} status={p.status} />
            <section className="panel">
              <h2>{p.ticker} day total</h2>
              <div className={`bigpnl ${p.tickerPnl > 0 ? 'pos' : p.tickerPnl < 0 ? 'neg' : ''}`}>{formatPnl(p.tickerPnl)}</div>
              <small className="muted">{p.earned.count} closed trades · {p.tickerRows.length} bots</small>
            </section>
          </div>
        )}
      </div>
    </div>
  )
}
