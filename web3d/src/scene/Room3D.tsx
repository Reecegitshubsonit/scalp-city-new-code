import { useEffect, useMemo, useState } from 'react'
import { useThree } from '@react-three/fiber'
import * as THREE from 'three'
import type { Series } from '../model/history'
import { chartHeader } from '../model/history'
import type { BotEvent, BotRow } from '../model/types'
import { drawChart } from '../panels/drawChart'
import { paintBoard, paintPlaque, paintScanner } from './roomPaint'
import { formatNum } from '../model/format'
import { Skyline, SkyDome } from './Sky'

/** World position of the room: far below the city ground, never visible from the outside view. */
export const ROOM_ORIGIN = new THREE.Vector3(0, -60, 0)

export interface RoomData {
  series: Record<string, Series>
  tickerTrades: Record<string, number>
  rows: BotRow[]
  feed: BotEvent[]
  selectedRow: BotRow | null
  total: number
}

/** The six wall screens: position relative to the room origin and size in world units. */
export const SCREENS: Array<{ id: string; pos: [number, number, number]; size: [number, number]; px: [number, number] }> = [
  { id: 'SPY', pos: [-4.3, 3.2, -6], size: [4, 2.4], px: [2048, 1228] },
  { id: 'QQQ', pos: [0, 3.2, -6], size: [4.6, 2.76], px: [2304, 1380] },
  { id: 'IWM', pos: [4.3, 3.2, -6], size: [4, 2.4], px: [2048, 1228] },
  { id: 'scanner', pos: [-4.3, 0.9, -6], size: [4, 1.9], px: [2048, 972] },
  { id: 'plaque', pos: [0, 0.9, -6], size: [3.6, 1.2], px: [1920, 640] },
  { id: 'board', pos: [4.3, 0.9, -6], size: [4, 1.9], px: [2048, 972] },
]

/** Camera pose that frames one wall screen. */
export function screenPose(id: string, aspect: number): { cam: THREE.Vector3; look: THREE.Vector3 } | null {
  const sc = SCREENS.find(s => s.id === id)
  if (!sc) return null
  const look = ROOM_ORIGIN.clone().add(new THREE.Vector3(...sc.pos))
  const dist = Math.max(sc.size[1] * 1.33, (sc.size[0] * 1.33) / aspect) * 1.08
  return { cam: look.clone().add(new THREE.Vector3(0, 0, dist)), look }
}

function Monitor({ id, position, size, px, paint, deps, everyMs, onPick }: {
  id: string; position: [number, number, number]; size: [number, number]; px: [number, number]
  paint: (ctx: CanvasRenderingContext2D, w: number, h: number) => void; deps: unknown[]; everyMs?: number
  onPick: (id: string) => void
}) {
  const gl = useThree(s => s.gl)
  const [hover, setHover] = useState(false)
  const { canvas, tex } = useMemo(() => {
    const canvas = document.createElement('canvas')
    canvas.width = px[0]; canvas.height = px[1]
    const tex = new THREE.CanvasTexture(canvas)
    tex.colorSpace = THREE.SRGBColorSpace
    tex.anisotropy = gl.capabilities.getMaxAnisotropy()
    tex.minFilter = THREE.LinearMipmapLinearFilter
    return { canvas, tex }
  }, [px, gl])
  useEffect(() => {
    const run = () => { paint(canvas.getContext('2d')!, px[0], px[1]); tex.needsUpdate = true }
    run()
    if (!everyMs) return
    const id = setInterval(run, everyMs)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return (
    <group
      position={position}
      onClick={e => { e.stopPropagation(); onPick(id) }}
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

/** The room inside a tower: night sky, six wall screens (click one to open it full size). */
export function Room3D({ data, onPick }: { data: RoomData; onPick: (id: string) => void }) {
  const { series, tickerTrades, rows, feed, selectedRow, total } = data
  const chart = (t: string) => (ctx: CanvasRenderingContext2D, w: number, h: number) => {
    const s = series[t]
    drawChart(ctx, w, h, s, { labels: true, axis: true, fontScale: 2.1 })
    const hd = chartHeader(s, tickerTrades[t] ?? 0)
    ctx.fillStyle = '#fff'; ctx.font = `bold ${Math.round(h * 0.052)}px system-ui, sans-serif`; ctx.textAlign = 'left'
    ctx.fillText(`${t} 1-MIN   ${hd.time ?? ''}   ${formatNum(hd.price)}   ${hd.changePct == null ? '' : (hd.changePct >= 0 ? '+' : '') + hd.changePct.toFixed(2) + '%'}   ${hd.trades} trades`, 14, h * 0.05)
  }
  const [x, y, z] = [ROOM_ORIGIN.x, ROOM_ORIGIN.y, ROOM_ORIGIN.z]
  const at = (id: string) => { const s = SCREENS.find(v => v.id === id)!; return { s, pos: [x + s.pos[0], y + s.pos[1], z + s.pos[2]] as [number, number, number] } }
  const paints: Record<string, { paint: (c: CanvasRenderingContext2D, w: number, h: number) => void; deps: unknown[]; everyMs?: number }> = {
    SPY: { paint: chart('SPY'), deps: [series.SPY, tickerTrades.SPY] },
    QQQ: { paint: chart('QQQ'), deps: [series.QQQ, tickerTrades.QQQ] },
    IWM: { paint: chart('IWM'), deps: [series.IWM, tickerTrades.IWM] },
    scanner: { paint: (c, w, h) => paintScanner(c, w, h, selectedRow, feed), deps: [selectedRow, feed] },
    board: { paint: (c, w, h) => paintBoard(c, w, h, rows), deps: [rows] },
    plaque: { paint: (c, w, h) => paintPlaque(c, w, h, Date.now(), total), deps: [total], everyMs: 1000 },
  }
  return (
    <group>
      <SkyDome center={[x, y, z]} radius={120} />
      <Skyline center={[x, y, z]} rMin={14} rMax={30} count={44} maxH={10} />
      <pointLight position={[x, y + 4, z + 2]} intensity={60} color="#9fb3ff" distance={30} />
      <mesh position={[x, y - 0.01, z]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[60, 48]} />
        <meshStandardMaterial color="#0d0a3a" roughness={0.9} />
      </mesh>
      <gridHelper args={[60, 60, '#5b4dff', '#241f6a']} position={[x, y, z]} />
      {SCREENS.map(sc => {
        const { s, pos } = at(sc.id)
        const p = paints[sc.id]
        return <Monitor key={sc.id} id={sc.id} position={pos} size={s.size} px={s.px} paint={p.paint} deps={p.deps} everyMs={p.everyMs} onPick={onPick} />
      })}
    </group>
  )
}
