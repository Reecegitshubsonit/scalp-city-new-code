import { TRIGGERS } from './layout'
import type { BotEvent, BotRow } from './types'

const order = (bot: string) => { const i = (TRIGGERS as readonly string[]).indexOf(bot.split('-')[1]); return i < 0 ? 99 : i }

/** The bots that trade one ticker, in trigger order (VWAP, EMA50, RANGE). A tower room shows only these. */
export const botsOfTicker = (rows: BotRow[], ticker: string): BotRow[] =>
  rows.filter(r => r.ticker === ticker).sort((a, b) => order(a.bot) - order(b.bot))

export const tradesOfTicker = <T extends { ticker: string }>(xs: T[], ticker: string): T[] => xs.filter(x => x.ticker === ticker)

export const eventsOfTicker = (events: BotEvent[], ticker: string): BotEvent[] => events.filter(e => e.ticker === ticker)

export const tickerPnl = (rows: BotRow[], ticker: string): number => rows.filter(r => r.ticker === ticker).reduce((a, r) => a + r.pnl_day, 0)

/** Scanner wall screens are scan0..scan2, one per trigger in trigger order. */
export const scanId = (bot: string): string | null => {
  const i = (TRIGGERS as readonly string[]).indexOf(bot.split('-')[1])
  return i < 0 ? null : `scan${i}`
}
export const botOfScreen = (screen: string, tickerRows: BotRow[]): BotRow | null => {
  const m = /^scan([0-2])$/.exec(screen)
  return m ? tickerRows[Number(m[1])] ?? null : null
}
