export type Side = 'CALL' | 'PUT'
export type SideSource = 'explicit' | 'signal' | 'inferred' | 'none'
export interface Inputs { price?: number; vwap?: number; ema9?: number; ema21?: number; ema50?: number; atr?: number; distance_atr?: number }

export interface BotEvent {
  seq: number; time: string; mode?: string; bot: string; ticker: string; kind: string
  state: string; reason_code: string; reason_text: string; inputs: Inputs; charge_pct: number | null
  side?: Side | null
  contract?: string; qty?: number; fill_price?: number; fill_source?: string
  pnl?: number; pnl_day?: number; trades?: number; paused?: boolean
}
export interface SnapshotBot {
  bot: string; ticker: string; state: string; reason_code: string; reason_text: string
  charge_pct: number | null; inputs: Inputs; time: string | null; pnl_day: number; trades: number; paused: boolean
  side?: Side | null
}
export interface BotRow {
  bot: string; ticker: string; state: string; reason_code: string; reason_text: string
  charge_pct: number | null; inputs: Inputs; time: string | null; pnl_day: number; trades: number; paused: boolean
  side: Side | null; sideSource: SideSource
}
export type ServerMsg =
  | { type: 'snapshot'; bots: Record<string, SnapshotBot>; last_seq: number }
  | { type: 'event'; event: BotEvent }
export interface TickPoint { time: string; price: number }
export interface Mark { time: string; price: number; type: 'entry' | 'exit'; bot: string }
export interface AppState {
  bots: Record<string, BotRow>; lastSeq: number; feed: BotEvent[]
  ticks: Record<string, TickPoint[]>; marks: Record<string, Mark[]>; lastEventAt: number | null
}
