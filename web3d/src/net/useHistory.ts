import { useEffect, useState } from 'react'
import type { History } from '../model/history'
import { fetchHistory } from './api'
import type { Status } from './socket'

/** Loads /history for each ticker, again on every reconnect and every `refreshMs` (live ticks fill the gaps in between). */
export function useHistory(tickers: readonly string[], status: Status, refreshMs = 30000): Record<string, History | null> {
  const [data, setData] = useState<Record<string, History | null>>({})
  const online = status === 'live' || status === 'polling'
  const key = tickers.join(',')
  useEffect(() => {
    if (!online) return
    let cancelled = false
    const load = () => {
      for (const t of key.split(',')) {
        fetchHistory(t).then(h => { if (!cancelled) setData(d => ({ ...d, [t]: h })) }).catch(() => { /* keep what we had */ })
      }
    }
    load()
    const id = setInterval(load, refreshMs)
    return () => { cancelled = true; clearInterval(id) }
  }, [key, online, refreshMs])
  return data
}
