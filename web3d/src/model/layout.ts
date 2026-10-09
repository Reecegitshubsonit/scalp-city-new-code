export const TICKERS = ['QQQ', 'SPY', 'IWM'] as const
export const TRIGGERS = ['VWAP', 'EMA50', 'RANGE'] as const
export const botId = (t: string, k: string) => `${t}-${k}`
export const ALL_BOTS: string[] = TICKERS.flatMap(t => TRIGGERS.map(k => botId(t, k)))

export function parseBotId(id: string): { ticker: string; trigger: string } | null {
  const m = /^([A-Z]+)-([A-Z0-9]+)$/.exec(id)
  return m ? { ticker: m[1], trigger: m[2] } : null
}

export function towerPosition(ti: number, ki: number): [number, number, number] {
  const a = (ti * 2 * Math.PI) / 3 + Math.PI / 2
  const R = 7
  const off = (ki - 1) * 2.4
  return [Math.cos(a) * R - Math.sin(a) * off, 0, Math.sin(a) * R + Math.cos(a) * off]
}
