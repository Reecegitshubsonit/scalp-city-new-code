import { useEffect, useReducer, useState } from 'react'
import { initialState, reduce } from '../model/reducer'
import type { AppState, ServerMsg } from '../model/types'
import { connectStream, type Status } from './socket'

type Batch = { msgs: ServerMsg[]; now: number }

/** Messages are queued and applied once per animation frame, so a burst of events costs one render. */
export function useStream(): { state: AppState; status: Status } {
  const [state, dispatch] = useReducer(
    (s: AppState, a: Batch) => a.msgs.reduce((acc, m) => reduce(acc, m, a.now), s),
    initialState,
  )
  const [status, setStatus] = useState<Status>('connecting')
  useEffect(() => {
    let queue: ServerMsg[] = []
    let raf = 0
    const flush = () => {
      raf = 0
      const msgs = queue
      queue = []
      dispatch({ msgs, now: Date.now() })
    }
    const stop = connectStream({
      onMessage: m => { queue.push(m); if (!raf) raf = requestAnimationFrame(flush) },
      onStatus: setStatus,
    })
    return () => { stop(); if (raf) cancelAnimationFrame(raf) }
  }, [])
  return { state, status }
}
