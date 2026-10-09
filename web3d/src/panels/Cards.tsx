import type { BotRow } from '../model/types'
import { formatNum, formatPct, formatPnl, formatTime } from '../model/format'
import { plainReason } from '../model/reasons'
import { stateIcon, stateLabel } from '../model/visual'

interface Props {
  rows: BotRow[]
  selected: string | null
  pending: Record<string, boolean>
  onSelect: (bot: string) => void
  onPause: (bot: string, paused: boolean) => void
}

export function Cards({ rows, selected, pending, onSelect, onPause }: Props) {
  return (
    <section className="cards" aria-label="Bots">
      {rows.map(r => {
        const isPending = r.bot in pending
        return (
          <article key={r.bot} className={`card st-${r.state}${selected === r.bot ? ' sel' : ''}`}>
            <button className="cardmain" aria-pressed={selected === r.bot} onClick={() => onSelect(r.bot)}>
              <span className="cardhead">
                <strong>{r.bot}</strong>
                <span className="chip"><span aria-hidden="true">{stateIcon(r.state)}</span> {stateLabel(r.state)}</span>
              </span>
              <span className="reason">{plainReason(r.reason_code)}</span>
              <span className="reasontext">{r.reason_text} <small>({r.reason_code || '-'})</small></span>
              <span className="charge" aria-label={`charge ${formatPct(r.charge_pct)}`}>
                <span className="bar"><span style={{ width: `${Math.min(100, Math.max(0, r.charge_pct ?? 0))}%` }} className={`fill ${r.side ?? 'none'}`} /></span>
                <span>{formatPct(r.charge_pct)}</span>
              </span>
              <span className="nums">
                <span>Price <b>{formatNum(r.inputs.price)}</b></span>
                <span>Day <b className={r.pnl_day > 0 ? 'pos' : r.pnl_day < 0 ? 'neg' : ''}>{formatPnl(r.pnl_day)}</b></span>
                <span>Trades <b>{r.trades}</b></span>
                <span>Side <b>{r.side ?? '-'}</b></span>
                <span>Upd <b>{formatTime(r.time)}</b></span>
              </span>
            </button>
            <button className="pause" disabled={isPending} onClick={() => onPause(r.bot, !r.paused)}>
              {isPending ? '...' : r.paused ? 'Resume' : 'Pause'}
            </button>
          </article>
        )
      })}
    </section>
  )
}
