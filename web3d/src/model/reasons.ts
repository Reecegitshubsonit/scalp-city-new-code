const REASONS: Record<string, string> = {
  OUTSIDE_WINDOW: "Outside this bot's trading window",
  RANGE_FORMING: 'Opening range still forming',
  WARMING_UP: 'Warming up indicators',
  NO_RANGE: 'No opening range today',
  WATCHING: 'Watching for a signal',
  CHOP_SQUEEZE: 'Skipped: choppy market (EMA9 and EMA21 squeezed)',
  COOLDOWN: 'Cooling down after a trade',
  DAILY_GOAL: 'Daily profit goal reached, done for today',
  DAILY_LOSS: 'Daily loss limit reached, done for today',
  PAUSED: 'Paused by you',
  STALE_DATA: 'Data feed is stale',
  NO_DATA: 'No data yet',
  SIGNAL: 'Signal fired, entering',
  HOLDING: 'Holding position',
  EXIT_STOP: 'Exit: stop hit',
  EXIT_TARGET: 'Exit: target hit',
  EXIT_TIME: 'Exit: time limit',
  EXIT_LOCK: 'Exit: profit locked',
  EXIT_PARTIAL: 'Exit: partial take',
  EXIT_STALE: 'Exit: data went stale',
  EXIT_BREAKEVEN: 'Exit: breakeven stop',
  ORDER_FAILED: 'Order failed',
  EXIT_RETRY: 'Retrying exit',
  ENTRY_FILL: 'Entry filled',
  EXIT_FILL: 'Exit filled',
  PARTIAL_FILL: 'Partial fill',
}

export function plainReason(code: string): string {
  if (!code) return '-'
  return REASONS[code] ?? code
}
