import { useEffect, useMemo, useRef, useState } from 'react'
import { useThree } from '@react-three/fiber'
import * as THREE from 'three'
import type { Series } from '../model/history'
import { nextSpeed } from '../model/lab'
import type { BotEvent, BotRow } from '../model/types'
import type { Trade } from '../model/trades'
import { paintBoard, paintChart1m, paintEarned, paintPlaque, paintScanner, paintWallLine } from './roomPaint'
import { Skyline, SkyDome } from './Sky'
import { Desk, HexSurfaces, NeonSign, Robot, type DiscSpec } from './Lab'

/** World position of the room: far below the city ground, never visible from the outside view. */
export const ROOM_ORIGIN = new THREE.Vector3(0, -60, 0)
/** Default camera pose inside the room: behind and above the robot, looking at the wall of screens. */
export const ROOM_CAM_POS = new THREE.Vector3(ROOM_ORIGIN.x, ROOM_ORIGIN.y + 4.7, ROOM_ORIGIN.z + 4.6)
export const ROOM_LOOK_POS = new THREE.Vector3(ROOM_ORIGIN.x, ROOM_ORIGIN.y + 3.5, ROOM_ORIGIN.z - 6)

export interface LabControls {
  replayActive: boolean; playing: boolean; speed: number
  onPlayPause: () => void; onStop: () => void; onSpeed: (s: number) => void; onOpenPicker: () => void
}

export interface RoomData {
  series: Record<string, Series>
  tickerTrades: Record<string, number>
  rows: BotRow[]
  feed: BotEvent[]
  selectedRow: BotRow | null
  total: number
  earned: { label: string; pnl: number; count: number; wins: number; trades: Trade[] }
  lab: LabControls
}

interface ScreenDef { id: string; pos: [number, number, number]; size: [number, number]; px: [number, number]; rotY?: number }

/** The eight wall screens: position relative to the room origin and size in world units. */
export const SCREENS: ScreenDef[] = [
  { id: 'SPY', pos: [-4.6, 4.5, -6], size: [4, 2.4], px: [1280, 768] },
  { id: 'QQQ', pos: [0, 4.5, -6], size: [4.6, 2.76], px: [1472, 883] },
  { id: 'IWM', pos: [4.6, 4.5, -6], size: [4, 2.4], px: [1280, 768] },
  { id: 'scanner', pos: [-4.6, 1.95, -6], size: [4, 1.9], px: [1280, 608] },
  { id: 'chart1m', pos: [0, 1.95, -6], size: [4.6, 1.9], px: [1472, 608] },
  { id: 'board', pos: [4.6, 1.95, -6], size: [4, 1.9], px: [1280, 608] },
  { id: 'plaque', pos: [-8.6, 3.4, -4.3], size: [3.4, 1.15], px: [1088, 368], rotY: 0.55 },
  { id: 'earned', pos: [8.6, 3.4, -4.3], size: [3.2, 3.2], px: [896, 896], rotY: -0.55 },
]

/** Camera pose that frames one wall screen face-on. */
export function screenPose(id: string, aspect: number): { cam: THREE.Vector3; look: THREE.Vector3 } | null {
  const sc = SCREENS.find(s => s.id === id)
  if (!sc) return null
  const look = ROOM_ORIGIN.clone().add(new THREE.Vector3(...sc.pos))
  const dist = Math.max(sc.size[1] * 1.33, (sc.size[0] * 1.33) / aspect) * 1.08
  const ry = sc.rotY ?? 0
  return { cam: look.clone().add(new THREE.Vector3(Math.sin(ry) * dist, 0, Math.cos(ry) * dist)), look }
}

