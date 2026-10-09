import { memo, useEffect, useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { Html } from '@react-three/drei'
import * as THREE from 'three'
import type { BotRow } from '../model/types'
import { visualFor } from '../model/visual'
import { hashStr, windowTexture } from './textures'

const BEAM_MAX = 9
const LEVELS: Array<{ w: number; h: number }> = [{ w: 1.7, h: 1.4 }, { w: 1.3, h: 1.1 }, { w: 0.9, h: 0.9 }]
const BODY_H = LEVELS.reduce((a, l) => a + l.h, 0)
const TOP = BODY_H + 0.7

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
  const ring = useRef<THREE.Mesh>(null)
  const beamH = useRef(0)
  const ringT = useRef(-1)
  const prev = useRef(row.state)
  const color = useMemo(() => new THREE.Color(v.color), [v.color])
  const beamColor = useMemo(() => new THREE.Color(v.color).multiplyScalar(1.6), [v.color])

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
    if (beam.current) {
      beam.current.visible = beamH.current > 0.05
      beam.current.scale.y = Math.max(beamH.current, 0.001)
      beam.current.position.y = TOP + beamH.current / 2
    }

    if (ring.current) {
      const mat = ring.current.material as THREE.MeshBasicMaterial
      if (ringT.current >= 0) {
        ringT.current += dt
        const dur = reducedMotion ? 2 : 1
        if (ringT.current > dur) { ringT.current = -1; ring.current.visible = false }
        else {
          ring.current.visible = true
          const p = ringT.current / dur
          const s = reducedMotion ? 2.2 : 1 + p * 3.5
          ring.current.scale.set(s, s, 1)
          mat.opacity = reducedMotion ? 0.8 : 1 - p
        }
      } else ring.current.visible = false
    }
  })

  let y = 0
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
            <meshStandardMaterial ref={m => { if (m) mats.current[i] = m }} color="#12103a" emissive={color} emissiveMap={tex}
              emissiveIntensity={v.glow * 2.2} roughness={0.7} metalness={0.2} />
          </mesh>
        )
      })}
      <mesh position={[0, BODY_H + 0.35, 0]}>
        <coneGeometry args={[0.35, 0.7, 6]} />
        <meshStandardMaterial ref={m => { if (m) mats.current[3] = m }} color="#12103a" emissive={color} emissiveIntensity={v.glow * 2.2} />
      </mesh>
      <mesh ref={beam} visible={false} position={[0, TOP, 0]}>
        <cylinderGeometry args={[0.09, 0.09, 1, 10, 1, true]} />
        <meshBasicMaterial color={beamColor} transparent opacity={0.9} toneMapped={false} depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      <mesh ref={ring} visible={false} position={[0, 0.2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <torusGeometry args={[1.3, 0.07, 8, 48]} />
        <meshBasicMaterial color={beamColor} transparent opacity={1} toneMapped={false} depthWrite={false} />
      </mesh>
      <mesh position={[0, 0.03, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[1.25, 1.4, 40]} />
        <meshBasicMaterial color={selected ? '#ffffff' : color} transparent opacity={selected ? 0.95 : 0.25 + v.glow * 0.4} toneMapped={false} />
      </mesh>
      <Html position={[0, -0.05, 1.5]} center zIndexRange={[10, 0]} style={{ pointerEvents: 'none' }}>
        <div className="tname">{row.bot.split('-')[1]}</div>
      </Html>
      {v.label && (
        <Html position={[0, TOP + 0.8 + v.beam * BEAM_MAX * 0, 0]} center zIndexRange={[10, 0]} style={{ pointerEvents: 'none' }}>
          <div className="tlabel" style={{ borderColor: v.color, color: v.color }}>{v.label}</div>
        </Html>
      )}
    </group>
  )
}

export const Tower = memo(TowerImpl)
