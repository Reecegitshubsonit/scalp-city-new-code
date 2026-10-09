import { useEffect, useMemo, useRef } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Html, Line, OrbitControls } from '@react-three/drei'
import { Bloom, EffectComposer } from '@react-three/postprocessing'
import * as THREE from 'three'
import { badgeFor } from '../model/badge'
import { TICKERS, TRIGGERS, towerPosition } from '../model/layout'
import type { BotRow, TradeRec } from '../model/types'
import { Dome } from './Dome'
import { TOWER_TOP, Tower } from './Tower'
import { windowTexture } from './textures'

interface Props {
  rows: BotRow[]; selected: string | null; onSelect: (b: string) => void; onDome: () => void
  reducedMotion: boolean; total: number; lastTrade: Record<string, TradeRec>
}

const POS: Record<string, [number, number, number]> = Object.fromEntries(
  TICKERS.flatMap((t, ti) => TRIGGERS.map((k, ki) => [`${t}-${k}`, towerPosition(ti, ki)] as const)),
)
const HOME_POS = new THREE.Vector3(0, 9, 15)
const HOME_TARGET = new THREE.Vector3(0, 1.5, 0)

function Skyline() {
  const items = useMemo(() => {
    const out: Array<{ x: number; z: number; w: number; h: number; seed: number }> = []
    let s = 7
    const r = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296 }
    for (let i = 0; i < 56; i++) {
      const a = (i / 56) * Math.PI * 2, d = 26 + r() * 8
      out.push({ x: Math.cos(a) * d, z: Math.sin(a) * d, w: 1.2 + r() * 1.6, h: 2 + r() * 6, seed: i + 1 })
    }
    return out
  }, [])
  const tex = useMemo(() => windowTexture(99, false), [])
  return (
    <group>
      {items.map(b => (
        <mesh key={b.seed} position={[b.x, b.h / 2, b.z]}>
          <boxGeometry args={[b.w, b.h, b.w]} />
          <meshStandardMaterial color="#0e0b33" emissive="#6a5cff" emissiveMap={tex} emissiveIntensity={0.35} />
        </mesh>
      ))}
    </group>
  )
}

/** Flies the camera to the selected tower (shifted so the tower sits right of the scanner panel) and back. */
function CameraRig({ selected, reducedMotion }: { selected: string | null; reducedMotion: boolean }) {
  const { camera, controls } = useThree() as unknown as { camera: THREE.Camera; controls: { target: THREE.Vector3; update: () => void } | null }
  const anim = useRef({ active: false, t: 0, fp: new THREE.Vector3(), ft: new THREE.Vector3(), tp: new THREE.Vector3(), tt: new THREE.Vector3() })
  const mounted = useRef(false)
  useEffect(() => {
    if (!controls) return
    if (!mounted.current) { mounted.current = true; return }
    const a = anim.current
    a.fp.copy(camera.position); a.ft.copy(controls.target)
    if (selected && POS[selected]) {
      const P = new THREE.Vector3(...POS[selected])
      const out = P.clone().setY(0).normalize()
      a.tp.copy(P).addScaledVector(out, 6.5).add(new THREE.Vector3(0, 3.5, 0))
      const look = P.clone().add(new THREE.Vector3(0, 2, 0))
      const fwd = look.clone().sub(a.tp).normalize()
      const right = fwd.clone().cross(new THREE.Vector3(0, 1, 0)).normalize()
      a.tt.copy(look).addScaledVector(right, -2.4)
    } else { a.tp.copy(HOME_POS); a.tt.copy(HOME_TARGET) }
    a.t = 0; a.active = true
  }, [selected, controls, camera])
  useFrame((_, dt) => {
    const a = anim.current
    if (!a.active || !controls) return
    a.t = Math.min(1, a.t + dt / (reducedMotion ? 0.01 : 1.2))
    const k = a.t * a.t * (3 - 2 * a.t)
    camera.position.lerpVectors(a.fp, a.tp, k)
    controls.target.lerpVectors(a.ft, a.tt, k)
    controls.update()
    if (a.t >= 1) a.active = false
  })
  return null
}

