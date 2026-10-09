import type { ServerMsg } from '../model/types'

export type Status = 'connecting' | 'live' | 'polling' | 'down'

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

export const POLL_MS = 2000
/** Failed websocket attempts in a row before falling back to polling /snapshot. */
export const POLL_AFTER_FAILURES = 2

export function connectStream(h: { onMessage: (m: ServerMsg) => void; onStatus: (s: Status) => void }): () => void {
  let ws: WebSocket | null = null
  let attempt = 0
  let timer: ReturnType<typeof setTimeout> | undefined
  let closed = false
  let failures = 0
  let poller: ReturnType<typeof setInterval> | undefined
  const stopPolling = () => { clearInterval(poller); poller = undefined }
  const poll = async () => {
    try {
      const r = await fetch(apiUrl('/snapshot'))
      if (!r.ok || closed || !poller) return
      h.onMessage({ type: 'snapshot', ...(await r.json()) })
      h.onStatus('polling')
    } catch { if (!closed && poller) h.onStatus('down') }
  }
  const startPolling = () => { if (poller) return; poller = setInterval(poll, POLL_MS); void poll() }
  const open = () => {
    if (closed) return
    h.onStatus('connecting')
    const sock = (ws = new WebSocket(wsUrl()))
    sock.onopen = () => { attempt = 0; failures = 0; stopPolling(); h.onStatus('live') }
    sock.onmessage = e => {
      try {
        const m = JSON.parse(e.data)
        if (m && (m.type === 'snapshot' || m.type === 'event')) h.onMessage(m)
      } catch { /* ignore bad frame */ }
    }
    sock.onclose = () => {
      if (closed || ws !== sock) return
      if (++failures >= POLL_AFTER_FAILURES) startPolling()
      else h.onStatus('down')
      timer = setTimeout(open, backoffDelay(attempt++))
    }
    sock.onerror = () => sock.close()
  }
  open()
  return () => { closed = true; clearTimeout(timer); stopPolling(); ws?.close() }
}
