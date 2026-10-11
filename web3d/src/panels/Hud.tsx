import { memo } from 'react'
import type { HudCard } from '../model/hud'

/** Four small cards over the top-left of the city view; click opens the day summary. */
function HudImpl({ cards, onOpen }: { cards: HudCard[]; onOpen: () => void }) {
  return (
    <div className="hud" role="group" aria-label="Day totals">
      {cards.map(c => (
        <button key={c.id} className={`hudcard ${c.tone}`} onClick={onOpen} aria-label={`${c.label} ${c.value}, ${c.sub}. Open day summary`}>
          <small>{c.label}</small>
          <b>{c.value}</b>
          <small>{c.sub}</small>
        </button>
      ))}
    </div>
  )
}
export const Hud = memo(HudImpl)
