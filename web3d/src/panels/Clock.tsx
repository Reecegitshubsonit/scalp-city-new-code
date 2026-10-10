import { useNow } from '../hooks'
import { freshness, marketPhase } from '../model/format'
import type { Status } from '../net/socket'

const FRESH_TEXT = { live: 'LIVE', slow: 'SLOW', stale: 'STALE', closed: 'CLOSED', none: 'NO DATA' } as const

function hms(s: number) {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60
  return `${h}h ${String(m).padStart(2, '0')}m ${String(x).padStart(2, '0')}s`
}

export function Clock({ lastEventAt, dataTime, status, replayMs = null }: { lastEventAt: number | null; dataTime: string | null; status: Status; replayMs?: number | null }) {
  const realNow = useNow()
  const now = replayMs ?? realNow
  const phase = marketPhase(new Date(now))
  // websocket: age of the last event received; polling: age of the newest bar time in the snapshot
  const dataMs = dataTime ? Date.parse(dataTime) : NaN
  const age = status === 'polling'
    ? (Number.isNaN(dataMs) ? null : Math.max(0, Math.round((now - dataMs) / 1000)))
    : (lastEventAt == null ? null : Math.max(0, Math.round((now - lastEventAt) / 1000)))
  const online = status === 'live' || status === 'polling' || replayMs != null
  const f = online && replayMs == null ? freshness(age, phase) : 'none'
  const et = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(now)
  return (
    <section className="panel" aria-label="Market and data">
      <h2>Market</h2>
      <p><b>{et} ET</b> · {phase.label}{phase.phase !== 'closed' && <> · {hms(phase.seconds)}</>}</p>
      <p>Data: <span className={`fresh f-${f}`}>{replayMs != null ? 'REPLAY' : online ? FRESH_TEXT[f] : 'NO CONNECTION'}</span>
        {age != null && online && replayMs == null && <small className="muted"> {status === 'polling' ? 'last bar' : 'last event'} {age}s ago</small>}</p>
      <p className="muted">Open 9:30 ET, close 16:00 ET</p>
    </section>
  )
}
