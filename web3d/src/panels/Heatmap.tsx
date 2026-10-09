import { memo } from 'react'
import type { BotRow } from '../model/types'
import { TICKERS, TRIGGERS } from '../model/layout'
import { formatPnl } from '../model/format'

function tint(pnl: number, scale: number): string {
  const a = Math.min(0.75, 0.12 + (Math.abs(pnl) / scale) * 0.6)
  return pnl > 0 ? `rgba(25,245,160,${a})` : pnl < 0 ? `rgba(255,59,107,${a})` : 'rgba(120,120,180,0.15)'
}

function HeatmapImpl({ rows, onSelect }: { rows: BotRow[]; onSelect: (b: string) => void }) {
  const by = new Map(rows.map(r => [r.bot, r]))
  const scale = Math.max(300, ...rows.map(r => Math.abs(r.pnl_day)))
  return (
    <section className="panel heat" aria-label="P&L heatmap">
      <h2>Worker heatmap</h2>
      <div className="heatgrid">
        {TICKERS.flatMap(t => TRIGGERS.map(k => {
          const r = by.get(`${t}-${k}`)
          const pnl = r?.pnl_day ?? 0
          return (
            <button key={`${t}-${k}`} style={{ background: tint(pnl, scale) }} onClick={() => onSelect(`${t}-${k}`)} aria-label={`${t} ${k} ${formatPnl(pnl)}`}>
              <small>{t} {k}</small>
              <b>{formatPnl(pnl)}</b>
              <small>{r?.trades ?? 0} trades</small>
            </button>
          )
        }))}
      </div>
    </section>
  )
}
export const Heatmap = memo(HeatmapImpl)
