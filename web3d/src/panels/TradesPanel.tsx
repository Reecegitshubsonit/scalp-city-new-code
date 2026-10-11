import { useMemo, useState } from 'react'
import { formatNum, formatPnl, formatTime } from '../model/format'
import type { Day } from '../model/replay'
import { plainReason } from '../model/reasons'
import { filterTrades, tradeStats, tradesToCsv, type Trade, type TradeFilter } from '../model/trades'
import { ALL_BOTS, TICKERS } from '../model/layout'
import { dayLabel, EarnedCard } from './EarnedCard'

interface Props {
  days: Day[]
  viewKey: string                       // `${day}|${mode}` being shown
  onViewDay: (day: Day) => void
  trades: Trade[]                       // trades of the viewed day
  isCurrent: boolean
  enginePnl: number | null              // the engine's own day total, to flag a mismatch
  supported: boolean
  onOpenBot: (bot: string) => void
  onReplay: (day: Day) => void
}

function downloadCsv(name: string, csv: string) {
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
  const a = document.createElement('a')
  a.href = url; a.download = name; a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function TradesPanel({ days, viewKey, onViewDay, trades, isCurrent, enginePnl, supported, onOpenBot, onReplay }: Props) {
  const [bot, setBot] = useState('')
  const [ticker, setTicker] = useState('')
  const [result, setResult] = useState<'' | 'win' | 'loss'>('')
  const filter: TradeFilter = { bot: bot || undefined, ticker: ticker || undefined, result: result || undefined }
  const shown = useMemo(() => filterTrades(trades, filter).slice().reverse(), [trades, bot, ticker, result]) // eslint-disable-line react-hooks/exhaustive-deps
  const all = tradeStats(trades)
  const sel = tradeStats(shown)
  const [dayStr] = viewKey.split('|')
  const viewDay = days.find(d => `${d.day}|${d.mode}` === viewKey)
  const mismatch = isCurrent && enginePnl != null && trades.length > 0 && Math.abs(enginePnl - all.pnl) > 0.01
  return (
    <section className="panel trades" aria-label="Trades">
      <header className="tradeshead">
        <h2>Trades</h2>
        <label>Day{' '}
          <select value={viewKey} onChange={e => { const d = days.find(x => `${x.day}|${x.mode}` === e.target.value); if (d) onViewDay(d) }}>
            {!viewDay && <option value={viewKey}>{dayStr}</option>}
            {days.map(d => <option key={`${d.day}|${d.mode}`} value={`${d.day}|${d.mode}`}>{d.day} ({d.mode})</option>)}
          </select>
        </label>
        <label>Bot{' '}
          <select value={bot} onChange={e => setBot(e.target.value)}><option value="">All</option>{ALL_BOTS.map(b => <option key={b}>{b}</option>)}</select>
        </label>
        <label>Ticker{' '}
          <select value={ticker} onChange={e => setTicker(e.target.value)}><option value="">All</option>{TICKERS.map(t => <option key={t}>{t}</option>)}</select>
        </label>
        <label>Result{' '}
          <select value={result} onChange={e => setResult(e.target.value as '' | 'win' | 'loss')}><option value="">All</option><option value="win">Wins</option><option value="loss">Losses</option></select>
        </label>
        <button onClick={() => downloadCsv(`trades-${dayStr}.csv`, tradesToCsv(shown.slice().reverse()))} disabled={!shown.length}>Download CSV</button>
        {viewDay && <button onClick={() => onReplay(viewDay)}>Replay this day</button>}
      </header>
      {!supported && <p className="muted">This engine has no /trades endpoint; showing only trades seen since the page loaded. Restart the engine with the latest code.</p>}
      <div className="earnedrow">
        <EarnedCard label={dayLabel(dayStr)} pnl={all.pnl} count={all.count} wins={all.wins} lines={trades} />
        <div className="tradestats">
          <div>Showing <b>{sel.count}</b> of {all.count} trades · <b className={sel.pnl > 0 ? 'pos' : sel.pnl < 0 ? 'neg' : ''}>{formatPnl(sel.pnl)}</b>{sel.winRate != null && <> · {Math.round(sel.winRate)}% wins</>}</div>
          {all.best && <div className="muted">Best {all.best.bot} <span className="pos">{formatPnl(all.best.pnl)}</span> · worst {all.worst!.bot} <span className="neg">{formatPnl(all.worst!.pnl)}</span></div>}
          {mismatch && <div className="warn" role="note">Engine day P&amp;L is {formatPnl(enginePnl!)} but the logged trades add up to {formatPnl(all.pnl)} (difference {formatPnl(enginePnl! - all.pnl)}). An engine restart earlier in the day can reset a bot's running total.</div>}
        </div>
      </div>
      <div className="tablewrap">
        <table>
          <thead><tr><th>Closed</th><th>Bot</th><th>Side</th><th>Contract</th><th>Qty</th><th>Entry</th><th>Exit</th><th>Why it closed</th><th className="num">P&amp;L</th><th className="num">Day P&amp;L</th></tr></thead>
          <tbody>
            {shown.length === 0 && <tr><td colSpan={10} className="muted">No trades for this selection.</td></tr>}
            {shown.map((t, i) => (
              <tr key={`${t.bot}-${t.exit_time}-${i}`} className={t.pnl >= 0 ? 'win' : 'loss'}>
                <td>{formatTime(t.exit_time).slice(0, 5)}</td>
                <td><button className="link" onClick={() => onOpenBot(t.bot)}>{t.bot}</button></td>
                <td>{t.side ?? '-'}</td>
                <td className="mono">{t.contract ?? '-'}</td>
                <td>{t.qty ?? '-'}</td>
                <td>{t.entry_time ? `${formatTime(t.entry_time).slice(0, 5)} @ ${formatNum(t.entry_price)}` : '-'}</td>
                <td>{formatNum(t.exit_price)}</td>
                <td>{t.exit_code ? plainReason(t.exit_code) : '-'}</td>
                <td className={`num ${t.pnl >= 0 ? 'pos' : 'neg'}`}><b>{formatPnl(t.pnl)}</b></td>
                <td className="num">{t.pnl_day == null ? '-' : formatPnl(t.pnl_day)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
