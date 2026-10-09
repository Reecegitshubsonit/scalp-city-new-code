import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { Html } from '@react-three/drei'
import * as THREE from 'three'
import { formatPnl } from '../model/format'
import { COLORS } from '../model/visual'

export function Dome({ total, onClick, reducedMotion }: { total: number; onClick: () => void; reducedMotion: boolean }) {
  const color = total > 0 ? COLORS.CALL : total < 0 ? COLORS.PUT : COLORS.NEUTRAL
  const spin = useRef<THREE.Group>(null)
  useFrame((_, dt) => { if (spin.current && !reducedMotion) spin.current.rotation.y += dt * 0.5 })
  return (
    <group
      onClick={e => { e.stopPropagation(); onClick() }}
      onPointerOver={() => { document.body.style.cursor = 'pointer' }}
      onPointerOut={() => { document.body.style.cursor = '' }}
    >
      <mesh position={[0, 0.3, 0]}>
        <cylinderGeometry args={[1.5, 1.7, 0.6, 32]} />
        <meshStandardMaterial color="#1a1560" emissive={color} emissiveIntensity={0.35} />
      </mesh>
      <mesh position={[0, 1.2, 0]}>
        <sphereGeometry args={[1.15, 32, 20, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <meshStandardMaterial color="#2a2370" emissive={color} emissiveIntensity={1.1} roughness={0.2} transparent opacity={0.92} />
      </mesh>
      <group ref={spin}>
        <mesh position={[0, 0.9, 0]} rotation={[Math.PI / 2 - 0.35, 0, 0]}>
          <torusGeometry args={[1.7, 0.03, 8, 64]} />
          <meshBasicMaterial color={color} toneMapped={false} />
        </mesh>
        {Array.from({ length: 6 }, (_, i) => {
          const a = (i / 6) * Math.PI * 2
          return (
            <mesh key={i} position={[Math.cos(a) * 2.1, 0.25, Math.sin(a) * 2.1]}>
              <coneGeometry args={[0.12, 0.4, 8]} />
              <meshBasicMaterial color="#3de0ff" toneMapped={false} />
            </mesh>
          )
        })}
      </group>
      <Html position={[0, 2.9, 0]} center zIndexRange={[10, 0]} style={{ pointerEvents: 'none' }}>
        <div className="tlabel big" style={{ borderColor: color, color }}>{formatPnl(total)}</div>
      </Html>
    </group>
  )
}
