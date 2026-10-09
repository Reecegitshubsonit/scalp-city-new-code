import { apiUrl } from './socket'

export async function postPause(bot: string, paused: boolean): Promise<void> {
  const r = await fetch(apiUrl('/control/pause'), {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bot, paused }),
  })
  if (r.status === 404) throw new Error('unknown bot')
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
}
