import { Html } from '@react-three/drei'
import { formatPnl } from '../model/format'
import { COLORS } from '../model/visual'

export function Dome({ total }: { total: number }) {
  const color = total > 0 ? COLORS.CALL : total < 0 ? COLORS.PUT : COLORS.NEUTRAL
  return (
    <group>
      <mesh position={[0, 0.3, 0]}>
        <cylinderGeometry args={[1.5, 1.7, 0.6, 32]} />
        <meshStandardMaterial color="#1a1560" emissive={color} emissiveIntensity={0.35} />
      </mesh>
      <mesh position={[0, 1.2, 0]}>
        <sphereGeometry args={[1.15, 32, 20, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <meshStandardMaterial color="#2a2370" emissive={color} emissiveIntensity={1.1} roughness={0.2} transparent opacity={0.92} />
      </mesh>
      <Html position={[0, 2.9, 0]} center zIndexRange={[10, 0]} style={{ pointerEvents: 'none' }}>
        <div className="tlabel big" style={{ borderColor: color, color }}>{formatPnl(total)}</div>
      </Html>
    </group>
  )
}
