import { describe, it, expect } from 'vitest'
import { botsOfTicker, tradesOfTicker, eventsOfTicker, tickerPnl } from '../src/model/tower'
import type { BotEvent, BotRow } from '../src/model/types'

const row = (bot: string, pnl_day = 0, trades = 0): BotRow => ({
  bot, ticker: bot.split('-')[0], state: 'idle', reason_code: '', reason_text: '', charge_pct: null, inputs: {}, time: null,
  pnl_day, trades, paused: false, side: null, sideSource: 'none', exit_code: null,
})
const rows = [row('SPY-RANGE', 5), row('QQQ-RANGE', 30, 2), row('QQQ-VWAP', -10, 1), row('IWM-VWAP', 99), row('QQQ-EMA50', 7, 3)]

describe('tower scoping', () => {
  it('botsOfTicker keeps only that ticker, in VWAP, EMA50, RANGE order', () => {
    expect(botsOfTicker(rows, 'QQQ').map(r => r.bot)).toEqual(['QQQ-VWAP', 'QQQ-EMA50', 'QQQ-RANGE'])
    expect(botsOfTicker(rows, 'IWM').map(r => r.bot)).toEqual(['IWM-VWAP'])
    expect(botsOfTicker(rows, 'ZZZ')).toEqual([])
  })
  it('tickerPnl sums only that ticker', () => {
    expect(tickerPnl(rows, 'QQQ')).toBe(27)
    expect(tickerPnl(rows, 'SPY')).toBe(5)
    expect(tickerPnl(rows, 'ZZZ')).toBe(0)
  })
  it('tradesOfTicker and eventsOfTicker filter by ticker', () => {
    const ts = [{ ticker: 'QQQ', n: 1 }, { ticker: 'SPY', n: 2 }, { ticker: 'QQQ', n: 3 }]
    expect(tradesOfTicker(ts, 'QQQ').map(t => t.n)).toEqual([1, 3])
    const ev = [{ ticker: 'IWM', seq: 1 }, { ticker: 'QQQ', seq: 2 }] as unknown as BotEvent[]
    expect(eventsOfTicker(ev, 'QQQ').map(e => e.seq)).toEqual([2])
  })
})
