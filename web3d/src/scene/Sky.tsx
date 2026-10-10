import { useMemo } from 'react'
import * as THREE from 'three'
import { windowTexture } from './textures'

/** Night sky: indigo overhead fading to a purple horizon, plus a field of white stars. Never fogged. */
export function SkyDome({ center = [0, 0, 0], radius = 150 }: { center?: [number, number, number]; radius?: number }) {
  const { geo, stars } = useMemo(() => {
    const g = new THREE.SphereGeometry(radius, 32, 24)
    const pos = g.getAttribute('position')
    const colors = new Float32Array(pos.count * 3)
    const top = new THREE.Color('#080624'), horizon = new THREE.Color('#4a1f8c'), low = new THREE.Color('#0b0830')
    const c = new THREE.Color()
    for (let i = 0; i < pos.count; i++) {
      const t = pos.getY(i) / radius          // -1 below, 0 horizon, 1 zenith
      if (t >= 0) c.copy(horizon).lerp(top, Math.pow(t, 0.55))
      else c.copy(horizon).lerp(low, Math.min(1, -t * 4))
      colors.set([c.r, c.g, c.b], i * 3)
    }
    g.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    let s = 12345
    const r = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296 }
    const pts = new Float32Array(900 * 3)
    for (let i = 0; i < 900; i++) {
      const th = r() * Math.PI * 2, ph = Math.acos(0.04 + r() * 0.96)   // upper hemisphere only
      const rr = radius * 0.96
      pts.set([rr * Math.sin(ph) * Math.cos(th), rr * Math.cos(ph), rr * Math.sin(ph) * Math.sin(th)], i * 3)
    }
    const sg = new THREE.BufferGeometry()
    sg.setAttribute('position', new THREE.BufferAttribute(pts, 3))
    return { geo: g, stars: sg }
  }, [radius])
  return (
    <group position={center}>
      <mesh geometry={geo} renderOrder={-2}>
        <meshBasicMaterial vertexColors side={THREE.BackSide} fog={false} depthWrite={false} toneMapped={false} />
      </mesh>
      <points geometry={stars} renderOrder={-1}>
        <pointsMaterial color="#ffffff" size={2.2} sizeAttenuation={false} fog={false} transparent opacity={0.9} depthWrite={false} toneMapped={false} />
      </points>
    </group>
  )
}

/** Ring of lit towers in the distance. */
export function Skyline({ center = [0, 0, 0], rMin = 26, rMax = 34, count = 56, maxH = 8 }: {
  center?: [number, number, number]; rMin?: number; rMax?: number; count?: number; maxH?: number
}) {
  const items = useMemo(() => {
    const out: Array<{ x: number; z: number; w: number; h: number; seed: number }> = []
    let s = 7
    const r = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296 }
    for (let i = 0; i < count; i++) {
      const a = (i / count) * Math.PI * 2, d = rMin + r() * (rMax - rMin)
      out.push({ x: Math.cos(a) * d, z: Math.sin(a) * d, w: 1.2 + r() * 1.6, h: 2 + r() * (maxH - 2), seed: i + 1 })
    }
    return out
  }, [rMin, rMax, count, maxH])
  const tex = useMemo(() => windowTexture(99, false), [])
  return (
    <group position={center}>
      {items.map(b => (
        <mesh key={b.seed} position={[b.x, b.h / 2, b.z]}>
          <boxGeometry args={[b.w, b.h, b.w]} />
          <meshStandardMaterial color="#0e0b33" emissive="#6a5cff" emissiveMap={tex} emissiveIntensity={0.35} />
        </mesh>
      ))}
    </group>
  )
}
