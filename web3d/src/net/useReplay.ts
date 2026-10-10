import { useCallback, useEffect, useRef, useState } from 'react'
import { initialState, reduce } from '../model/reducer'
import { countAt, eventTimes, replayStateAt, type Day } from '../model/replay'
import type { AppState, BotEvent } from '../model/types'
import { fetchDay } from './api'

export const REPLAY_SPEEDS = [1, 5, 15, 60, 300]
const TICK_MS = 100

export interface Replay {
  active: boolean; loading: boolean; error: string | null
  day: Day | null; state: AppState
  startMs: number; endMs: number; posMs: number; playing: boolean; speed: number
  start: (d: Day) => Promise<void>; stop: () => void
  play: () => void; pause: () => void; setSpeed: (s: number) => void; seek: (posMs: number) => void
}

/** Plays a logged day through the same reducer as the live stream. Scrubbing backwards rebuilds the state from the start. */
export function useReplay(): Replay {
  const events = useRef<BotEvent[]>([])
  const times = useRef<number[]>([])
  const count = useRef(0)
  const stateRef = useRef<AppState>(initialState)
  const posRef = useRef(0)
  const [day, setDay] = useState<Day | null>(null)
  const [state, setState] = useState<AppState>(initialState)
  const [startMs, setStartMs] = useState(0)
  const [endMs, setEndMs] = useState(0)
  const [pos, setPos] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeedState] = useState(60)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const apply = useCallback((p: number, base: number) => {
    const target = countAt(times.current, base + p)
    if (target === count.current) return
    if (target > count.current) {
      let s = stateRef.current
      for (let i = count.current; i < target; i++) s = reduce(s, { type: 'event', event: events.current[i] }, 0)
      stateRef.current = s
    } else stateRef.current = replayStateAt(events.current, target)
    count.current = target
    setState(stateRef.current)
  }, [])

  const start = useCallback(async (d: Day) => {
    setLoading(true); setError(null)
    try {
      const ev = await fetchDay(d.day, d.mode)
      if (!ev.length) throw new Error('that day has no events')
      events.current = ev; times.current = eventTimes(ev); count.current = 0
      stateRef.current = replayStateAt(ev, 0)
      const s0 = times.current[0], s1 = times.current[times.current.length - 1]
      posRef.current = 0
      setDay(d); setStartMs(s0); setEndMs(s1); setPos(0); setState(stateRef.current); setPlaying(true)
    } catch (e) { setError((e as Error).message) } finally { setLoading(false) }
  }, [])

  const stop = useCallback(() => {
    setDay(null); setPlaying(false); setPos(0); posRef.current = 0; events.current = []; times.current = []; count.current = 0
    stateRef.current = initialState; setState(initialState)
  }, [])

  useEffect(() => {
    if (!playing || !day) return
    const id = setInterval(() => {
      const next = Math.min(endMs - startMs, posRef.current + speed * TICK_MS)
      posRef.current = next
      setPos(next)
      apply(next, startMs)
      if (next >= endMs - startMs) setPlaying(false)
    }, TICK_MS)
    return () => clearInterval(id)
  }, [playing, day, speed, startMs, endMs, apply])

  const seek = useCallback((p: number) => { const c = Math.max(0, Math.min(endMs - startMs, p)); posRef.current = c; setPos(c); apply(c, startMs) }, [apply, startMs, endMs])
  const play = useCallback(() => { if (posRef.current >= endMs - startMs) { posRef.current = 0; setPos(0); apply(0, startMs) } setPlaying(true) }, [endMs, startMs, apply])
  return {
    active: day !== null, loading, error, day, state, startMs, endMs, posMs: pos, playing, speed,
    start, stop, play, pause: () => setPlaying(false), setSpeed: setSpeedState, seek,
  }
}
