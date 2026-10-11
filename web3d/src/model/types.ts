export type Side = 'CALL' | 'PUT'
export type SideSource = 'explicit' | 'signal' | 'inferred' | 'none'
export interface Inputs { price?: number; vwap?: number; ema9?: number; ema21?: number; ema50?: number; atr?: number; distance_atr?: number }

export interface BotEvent {
  seq: number; time: string; mode?: string; bot: string; ticker: string; kind: string
  state: string; reason_code: string; reason_text: string; inputs: Inputs; charge_pct: number | null
  side?: Side | null
  contract?: string; qty?: number; fill_price?: number; fill_source?: string
  pnl?: number; pnl_day?: number; trades?: number; paused?: boolean
  prev_state?: string   // added by the view: the bot's state before this event
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
  exit_code: string | null   // reason code of the last exit, kept for trade summaries
}
export type ServerMsg =
  | { type: 'snapshot'; bots: Record<string, SnapshotBot>; last_seq: number }
  | { type: 'event'; event: BotEvent }
export interface TickPoint { time: string; price: number; vwap?: number; ema50?: number }
export interface Mark { time: string; price: number; type: 'entry' | 'exit'; bot: string; side: Side | null; pnl?: number }
export interface TradeRec { time: string; bot: string; ticker: string; pnl: number; exit_code: string | null; side: Side | null }
/** The latest entry of a bot: kept even when fired and managing arrive in the same batch, so the view can play the fire effect. */
export interface Fire { seq: number; side: Side | null; time: string; filled: boolean }
export interface AppState {
  bots: Record<string, BotRow>; lastSeq: number; feed: BotEvent[]
  ticks: Record<string, TickPoint[]>; marks: Record<string, Mark[]>; trades: TradeRec[]; mode: string | null; lastEventAt: number | null
  fires: Record<string, Fire>
}
