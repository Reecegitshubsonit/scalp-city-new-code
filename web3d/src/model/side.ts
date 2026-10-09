import type { Inputs, Side } from './types'

export function inferSide(bot: string, inputs: Inputs): Side | null {
  const trigger = bot.split('-')[1]
  const level = trigger === 'VWAP' ? inputs.vwap : trigger === 'EMA50' ? inputs.ema50 : undefined
  const price = inputs.price
  if (typeof level !== 'number' || typeof price !== 'number' || price === level) return null
  return price < level ? 'CALL' : 'PUT'
}

export function parseSignalSide(text: string): Side | null {
  const m = /\b(CALL|PUT)\b/.exec(text ?? '')
  return m ? (m[1] as Side) : null
}
