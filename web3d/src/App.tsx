import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useReducedMotion, useStored } from './hooks'
import { ALL_BOTS, TICKERS } from './model/layout'
import { mergeSeries } from './model/history'
import { useHistory } from './net/useHistory'
import { leaderboard, totalPnl } from './model/reducer'
import { formatPnl } from './model/format'
import type { BotRow, TradeRec } from './model/types'
import { postPause } from './net/api'
import { useStream } from './net/useStream'
import { useReplay } from './net/useReplay'
import { ReplayBar } from './panels/ReplayBar'
import { ReplayPicker } from './panels/ReplayPicker'
import { Cards } from './panels/Cards'
import { CandleChart } from './panels/CandleChart'
import { Charts } from './panels/Charts'
import { Clock } from './panels/Clock'
import { Feed } from './panels/Feed'
import { Heatmap } from './panels/Heatmap'
import { Leaderboard } from './panels/Leaderboard'
import { Room } from './panels/Room'
import { ScreenViewer } from './panels/ScreenViewer'
import { Summary } from './panels/Summary'
import { Tape } from './panels/Tape'

const City = lazy(() => import('./scene/City'))

const TITLE = new URLSearchParams(location.search).get('title') || import.meta.env.VITE_TITLE || 'Scalp City'

const placeholder = (bot: string): BotRow => ({
  bot, ticker: bot.split('-')[0], state: 'idle', reason_code: 'NO_DATA', reason_text: 'waiting for data', charge_pct: null,
  inputs: {}, time: null, pnl_day: 0, trades: 0, paused: false, side: null, sideSource: 'none', exit_code: null,
})

