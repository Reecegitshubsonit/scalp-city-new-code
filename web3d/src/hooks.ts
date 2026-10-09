import { useCallback, useEffect, useState } from 'react'

export function useReducedMotion(): boolean {
  const q = '(prefers-reduced-motion: reduce)'
  const [r, setR] = useState(() => (typeof matchMedia === 'function' ? matchMedia(q).matches : false))
  useEffect(() => {
    const m = matchMedia(q)
    const on = () => setR(m.matches)
    m.addEventListener('change', on)
    return () => m.removeEventListener('change', on)
  }, [])
  return r
}

export function useNow(ms = 1000): number {
  const [n, setN] = useState(() => Date.now())
  useEffect(() => { const id = setInterval(() => setN(Date.now()), ms); return () => clearInterval(id) }, [ms])
  return n
}

export function useStored<T>(key: string, init: T): [T, (v: T) => void] {
  const [v, setV] = useState<T>(() => {
    try { const s = localStorage.getItem(key); return s == null ? init : (JSON.parse(s) as T) } catch { return init }
  })
  const set = useCallback((x: T) => { setV(x); try { localStorage.setItem(key, JSON.stringify(x)) } catch { /* ignore */ } }, [key])
  return [v, set]
}
