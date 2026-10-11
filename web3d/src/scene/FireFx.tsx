import { useEffect, useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { FIRE_SECONDS, fireFrame, fireText, type FireFrame } from '../model/fire'
import type { Side } from '../model/types'
import { sideColor } from '../model/visual'

/** Seconds since the latest fire, or -1. Starts when `seq` changes after mount (a fire already on record at load stays quiet). */
export function useFireClock(seq: number | undefined, reduced: boolean, scope = ''): { t: React.MutableRefObject<number>; frame: React.MutableRefObject<FireFrame> } {
  const t = useRef(-1)
  const frame = useRef<FireFrame>(fireFrame(-1, reduced))
  const prev = useRef(seq)
  const prevScope = useRef(scope)
  useEffect(() => {
    if (scope !== prevScope.current) { prevScope.current = scope; prev.current = seq; return }   // another room: its latest fire is old news
    if (seq !== prev.current) { prev.current = seq; t.current = 0 }
  }, [seq, scope])
  useFrame((_, dt) => {
    if (t.current >= 0) {
      t.current += Math.min(dt, 0.1)
      if (t.current > FIRE_SECONDS) t.current = -1
    }
    frame.current = fireFrame(t.current, reduced)
  })
  return { t, frame }
}

const glowTex = (() => {
  let tex: THREE.CanvasTexture | null = null
  return () => {
    if (tex) return tex
    const c = document.createElement('canvas'); c.width = c.height = 128
    const g = c.getContext('2d')!, grad = g.createRadialGradient(64, 64, 0, 64, 64, 64)
    grad.addColorStop(0, 'rgba(255,255,255,1)'); grad.addColorStop(0.25, 'rgba(255,255,255,0.55)'); grad.addColorStop(1, 'rgba(255,255,255,0)')
    g.fillStyle = grad; g.fillRect(0, 0, 128, 128)
    tex = new THREE.CanvasTexture(c)
    return tex
  }
})()

const labelTex = new Map<string, THREE.CanvasTexture>()
function textTexture(text: string, color: string): THREE.CanvasTexture {
  const key = `${text}|${color}`
  const hit = labelTex.get(key)
  if (hit) return hit
  const c = document.createElement('canvas'); c.width = 768; c.height = 192
  const g = c.getContext('2d')!
  g.textAlign = 'center'; g.font = 'bold 120px system-ui, sans-serif'
  g.lineWidth = 14; g.strokeStyle = '#05031e'; g.strokeText(text, 384, 135)
  g.shadowColor = color; g.shadowBlur = 30; g.fillStyle = color; g.fillText(text, 384, 135)
  g.shadowBlur = 0; g.fillStyle = '#ffffff'; g.globalAlpha = 0.55; g.fillText(text, 384, 135)
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace
  labelTex.set(key, tex)
  return tex
}

/** "FIRE CALL" / "FIRE PUT" burst: faces the camera, pops in, rises and fades. */
export function FireLabel({ frame, side, base, size = [4.4, 1.1] }: { frame: React.MutableRefObject<FireFrame>; side: Side | null; base: [number, number, number]; size?: [number, number] }) {
  const mesh = useRef<THREE.Mesh>(null)
  const tex = useMemo(() => textTexture(fireText(side), sideColor(side)), [side])
  useFrame(({ camera }) => {
    const m = mesh.current; if (!m) return
    const f = frame.current.label
    m.visible = frame.current.active
    if (!m.visible) return
    m.quaternion.copy(camera.quaternion)
    m.position.set(base[0], base[1] + f.rise, base[2])
    m.scale.set(f.scale, f.scale, 1)
    ;(m.material as THREE.MeshBasicMaterial).opacity = f.opacity
  })
  return (
    <mesh ref={mesh} visible={false} renderOrder={10}>
      <planeGeometry args={size} />
      <meshBasicMaterial map={tex} transparent toneMapped={false} depthWrite={false} depthTest={false} />
    </mesh>
  )
}

/** Entry effect at a tower's base: expanding glowing disc and two rings, a tall bright beam flash, a halo, and the FIRE label. */
export function FireBurst({ seq, side, reduced, color, labelY, beamHeight }: { seq: number | undefined; side: Side | null; reduced: boolean; color: THREE.Color; labelY: number; beamHeight: number }) {
  const { frame } = useFireClock(seq, reduced)
  const disc = useRef<THREE.Mesh>(null), r1 = useRef<THREE.Mesh>(null), r2 = useRef<THREE.Mesh>(null)
  const beam = useRef<THREE.Mesh>(null), glow = useRef<THREE.Mesh>(null)
  const hot = useMemo(() => color.clone().lerp(new THREE.Color('#ffffff'), 0.25).multiplyScalar(1.5), [color])
  const halo = useMemo(() => glowTex(), [])
  useFrame(({ camera }) => {
    const f = frame.current
    const put = (m: THREE.Mesh | null, o: { scale: number; opacity: number }) => {
      if (!m) return
      m.visible = f.active && o.opacity > 0.01
      if (!m.visible) return
      m.scale.set(o.scale, o.scale, 1)
      ;(m.material as THREE.MeshBasicMaterial).opacity = o.opacity
    }
    put(disc.current, f.disc); put(r1.current, f.ring1); put(r2.current, f.ring2)
    if (beam.current) {
      beam.current.visible = f.active && f.beam.opacity > 0.01
      beam.current.scale.set(f.beam.width, 1, f.beam.width)
      ;(beam.current.material as THREE.MeshBasicMaterial).opacity = f.beam.opacity
    }
    if (glow.current) {
      glow.current.visible = f.active && f.glow.opacity > 0.01
      glow.current.quaternion.copy(camera.quaternion)
      glow.current.scale.set(f.glow.scale, f.glow.scale, 1)
      ;(glow.current.material as THREE.MeshBasicMaterial).opacity = f.glow.opacity
    }
  })
  const add = { transparent: true, toneMapped: false, depthWrite: false, blending: THREE.AdditiveBlending } as const
  return (
    <group>
      <mesh ref={disc} visible={false} position={[0, 0.12, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[1.3, 48]} /><meshBasicMaterial color={hot} {...add} />
      </mesh>
      <mesh ref={r1} visible={false} position={[0, 0.2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <torusGeometry args={[1.3, 0.12, 8, 64]} /><meshBasicMaterial color={hot} {...add} />
      </mesh>
      <mesh ref={r2} visible={false} position={[0, 0.22, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <torusGeometry args={[1.3, 0.07, 8, 64]} /><meshBasicMaterial color={color} {...add} />
      </mesh>
      <mesh ref={beam} visible={false} position={[0, beamHeight / 2, 0]}>
        <cylinderGeometry args={[0.55, 0.55, beamHeight, 16, 1, true]} /><meshBasicMaterial color={hot} side={THREE.DoubleSide} {...add} />
      </mesh>
      <mesh ref={glow} visible={false} position={[0, 0.9, 0]}>
        <planeGeometry args={[1, 1]} /><meshBasicMaterial map={halo} color={hot} {...add} />
      </mesh>
      <FireLabel frame={frame} side={side} base={[0, labelY, 0]} />
    </group>
  )
}
