import { describe, it, expect } from 'vitest'
import { countAt, replayStateAt, eventTimes, placeholderSnapshot } from '../src/model/replay'
import type { BotEvent } from '../src/model/types'

const ev = (seq: number, time: string, o: Partial<BotEvent> = {}): BotEvent => ({
  seq, time, bot: 'QQQ-VWAP', ticker: 'QQQ', kind: 'tick', state: 'idle', reason_code: 'WATCHING', reason_text: '',
  inputs: { price: 100 + seq }, charge_pct: null, mode: 'replay', ...o,
})
const events = [
  ev(1, '2026-10-07T09:31:00-04:00'),
  ev(2, '2026-10-07T09:32:00-04:00', { state: 'forming', kind: 'state_change', charge_pct: 40 }),
  ev(3, '2026-10-07T09:33:00-04:00', { kind: 'trade_closed', state: 'cooldown', pnl: 55, pnl_day: 55, trades: 1 }),
]

describe('replay helpers', () => {
  it('placeholder snapshot has the nine bots', () => {
    const s = placeholderSnapshot()
    expect(s.type).toBe('snapshot')
    expect(Object.keys((s as { bots: object }).bots)).toHaveLength(9)
  })
  it('countAt counts events at or before a time', () => {
    const t = eventTimes(events)
    expect(countAt(t, Date.parse('2026-10-07T09:30:00-04:00'))).toBe(0)
    expect(countAt(t, Date.parse('2026-10-07T09:32:00-04:00'))).toBe(2)
    expect(countAt(t, Date.parse('2026-10-07T23:00:00-04:00'))).toBe(3)
  })
  it('replayStateAt reduces the first N events from scratch, so scrubbing back works', () => {
    const full = replayStateAt(events, 3)
    expect(full.bots['QQQ-VWAP'].pnl_day).toBe(55); expect(full.trades).toHaveLength(1)
    const early = replayStateAt(events, 2)
    expect(early.bots['QQQ-VWAP'].state).toBe('forming'); expect(early.bots['QQQ-VWAP'].pnl_day).toBe(0)
    expect(replayStateAt(events, 0).feed).toEqual([])
    expect(full.mode).toBe('replay')
  })
})
