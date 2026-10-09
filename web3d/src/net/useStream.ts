import { useEffect, useReducer, useState } from 'react'
import { initialState, reduce } from '../model/reducer'
import type { AppState, ServerMsg } from '../model/types'
import { connectStream, type Status } from './socket'

type Batch = { msgs: ServerMsg[]; now: number }

/** Messages are queued and applied at most every 150 ms, so a burst of events costs one render (3D animates on its own clock). */
export function useStream(): { state: AppState; status: Status } {
  const [state, dispatch] = useReducer(
    (s: AppState, a: Batch) => a.msgs.reduce((acc, m) => reduce(acc, m, a.now), s),
    initialState,
  )
  const [status, setStatus] = useState<Status>('connecting')
  useEffect(() => {
    let queue: ServerMsg[] = []
    let timer: ReturnType<typeof setTimeout> | undefined
    const flush = () => {
      timer = undefined
      const msgs = queue
      queue = []
      dispatch({ msgs, now: Date.now() })
    }
    const stop = connectStream({
      onMessage: m => { queue.push(m); if (timer === undefined) timer = setTimeout(flush, 150) },
      onStatus: setStatus,
    })
    return () => { stop(); clearTimeout(timer) }
  }, [])
  return { state, status }
}
