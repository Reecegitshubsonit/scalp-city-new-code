import * as THREE from 'three'

const cache = new Map<string, THREE.CanvasTexture>()

function rng(seed: number) {
  let s = seed >>> 0
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296 }
}

export const hashStr = (s: string) => { let h = 2166136261; for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619); return h >>> 0 }

/** Procedural window grid (white = lit). Hatched variant draws diagonal stripes instead. */
export function windowTexture(seed: number, hatched: boolean): THREE.CanvasTexture {
  const key = `${seed}:${hatched}`
  const hit = cache.get(key)
  if (hit) return hit
  const W = 128, H = 256
  const c = document.createElement('canvas'); c.width = W; c.height = H
  const g = c.getContext('2d')!
  g.fillStyle = '#000'; g.fillRect(0, 0, W, H)
  if (hatched) {
    g.strokeStyle = '#fff'; g.lineWidth = 5
    for (let x = -H; x < W; x += 20) { g.beginPath(); g.moveTo(x, H); g.lineTo(x + H, 0); g.stroke() }
  } else {
    const r = rng(seed)
    const cols = 8, rows = 18, cw = W / cols, ch = H / rows
    for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++) {
      if (r() < 0.6) { g.fillStyle = r() < 0.15 ? '#9a9' : '#fff'; g.fillRect(i * cw + 3, j * ch + 3, cw - 6, ch - 6) }
    }
  }
  const t = new THREE.CanvasTexture(c)
  t.colorSpace = THREE.SRGBColorSpace
  cache.set(key, t)
  return t
}
