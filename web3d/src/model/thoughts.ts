import type { BotEvent } from './types'
import { formatPnl } from './format'
import { plainReason } from './reasons'

/** One plain sentence for an event, as shown in the thoughts feed and the scanner. */
export function thoughtText(ev: BotEvent): string {
  switch (ev.kind) {
    case 'order_rejected': return 'order rejected, standing down'
    case 'order_sent': {
      const q = ev.qty != null ? `x${ev.qty}` : ''
      const rest = [ev.contract, q].filter(Boolean).join(' ')
      return rest ? `order sent: ${rest}` : 'order sent'
    }
    case 'fill': {
      const px = typeof ev.fill_price === 'number' ? ` @ ${ev.fill_price.toFixed(2)}` : ''
      const src = ev.fill_source ? ` (${ev.fill_source})` : ''
      if (ev.reason_code === 'ENTRY_FILL') return `entry filled${px}${src}`
      if (ev.reason_code === 'EXIT_FILL') return `exit filled${px}${src}`
      if (ev.reason_code === 'PARTIAL_FILL') return `partial fill${px}${src}`
      return `${plainReason(ev.reason_code).toLowerCase()}${px}`
    }
    case 'trade_closed':
      if (typeof ev.pnl !== 'number') return 'trade closed'
      return ev.pnl > 0 ? `profit locked ${formatPnl(ev.pnl)}` : ev.pnl < 0 ? `stopped out ${formatPnl(ev.pnl)}` : 'closed flat'
    case 'feed_stale': return 'data feed went stale, standing by'
    case 'feed_fresh': return 'data is fresh again, resuming'
    case 'control':
      if (ev.paused === true) return 'paused by you'
      if (ev.paused === false) return 'resumed'
      break
  }
  const pct = ev.charge_pct != null ? `, ${Math.round(ev.charge_pct)}% charged` : ''
  if (ev.state === 'forming') return `setup forming${ev.side ? ': ' + ev.side : ''}${pct}`
  if (ev.state === 'idle' && ev.prev_state === 'forming') return 'setup faded, standing down'
  if (ev.state === 'fired' && ev.reason_code === 'SIGNAL') return `FIRE${ev.side ? ' ' + ev.side : ''}: ${ev.reason_text}`
  if (ev.state === 'locked') {
    if (ev.reason_code === 'DAILY_GOAL') return 'daily goal reached, clocking out'
    if (ev.reason_code === 'DAILY_LOSS') return 'daily loss limit hit, standing down'
  }
  if (ev.state === 'cooldown' && ev.reason_code === 'COOLDOWN') return 'cooling down before the next setup'
  const plain = plainReason(ev.reason_code)
  if (plain !== ev.reason_code) return plain
  return ev.reason_text ? `${ev.reason_code}: ${ev.reason_text}` : ev.reason_code
}
