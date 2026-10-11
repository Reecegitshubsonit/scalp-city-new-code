import { useEffect, useRef } from 'react'
import type { Series } from '../model/history'
import { daySummary } from '../model/summary'
import { formatPnl } from '../model/format'
import type { BotEvent, BotRow, TradeRec } from '../model/types'
import type { Trade } from '../model/trades'
import { earnedLines } from '../model/lab'
import { EarnedCard } from './EarnedCard'
import type { Status } from '../net/socket'
import { Clock } from './Clock'
import { Heatmap } from './Heatmap'
import { Leaderboard } from './Leaderboard'
import { ScannerView } from './ScannerView'
import { ZoomChart } from './ZoomChart'

export const SCREEN_TITLES: Record<string, string> = {
  SPY: 'SPY 1-minute chart', QQQ: 'QQQ 1-minute chart', IWM: 'IWM 1-minute chart',
  scanner: 'Signal scanner', board: 'Worker heatmap and leaderboard', plaque: 'Market and day total',
  chart1m: '1-minute chart of the selected bot', earned: 'Earned: closed trades',
}

interface Props {
  screen: string
  series: Record<string, Series>
  tickerTrades: Record<string, number>
  rows: BotRow[]
  board: BotRow[]
  feed: BotEvent[]
  trades: TradeRec[]
  selectedBot: string | null
  earned: { label: string; pnl: number; count: number; wins: number; trades: Trade[] }
  total: number
  lastEventAt: number | null
  dataTime: string | null
  status: Status
  onSelectBot: (bot: string) => void
  onClose: () => void
}

/** Full-size, crisp version of one wall screen of the 3D room, opened by clicking that screen. */
export function ScreenViewer(p: Props) {
  const closeRef = useRef<HTMLButtonElement>(null)
  useEffect(() => { closeRef.current?.focus() }, [p.screen])
  const row = p.rows.find(r => r.bot === p.selectedBot) ?? p.rows[0]
  const sum = daySummary(p.rows, p.trades)
  return (
    <div className="modal screenmodal" role="dialog" aria-label={SCREEN_TITLES[p.screen] ?? p.screen}>
      <div className="sumcard bigcard">
        <header>
          <h2>{SCREEN_TITLES[p.screen] ?? p.screen}</h2>
          <button ref={closeRef} onClick={p.onClose} aria-label="Close screen (Esc)">Close (Esc)</button>
        </header>
        {['SPY', 'QQQ', 'IWM'].includes(p.screen) && p.series[p.screen] &&
          <ZoomChart series={p.series[p.screen]} trades={p.tickerTrades[p.screen] ?? 0} height={Math.max(300, Math.min(620, Math.round(window.innerHeight * 0.62)))} />}
        {p.screen === 'chart1m' && row && p.series[row.ticker] &&
          <ZoomChart series={p.series[row.ticker]} trades={p.tickerTrades[row.ticker] ?? 0} height={Math.max(300, Math.min(620, Math.round(window.innerHeight * 0.62)))} />}
        {p.screen === 'earned' && (
          <div className="twocol">
            <EarnedCard label={p.earned.label} pnl={p.earned.pnl} count={p.earned.count} wins={p.earned.wins} lines={p.earned.trades} />
            <ol className="feed small">
              {earnedLines(p.earned.trades, 200).map((l, i) => <li key={i} className={l.includes('-$') ? 'loss' : 'win'}>{l}</li>)}
              {p.earned.trades.length === 0 && <li className="muted">No closed trades yet.</li>}
            </ol>
          </div>
        )}
        {p.screen === 'scanner' && row && (
          <>
            <label className="muted">Bot{' '}
              <select value={row.bot} onChange={e => p.onSelectBot(e.target.value)}>
                {p.rows.map(r => <option key={r.bot} value={r.bot}>{r.bot}</option>)}
              </select>
            </label>
            <ScannerView row={row} events={p.feed} limit={40} />
          </>
        )}
        {p.screen === 'board' && (
          <div className="twocol">
            <Heatmap rows={p.rows} onSelect={p.onSelectBot} />
            <Leaderboard rows={p.board} onSelect={p.onSelectBot} />
          </div>
        )}
        {p.screen === 'plaque' && (
          <div className="twocol">
            <Clock lastEventAt={p.lastEventAt} dataTime={p.dataTime} status={p.status} />
            <section className="panel">
              <h2>Day total</h2>
              <div className={`bigpnl ${p.total > 0 ? 'pos' : p.total < 0 ? 'neg' : ''}`}>{formatPnl(p.total)}</div>
              <div className="bar"><span className="fill CALL" style={{ width: `${sum.goalPct}%` }} /></div>
              <small className="muted">{sum.goalPct.toFixed(0)}% of the $5,000 goal · {sum.trades} trades</small>
            </section>
          </div>
        )}
      </div>
    </div>
  )
}
