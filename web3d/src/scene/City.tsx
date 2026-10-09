import type { BotRow } from '../model/types'
interface Props { rows: BotRow[]; selected: string | null; onSelect: (b: string) => void; reducedMotion: boolean; total: number }
export default function City(_p: Props) { return <div className="muted pad">3D placeholder</div> }
