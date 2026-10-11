import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { Bloom, EffectComposer } from '@react-three/postprocessing'
import * as THREE from 'three'
import { badgeFor } from '../model/badge'
import { formatPnl } from '../model/format'
import { COLORS } from '../model/visual'
import { LabelLayer, LabelProjector, type Anchor } from './Labels'
import { TICKERS, TRIGGERS, towerPosition } from '../model/layout'
import type { BotRow, Fire, TradeRec } from '../model/types'
import { Dome } from './Dome'
import { TOWER_TOP, Tower } from './Tower'
import { SkyDome, Skyline } from './Sky'
import type { Series } from '../model/history'
import { Billboard } from './Billboard'
import { ROOM_CAM_POS, ROOM_LOOK_POS, Room3D, screenPose, type RoomData } from './Room3D'

interface Props {
  rows: BotRow[]; selected: string | null; onSelect: (b: string) => void; onDome: () => void
  reducedMotion: boolean; total: number; lastTrade: Record<string, TradeRec>; title: string
  fires: Record<string, Fire>; inside: boolean; roomData: RoomData; allSeries: Record<string, Series>; floatChart: ReactNode
  screen: string | null; onPickScreen: (id: string) => void
}

const POS: Record<string, [number, number, number]> = Object.fromEntries(
  TICKERS.flatMap((t, ti) => TRIGGERS.map((k, ki) => [`${t}-${k}`, towerPosition(ti, ki)] as const)),
)
const HOME_POS = new THREE.Vector3(0, 9, 15)
const HOME_TARGET = new THREE.Vector3(0, 1.5, 0)

/** Big glowing white rings that spin around the clicked tower, like a gyroscope. Static under reduced motion. */
function GyroRings({ position, reducedMotion }: { position: [number, number, number]; reducedMotion: boolean }) {
  const g1 = useRef<THREE.Group>(null), g2 = useRef<THREE.Group>(null), g3 = useRef<THREE.Group>(null)
  useFrame((_, dt) => {
    if (reducedMotion) return
    if (g1.current) g1.current.rotation.y += dt * 0.9
    if (g2.current) g2.current.rotation.x += dt * 0.7
    if (g3.current) g3.current.rotation.z -= dt * 1.1
  })
  const ring = (r: number, tilt: [number, number, number]) => (
    <group rotation={tilt}>
      <mesh><torusGeometry args={[r, 0.05, 10, 96]} /><meshBasicMaterial color="#ffffff" toneMapped={false} transparent opacity={0.95} /></mesh>
      <mesh><torusGeometry args={[r, 0.2, 10, 96]} /><meshBasicMaterial color="#9fd8ff" toneMapped={false} transparent opacity={0.16} depthWrite={false} blending={THREE.AdditiveBlending} /></mesh>
    </group>
  )
  return (
    <group position={[position[0], TOWER_TOP * 0.62, position[2]]}>
      <group ref={g1} rotation={[0.35, 0, 0.2]}>{ring(3.3, [Math.PI / 2, 0, 0])}</group>
      <group ref={g2} rotation={[0, 0.4, 0.5]}>{ring(2.7, [0, 0, 0])}</group>
      <group ref={g3} rotation={[0.9, 0.3, 0]}>{ring(3.9, [0, Math.PI / 2, 0])}</group>
    </group>
  )
}

