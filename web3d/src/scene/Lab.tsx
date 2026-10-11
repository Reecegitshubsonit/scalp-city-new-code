import { useEffect, useMemo, useRef, useState } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { paintDiscLabel, paintHex, paintSign } from './roomPaint'

function useCanvasTex(w: number, h: number, paint: (ctx: CanvasRenderingContext2D, w: number, h: number) => void, deps: unknown[], opts?: { repeat?: [number, number] }) {
  const gl = useThree(s => s.gl)
  const { canvas, tex } = useMemo(() => {
    const canvas = document.createElement('canvas'); canvas.width = w; canvas.height = h
    const tex = new THREE.CanvasTexture(canvas)
    tex.colorSpace = THREE.SRGBColorSpace
    tex.anisotropy = gl.capabilities.getMaxAnisotropy()
    if (opts?.repeat) { tex.wrapS = tex.wrapT = THREE.RepeatWrapping; tex.repeat.set(...opts.repeat) }
    return { canvas, tex }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [w, h, gl])
  useEffect(() => { paint(canvas.getContext('2d')!, w, h); tex.needsUpdate = true }, deps) // eslint-disable-line react-hooks/exhaustive-deps
  return tex
}

/** The trader robot: sits at the desk facing the wall of screens, types, sways, antenna light blinks. Static under reduced motion. */
export function Robot({ reducedMotion, mood }: { reducedMotion: boolean; mood: 'up' | 'down' | 'flat' }) {
  const head = useRef<THREE.Group>(null), armL = useRef<THREE.Group>(null), armR = useRef<THREE.Group>(null), light = useRef<THREE.MeshBasicMaterial>(null)
  useFrame(({ clock }) => {
    if (reducedMotion) return
    const t = clock.elapsedTime
    if (head.current) { head.current.rotation.y = Math.sin(t * 0.5) * 0.18; head.current.rotation.x = mood === 'down' ? 0.25 : Math.sin(t * 0.9) * 0.04 }
    if (armL.current) armL.current.rotation.x = -1.1 + Math.sin(t * 7) * 0.08
    if (armR.current) armR.current.rotation.x = mood === 'up' ? -2.6 + Math.sin(t * 6) * 0.2 : -1.1 + Math.sin(t * 7 + 1.7) * 0.08
    if (light.current) light.current.color.set(Math.sin(t * 3) > 0 ? '#ff3bd4' : '#7a1f6a')
  })
  const white = <meshStandardMaterial color="#f4f2ff" emissive="#3a3680" emissiveIntensity={0.35} roughness={0.25} metalness={0.1} />
  const black = <meshStandardMaterial color="#0c0a22" roughness={0.5} />
  return (
    <group>
      {/* chair */}
      <mesh position={[0, 0.04, 0]}><cylinderGeometry args={[0.55, 0.55, 0.06, 20]} />{black}</mesh>
      <mesh position={[0, 0.4, 0]}><cylinderGeometry args={[0.07, 0.07, 0.7, 10]} />{black}</mesh>
      <mesh position={[0, 0.78, 0]}><boxGeometry args={[1, 0.14, 0.95]} />{black}</mesh>
      <mesh position={[0, 1.4, 0.5]}><boxGeometry args={[0.95, 1.1, 0.1]} />{black}</mesh>
      {/* body */}
      <mesh position={[0, 1.05, 0]}><boxGeometry args={[0.8, 0.45, 0.55]} />{black}</mesh>
      <mesh position={[0, 1.55, 0]}><capsuleGeometry args={[0.33, 0.45, 6, 14]} />{white}</mesh>
      <mesh position={[0, 0.7, -0.35]}><boxGeometry args={[0.7, 0.18, 0.7]} />{black}</mesh>
      <mesh position={[0, 0.35, -0.65]}><boxGeometry args={[0.55, 0.7, 0.2]} />{black}</mesh>
      {/* arms */}
      <group ref={armL} position={[-0.45, 1.8, 0]} rotation={[-1.1, 0, 0]}>
        <mesh position={[0, -0.32, 0]}><capsuleGeometry args={[0.09, 0.45, 5, 10]} />{white}</mesh>
      </group>
      <group ref={armR} position={[0.45, 1.8, 0]} rotation={[-1.1, 0, 0]}>
        <mesh position={[0, -0.32, 0]}><capsuleGeometry args={[0.09, 0.45, 5, 10]} />{white}</mesh>
      </group>
      {/* head */}
      <group ref={head} position={[0, 2.3, 0]}>
        <mesh><sphereGeometry args={[0.4, 28, 20]} />{white}</mesh>
        <mesh position={[0, 0.02, -0.2]} scale={[0.95, 0.72, 0.6]}><sphereGeometry args={[0.36, 24, 16]} /><meshStandardMaterial color="#05031a" roughness={0.1} metalness={0.4} /></mesh>
        {[-1, 1].map(sx => (
          <mesh key={sx} position={[sx * 0.4, 0, 0]} rotation={[0, Math.PI / 2, 0]}>
            <torusGeometry args={[0.16, 0.035, 8, 24]} /><meshBasicMaterial color="#ffe14d" toneMapped={false} />
          </mesh>
        ))}
        <mesh position={[0, 0.5, 0]}><cylinderGeometry args={[0.02, 0.02, 0.3, 6]} />{white}</mesh>
        <mesh position={[0, 0.68, 0]}><sphereGeometry args={[0.065, 12, 10]} /><meshBasicMaterial ref={light} color="#ff3bd4" toneMapped={false} /></mesh>
      </group>
    </group>
  )
}

export interface DiscSpec { id: 'play' | 'stop' | 'speed'; color: string; x: number; label: string; labelColor: string; onClick: () => void }

/** Desk with the three round buttons, a keyboard strip, a mug and a sheet of paper. */
export function Desk({ discs }: { discs: DiscSpec[] }) {
  const [hover, setHover] = useState<string | null>(null)
  const keyTex = useCanvasTex(256, 64, (ctx, w, h) => {
    const g = ctx.createLinearGradient(0, 0, w, 0)
    ;['#ff3b6b', '#ffb020', '#ffe14d', '#19f5a0', '#3de0ff', '#7d6bff', '#ff3bd4'].forEach((c, i, a) => g.addColorStop(i / (a.length - 1), c))
    ctx.fillStyle = g; ctx.fillRect(0, 0, w, h)
  }, [])
  const edge = <meshBasicMaterial color="#ffe14d" toneMapped={false} />
  return (
    <group>
      <mesh position={[0, 1.0, 0]}><boxGeometry args={[9.4, 0.12, 1.6]} /><meshStandardMaterial color="#120e45" roughness={0.6} /></mesh>
      <mesh position={[0, 1.07, 0.8]}><boxGeometry args={[9.4, 0.04, 0.04]} />{edge}</mesh>
      <mesh position={[-4.7, 0.55, 0]}><boxGeometry args={[0.1, 1.0, 1.4]} /><meshStandardMaterial color="#120e45" /></mesh>
      <mesh position={[4.7, 0.55, 0]}><boxGeometry args={[0.1, 1.0, 1.4]} /><meshStandardMaterial color="#120e45" /></mesh>
      <mesh position={[0, 1.075, 0.45]} rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[2.8, 0.5]} /><meshBasicMaterial map={keyTex} toneMapped={false} /></mesh>
      <mesh position={[-3.3, 1.2, 0]}><cylinderGeometry args={[0.16, 0.14, 0.24, 14]} /><meshStandardMaterial color="#ffe14d" emissive="#ffb020" emissiveIntensity={0.4} /></mesh>
      <mesh position={[-4.1, 1.07, 0.1]} rotation={[0, 0.4, 0]}><boxGeometry args={[0.9, 0.02, 0.65]} /><meshStandardMaterial color="#f4f2ff" /></mesh>
      {discs.map(d => (
        <group key={d.id} position={[d.x, 1.1, 0.1]}
          onClick={e => { e.stopPropagation(); d.onClick() }}
          onPointerOver={e => { e.stopPropagation(); setHover(d.id); document.body.style.cursor = 'pointer' }}
          onPointerOut={() => { setHover(null); document.body.style.cursor = '' }}>
          <mesh scale={hover === d.id ? 1.12 : 1}><cylinderGeometry args={[0.3, 0.3, 0.08, 24]} /><meshBasicMaterial color={d.color} toneMapped={false} /></mesh>
          <DiscLabel label={d.label} color={d.labelColor} />
        </group>
      ))}
    </group>
  )
}

