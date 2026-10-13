import { describe, it, expect } from 'vitest'
import { levelsAt, tradeLevels } from '../src/model/tradeLevels'
import type { BotEvent } from '../src/model/types'

const T = (m: number) => `2026-10-13T09:${String(m).padStart(2, '0')}:00-04:00`
let seq = 0
const ev = (m: number, bot: string, kind: string, reason_code: string, reason_text: string, state = 'managing', price = 740): BotEvent =>
  ({ seq: ++seq, time: T(m), bot, ticker: bot.split('-')[0], kind, state, reason_code, reason_text, inputs: { price }, charge_pct: null } as BotEvent)

const day = [
  ev(31, 'QQQ-VWAP', 'state_change', 'SIGNAL', 'PUT signal at 740.18', 'fired', 740.18),
  ev(31, 'QQQ-VWAP', 'fill', 'ENTRY_FILL', 'bought 10 QQQ261014P00740000 @ 3.63 (broker)', 'managing', 740.18),
  ev(32, 'QQQ-VWAP', 'tick', 'HOLDING', 'PUT held, stop 740.83, target 738.87'),
  ev(33, 'QQQ-VWAP', 'state_change', 'EXIT_RETRY', 'exit not filled (NO_FILL); retrying next bar'),
  ev(34, 'QQQ-VWAP', 'trade_closed', 'COOLDOWN', 'trade P&L -180.00', 'cooldown'),
  ev(40, 'QQQ-VWAP', 'state_change', 'SIGNAL', 'CALL signal at 741.00', 'fired', 741),
  ev(40, 'QQQ-VWAP', 'fill', 'ENTRY_FILL', 'bought 10 QQQ261014C00741000 @ 2.00 (broker)', 'managing', 741),
  ev(41, 'QQQ-VWAP', 'tick', 'HOLDING', 'CALL held, stop 740.30, target 742.40'),
]

describe('tradeLevels', () => {
  it('gives every trade its own stop and target, entry to exit', () => {
    const lv = tradeLevels(day)
    expect(lv).toHaveLength(2)
    expect(lv[0]).toMatchObject({ bot: 'QQQ-VWAP', side: 'PUT', entry: T(31), exit: T(34), entryPrice: 740.18, stop: 740.83, target: 738.87 })
    expect(lv[1]).toMatchObject({ side: 'CALL', entry: T(40), exit: null, stop: 740.3, target: 742.4 })
  })
  it('picks up a trade recovered after an engine restart', () => {
    const lv = tradeLevels([ev(50, 'SPY-EMA50', 'state_change', 'HOLDING', 'CALL recovered, stop 777.50, target 778.16')])
    expect(lv[0]).toMatchObject({ bot: 'SPY-EMA50', side: 'CALL', exit: null, stop: 777.5 })
  })
  it('replay: hides later trades and reopens trades closed after the position', () => {
    const at = levelsAt(tradeLevels(day), Date.parse(T(32)))
    expect(at).toHaveLength(1)
    expect(at[0].exit).toBeNull()
  })
})
