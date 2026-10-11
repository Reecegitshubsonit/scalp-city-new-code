import type { Candle } from './history'
import { formatPnl, formatTime } from './format'
import { plainReason } from './reasons'
import type { Trade } from './trades'
import { REPLAY_SPEEDS } from '../net/useReplay'

/** "WINNING +$329.00" / "LOSING -$2,072.00": the standing label on the backtest room's 1-minute chart. */
export const standingLabel = (pnl: number): string =>
  pnl > 0 ? `WINNING ${formatPnl(pnl)}` : pnl < 0 ? `LOSING ${formatPnl(pnl)}` : `FLAT ${formatPnl(0)}`

/** Colour of a wall chart's price line: up from the day's open = green, down = red. */
export function lineTone(candles: Candle[]): 'up' | 'down' | 'flat' {
  if (candles.length < 1) return 'flat'
  const d = candles[candles.length - 1].close - candles[0].open
  return d > 0 ? 'up' : d < 0 ? 'down' : 'flat'
}

/** "Wed 10/7 · 11:04 AM ET" for a replay position. */
export function replayClockLabel(ms: number): string {
  const p = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', weekday: 'short', month: 'numeric', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true }).formatToParts(ms)
  const g = (t: string) => p.find(x => x.type === t)?.value ?? ''
  return `${g('weekday')} ${g('month')}/${g('day')} · ${g('hour')}:${g('minute')} ${g('dayPeriod')} ET`
}

export const nextSpeed = (cur: number): number => {
  const i = REPLAY_SPEEDS.indexOf(cur)
  return REPLAY_SPEEDS[(i + 1) % REPLAY_SPEEDS.length]
}

/** Latest trades first, as one-line sentences for the EARNED screen. */
export function earnedLines(trades: Trade[], n: number): string[] {
  return trades.slice(-n).reverse().map(t =>
    `${formatTime(t.exit_time).slice(0, 5)} ${t.bot} ${t.pnl >= 0 ? 'profit locked' : plainReason(t.exit_code ?? '').replace('Exit: ', '').toLowerCase() || 'closed'} ${formatPnl(t.pnl)}`)
}
