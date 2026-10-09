import { memo } from 'react'
import type { Series } from '../model/history'
import { TICKERS } from '../model/layout'
import { CandleChart } from './CandleChart'

interface Props { series: Record<string, Series>; trades: Record<string, number> }
function ChartsImpl({ series, trades }: Props) {
  return (
    <section className="charts" aria-label="Price charts">
      {TICKERS.map(t => series[t] && <CandleChart key={t} series={series[t]} trades={trades[t] ?? 0} height={150} labels={false} compact />)}
    </section>
  )
}
export const Charts = memo(ChartsImpl)
