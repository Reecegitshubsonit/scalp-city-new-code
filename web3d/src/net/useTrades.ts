import { useEffect, useState } from 'react'
import type { Trade } from '../model/trades'
import { fetchTrades } from './api'

/** Closed trades for one logged day. Reloads when `signal` changes (e.g. a new live trade arrived) and every minute. */
export function useTrades(day: string | null, mode: string, enabled: boolean, signal: number): { trades: Trade[]; loaded: boolean; supported: boolean } {
  const [data, setData] = useState<{ key: string; trades: Trade[] | null } | null>(null)
  const key = `${day}|${mode}`
  useEffect(() => {
    if (!enabled || !day) return
    let cancelled = false
    const load = () => fetchTrades(day, mode).then(t => { if (!cancelled) setData({ key, trades: t }) }).catch(() => { /* keep what we had */ })
    load()
    const id = setInterval(load, 60000)
    return () => { cancelled = true; clearInterval(id) }
  }, [day, mode, enabled, signal, key])
  const mine = data && data.key === key ? data : null
  return { trades: mine?.trades ?? [], loaded: mine !== null, supported: mine === null || mine.trades !== null }
}
