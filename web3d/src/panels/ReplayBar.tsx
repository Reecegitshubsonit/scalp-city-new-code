import type { Replay } from '../net/useReplay'
import { REPLAY_SPEEDS } from '../net/useReplay'
import { formatPnl } from '../model/format'

const etTime = (ms: number) =>
  new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(ms)

export function ReplayBar({ r }: { r: Replay }) {
  const dur = r.endMs - r.startMs
  return (
    <section className="replaybar" aria-label="Replay controls">
      <b className="replaytag">REPLAY {r.day?.day}</b>
      {typeof r.day?.pnl === 'number' && <span>Final <b className={r.day.pnl > 0 ? 'pos' : r.day.pnl < 0 ? 'neg' : ''}>{formatPnl(r.day.pnl)}</b></span>}
      <button onClick={r.playing ? r.pause : r.play} aria-label={r.playing ? 'Pause replay' : 'Play replay'}>{r.playing ? '❚❚ Pause' : '▶ Play'}</button>
      <label>Speed{' '}
        <select value={r.speed} onChange={e => r.setSpeed(+e.target.value)}>
          {REPLAY_SPEEDS.map(s => <option key={s} value={s}>{s}x</option>)}
        </select>
      </label>
      <input type="range" min={0} max={dur} step={1000} value={r.posMs} onChange={e => r.seek(+e.target.value)} aria-label="Replay position" className="scrub" />
      <time>{etTime(r.startMs + r.posMs)} ET</time>
      <button onClick={r.stop}>Back to live</button>
    </section>
  )
}
