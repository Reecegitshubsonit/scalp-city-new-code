import type { Side } from './types'

/** The entry effect is shown at least this long (wall clock), even if the bot leaves the fired state in the same bar. */
export const FIRE_SECONDS = 2.5

export const fireText = (side: Side | null): string => (side ? `FIRE ${side}` : 'FIRE')

const clamp01 = (x: number) => Math.min(1, Math.max(0, x))
const easeOut = (x: number) => 1 - (1 - clamp01(x)) ** 3

export interface FireFrame {
  active: boolean
  disc: { scale: number; opacity: number }     // big additive disc on the ground
  ring1: { scale: number; opacity: number }
  ring2: { scale: number; opacity: number }
  beam: { width: number; opacity: number }     // tall flash along the beam
  glow: { scale: number; opacity: number }     // soft halo, the cheap stand-in for bloom
  label: { rise: number; scale: number; opacity: number }
  flash: number                                // 0..1, room/scanner/desk light flash
}

const OFF: FireFrame = {
  active: false, disc: { scale: 1, opacity: 0 }, ring1: { scale: 1, opacity: 0 }, ring2: { scale: 1, opacity: 0 },
  beam: { width: 1, opacity: 0 }, glow: { scale: 1, opacity: 0 }, label: { rise: 0, scale: 1, opacity: 0 }, flash: 0,
}

/** Pure animation curve of one fire effect, t seconds after the entry. Reduced motion gives a static ring and label and no flashing. */
export function fireFrame(t: number, reduced: boolean): FireFrame {
  if (t < 0 || t > FIRE_SECONDS) return OFF
  const fade = clamp01((FIRE_SECONDS - t) / 0.5)            // everything fades out over the last half second
  if (reduced) {
    return {
      active: true, disc: { scale: 3, opacity: 0.35 * fade }, ring1: { scale: 3.2, opacity: 0.9 * fade }, ring2: { scale: 1, opacity: 0 },
      beam: { width: 1, opacity: 0 }, glow: { scale: 1, opacity: 0 }, label: { rise: 0, scale: 1, opacity: fade }, flash: 0,
    }
  }
  const e = easeOut(t / 1.3)
  const decay = Math.exp(-t * 2.4)
  return {
    active: true,
    disc: { scale: 1 + 7 * e, opacity: clamp01(1 - t / 1.5) * 0.85 },
    ring1: { scale: 1 + 8 * e, opacity: clamp01(1 - t / 1.6) },
    ring2: { scale: 1 + 8 * easeOut((t - 0.25) / 1.3), opacity: t < 0.25 ? 0 : clamp01(1 - (t - 0.25) / 1.4) * 0.8 },
    beam: { width: 1 + 3.5 * decay, opacity: decay },
    glow: { scale: 4 + 6 * e, opacity: clamp01(decay * 1.1) * 0.9 },
    label: { rise: 1.2 * easeOut(t / 0.9), scale: t < 0.25 ? 0.5 + 2 * (t / 0.25) * 0.65 : 1.1 - 0.1 * clamp01((t - 0.25) / 0.3), opacity: Math.min(clamp01(t / 0.12), fade) },
    flash: clamp01(1 - t / 0.7),
  }
}
