import type { PlanScores } from '../lib/types'

interface Props {
  scores: PlanScores | null
}

/** The day plan's accuracy over the latest ten sessions with scored candles. */
export default function AccuracyHistory({ scores }: Props) {
  const days = scores?.recent.filter((day) => day.total > 0).slice(-10) ?? []
  const lastDate = days.length ? days[days.length - 1].date : null
  const left = 32
  const top = 24
  const height = 120
  const bottom = top + height
  const width = 312
  const step = width / Math.max(days.length, 1)
  const barWidth = Math.min(22, step * 0.68)

  return (
    <section className="panel accuracy-panel" aria-labelledby="accuracy-heading">
      <header className="panel-head">
        <h2 id="accuracy-heading">Directional accuracy</h2>
      </header>
      <p className="accuracy-subtitle">Day plan · last {days.length || 10} trading sessions{lastDate ? ` through ${lastDate}` : ''}</p>

      {days.length ? (
        <>
          <svg className="accuracy-chart" viewBox="0 0 360 180" role="img" aria-labelledby="accuracy-chart-title accuracy-chart-desc">
            <title id="accuracy-chart-title">Day-plan accuracy by trading session</title>
            <desc id="accuracy-chart-desc">Each bar shows the percentage of non-flat five-minute candles called correctly. The dashed line marks 50 percent.</desc>
            {[0, 0.5, 1].map((value) => {
              const y = bottom - value * height
              return (
                <g key={value}>
                  <line x1={left} x2={left + width} y1={y} y2={y} className={value === 0.5 ? 'accuracy-midline' : 'accuracy-gridline'} />
                  <text x={left - 6} y={y + 4} textAnchor="end" className="accuracy-axis">{Math.round(value * 100)}</text>
                </g>
              )
            })}
            {days.map((day, index) => {
              const accuracy = day.right / day.total
              const x = left + index * step + (step - barWidth) / 2
              const y = bottom - accuracy * height
              return (
                <g key={day.date}>
                  <title>{`${day.date}: ${(accuracy * 100).toFixed(1)}%, ${day.right} of ${day.total} candles correct`}</title>
                  <rect x={x} y={y} width={barWidth} height={bottom - y} rx="3" className={accuracy >= 0.5 ? 'accuracy-above' : 'accuracy-below'} />
                  <text x={x + barWidth / 2} y={Math.max(top - 9, y - 5)} textAnchor="middle" className="accuracy-value">{Math.round(accuracy * 100)}%</text>
                  <text x={x + barWidth / 2} y={bottom + 17} textAnchor="middle" className="accuracy-date">{day.date.slice(5)}</text>
                </g>
              )
            })}
          </svg>
          <p className="accuracy-note">Correct calls ÷ non-flat candles. The newest session updates as candles arrive.</p>
        </>
      ) : (
        <p className="accuracy-note">Accuracy history will appear when the model scores are available.</p>
      )}
    </section>
  )
}
