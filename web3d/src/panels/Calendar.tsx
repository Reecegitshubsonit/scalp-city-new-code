import { useEffect, useMemo, useRef, useState } from 'react'
import { fetchDays } from '../net/api'
import type { Day } from '../model/replay'
import { DAY_NOTES } from '../model/dayNotes'
import { formatPnl } from '../model/format'

interface Props { loading: boolean; onPick: (d: Day) => void; onClose: () => void }

const cls = (n: number) => (n > 0 ? 'pos' : n < 0 ? 'neg' : '')
const monthName = (ym: string) => new Date(`${ym}-01T12:00:00Z`).toLocaleString('en-US', { month: 'long', year: 'numeric', timeZone: 'UTC' })

/** Weekday cells (Mon-Fri) of one month, padded so the first day sits under its weekday. */
function weekdays(ym: string): (string | null)[] {
  const [y, m] = ym.split('-').map(Number)
  const n = new Date(Date.UTC(y, m, 0)).getUTCDate()
  const out: (string | null)[] = []
  for (let d = 1; d <= n; d++) {
    const wd = new Date(Date.UTC(y, m - 1, d)).getUTCDay()
    if (wd === 0 || wd === 6) continue
    if (!out.length) for (let i = 1; i < wd; i++) out.push(null)
    out.push(`${ym}-${String(d).padStart(2, '0')}`)
  }
  return out
}

/** Month calendar of logged days: final P&L, trades, wins and the written biggest downfall of each day. */
export function Calendar({ loading, onPick, onClose }: Props) {
  const [days, setDays] = useState<Day[] | null | undefined>(undefined)
  const [err, setErr] = useState<string | null>(null)
  const [month, setMonth] = useState<string | null>(null)
  const [picked, setPicked] = useState<string | null>(null)
  const closeRef = useRef<HTMLButtonElement>(null)
  const detailRef = useRef<HTMLDivElement>(null)
  useEffect(() => { if (picked) detailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }) }, [picked])
  useEffect(() => { closeRef.current?.focus(); fetchDays().then(setDays).catch(e => setErr((e as Error).message)) }, [])
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [onClose])

  // one entry per date: the live paper day when there is one, else the replay day
  const byDate = useMemo(() => {
    const m: Record<string, Day> = {}
    for (const d of days ?? []) if (!m[d.day] || (m[d.day].mode !== 'live' && d.mode === 'live')) m[d.day] = d
    return m
  }, [days])
  const months = useMemo(() => [...new Set(Object.keys(byDate).map(d => d.slice(0, 7)))].sort(), [byDate])
  const ym = month ?? months[months.length - 1] ?? null
  const mi = ym ? months.indexOf(ym) : -1
  const inMonth = Object.values(byDate).filter(d => ym && d.day.startsWith(ym) && d.mode === 'live')
  const mTotal = inMonth.reduce((s, d) => s + (d.pnl ?? 0), 0)
  const mTrades = inMonth.reduce((s, d) => s + (d.trades ?? 0), 0)
  const sel = picked ? byDate[picked] : null
  const note = picked ? DAY_NOTES[picked] : undefined

  return (
    <div className="modal" role="dialog" aria-label="P&L calendar">
      <div className="sumcard calcard">
        <header><h2>P&amp;L calendar</h2><button ref={closeRef} onClick={onClose}>Close</button></header>
        {err && <p className="neg" role="alert">{err}</p>}
        {days === undefined && !err && <p className="muted">Loading days...</p>}
        {days === null && <p className="neg">This engine has no /days endpoint. Restart it with the latest code.</p>}
        {ym && (
          <>
            <div className="calnav">
              <button disabled={mi <= 0} onClick={() => setMonth(months[mi - 1])} aria-label="Previous month">‹</button>
              <b>{monthName(ym)}</b>
              <button disabled={mi >= months.length - 1} onClick={() => setMonth(months[mi + 1])} aria-label="Next month">›</button>
              <span className="calsum">Paper total <b className={cls(mTotal)}>{formatPnl(mTotal)}</b> <span className="muted">· {inMonth.length} days · {mTrades} trades</span></span>
            </div>
            <div className="calgrid">
              {['Mon', 'Tue', 'Wed', 'Thu', 'Fri'].map(w => <span key={w} className="calwd muted">{w}</span>)}
              {weekdays(ym).map((date, i) => {
                if (!date) return <span key={`pad${i}`} />
                const d = byDate[date]
                const n = DAY_NOTES[date]
                if (!d) return <div key={date} className="calday empty"><span className="caldate">{+date.slice(8)}</span></div>
                return (
                  <button key={date} className={`calday${picked === date ? ' on' : ''}`} onClick={() => setPicked(date)} title={n?.detail}>
                    <span className="caldate">{+date.slice(8)}{d.mode !== 'live' && <span className="chip">{d.mode}</span>}</span>
                    <b className={cls(d.pnl ?? 0)}>{formatPnl(d.pnl ?? 0)}</b>
                    <small className="muted">{d.trades ?? 0} trades · {d.wins ?? 0} wins</small>
                    <small className="caldown">{n ? n.short : 'No note yet'}</small>
                  </button>
                )
              })}
            </div>
            {sel && (
              <div className="caldetail" ref={detailRef}>
                <header>
                  <b>{sel.day}</b> <span className="chip">{sel.mode}</span>
                  <b className={cls(sel.pnl ?? 0)}>{formatPnl(sel.pnl ?? 0)}</b>
                  <span className="muted">{sel.trades ?? 0} trades · {sel.wins ?? 0} wins</span>
                  <button disabled={loading} onClick={() => onPick(sel)}>{loading ? '...' : 'Replay'}</button>
                </header>
                <p><b>Biggest downfall:</b> {note ? note.detail : 'No note written for this day yet.'}</p>
                {note && <small className="muted">Source: {note.source}</small>}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
