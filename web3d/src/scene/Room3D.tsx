import { useEffect, useMemo } from 'react'
import * as THREE from 'three'
import type { Series } from '../model/history'
import { chartHeader } from '../model/history'
import type { BotEvent, BotRow } from '../model/types'
import { drawChart } from '../panels/drawChart'
import { paintBoard, paintPlaque, paintScanner } from './roomPaint'
import { formatNum } from '../model/format'

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

function useCanvasTexture(w: number, h: number) {
  return useMemo(() => {
    const canvas = document.createElement('canvas')
    canvas.width = w; canvas.height = h
    const tex = new THREE.CanvasTexture(canvas)
    tex.colorSpace = THREE.SRGBColorSpace
    return { canvas, tex }
  }, [w, h])
}

function Monitor({ position, size, px, paint, deps, everyMs }: {
  position: [number, number, number]; size: [number, number]; px: [number, number]
  paint: (ctx: CanvasRenderingContext2D, w: number, h: number) => void; deps: unknown[]; everyMs?: number
}) {
  const { canvas, tex } = useCanvasTexture(px[0], px[1])
  useEffect(() => {
    const run = () => { paint(canvas.getContext('2d')!, px[0], px[1]); tex.needsUpdate = true }
    run()
    if (!everyMs) return
    const id = setInterval(run, everyMs)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return (
    <group position={position}>
      <mesh position={[0, 0, -0.05]}>
        <boxGeometry args={[size[0] + 0.25, size[1] + 0.25, 0.1]} />
        <meshStandardMaterial color="#12103a" emissive="#5b4dff" emissiveIntensity={0.6} />
      </mesh>
      <mesh>
        <planeGeometry args={size} />
        <meshBasicMaterial map={tex} toneMapped={false} />
      </mesh>
    </group>
  )
}

/** The room inside a tower: three wall charts, scanner, heatmap and leaderboard, market plaque. */
export function Room3D({ data }: { data: RoomData }) {
  const { series, tickerTrades, rows, feed, selectedRow, total } = data
  const chart = (t: string) => (ctx: CanvasRenderingContext2D, w: number, h: number) => {
    const s = series[t]
    drawChart(ctx, w, h, s, { labels: true, axis: true })
    const hd = chartHeader(s, tickerTrades[t] ?? 0)
    ctx.fillStyle = '#fff'; ctx.font = `bold ${h * 0.07}px system-ui, sans-serif`; ctx.textAlign = 'left'
    ctx.fillText(`${t} 1-MIN  ${hd.time ?? ''}  ${formatNum(hd.price)}  ${hd.changePct == null ? '' : (hd.changePct >= 0 ? '+' : '') + hd.changePct.toFixed(2) + '%'}  ${hd.trades} trades`, 8, h * 0.075)
  }
  const [x, y, z] = [ROOM_ORIGIN.x, ROOM_ORIGIN.y, ROOM_ORIGIN.z]
  return (
    <group>
      <pointLight position={[x, y + 4, z + 2]} intensity={60} color="#9fb3ff" distance={30} />
      <mesh position={[x, y - 0.01, z]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[40, 40]} />
        <meshStandardMaterial color="#0d0a3a" roughness={0.9} />
      </mesh>
      <gridHelper args={[40, 40, '#5b4dff', '#241f6a']} position={[x, y, z]} />
      <mesh position={[x, y + 4, z - 6.2]}>
        <planeGeometry args={[40, 10]} />
        <meshBasicMaterial color="#0f0b45" />
      </mesh>
      <Monitor position={[x - 4.3, y + 3.2, z - 6]} size={[4, 2.4]} px={[1024, 614]} paint={chart('SPY')} deps={[series.SPY, tickerTrades.SPY]} />
      <Monitor position={[x, y + 3.2, z - 6]} size={[4.6, 2.76]} px={[1152, 690]} paint={chart('QQQ')} deps={[series.QQQ, tickerTrades.QQQ]} />
      <Monitor position={[x + 4.3, y + 3.2, z - 6]} size={[4, 2.4]} px={[1024, 614]} paint={chart('IWM')} deps={[series.IWM, tickerTrades.IWM]} />
      <Monitor position={[x - 4.3, y + 0.9, z - 5.9]} size={[4, 1.9]} px={[1024, 486]} paint={(c, w, h) => paintScanner(c, w, h, selectedRow, feed)} deps={[selectedRow, feed]} />
      <Monitor position={[x + 4.3, y + 0.9, z - 5.9]} size={[4, 1.9]} px={[1024, 486]} paint={(c, w, h) => paintBoard(c, w, h, rows)} deps={[rows]} />
      <Monitor position={[x, y + 0.9, z - 5.9]} size={[3.6, 1.2]} px={[960, 320]} paint={(c, w, h) => paintPlaque(c, w, h, Date.now(), total)} deps={[total]} everyMs={1000} />
    </group>
  )
}