export default function City({ rows, selected, onSelect, onDome, reducedMotion, total, lastTrade }: Props) {
  const byBot = useMemo(() => Object.fromEntries(rows.map(r => [r.bot, r])), [rows])
  const spokes = useMemo(() => Array.from({ length: 12 }, (_, i) => {
    const a = (i / 12) * Math.PI * 2
    return [new THREE.Vector3(Math.cos(a) * 3.4, 0.03, Math.sin(a) * 3.4), new THREE.Vector3(Math.cos(a) * 11.3, 0.03, Math.sin(a) * 11.3)] as [THREE.Vector3, THREE.Vector3]
  }), [])
  const links = useMemo(() => {
    const out: Array<[THREE.Vector3, THREE.Vector3]> = []
    const top = (id: string) => new THREE.Vector3(POS[id][0], TOWER_TOP + 0.2, POS[id][2])
    const hub = new THREE.Vector3(0, 2.4, 0)
    for (const t of TICKERS) {
      for (const k of TRIGGERS) out.push([top(`${t}-${k}`), hub])
      out.push([top(`${t}-VWAP`), top(`${t}-EMA50`)], [top(`${t}-EMA50`), top(`${t}-RANGE`)])
    }
    return out
  }, [])
  return (
    <div style={{ width: '100%', height: '100%' }} role="img" aria-label="3D city of bots. Every value shown here is also in the panels.">
      <Canvas dpr={[1, 2]} camera={{ position: [0, 9, 15], fov: 45 }}>
        <color attach="background" args={['#0b0830']} />
        <fog attach="fog" args={['#0b0830', 30, 70]} />
        <ambientLight intensity={0.55} color="#6a5cff" />
        <directionalLight position={[8, 14, 6]} intensity={0.6} color="#9fb3ff" />

        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]}>
          <circleGeometry args={[44, 64]} />
          <meshStandardMaterial color="#0d0a3a" roughness={1} />
        </mesh>
        <gridHelper args={[60, 60, '#2a2570', '#171250']} />
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
          <ringGeometry args={[11.3, 11.55, 96]} />
          <meshBasicMaterial color="#5b4dff" toneMapped={false} />
        </mesh>
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
          <ringGeometry args={[3.2, 3.32, 64]} />
          <meshBasicMaterial color="#3d8bff" toneMapped={false} />
        </mesh>
        {spokes.map((p, i) => <Line key={i} points={p} color="#3a33a0" lineWidth={1} transparent opacity={0.5} />)}
        {links.map((p, i) => <Line key={i} points={p} color="#6a5cff" lineWidth={1} transparent opacity={0.22} />)}

        {TICKERS.map((t, ti) => {
          const [cx, , cz] = towerPosition(ti, 1)
          return (
            <group key={t}>
              <mesh rotation={[-Math.PI / 2, 0, 0]} position={[cx, 0.01, cz]}>
                <circleGeometry args={[4.1, 48]} />
                <meshStandardMaterial color="#17125a" emissive="#2a2290" emissiveIntensity={0.25} />
              </mesh>
              <Html position={[cx * 1.55, 0.1, cz * 1.55]} center zIndexRange={[10, 0]} style={{ pointerEvents: 'none' }}>
                <div className="dname">{t}</div>
              </Html>
              {TRIGGERS.map(k => {
                const id = `${t}-${k}`
                const row = byBot[id]
                return row ? (
                  <Tower key={id} row={row} position={POS[id]} reducedMotion={reducedMotion} selected={selected === id}
                    badge={badgeFor(row, lastTrade[id])} onSelect={onSelect} />
                ) : null
              })}
            </group>
          )
        })}

        <Dome total={total} onClick={onDome} reducedMotion={reducedMotion} />
        <Skyline />
        <CameraRig selected={selected} reducedMotion={reducedMotion} />
        <OrbitControls makeDefault enablePan={false} minDistance={6} maxDistance={40} maxPolarAngle={Math.PI * 0.47}
          autoRotate={!reducedMotion && !selected} autoRotateSpeed={0.4} target={HOME_TARGET} />
        <EffectComposer>
          <Bloom mipmapBlur luminanceThreshold={0.25} intensity={1.1} />
        </EffectComposer>
      </Canvas>
    </div>
  )
}
