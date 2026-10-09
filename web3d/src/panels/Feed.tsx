import { memo } from 'react'
import type { BotEvent } from '../model/types'
import { formatTime } from '../model/format'
import { thoughtText } from '../model/thoughts'
import { stateLabel } from '../model/visual'

const ids = new WeakMap<object, number>()
let nextId = 0
export const idOf = (e: BotEvent) => {
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
          <li key={idOf(e)} className={e.kind === 'trade_closed' ? (e.pnl ?? 0) >= 0 ? 'win' : 'loss' : ''}>
            <time>{formatTime(e.time)}</time> <b>{e.bot}</b> <span className="muted">[{e.state ? stateLabel(e.state) : e.kind}]</span>{' '}
            {thoughtText(e)}
          </li>
        ))}
      </ol>
    </section>
  )
}
export const Feed = memo(FeedImpl)
