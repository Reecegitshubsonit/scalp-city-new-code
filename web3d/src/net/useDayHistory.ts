import { useEffect, useState } from 'react'
import type { History } from '../model/history'
import { fetchHistory } from './api'

/** Real candles of one logged past day, once per day (null while loading or when the engine has no cached bars for it). */
export function useDayHistory(tickers: readonly string[], day: { day: string; mode: string } | null): Record<string, History | null> {
  const [data, setData] = useState<{ key: string; h: Record<string, History | null> }>({ key: '', h: {} })
  const key = day ? `${day.day}|${day.mode}` : ''
  useEffect(() => {
    if (!day) return
    let cancelled = false
    Promise.all(tickers.map(t => fetchHistory(t, day).catch(() => null))).then(all => {
      if (!cancelled) setData({ key, h: Object.fromEntries(tickers.map((t, i) => [t, all[i]])) })
    })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, tickers.join(',')])
  return data.key === key && key ? data.h : {}
}
