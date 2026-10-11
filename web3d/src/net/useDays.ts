import { useEffect, useState } from 'react'
import type { Day } from '../model/replay'
import { fetchDays } from './api'

/** Logged days the engine knows (for the trades day picker and EARNED cards); refreshed every 5 minutes. */
export function useDays(enabled: boolean, signal: number): Day[] {
  const [days, setDays] = useState<Day[]>([])
  useEffect(() => {
    if (!enabled) return
    let cancelled = false
    const load = () => fetchDays().then(d => { if (!cancelled && d) setDays(d) }).catch(() => { /* keep what we had */ })
    load()
    const id = setInterval(load, 300000)
    return () => { cancelled = true; clearInterval(id) }
  }, [enabled, signal])
  return days
}
