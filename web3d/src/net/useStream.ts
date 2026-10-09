import { useEffect, useReducer, useState } from 'react'
import { initialState, reduce } from '../model/reducer'
import type { AppState, ServerMsg } from '../model/types'
import { connectStream, type Status } from './socket'

export function useStream(): { state: AppState; status: Status } {
  const [state, dispatch] = useReducer(
    (s: AppState, a: { msg: ServerMsg; now: number }) => reduce(s, a.msg, a.now),
    initialState,
  )
  const [status, setStatus] = useState<Status>('connecting')
  useEffect(() => connectStream({ onMessage: msg => dispatch({ msg, now: Date.now() }), onStatus: setStatus }), [])
  return { state, status }
}
