import { useRef, type ReactNode } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

export interface Anchor { id: string; pos: [number, number, number]; node: ReactNode; className?: string; color?: string; top?: boolean }

/** DOM overlay: one div per label, positioned from 3D anchors by a single projector (see LabelProjector). */
export function LabelLayer({ anchors, refs, hidden = false }: { anchors: Anchor[]; refs: React.MutableRefObject<Record<string, HTMLDivElement | null>>; hidden?: boolean }) {
  return (
    <div className="labels" aria-hidden="true" style={hidden ? { display: 'none' } : undefined}>
      {anchors.map(a => (
        <div key={a.id} ref={el => { refs.current[a.id] = el }} className={`lab ${a.className ?? ''}`} style={a.color ? { color: a.color } : undefined}>{a.node}</div>
      ))}
    </div>
  )
}

/** Inside the Canvas: projects every anchor to screen space once per frame. */
export function LabelProjector({ anchors, refs, enabled = true }: { anchors: Anchor[]; refs: React.MutableRefObject<Record<string, HTMLDivElement | null>>; enabled?: boolean }) {
  const v = useRef(new THREE.Vector3())
  const cache = useRef(new WeakMap<HTMLElement, string>())   // last written transform|z|visibility per label element: unchanged labels cost no DOM write (keyed by element so re-created labels get positioned)
  useFrame(({ camera, size }) => {
    if (!enabled) return
    for (const a of anchors) {
      const el = refs.current[a.id]
      if (!el) continue
      v.current.set(...a.pos)
      const dist = camera.position.distanceTo(v.current)
      v.current.project(camera)
      if (v.current.z > 1 || v.current.z < -1) {
        if (cache.current.get(el) !== 'hidden') { el.style.visibility = 'hidden'; cache.current.set(el, 'hidden') }
        continue
      }
      const x = Math.round((v.current.x * 0.5 + 0.5) * size.width * 2) / 2
      const y = Math.round((-v.current.y * 0.5 + 0.5) * size.height * 2) / 2
      const k = Math.round(Math.min(1.3, Math.max(0.55, 15 / dist)) * 50) / 50
      const z = a.top ? '5000' : String(Math.max(1, Math.round(1000 - dist * 10)))
      const key = `${x}|${y}|${k}|${z}`
      if (cache.current.get(el) === key) continue
      cache.current.set(el, key)
      el.style.visibility = 'visible'
      el.style.transform = `translate(${x}px, ${y}px) translate(-50%, -50%) scale(${k})`
      el.style.zIndex = z
    }
  })
  return null
}
