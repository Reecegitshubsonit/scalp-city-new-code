import { memo } from 'react'
import type { BotRow } from '../model/types'
import { formatPnl } from '../model/format'

function tint(pnl: number, scale: number): string {
  const a = Math.min(0.75, 0.12 + (Math.abs(pnl) / scale) * 0.6)
  return pnl > 0 ? `rgba(25,245,160,${a})` : pnl < 0 ? `rgba(255,59,107,${a})` : 'rgba(120,120,180,0.15)'
}

function HeatmapImpl({ rows, onSelect, title = 'Worker heatmap' }: { rows: BotRow[]; onSelect: (b: string) => void; title?: string }) {
  const scale = Math.max(300, ...rows.map(r => Math.abs(r.pnl_day)))
  return (
    <section className="panel heat" aria-label="P&L heatmap">
      <h2>{title}</h2>
      <div className="heatgrid">
        {rows.map(r => (
          <button key={r.bot} style={{ background: tint(r.pnl_day, scale) }} onClick={() => onSelect(r.bot)} aria-label={`${r.ticker} ${r.bot.split('-')[1]} ${formatPnl(r.pnl_day)}`}>
            <small>{r.ticker} {r.bot.split('-')[1]}</small>
            <b>{formatPnl(r.pnl_day)}</b>
            <small>{r.trades} trades</small>
          </button>
        ))}
      </div>
    </section>
  )
}
export const Heatmap = memo(HeatmapImpl)
