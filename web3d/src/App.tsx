import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useReducedMotion, useStored } from './hooks'
import { ALL_BOTS } from './model/layout'
import { leaderboard, totalPnl } from './model/reducer'
import { formatPnl } from './model/format'
import type { BotRow } from './model/types'
import { postPause } from './net/api'
import { useStream } from './net/useStream'
import { Cards } from './panels/Cards'
import { Clock } from './panels/Clock'
import { Drawer } from './panels/Drawer'
import { Feed } from './panels/Feed'
import { Leaderboard } from './panels/Leaderboard'

const City = lazy(() => import('./scene/City'))

const TITLE = new URLSearchParams(location.search).get('title') || import.meta.env.VITE_TITLE || 'Scalp City'

const placeholder = (bot: string): BotRow => ({
  bot, ticker: bot.split('-')[0], state: 'idle', reason_code: 'NO_DATA', reason_text: 'waiting for data', charge_pct: null,
  inputs: {}, time: null, pnl_day: 0, trades: 0, paused: false, side: null, sideSource: 'none',
})

export default function App() {
  const { state, status } = useStream()
  const reduced = useReducedMotion()
  const [tableOnly, setTableOnly] = useStored<boolean>('tableOnly', false)
  const [selected, setSelected] = useState<string | null>(null)
  const [pending, setPending] = useState<Record<string, boolean>>({})
  const [toast, setToast] = useState<string | null>(null)
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({})

  useEffect(() => { document.title = TITLE }, [])

  const rows = useMemo(() => ALL_BOTS.map(b => state.bots[b] ?? placeholder(b)), [state.bots])
  const board = useMemo(() => leaderboard(state), [state])
  const total = totalPnl(state)

  // clear pending once the row reflects the requested value
  useEffect(() => {
    setPending(p => {
      const next = { ...p }
      let changed = false
      for (const [bot, want] of Object.entries(p)) {
        if (state.bots[bot]?.paused === want) { delete next[bot]; clearTimeout(timers.current[bot]); changed = true }
      }
      return changed ? next : p
    })
  }, [state.bots])

  const onPause = useCallback(async (bot: string, paused: boolean) => {
    setPending(p => ({ ...p, [bot]: paused }))
    clearTimeout(timers.current[bot])
    timers.current[bot] = setTimeout(() => setPending(p => { const n = { ...p }; delete n[bot]; return n }), 5000)
    try { await postPause(bot, paused) } catch (e) {
      clearTimeout(timers.current[bot])
      setPending(p => { const n = { ...p }; delete n[bot]; return n })
      setToast(`Pause failed for ${bot}: ${(e as Error).message}`)
      setTimeout(() => setToast(null), 5000)
    }
  }, [])

  const onSelect = useCallback((bot: string) => setSelected(s => (s === bot ? null : bot)), [])
  const onClose = useCallback(() => setSelected(null), [])
  const sel = selected ? state.bots[selected] ?? placeholder(selected) : null

  return (
    <div className="app">
      <header className="top">
        <h1>{TITLE}</h1>
        <span className={`conn c-${status}`} role="status">{status === 'live' ? 'Connected' : status === 'connecting' ? 'Connecting...' : 'Disconnected, retrying...'}</span>
        <span className="total">Day P&amp;L <b className={total > 0 ? 'pos' : total < 0 ? 'neg' : ''}>{formatPnl(total)}</b></span>
        <button aria-pressed={tableOnly} onClick={() => setTableOnly(!tableOnly)}>{tableOnly ? 'Show 3D' : 'Table only'}</button>
      </header>
      {toast && <div className="toast" role="alert">{toast}</div>}
      <main className={`main${tableOnly ? ' tableonly' : ''}`}>
        <div className="left">
          {!tableOnly && (
            <div className="canvaswrap">
              <Suspense fallback={<div className="muted pad">Loading 3D...</div>}>
                <City rows={rows} selected={selected} onSelect={onSelect} reducedMotion={reduced} total={total} />
              </Suspense>
            </div>
          )}
          <Cards rows={rows} selected={selected} pending={pending} onSelect={onSelect} onPause={onPause} />
        </div>
        <div className="right">
          <Clock lastEventAt={state.lastEventAt} status={status} />
          <Leaderboard rows={board} onSelect={onSelect} />
          <Feed events={state.feed} />
          {sel && (
            <Drawer row={sel} ticks={state.ticks[sel.ticker] ?? []} marks={state.marks[sel.ticker] ?? []}
              pending={sel.bot in pending} onClose={onClose} onPause={onPause} />
          )}
        </div>
      </main>
    </div>
  )
}
