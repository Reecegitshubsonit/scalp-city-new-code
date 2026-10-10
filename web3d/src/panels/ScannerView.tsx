import type { BotEvent, BotRow } from '../model/types'
import { formatPct, formatTime } from '../model/format'
import { headline } from '../model/headline'
import { plainReason } from '../model/reasons'
import { thoughtText } from '../model/thoughts'
import { stateIcon, stateLabel } from '../model/visual'
import { idOf } from './Feed'

/** Signal scanner for one bot: headline, charge bar, state, and its latest thoughts in plain sentences. */
export function ScannerView({ row, events, limit = 12 }: { row: BotRow; events: BotEvent[]; limit?: number }) {
  const mine = events.filter(e => e.bot === row.bot).slice(0, limit)
  const pct = Math.min(100, Math.max(0, row.charge_pct ?? 0))
  return (
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
  )
}
