import { useNow } from '../hooks'
import { freshness, marketPhase } from '../model/format'
import type { Status } from '../net/socket'

const FRESH_TEXT = { live: 'LIVE', slow: 'SLOW', stale: 'STALE', closed: 'CLOSED', none: 'NO DATA' } as const

function hms(s: number) {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60
  return `${h}h ${String(m).padStart(2, '0')}m ${String(x).padStart(2, '0')}s`
}

export function Clock({ lastEventAt, status }: { lastEventAt: number | null; status: Status }) {
  const now = useNow()
  const phase = marketPhase(new Date(now))
  const age = lastEventAt == null ? null : Math.max(0, Math.round((now - lastEventAt) / 1000))
  const f = status === 'live' ? freshness(age, phase) : 'none'
  const et = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(now)
  return (
    <section className="panel" aria-label="Market and data">
      <h2>Market</h2>
      <p><b>{et} ET</b> · {phase.label}{phase.phase !== 'closed' && <> · {hms(phase.seconds)}</>}</p>
      <p>Data: <span className={`fresh f-${f}`}>{status === 'live' ? FRESH_TEXT[f] : 'NO CONNECTION'}</span>
        {age != null && status === 'live' && <small className="muted"> last event {age}s ago</small>}</p>
      <p className="muted">Open 9:30 ET, close 16:00 ET</p>
    </section>
  )
}