function Monitor({ def, paint, deps, everyMs, onPick }: {
  def: ScreenDef; paint: (ctx: CanvasRenderingContext2D, w: number, h: number) => void; deps: unknown[]; everyMs?: number; onPick: (id: string) => void
}) {
  const gl = useThree(s => s.gl)
  const [hover, setHover] = useState(false)
  const { canvas, tex } = useMemo(() => {
    const canvas = document.createElement('canvas')
    canvas.width = def.px[0]; canvas.height = def.px[1]
    const tex = new THREE.CanvasTexture(canvas)
    tex.colorSpace = THREE.SRGBColorSpace
    tex.anisotropy = Math.min(6, gl.capabilities.getMaxAnisotropy())
    tex.minFilter = THREE.LinearMipmapLinearFilter
    return { canvas, tex }
  }, [def.id, def.px, gl])   // keyed on stable values: re-creating the texture every render would leave the screen black
  // repaint is throttled: each repaint uploads a multi-megabyte texture, and events can arrive in bursts
  const last = useRef(0)
  useEffect(() => {
    const run = () => { last.current = performance.now(); paint(canvas.getContext('2d')!, def.px[0], def.px[1]); tex.needsUpdate = true }
    // at most once a second, and staggered per screen so the repaints never land in the same frame
    const stagger = (SCREENS.findIndex(d => d.id === def.id) % 8) * 110
    const wait = Math.max(stagger, 1000 - (performance.now() - last.current))
    const first = setTimeout(run, wait)
    const id = everyMs ? setInterval(run, everyMs) : undefined
    return () => { clearTimeout(first); if (id) clearInterval(id) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  const { size } = def
  return (
    <group
      position={def.pos} rotation={[0, def.rotY ?? 0, 0]}
      onClick={e => { e.stopPropagation(); onPick(def.id) }}
      onPointerOver={e => { e.stopPropagation(); setHover(true); document.body.style.cursor = 'pointer' }}
      onPointerOut={() => { setHover(false); document.body.style.cursor = '' }}
    >
      {/* frame sits behind the screen; the screen is offset toward the camera so the two never share a depth (no z-fighting) */}
      <mesh position={[0, 0, -0.08]}>
        <boxGeometry args={[size[0] + 0.22, size[1] + 0.22, 0.1]} />
        <meshBasicMaterial color={hover ? '#9a8cff' : '#4a3fd0'} toneMapped={false} />
      </mesh>
      <mesh position={[0, 0, 0.01]}>
        <planeGeometry args={size} />
        <meshBasicMaterial map={tex} toneMapped={false} />
      </mesh>
    </group>
  )
}

/** The backtest room: night sky and skyline, eight wall screens (click one to open it full size), the robot at its desk, hex floor. */
export function Room3D({ data, onPick, reducedMotion }: { data: RoomData; onPick: (id: string) => void; reducedMotion: boolean }) {
  const { series, tickerTrades, rows, feed, selectedRow, total, earned, lab } = data
  const [x, y, z] = [ROOM_ORIGIN.x, ROOM_ORIGIN.y, ROOM_ORIGIN.z]
  const worldScreens = useMemo(() => SCREENS.map(d => ({ ...d, pos: [x + d.pos[0], y + d.pos[1], z + d.pos[2]] as [number, number, number] })), [x, y, z])
  const ticker = selectedRow?.ticker ?? 'QQQ'
  const tickerPnl = rows.filter(r => r.ticker === ticker).reduce((a, r) => a + r.pnl_day, 0)
  const paints: Record<string, { paint: (c: CanvasRenderingContext2D, w: number, h: number) => void; deps: unknown[]; everyMs?: number }> = {
    SPY: { paint: (c, w, h) => paintWallLine(c, w, h, 'SPY', series.SPY, tickerTrades.SPY ?? 0), deps: [series.SPY, tickerTrades.SPY] },
    QQQ: { paint: (c, w, h) => paintWallLine(c, w, h, 'QQQ', series.QQQ, tickerTrades.QQQ ?? 0), deps: [series.QQQ, tickerTrades.QQQ] },
    IWM: { paint: (c, w, h) => paintWallLine(c, w, h, 'IWM', series.IWM, tickerTrades.IWM ?? 0), deps: [series.IWM, tickerTrades.IWM] },
    scanner: { paint: (c, w, h) => paintScanner(c, w, h, selectedRow, feed), deps: [selectedRow, feed] },
    chart1m: { paint: (c, w, h) => paintChart1m(c, w, h, ticker, series[ticker], tickerPnl), deps: [series[ticker], ticker, tickerPnl] },
    board: { paint: (c, w, h) => paintBoard(c, w, h, rows), deps: [rows] },
    plaque: { paint: (c, w, h) => paintPlaque(c, w, h, Date.now(), total), deps: [total], everyMs: 1000 },
    earned: { paint: (c, w, h) => paintEarned(c, w, h, earned), deps: [earned] },
  }
  const discs: DiscSpec[] = [
    { id: 'play', color: '#19f5a0', x: 2.5, label: lab.replayActive ? (lab.playing ? 'PAUSE' : 'PLAY') : 'REPLAY A DAY', labelColor: '#19f5a0', onClick: lab.replayActive ? lab.onPlayPause : lab.onOpenPicker },
    { id: 'stop', color: '#ff3bd4', x: 3.5, label: lab.replayActive ? 'BACK TO LIVE' : 'LIVE', labelColor: '#ff9bea', onClick: lab.replayActive ? lab.onStop : () => {} },
    { id: 'speed', color: '#f4f2ff', x: 4.5, label: `SPEED ${lab.speed}x`, labelColor: '#f4f2ff', onClick: () => lab.onSpeed(nextSpeed(lab.speed)) },
  ]
  const mood = tickerPnl > 0 ? 'up' : tickerPnl < 0 ? 'down' : 'flat'
  return (
    <group>
      <SkyDome center={[x, y, z]} radius={120} />
      <Skyline center={[x, y, z]} rMin={16} rMax={34} count={48} maxH={12} />
      <mesh position={[x, y - 0.01, z]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[60, 48]} />
        <meshStandardMaterial color="#0d0a3a" roughness={0.9} />
      </mesh>
      <gridHelper args={[60, 60, '#5b4dff', '#241f6a']} position={[x, y, z]} />
      <group position={[x, y, z]}><HexSurfaces /></group>
      <NeonSign label="NEVER SLEEPS" position={[x, y + 6.95, z - 6.1]} size={[6.4, 1.2]} />
      {worldScreens.map(def => {
        const p = paints[def.id]
        return <Monitor key={def.id} def={def} paint={p.paint} deps={p.deps} everyMs={p.everyMs} onPick={onPick} />
      })}
      <group position={[x, y, z - 3.7]}><Desk discs={discs} /></group>
      <group position={[x, y, z - 2.3]}><Robot reducedMotion={reducedMotion} mood={mood} /></group>
    </group>
  )
}
