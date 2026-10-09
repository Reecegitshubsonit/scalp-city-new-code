import { memo, useEffect, useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import type { BotRow } from '../model/types'
import { visualFor } from '../model/visual'
import { hashStr, windowTexture } from './textures'

export const BEAM_MAX = 16
const LEVELS: Array<{ w: number; h: number }> = [{ w: 1.7, h: 1.4 }, { w: 1.3, h: 1.1 }, { w: 0.9, h: 0.9 }]
const BODY_H = LEVELS.reduce((a, l) => a + l.h, 0)
export const TOWER_TOP = BODY_H + 0.7

interface Props {
  row: BotRow
  position: [number, number, number]
  reducedMotion: boolean
  selected: boolean
  onSelect: (bot: string) => void
}

function TowerImpl({ row, position, reducedMotion, selected, onSelect }: Props) {
  const v = visualFor(row, reducedMotion)
  const tex = useMemo(() => windowTexture(hashStr(row.bot), v.hatched), [row.bot, v.hatched])
  const mats = useRef<THREE.MeshStandardMaterial[]>([])
  const beam = useRef<THREE.Mesh>(null)
  const shell = useRef<THREE.Mesh>(null)
  const ring = useRef<THREE.Mesh>(null)
  const flash = useRef<THREE.Mesh>(null)
  const orbit = useRef<THREE.Group>(null)
  const beamH = useRef(0)
  const ringT = useRef(-1)
  const prev = useRef(row.state)
  const color = useMemo(() => new THREE.Color(v.color), [v.color])
  const beamColor = useMemo(() => new THREE.Color(v.color).multiplyScalar(1.8), [v.color])

  useEffect(() => {
    if (row.state === 'fired' && prev.current !== 'fired') ringT.current = 0
    prev.current = row.state
  }, [row.state])

  useFrame((st, dt) => {
    const t = st.clock.elapsedTime
    let k = 1
    if (v.effect === 'pulse') k = 0.65 + 0.35 * Math.sin(t * 6)
    if (v.effect === 'flicker') k = Math.sin(t * 41) * Math.sin(t * 13) > 0.15 ? 1 : 0.15
    for (const m of mats.current) if (m) m.emissiveIntensity = v.glow * 2.2 * k

    const target = v.beam * BEAM_MAX
    beamH.current = reducedMotion ? target : THREE.MathUtils.damp(beamH.current, target, 4, dt)
    for (const m of [beam.current, shell.current]) {
      if (!m) continue
      m.visible = beamH.current > 0.05
      m.scale.y = Math.max(beamH.current, 0.001)
      m.position.y = TOWER_TOP + beamH.current / 2
    }
    if (orbit.current && !reducedMotion) orbit.current.rotation.y += dt * (v.glow > 0.4 ? 0.9 : 0.25)

    const set = (m: THREE.Mesh | null, s: number, o: number, show: boolean) => {
      if (!m) return
      m.visible = show
      if (!show) return
      m.scale.set(s, s, 1)
      ;(m.material as THREE.MeshBasicMaterial).opacity = o
    }
    if (ringT.current >= 0) {
      ringT.current += dt
      const dur = reducedMotion ? 2 : 1.1
      if (ringT.current > dur) { ringT.current = -1; set(ring.current, 1, 0, false); set(flash.current, 1, 0, false) }
      else {
        const p = ringT.current / dur
        const s = reducedMotion ? 2.4 : 1 + p * 3.8
        const o = reducedMotion ? 0.8 : 1 - p
        set(ring.current, s, o, true)
        set(flash.current, s, o * 0.45, true)
      }
    } else { set(ring.current, 1, 0, false); set(flash.current, 1, 0, false) }
  })

  let y = 0
  const mat = (i: number) => (m: THREE.MeshStandardMaterial | null) => { if (m) mats.current[i] = m }
  return (
    <group
      position={position}
      onClick={e => { e.stopPropagation(); onSelect(row.bot) }}
      onPointerOver={() => { document.body.style.cursor = 'pointer' }}
      onPointerOut={() => { document.body.style.cursor = '' }}
    >
      {LEVELS.map((l, i) => {
        const cy = y + l.h / 2
        y += l.h
        return (
          <mesh key={i} position={[0, cy, 0]}>
            <boxGeometry args={[l.w, l.h, l.w]} />
            <meshStandardMaterial ref={mat(i)} color="#12103a" emissive={color} emissiveMap={tex}
              emissiveIntensity={v.glow * 2.2} roughness={0.7} metalness={0.2} />
          </mesh>
        )
      })}
      {[[-1, -1], [1, -1], [-1, 1], [1, 1]].map(([sx, sz], i) => (
        <mesh key={i} position={[sx * 0.52, LEVELS[0].h + LEVELS[1].h + 0.45, sz * 0.52]}>
          <boxGeometry args={[0.07, 0.9, 0.07]} />
          <meshStandardMaterial ref={mat(4 + i)} color="#12103a" emissive={color} emissiveIntensity={v.glow * 2.2} />
        </mesh>
      ))}
      <mesh position={[0, BODY_H + 0.35, 0]}>
        <coneGeometry args={[0.35, 0.7, 6]} />
        <meshStandardMaterial ref={mat(3)} color="#12103a" emissive={color} emissiveIntensity={v.glow * 2.2} />
      </mesh>
      <mesh position={[0, TOWER_TOP + 0.45, 0]}>
        <cylinderGeometry args={[0.025, 0.025, 0.9, 6]} />
        <meshBasicMaterial color={beamColor} toneMapped={false} />
      </mesh>
      <group ref={orbit}>
        <mesh position={[0, TOWER_TOP * 0.62, 0]} rotation={[Math.PI / 2 + 0.25, 0, 0]}>
          <torusGeometry args={[1.15, 0.018, 6, 48]} />
          <meshBasicMaterial color={beamColor} transparent opacity={0.25 + v.glow * 0.45} toneMapped={false} />
        </mesh>
        <mesh position={[0, TOWER_TOP * 0.9, 0]} rotation={[Math.PI / 2 - 0.3, 0, 0]}>
          <torusGeometry args={[0.8, 0.018, 6, 48]} />
          <meshBasicMaterial color={beamColor} transparent opacity={0.25 + v.glow * 0.45} toneMapped={false} />
        </mesh>
      </group>
      <mesh ref={beam} visible={false} position={[0, TOWER_TOP, 0]}>
        <cylinderGeometry args={[0.13, 0.13, 1, 12, 1, true]} />
        <meshBasicMaterial color={beamColor} transparent opacity={0.95} toneMapped={false} depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      <mesh ref={shell} visible={false} position={[0, TOWER_TOP, 0]}>
        <cylinderGeometry args={[0.42, 0.42, 1, 16, 1, true]} />
        <meshBasicMaterial color={beamColor} transparent opacity={0.16} toneMapped={false} depthWrite={false} side={THREE.DoubleSide} blending={THREE.AdditiveBlending} />
      </mesh>
      <mesh ref={ring} visible={false} position={[0, 0.2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <torusGeometry args={[1.3, 0.09, 8, 64]} />
        <meshBasicMaterial color={beamColor} transparent opacity={1} toneMapped={false} depthWrite={false} />
      </mesh>
      <mesh ref={flash} visible={false} position={[0, 0.15, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[1.3, 48]} />
        <meshBasicMaterial color={beamColor} transparent opacity={0.4} toneMapped={false} depthWrite={false} blending={THREE.AdditiveBlending} />
      </mesh>
      <mesh position={[0, 0.03, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[1.25, 1.4, 40]} />
        <meshBasicMaterial color={selected ? '#ffffff' : color} transparent opacity={selected ? 0.95 : 0.25 + v.glow * 0.4} toneMapped={false} />
      </mesh>
    </group>
  )
}
export const Tower = memo(TowerImpl, (a, b) =>
  a.row === b.row && a.selected === b.selected && a.reducedMotion === b.reducedMotion &&
  a.position === b.position && a.onSelect === b.onSelect)