/** Flies the camera to the selected tower (shifted so the tower sits right of the scanner panel) and back. */
function CameraRig({ selected, inside, screen, reducedMotion }: { selected: string | null; inside: boolean; screen: string | null; reducedMotion: boolean }) {
  const { camera, controls } = useThree() as unknown as { camera: THREE.Camera; controls: { target: THREE.Vector3; update: () => void } | null }
  const anim = useRef({ active: false, t: 0, fp: new THREE.Vector3(), ft: new THREE.Vector3(), tp: new THREE.Vector3(), tt: new THREE.Vector3() })
  const lastKey = useRef('null|false|null')   // the pose key the camera was last sent to; start = home
  const aspectRef = useRef(2.4)
  aspectRef.current = useThree(st => st.size.width / Math.max(1, st.size.height))
  useEffect(() => {
    if (!controls) return
    const key = `${selected}|${inside}|${screen}`
    if (key === lastKey.current) return
    lastKey.current = key
    const a = anim.current
    a.fp.copy(camera.position); a.ft.copy(controls.target)
    const sp = selected && inside && screen ? screenPose(screen, aspectRef.current) : null
    if (sp) { a.tp.copy(sp.cam); a.tt.copy(sp.look) }
    else if (selected && inside) { a.tp.copy(ROOM_CAM_POS); a.tt.copy(ROOM_LOOK_POS) }
    else if (selected && POS[selected]) {
      const P = new THREE.Vector3(...POS[selected])
      const out = P.clone().setY(0).normalize()
      a.tp.copy(P).addScaledVector(out, 9).add(new THREE.Vector3(0, 3.6, 0))
      const look = P.clone().add(new THREE.Vector3(0, 3.8, 0))
      const fwd = look.clone().sub(a.tp).normalize()
      const right = fwd.clone().cross(new THREE.Vector3(0, 1, 0)).normalize()
      a.tt.copy(look).addScaledVector(right, -2.4)   // tower sits right of centre, clear of the scanner panel
    } else { a.tp.copy(HOME_POS); a.tt.copy(HOME_TARGET) }
    a.t = 0; a.active = true
  }, [selected, inside, screen, controls, camera])
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

// Bloom costs about half the frame rate on integrated GPUs; beams have additive glow shells already, so it is opt-in.
const BLOOM = new URLSearchParams(location.search).get('fx') === 'high'

export default function City({ rows, selected, onSelect, onDome, reducedMotion, total, lastTrade, title, fires, inside, roomData, allSeries, floatChart, screen, onPickScreen }: Props) {
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
  const spokeGeo = useMemo(() => new THREE.BufferGeometry().setFromPoints(spokes.flat()), [spokes])
  const linkGeo = useMemo(() => new THREE.BufferGeometry().setFromPoints(links.flat()), [links])
  const [hover, setHover] = useState(false)   // pointer over the 3D view: stop auto-rotation so towers can be clicked
  const labelRefs = useRef<Record<string, HTMLDivElement | null>>({})
  const anchors = useMemo<Anchor[]>(() => {
    const out: Anchor[] = []
    out.push({ id: 'title', pos: [0, 11, -17], className: 'sign title', node: title })
    const domeColor = total > 0 ? COLORS.CALL : total < 0 ? COLORS.PUT : COLORS.NEUTRAL
    out.push({ id: 'dome', pos: [0, 2.9, 0], className: 'tlabel big', color: domeColor, node: formatPnl(total) })
    TICKERS.forEach((t, ti) => {
      const [cx, , cz] = towerPosition(ti, 1)
      out.push({ id: `d-${t}`, pos: [cx * 1.55, 0.1, cz * 1.55], className: 'dname', node: t })
      for (const k of TRIGGERS) {
        const id = `${t}-${k}`
        const row = byBot[id]
        const [x, , z] = POS[id]
        out.push({ id: `s-${id}`, pos: [x, TOWER_TOP + 1.3, z], className: 'sign', node: k })
        if (row) {
          const closes = (allSeries[t]?.candles ?? []).slice(-40).map(c => c.close)
          out.push({ id: `b-${id}`, pos: [x, TOWER_TOP + 2.4, z], className: 'bbwrap',
            node: <Billboard closes={closes} badge={badgeFor(row, lastTrade[id])} state={row.state} pnl={row.pnl_day} /> })
        }
      }
    })
    if (selected && POS[selected] && floatChart && !inside) {
      const [px, , pz] = POS[selected]
      out.push({ id: 'float', pos: [px, TOWER_TOP + 1.5, pz], className: 'floatchart', top: true, node: floatChart })
    }
    return out
  }, [byBot, lastTrade, total, title, selected, floatChart, inside, allSeries])
  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }} onPointerEnter={() => setHover(true)} onPointerLeave={() => setHover(false)} role="img" aria-label="3D city of bots. Every value shown here is also in the panels.">
      <Canvas dpr={[1, 1.5]} camera={{ position: [0, 9, 15], fov: 45 }}>
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
        <lineSegments geometry={spokeGeo}><lineBasicMaterial color="#3a33a0" transparent opacity={0.5} /></lineSegments>
        <lineSegments geometry={linkGeo}><lineBasicMaterial color="#6a5cff" transparent opacity={0.25} /></lineSegments>

        {TICKERS.map((t, ti) => {
          const [cx, , cz] = towerPosition(ti, 1)
          return (
            <group key={t}>
              <mesh rotation={[-Math.PI / 2, 0, 0]} position={[cx, 0.01, cz]}>
                <circleGeometry args={[4.1, 48]} />
                <meshStandardMaterial color="#17125a" emissive="#2a2290" emissiveIntensity={0.25} />
              </mesh>
              {TRIGGERS.map(k => {
                const id = `${t}-${k}`
                const row = byBot[id]
                return row ? (
                  <Tower key={id} row={row} fire={fires[id]} position={POS[id]} reducedMotion={reducedMotion} selected={selected === id} onSelect={onSelect} />
                ) : null
              })}
            </group>
          )
        })}

        <LabelProjector anchors={anchors} refs={labelRefs} enabled={!inside} />
        <Dome total={total} onClick={onDome} reducedMotion={reducedMotion} />
        <SkyDome />
        <Skyline />
        {selected && !inside && <GyroRings position={POS[selected]} reducedMotion={reducedMotion} />}
        <CameraRig selected={selected} inside={inside} screen={screen} reducedMotion={reducedMotion} />
        {selected && <Room3D data={roomData} onPick={onPickScreen} reducedMotion={reducedMotion} />}
        <OrbitControls makeDefault enablePan={false} minDistance={6} maxDistance={40} maxPolarAngle={Math.PI * 0.47}
          autoRotate={!reducedMotion && !selected && !hover} autoRotateSpeed={0.4} target={HOME_TARGET} />
        {BLOOM && (
          <EffectComposer multisampling={0}>
            <Bloom mipmapBlur levels={5} luminanceThreshold={0.25} intensity={1.1} />
          </EffectComposer>
        )}
      </Canvas>
      <LabelLayer anchors={anchors} refs={labelRefs} hidden={inside} />
    </div>
  )
}
