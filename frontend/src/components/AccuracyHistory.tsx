import { useState } from 'react'
import type { PlanScores } from '../lib/types'

interface Props {
  scores: PlanScores | null
}

const MIN = 0.3
const MAX = 0.7
const LEFT = 32
const TOP = 32
const WIDTH = 312
const HEIGHT = 120

/** The day plan's accuracy over the latest twenty sessions with scored candles. */
export default function AccuracyHistory({ scores }: Props) {
  const [hovered, setHovered] = useState<number | null>(null)
  const days = scores?.recent.filter((day) => day.total > 0).slice(-20) ?? []
  const lastDate = days.length ? days[days.length - 1].date : null
  const step = WIDTH / Math.max(days.length - 1, 1)
  const points = days.map((day, index) => {
    const accuracy = day.right / day.total
    const plotted = Math.max(MIN, Math.min(MAX, accuracy))
    return {
      ...day,
      accuracy,
      x: days.length === 1 ? LEFT + WIDTH / 2 : LEFT + index * step,
      y: TOP + ((MAX - plotted) / (MAX - MIN)) * HEIGHT,
    }
  })
  const active = hovered === null ? null : points[hovered] ?? null

  return (
    <section className="panel accuracy-panel" aria-labelledby="accuracy-heading">
      <header className="panel-head">
        <h2 id="accuracy-heading">Directional accuracy</h2>
      </header>
      <p className="accuracy-subtitle">Day plan · last {days.length || 20} trading sessions{lastDate ? ` through ${lastDate}` : ''}</p>

      {days.length ? (
        <>
          <svg className="accuracy-chart" viewBox="0 0 360 184" role="img" aria-labelledby="accuracy-chart-title accuracy-chart-desc">
            <title id="accuracy-chart-title">Day-plan accuracy trend</title>
            <desc id="accuracy-chart-desc">The vertical scale runs from 30 to 70 percent. Each point is the percentage of non-flat five-minute candles called correctly on one trading day. The dashed line marks 50 percent.</desc>
            {[0.3, 0.4, 0.5, 0.6, 0.7].map((value) => {
              const y = TOP + ((MAX - value) / (MAX - MIN)) * HEIGHT
              return (
                <g key={value}>
                  <line x1={LEFT} x2={LEFT + WIDTH} y1={y} y2={y} className={value === 0.5 ? 'accuracy-midline' : 'accuracy-gridline'} />
                  <text x={LEFT - 6} y={y + 4} textAnchor="end" className="accuracy-axis">{Math.round(value * 100)}</text>
                </g>
              )
            })}
            <polyline className="accuracy-trend" points={points.map(({ x, y }) => `${x},${y}`).join(' ')} />
            {points.map((point, index) => (
              <g key={point.date}>
                <circle cx={point.x} cy={point.y} r={hovered === index ? 5 : 3} className="accuracy-point" />
                {(index === 0 || index === points.length - 1 || (index + 1) % 5 === 0) && (
                  <text x={point.x} y={TOP + HEIGHT + 18} textAnchor={index === 0 ? 'start' : index === points.length - 1 ? 'end' : 'middle'} className="accuracy-date">{point.date.slice(5)}</text>
                )}
                <rect x={point.x - step / 2} y={TOP} width={step} height={HEIGHT} fill="transparent"
                  tabIndex={0} role="button"
                  aria-label={`${point.date}: ${(point.accuracy * 100).toFixed(1)}% correct, ${point.right} of ${point.total} candles`}
                  onMouseEnter={() => setHovered(index)} onMouseLeave={() => setHovered(null)}
                  onFocus={() => setHovered(index)} onBlur={() => setHovered(null)} />
              </g>
            ))}
            {active && (
              <g className="accuracy-tooltip">
                <rect x={Math.max(LEFT, Math.min(LEFT + WIDTH - 140, active.x - 70))} y={2} width={140} height={25} rx={5} />
                <text x={Math.max(LEFT, Math.min(LEFT + WIDTH - 140, active.x - 70)) + 70} y={19} textAnchor="middle">
                  {`${active.date} · ${(active.accuracy * 100).toFixed(1)}%`}
                </text>
              </g>
            )}
          </svg>
          <p className="accuracy-note">30–70% scale · hover for the exact date and percentage. The newest session updates as candles arrive.</p>
          {points.some((point) => point.accuracy < MIN || point.accuracy > MAX) && (
            <p className="accuracy-note">Values outside this range sit at the chart edge.</p>
          )}
        </>
      ) : (
        <p className="accuracy-note">Accuracy history will appear when the model scores are available.</p>
      )}
    </section>
  )
}
