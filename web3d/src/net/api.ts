import { apiUrl } from './socket'

export async function postPause(bot: string, paused: boolean): Promise<void> {
  const r = await fetch(apiUrl('/control/pause'), {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bot, paused }),
  })
  if (r.status === 404) throw new Error('unknown bot')
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
}

import type { History } from '../model/history'

/** Today's candles, indicator levels and trade markers; null when the engine has no /history (older engine). */
export async function fetchHistory(ticker: string): Promise<History | null> {
  const r = await fetch(apiUrl(`/history?ticker=${encodeURIComponent(ticker)}`))
  if (r.status === 404) return null
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return (await r.json()) as History
}
