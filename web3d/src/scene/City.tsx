import { useMemo } from 'react'
import { Canvas } from '@react-three/fiber'
import { Html, OrbitControls } from '@react-three/drei'
import { Bloom, EffectComposer } from '@react-three/postprocessing'
import * as THREE from 'three'
import { TICKERS, TRIGGERS, towerPosition } from '../model/layout'
import type { BotRow } from '../model/types'
import { Dome } from './Dome'
import { Tower } from './Tower'
import { windowTexture } from './textures'

interface Props { rows: BotRow[]; selected: string | null; onSelect: (b: string) => void; reducedMotion: boolean; total: number }

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

export default function City({ rows, selected, onSelect, reducedMotion, total }: Props) {
  const byBot = useMemo(() => Object.fromEntries(rows.map(r => [r.bot, r])), [rows])
  return (
    <div style={{ width: '100%', height: '100%' }} role="img" aria-label="3D city of bots. Every value shown here is also in the panels.">
      <Canvas dpr={[1, 2]} camera={{ position: [0, 9, 15], fov: 45 }} onPointerMissed={() => {}}>
        <color attach="background" args={['#0b0830']} />
        <fog attach="fog" args={['#0b0830', 30, 70]} />
        <ambientLight intensity={0.55} color="#6a5cff" />
        <directionalLight position={[8, 14, 6]} intensity={0.6} color="#9fb3ff" />

        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]}>
          <circleGeometry args={[44, 64]} />
          <meshStandardMaterial color="#0d0a3a" roughness={1} />
        </mesh>
        <gridHelper args={[60, 60, '#2a2570', '#171250']} position={[0, 0, 0]} />
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
          <ringGeometry args={[11.3, 11.5, 96]} />
          <meshBasicMaterial color="#5b4dff" toneMapped={false} />
        </mesh>
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
          <ringGeometry args={[3.2, 3.3, 64]} />
          <meshBasicMaterial color="#3d8bff" toneMapped={false} />
        </mesh>

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
              {TRIGGERS.map((k, ki) => {
                const id = `${t}-${k}`
                const row = byBot[id]
                return row ? (
                  <Tower key={id} row={row} position={towerPosition(ti, ki)} reducedMotion={reducedMotion} selected={selected === id} onSelect={onSelect} />
                ) : null
              })}
            </group>
          )
        })}

        <Dome total={total} />
        <Skyline />
        <OrbitControls enablePan={false} minDistance={8} maxDistance={40} maxPolarAngle={Math.PI * 0.47}
          autoRotate={!reducedMotion && !selected} autoRotateSpeed={0.4} target={new THREE.Vector3(0, 1.5, 0)} />
        <EffectComposer>
          <Bloom mipmapBlur luminanceThreshold={0.25} intensity={1.1} />
        </EffectComposer>
      </Canvas>
    </div>
  )
}
