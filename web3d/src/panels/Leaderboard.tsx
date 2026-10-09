import type { BotRow } from '../model/types'
import { formatPnl } from '../model/format'

export function Leaderboard({ rows, onSelect }: { rows: BotRow[]; onSelect: (bot: string) => void }) {
  return (
    <section className="panel" aria-label="Leaderboard">
      <h2>Leaderboard</h2>
      <ol className="lb">
        {rows.map((r, i) => (
          <li key={r.bot}>
            <button onClick={() => onSelect(r.bot)}>
              <span>{i + 1}. {r.bot}</span>
              <b className={r.pnl_day > 0 ? 'pos' : r.pnl_day < 0 ? 'neg' : ''}>{formatPnl(r.pnl_day)}</b>
            </button>
          </li>
        ))}
      </ol>
    </section>
  )
}
