import { memo } from 'react'
import type { BotEvent } from '../model/types'
import { formatPnl, formatTime } from '../model/format'
import { plainReason } from '../model/reasons'
import { stateLabel } from '../model/visual'

const ids = new WeakMap<object, number>()
let nextId = 0
const idOf = (e: BotEvent) => {
  let v = ids.get(e)
  if (v === undefined) { v = ++nextId; ids.set(e, v) }
  return v
}

function FeedImpl({ events }: { events: BotEvent[] }) {
  return (
    <section className="panel" aria-label="Thoughts">
      <h2>Thoughts</h2>
      <ol className="feed">
        {events.length === 0 && <li className="muted">Nothing yet.</li>}
        {events.map(e => (
          <li key={idOf(e)}>
            <time>{formatTime(e.time)}</time> <b>{e.bot}</b> <span className="kind">{e.kind}</span>{' '}
            {e.state && <span>{stateLabel(e.state)}: </span>}
            {plainReason(e.reason_code)}
            {typeof e.pnl === 'number' && <b className={e.pnl >= 0 ? 'pos' : 'neg'}> {formatPnl(e.pnl)}</b>}
            {e.reason_text && <small className="muted"> {e.reason_text}</small>}
          </li>
        ))}
      </ol>
    </section>
  )
}

export const Feed = memo(FeedImpl)
