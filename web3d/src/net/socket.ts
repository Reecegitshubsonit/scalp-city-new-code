import type { ServerMsg } from '../model/types'

export type Status = 'connecting' | 'live' | 'down'

export function backoffDelay(attempt: number, rand: () => number = Math.random): number {
  const base = Math.min(15000, 1000 * 2 ** attempt)
  return Math.max(500, Math.round(base * (0.5 + rand() * 0.5)))
}

const API_BASE = import.meta.env?.VITE_API_BASE as string | undefined
export const apiUrl = (p: string) => (API_BASE ? API_BASE.replace(/\/$/, '') + p : p)
const wsUrl = () => {
  if (API_BASE) return API_BASE.replace(/^http/, 'ws').replace(/\/$/, '') + '/ws'
  return `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`
}

export function connectStream(h: { onMessage: (m: ServerMsg) => void; onStatus: (s: Status) => void }): () => void {
  let ws: WebSocket | null = null
  let attempt = 0
  let timer: ReturnType<typeof setTimeout> | undefined
  let closed = false
  const open = () => {
    if (closed) return
    h.onStatus('connecting')
    const sock = (ws = new WebSocket(wsUrl()))
    sock.onopen = () => { attempt = 0; h.onStatus('live') }
    sock.onmessage = e => {
      try {
        const m = JSON.parse(e.data)
        if (m && (m.type === 'snapshot' || m.type === 'event')) h.onMessage(m)
      } catch { /* ignore bad frame */ }
    }
    sock.onclose = () => {
      if (closed || ws !== sock) return
      h.onStatus('down')
      timer = setTimeout(open, backoffDelay(attempt++))
    }
    sock.onerror = () => sock.close()
  }
  open()
  return () => { closed = true; clearTimeout(timer); ws?.close() }
}
