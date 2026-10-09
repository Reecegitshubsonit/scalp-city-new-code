import { useRef, type ReactNode } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

export interface Anchor { id: string; pos: [number, number, number]; node: ReactNode; className?: string; color?: string; top?: boolean }

/** DOM overlay: one div per label, positioned from 3D anchors by a single projector (see LabelProjector). */
export function LabelLayer({ anchors, refs }: { anchors: Anchor[]; refs: React.MutableRefObject<Record<string, HTMLDivElement | null>> }) {
  return (
    <div className="labels" aria-hidden="true">
      {anchors.map(a => (
        <div key={a.id} ref={el => { refs.current[a.id] = el }} className={`lab ${a.className ?? ''}`} style={a.color ? { color: a.color } : undefined}>{a.node}</div>
      ))}
    </div>
  )
}

/** Inside the Canvas: projects every anchor to screen space once per frame. */
export function LabelProjector({ anchors, refs }: { anchors: Anchor[]; refs: React.MutableRefObject<Record<string, HTMLDivElement | null>> }) {
  const v = useRef(new THREE.Vector3())
  useFrame(({ camera, size }) => {
    for (const a of anchors) {
      const el = refs.current[a.id]
      if (!el) continue
      v.current.set(...a.pos)
      const dist = camera.position.distanceTo(v.current)
      v.current.project(camera)
      if (v.current.z > 1 || v.current.z < -1) { el.style.visibility = 'hidden'; continue }
      const x = (v.current.x * 0.5 + 0.5) * size.width
      const y = (-v.current.y * 0.5 + 0.5) * size.height
      const k = Math.min(1.3, Math.max(0.55, 15 / dist))
      el.style.visibility = 'visible'
      el.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px) translate(-50%, -50%) scale(${k.toFixed(2)})`
      el.style.zIndex = a.top ? '5000' : String(Math.max(1, Math.round(1000 - dist * 10)))
    }
  })
  return null
}
