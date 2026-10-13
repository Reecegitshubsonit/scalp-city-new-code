import type { BotRow, Side } from './types'
import { formatPnl } from './format'

export const COLORS = {
  CALL: '#19f5a0', PUT: '#ff3b6b', NEUTRAL: '#b9a7ff',
  idle: '#3a3f6b', cooldown: '#3d8bff', locked: '#ffb020', paused: '#8a90a8', stale: '#ff2d2d',
  goal: '#ffd23f', lossLimit: '#9e1030',   // locked for the day: daily goal hit (gold) vs daily loss limit hit (dark crimson)
} as const

export const sideColor = (s: Side | null): string => (s === 'CALL' ? COLORS.CALL : s === 'PUT' ? COLORS.PUT : COLORS.NEUTRAL)

export const STATE_LABEL: Record<string, string> = {
  idle: 'Idle', forming: 'Charging', fired: 'Fired', managing: 'In trade', exiting: 'Exiting',
  cooldown: 'Cooldown', locked: 'Locked', paused: 'Paused', stale: 'Stale data',
}
export const STATE_ICON: Record<string, string> = {
  idle: '○', forming: '▲', fired: '✦', managing: '●', exiting: '◆', cooldown: '❄', locked: '■', paused: '❚❚', stale: '!',
}
export const stateLabel = (s: string) => STATE_LABEL[s] ?? s
export const stateIcon = (s: string) => STATE_ICON[s] ?? '?'

export const beamFraction = (c: number | null): number =>
  c == null || Number.isNaN(c) ? 0 : Math.min(1, Math.max(0, c / 100))

export type Effect = 'none' | 'ring' | 'ring-static' | 'pulse' | 'flicker'
export interface TowerVisual { color: string; glow: number; beam: number; effect: Effect; hatched: boolean; label: string | null }

export function visualFor(row: BotRow, reduced: boolean): TowerVisual {
  const sc = sideColor(row.side)
  const base: TowerVisual = { color: COLORS.idle, glow: 0.15, beam: 0, effect: 'none', hatched: false, label: null }
  switch (row.state) {
    case 'forming': return { ...base, color: sc, glow: 0.5, beam: beamFraction(row.charge_pct) }
    case 'fired': return { ...base, color: sc, glow: 1, beam: 1, effect: reduced ? 'ring-static' : 'ring' }
    case 'managing': return { ...base, color: sc, glow: 0.8, label: formatPnl(row.pnl_day) }
    case 'exiting': return { ...base, color: sc, glow: 0.8, effect: reduced ? 'none' : 'pulse' }
    case 'cooldown': return { ...base, color: COLORS.cooldown, glow: 0.45 }
    case 'locked':
      return row.reason_code === 'DAILY_LOSS' ? { ...base, color: COLORS.lossLimit, glow: 0.5, label: 'LOSS LIMIT' }
        : row.reason_code === 'DAILY_GOAL' ? { ...base, color: COLORS.goal, glow: 0.6, label: 'GOAL HIT' }
        : { ...base, color: COLORS.locked, glow: 0.5, label: 'LOCKED' }
    case 'paused': return { ...base, color: COLORS.paused, glow: 0.1, hatched: true, label: 'PAUSED' }
    case 'stale': return { ...base, color: COLORS.stale, glow: 0.7, effect: reduced ? 'none' : 'flicker', label: 'STALE' }
    default: return base
  }
}
