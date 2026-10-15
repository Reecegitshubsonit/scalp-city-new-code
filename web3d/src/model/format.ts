export const SLOW_SEC = 90
export const STALE_SEC = 180

export function formatPnl(n: number): string {
  const abs = Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return n > 0 ? `+$${abs}` : n < 0 ? `-$${abs}` : `$${abs}`
}
export const formatPct = (n: number | null | undefined) => (n == null ? '-' : `${Math.round(n)}%`)
export const formatNum = (n: number | undefined | null, d = 2) => (typeof n === 'number' ? n.toFixed(d) : '-')
/** Volume as "129.9K" or "2.98M". */
export const formatVolume = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : `${Math.round(n)}`)
export const formatTime = (iso: string | null) => (iso && iso.length >= 19 ? iso.slice(11, 19) : '-')

function etParts(now: Date) {
  const p = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York', weekday: 'short', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  }).formatToParts(now)
  const get = (t: string) => p.find(x => x.type === t)!.value
  return { wd: get('weekday'), sec: (+get('hour') % 24) * 3600 + +get('minute') * 60 + +get('second') }
}

export type Phase = { phase: 'pre' | 'open' | 'closed'; label: string; seconds: number }
export function marketPhase(now: Date): Phase {
  const { wd, sec } = etParts(now)
  const OPEN = 9.5 * 3600, CLOSE = 16 * 3600
  if (wd === 'Sat' || wd === 'Sun') return { phase: 'closed', label: 'Closed (weekend)', seconds: 0 }
  if (sec < OPEN) return { phase: 'pre', label: 'Opens 9:30 ET', seconds: OPEN - sec }
  if (sec < CLOSE) return { phase: 'open', label: 'Market open', seconds: CLOSE - sec }
  return { phase: 'closed', label: 'Market closed', seconds: 0 }
}

export type Fresh = 'live' | 'slow' | 'stale' | 'closed' | 'none'
export function freshness(ageSec: number | null, p: Pick<Phase, 'phase'>): Fresh {
  if (ageSec == null) return 'none'
  if (p.phase !== 'open') return ageSec > STALE_SEC ? 'closed' : 'live'
  return ageSec > STALE_SEC ? 'stale' : ageSec > SLOW_SEC ? 'slow' : 'live'
}
