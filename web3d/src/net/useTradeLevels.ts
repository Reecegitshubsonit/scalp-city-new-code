import { useEffect, useState } from 'react'
import { tradeLevels, type TradeLevel } from '../model/tradeLevels'
import { fetchDay } from './api'

/** Stop and target of every trade of one logged day. Reloads when `signal` changes (a trade opened or closed) and every minute. */
export function useTradeLevels(day: string | null, mode: string, enabled: boolean, signal: number): TradeLevel[] {
  const [data, setData] = useState<{ key: string; levels: TradeLevel[] } | null>(null)
  const key = `${day}|${mode}`
  useEffect(() => {
    if (!enabled || !day) return
    let cancelled = false
    const load = () => fetchDay(day, mode).then(ev => { if (!cancelled) setData({ key, levels: tradeLevels(ev) }) }).catch(() => { /* keep what we had */ })
    load()
    const id = setInterval(load, 60000)
    return () => { cancelled = true; clearInterval(id) }
  }, [day, mode, enabled, signal, key])
  return data && data.key === key ? data.levels : []
}
