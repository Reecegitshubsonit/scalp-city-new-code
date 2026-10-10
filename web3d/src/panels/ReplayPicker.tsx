import { useEffect, useRef, useState } from 'react'
import { fetchDays } from '../net/api'
import type { Day } from '../model/replay'
import { formatTime } from '../model/format'

interface Props { loading: boolean; error: string | null; onPick: (d: Day) => void; onClose: () => void }

export function ReplayPicker({ loading, error, onPick, onClose }: Props) {
  const [days, setDays] = useState<Day[] | null | undefined>(undefined)
  const [err, setErr] = useState<string | null>(null)
  const closeRef = useRef<HTMLButtonElement>(null)
  useEffect(() => { closeRef.current?.focus(); fetchDays().then(setDays).catch(e => setErr((e as Error).message)) }, [])
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [onClose])
  return (
    <div className="modal" role="dialog" aria-label="Replay a past day">
      <div className="sumcard">
        <header><h2>Replay a past day</h2><button ref={closeRef} onClick={onClose}>Close</button></header>
        <p className="muted">Plays the engine's logged events through the same city and panels. Live data keeps running in the background.</p>
        {(err || error) && <p className="neg" role="alert">{err ?? error}</p>}
        {days === undefined && !err && <p className="muted">Loading days...</p>}
        {days === null && <p className="neg">This engine has no /days endpoint. Restart it with the latest code.</p>}
        {days && days.length === 0 && <p className="muted">No logged days yet.</p>}
        <ol className="daylist">
          {days?.map(d => (
            <li key={`${d.day}-${d.mode}`}>
              <b>{d.day}</b> <span className="chip">{d.mode}</span>
              <span className="muted"> {d.events.toLocaleString()} events · {formatTime(d.first)} to {formatTime(d.last)} ET</span>
              <button disabled={loading} onClick={() => onPick(d)}>{loading ? '...' : 'Replay'}</button>
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}
