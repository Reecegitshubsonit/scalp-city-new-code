import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useReducedMotion, useStored } from './hooks'
import { ALL_BOTS, TICKERS } from './model/layout'
import { mergeSeries, truncateHistory } from './model/history'
import { useDayHistory } from './net/useDayHistory'
import { useHistory } from './net/useHistory'
import { useDays } from './net/useDays'
import { useTrades } from './net/useTrades'
import { mergeTrades, toTradeRecs, tradeStats } from './model/trades'
import { replayClockLabel } from './model/lab'
import { stateLabel } from './model/visual'
import { dayLabel } from './panels/EarnedCard'
import type { LabControls } from './scene/Room3D'
import { TradesPanel } from './panels/TradesPanel'
import { leaderboard, totalPnl } from './model/reducer'
import { botsOfTicker, eventsOfTicker, scanId, tickerPnl as sumTickerPnl, tradesOfTicker } from './model/tower'
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
import { Hud } from './panels/Hud'
import { hudCards } from './model/hud'
import { daySummary } from './model/summary'
import { deskKey, nextSpeed } from './model/lab'
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
  const replayDay = replay.active && replay.day ? { day: replay.day.day, mode: replay.day.mode } : null
  const dayHistory = useDayHistory(TICKERS, replayDay)   // real candles of the replayed day, when the engine has them cached
  const replayAtMs = replay.active ? Math.floor((replay.startMs + replay.posMs) / 60000) * 60000 + 59999 : null   // per minute: one new candle at a time, not a rebuild every tick
  const series = useMemo(
    () => Object.fromEntries(TICKERS.map(t => {
      const dh = dayHistory[t]
      const h = replay.active ? (dh && replayAtMs != null ? truncateHistory(dh, replayAtMs) : null) : history[t] ?? null
      return [t, mergeSeries(t, h, state.ticks[t] ?? [], state.marks[t] ?? [])]
    })),
    [history, state.ticks, state.marks, replay.active, dayHistory, replayAtMs],
  )
  const tickerTrades = useMemo(() => {
    const m: Record<string, number> = {}
    for (const r of rows) m[r.ticker] = (m[r.ticker] ?? 0) + r.trades
    return m
  }, [rows])
  const newest = useMemo(() => rows.map(r => r.time).filter((t): t is string => !!t).sort().pop() ?? null, [rows])
  const date = newest?.slice(0, 10) ?? null

  // all past trades: the engine's logged trades for the viewed day, merged with trades seen live since the page loaded
  const enabled = replay.active || status === 'live' || status === 'polling'
  const currentDay = replay.active && replay.day ? { day: replay.day.day, mode: replay.day.mode } : date ? { day: date, mode: 'live' } : null
  const currentKey = currentDay ? `${currentDay.day}|${currentDay.mode}` : ''
  const [panelKey, setPanelKey] = useState<string | null>(null)
  const viewKey = panelKey ?? currentKey
  const isCurrent = viewKey === currentKey
  const cur = useTrades(currentDay?.day ?? null, currentDay?.mode ?? 'live', enabled, replay.active ? 0 : state.trades.length)
  const [vDay, vMode] = viewKey.split('|')
  const other = useTrades(!isCurrent && vDay ? vDay : null, vMode ?? 'live', enabled && !isCurrent, 0)
  const days = useDays(enabled, 0)
  const replayMs = replay.active ? replay.startMs + replay.posMs : null
  const currentTrades = useMemo(
    () => mergeTrades(replayMs == null ? cur.trades : cur.trades.filter(t => Date.parse(t.exit_time) <= replayMs), state.trades),
    [cur.trades, state.trades, replayMs],
  )
  const panelTrades = isCurrent ? currentTrades : other.trades
  const tradeRecs = useMemo(() => toTradeRecs(currentTrades), [currentTrades])
  const lastTrade = useMemo(() => {
    const m: Record<string, TradeRec> = {}
    for (const t of tradeRecs) m[t.bot] = t
    return m
  }, [tradeRecs])

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

  const onSelect = useCallback((bot: string) => setSelected(bot), [])   // selecting never toggles off; close with the X or Esc
  const onClose = useCallback(() => { setSelected(null); setInside(false); setScreen(null) }, [])
  const onPickScreen = useCallback((id: string) => setScreen(id), [])
  const closeScreen = useCallback(() => setScreen(null), [])
  // leaderboard, heatmap and trade rows: open that bot, and always show something (scanner screen inside the room, else scroll to it)
  const openBot = useCallback((bot: string) => {
    setSelected(bot)
    if (inside) setScreen(scanId(bot) ?? 'scan0')
    else setTimeout(() => (document.querySelector('.stage') ?? document.querySelector('.room'))?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 80)
  }, [inside])
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
  const ticker = sel?.ticker ?? 'QQQ'   // a tower room shows only the clicked tower's ticker
  const hud = useMemo(() => hudCards(daySummary(rows, tradeRecs)), [rows, tradeRecs])
  const tickerRows = useMemo(() => botsOfTicker(rows, ticker), [rows, ticker])
  const tickerFeed = useMemo(() => eventsOfTicker(state.feed, ticker), [state.feed, ticker])
  const tickerTradeList = useMemo(() => tradesOfTicker(currentTrades, ticker), [currentTrades, ticker])
  const tickerFire = useMemo(() => {
    let best: { seq: number; side: import('./model/types').Side | null; bot: string } | null = null
    for (const r of tickerRows) { const f = state.fires[r.bot]; if (f && (!best || f.seq > best.seq)) best = { seq: f.seq, side: f.side, bot: r.bot } }
    return best
  }, [tickerRows, state.fires])
  const tPnl = useMemo(() => sumTickerPnl(rows, ticker), [rows, ticker])

  const room = sel && !inside && (
    <Room row={sel} events={state.feed} series={series[sel.ticker]} tickerTrades={tickerTrades[sel.ticker] ?? 0}
      siblings={tickerRows} recent={tickerTradeList} onSelectBot={onSelect} pending={sel.bot in pending} onClose={onClose} onPause={onPause} onInside={tableOnly ? undefined : onInside} />
  )
  const floatChart = sel ? <CandleChart series={series[sel.ticker]} trades={tickerTrades[sel.ticker] ?? 0} height={120} labels={false} compact /> : null
  const stats = useMemo(() => tradeStats(tickerTradeList), [tickerTradeList])
  const earned = useMemo(
    () => ({ label: `${ticker} · ${date ? dayLabel(date) : 'TODAY'}`, pnl: stats.pnl, count: stats.count, wins: stats.wins, trades: tickerTradeList }),
    [date, stats, tickerTradeList, ticker],
  )
  const [deskHint, setDeskHint] = useState<string | null>(null)
  const deskAct = useRef<(a: 'play' | 'stop' | 'speed') => void>(() => {})
  deskAct.current = a => {
    if (a === 'play') { if (replay.active) { if (replay.playing) replay.pause(); else replay.play() } else setShowPicker(true) }
    else if (a === 'stop') { if (replay.active) replay.stop() }
    else replay.setSpeed(nextSpeed(replay.speed))
  }
  useEffect(() => {
    if (!inside || screen || showPicker) return
    const key = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null
      if (t && /^(INPUT|SELECT|TEXTAREA|BUTTON)$/.test(t.tagName)) return
      if (e.ctrlKey || e.metaKey || e.altKey) return
      const a = deskKey(e.key)
      if (!a) return
      e.preventDefault(); deskAct.current(a)
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [inside, screen, showPicker])
  const lab: LabControls = {
    onHint: setDeskHint,
    replayActive: replay.active, playing: replay.playing, speed: replay.speed,
    onPlayPause: () => (replay.playing ? replay.pause() : replay.play()), onStop: replay.stop, onSpeed: replay.setSpeed,
    onOpenPicker: () => setShowPicker(true),
  }
  const roomData = { ticker, series: series[ticker], tradeCount: tickerTrades[ticker] ?? 0, tickerRows, feed: tickerFeed, selectedBot: selected, tickerPnl: tPnl, fire: tickerFire, earned, lab }

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
      <Tape trades={tradeRecs} />
      <main className={`main${tableOnly ? ' tableonly' : ''}`}>
        <div className="left">
          {!tableOnly && (
            <div className="canvaswrap">
              <div className="stage">
                <Suspense fallback={<div className="muted pad">Loading 3D...</div>}>
                  <City rows={rows} selected={selected} onSelect={onSelect} onDome={openSummary} reducedMotion={reduced} total={total} lastTrade={lastTrade} title={TITLE} fires={state.fires}
                    inside={inside} roomData={roomData} allSeries={series} floatChart={floatChart} screen={screen} onPickScreen={onPickScreen} />
                </Suspense>
                {!inside && <Hud cards={hud} onOpen={openSummary} />}
                {sel && inside && (
                  <div className="insidebar">
                    <button onClick={() => setInside(false)}>← Back outside (Esc)</button>
                    <b>{ticker} tower</b>
                    <span className="muted">{replay.active ? replayClockLabel(replayMs ?? 0) : 'LIVE'} · {stateLabel(sel.state).toLowerCase()}</span>
                    <span className="deskhint" role="status">{deskHint ?? 'Desk keys: Space replay/pause, L live, S speed'}</span>
                    <label className="muted">Screens{' '}
                      <select value="" aria-label="Open a wall screen" onChange={e => { if (e.target.value) onPickScreen(e.target.value) }}>
                        <option value="">Open a screen...</option>
                        {[...tickerRows.map((r, i) => [`scan${i}`, `${r.bot.split('-')[1]} scanner`]), ['chart', `${ticker} chart`], ['chart1m', '1-minute chart'], ['board', 'Heatmap and leaderboard'], ['plaque', 'Market'], ['earned', 'Earned trades']].map(([id, label]) => <option key={id} value={id}>{label}</option>)}
                      </select>
                    </label>
                    <button onClick={onClose}>Close</button>
                  </div>
                )}
              </div>
              {room}
            </div>
          )}
          <div className="insight">
            <Charts series={series} trades={tickerTrades} />
            <Heatmap rows={rows} onSelect={openBot} />
          </div>
          <Cards rows={rows} selected={selected} pending={pending} onSelect={onSelect} onPause={onPause} />
          <TradesPanel days={days} viewKey={viewKey} onViewDay={d => setPanelKey(`${d.day}|${d.mode}`)} trades={panelTrades} isCurrent={isCurrent}
            enginePnl={isCurrent && !replay.active ? total : null} supported={isCurrent ? cur.supported : other.supported}
            onOpenBot={openBot} onReplay={async d => { await replay.start(d); onClose(); window.scrollTo({ top: 0, behavior: 'smooth' }) }} />
        </div>
        <div className="right">
          <Clock lastEventAt={state.lastEventAt} dataTime={newest} status={status} replayMs={replay.active ? replay.startMs + replay.posMs : null} />
          <Leaderboard rows={board} onSelect={openBot} />
          <Feed events={state.feed} />
          {tableOnly && room}
        </div>
      </main>
      {screen && inside && (
        <ScreenViewer screen={screen} ticker={ticker} series={series[ticker]} tradeCount={tickerTrades[ticker] ?? 0} tickerRows={tickerRows} feed={tickerFeed}
          earned={earned} tickerPnl={tPnl} lastEventAt={state.lastEventAt} dataTime={newest} status={status} onSelectBot={openBot} onClose={closeScreen} />
      )}
      {showPicker && <ReplayPicker loading={replay.loading} error={replay.error} onClose={() => setShowPicker(false)} onPick={async d => { await replay.start(d); setShowPicker(false); onClose() }} />}
      {showSummary && <Summary rows={rows} trades={tradeRecs} date={date} onClose={closeSummary} />}
    </div>
  )
}