function DiscLabel({ label, color }: { label: string; color: string }) {
  const tex = useCanvasTex(512, 96, (ctx, w, h) => paintDiscLabel(ctx, w, h, label, color), [label, color])
  return (
    <mesh position={[0, 0.34, 0.35]} rotation={[-0.5, 0, 0]}>
      <planeGeometry args={[1.35, 0.25]} /><meshBasicMaterial map={tex} transparent toneMapped={false} />
    </mesh>
  )
}

/** Hex-tile floor patch and side wall. */
export function HexSurfaces() {
  const floor = useCanvasTex(1024, 640, paintHex, [], { repeat: [1, 1] })
  const wall = useCanvasTex(1024, 640, paintHex, [], { repeat: [1, 1] })
  return (
    <group>
      <mesh position={[0, 0.03, -2.2]} rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[19, 11.5]} /><meshBasicMaterial map={floor} toneMapped={false} /></mesh>
      <mesh position={[-9.6, 4.2, -4]} rotation={[0, Math.PI / 2.6, 0]}><planeGeometry args={[10, 6.2]} /><meshBasicMaterial map={wall} toneMapped={false} /></mesh>
    </group>
  )
}

export function NeonSign({ label, position, size }: { label: string; position: [number, number, number]; size: [number, number] }) {
  const tex = useCanvasTex(1024, 192, (ctx, w, h) => paintSign(ctx, w, h, label), [label])
  return <mesh position={position}><planeGeometry args={size} /><meshBasicMaterial map={tex} transparent toneMapped={false} depthWrite={false} /></mesh>
}