export default function App() {
  const { state: liveState, status } = useStream()
  const replay = useReplay()
  const state = replay.active ? replay.state : liveState   // replaying a logged day swaps the whole view's data; live keeps running underneath
  const [showPicker, setShowPicker] = useState(false)
  const reduced = useReducedMotion()
  const [tableOnly, setTableOnly] = useStored<boolean>('tableOnly', false)
  const [selected, setSelected] = useState<string | null>(null)
  const [showSummary, setShowSummary] = useState(false)
  const [inside, setInside] = useState(false)
  const [screen, setScreen] = useState<string | null>(null)
  const [pending, setPending] = useState<Record<string, boolean>>({})
  const [toast, setToast] = useState<string | null>(null)
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({})

  useEffect(() => { document.title = TITLE }, [])

  const rows = useMemo(() => ALL_BOTS.map(b => state.bots[b] ?? placeholder(b)), [state.bots])
  const board = useMemo(() => leaderboard(state), [state])
  const total = totalPnl(state)
  const history = useHistory(TICKERS, replay.active ? 'down' : status)
  const series = useMemo(
    () => Object.fromEntries(TICKERS.map(t => [t, mergeSeries(t, replay.active ? null : history[t] ?? null, state.ticks[t] ?? [], state.marks[t] ?? [])])),
    [history, state.ticks, state.marks, replay.active],
  )
  const tickerTrades = useMemo(() => {
    const m: Record<string, number> = {}
    for (const r of rows) m[r.ticker] = (m[r.ticker] ?? 0) + r.trades
    return m
  }, [rows])
  const lastTrade = useMemo(() => {
    const m: Record<string, TradeRec> = {}
    for (const t of state.trades) m[t.bot] = t
    return m
  }, [state.trades])
  const newest = useMemo(() => rows.map(r => r.time).filter((t): t is string => !!t).sort().pop() ?? null, [rows])
  const date = newest?.slice(0, 10) ?? null

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
    if (replay.active) { setPending(p => { const n = { ...p }; delete n[bot]; return n }); setToast('Replay is read-only: Pause is disabled.'); setTimeout(() => setToast(null), 4000); return }
    try { await postPause(bot, paused) } catch (e) {
      clearTimeout(timers.current[bot])
      setPending(p => { const n = { ...p }; delete n[bot]; return n })
      setToast(`Pause failed for ${bot}: ${(e as Error).message}`)
      setTimeout(() => setToast(null), 5000)
    }
  }, [replay.active])

  const onSelect = useCallback((bot: string) => setSelected(s => (s === bot ? null : bot)), [])
  const onClose = useCallback(() => { setSelected(null); setInside(false); setScreen(null) }, [])
  const onPickScreen = useCallback((id: string) => setScreen(id), [])
  const closeScreen = useCallback(() => setScreen(null), [])
  const selectBot = useCallback((bot: string) => setSelected(bot), [])
  const onInside = useCallback(() => setInside(true), [])
  const openSummary = useCallback(() => setShowSummary(true), [])
  const closeSummary = useCallback(() => setShowSummary(false), [])
  // Esc: step back outside first, then close the selection (the summary handles its own Esc)
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key !== 'Escape' || showSummary) return
      if (screen) setScreen(null)
      else if (inside) setInside(false)
      else if (selected) setSelected(null)
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [inside, selected, showSummary, screen])
  useEffect(() => { if (!selected) { setInside(false); setScreen(null) } }, [selected])
  useEffect(() => { if (!inside) setScreen(null) }, [inside])
  const sel = selected ? state.bots[selected] ?? placeholder(selected) : null

  const room = sel && !inside && (
    <Room row={sel} events={state.feed} series={series[sel.ticker]} tickerTrades={tickerTrades[sel.ticker] ?? 0}
      pending={sel.bot in pending} onClose={onClose} onPause={onPause} onInside={tableOnly ? undefined : onInside} />
  )
  const floatChart = sel ? <CandleChart series={series[sel.ticker]} trades={tickerTrades[sel.ticker] ?? 0} height={120} labels={false} compact /> : null
  const roomData = { series, tickerTrades, rows, feed: state.feed, selectedRow: sel, total }

  return (
    <div className="app">
      <header className="top">
        <h1>{TITLE}</h1>
        <span className={`conn c-${status}`} role="status">{status === 'live' ? 'Connected' : status === 'polling' ? 'Polling every 2 s (no websocket)' : status === 'connecting' ? 'Connecting...' : 'Disconnected, retrying...'}</span>
        {(replay.active || state.mode) && <span className={`mode m-${replay.active ? 'replay' : state.mode}`}>{replay.active ? 'REPLAY' : state.mode === 'mock' ? 'MOCK DATA, NOT REAL' : state.mode === 'replay' ? 'REPLAY' : state.mode === 'live' ? 'LIVE PAPER' : state.mode!.toUpperCase()}</span>}
        <span className="total">Day P&amp;L <b className={total > 0 ? 'pos' : total < 0 ? 'neg' : ''}>{formatPnl(total)}</b></span>
        <button onClick={openSummary}>Day summary</button>
        <button onClick={() => setShowPicker(true)}>Replay</button>
        <button aria-pressed={tableOnly} onClick={() => setTableOnly(!tableOnly)}>{tableOnly ? 'Show 3D' : 'Table only'}</button>
      </header>
      {toast && <div className="toast" role="alert">{toast}</div>}
      {replay.active && <ReplayBar r={replay} />}
      <Tape trades={state.trades} />
      <main className={`main${tableOnly ? ' tableonly' : ''}`}>
        <div className="left">
          {!tableOnly && (
            <div className="canvaswrap">
              <div className="stage">
                <Suspense fallback={<div className="muted pad">Loading 3D...</div>}>
                  <City rows={rows} selected={selected} onSelect={onSelect} onDome={openSummary} reducedMotion={reduced} total={total} lastTrade={lastTrade} title={TITLE}
                    inside={inside} roomData={roomData} floatChart={floatChart} screen={screen} onPickScreen={onPickScreen} />
                </Suspense>
                {sel && inside && (
                  <div className="insidebar">
                    <button onClick={() => setInside(false)}>← Back outside (Esc)</button>
                    <b>{sel.bot}</b>
                    {[['SPY', 'SPY'], ['QQQ', 'QQQ'], ['IWM', 'IWM'], ['scanner', 'Scanner'], ['board', 'Heatmap'], ['plaque', 'Market']].map(([id, label]) => (
                      <button key={id} onClick={() => onPickScreen(id)} aria-label={`Open ${label} screen`}>{label}</button>
                    ))}
                    <button onClick={onClose}>Close</button>
                  </div>
                )}
              </div>
              {room}
            </div>
          )}
          <div className="insight">
            <Charts series={series} trades={tickerTrades} />
            <Heatmap rows={rows} onSelect={onSelect} />
          </div>
          <Cards rows={rows} selected={selected} pending={pending} onSelect={onSelect} onPause={onPause} />
        </div>
        <div className="right">
          <Clock lastEventAt={state.lastEventAt} dataTime={newest} status={status} replayMs={replay.active ? replay.startMs + replay.posMs : null} />
          <Leaderboard rows={board} onSelect={onSelect} />
          <Feed events={state.feed} />
          {tableOnly && room}
        </div>
      </main>
      {screen && inside && (
        <ScreenViewer screen={screen} series={series} tickerTrades={tickerTrades} rows={rows} board={board} feed={state.feed} trades={state.trades}
          selectedBot={selected} total={total} lastEventAt={state.lastEventAt} dataTime={newest} status={status} onSelectBot={selectBot} onClose={closeScreen} />
      )}
      {showPicker && <ReplayPicker loading={replay.loading} error={replay.error} onClose={() => setShowPicker(false)} onPick={async d => { await replay.start(d); setShowPicker(false); onClose() }} />}
      {showSummary && <Summary rows={rows} trades={state.trades} date={date} onClose={closeSummary} />}
    </div>
  )
}
