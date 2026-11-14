import type { DayPlan } from '../lib/types'

const pct = (v: number) => `${(v * 100).toFixed(1)}%`

function Bar({ value, color }: { value: number; color: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ flex: 1, height: 7, background: 'var(--line)', borderRadius: 4, overflow: 'hidden' }}>
        <div style={{ width: `${value * 100}%`, height: '100%', background: color, borderRadius: 4 }} />
      </div>
      <span style={{ fontSize: 12, fontWeight: 600, minWidth: 38, textAlign: 'right', color }}>
        {pct(value)}
      </span>
    </div>
  )
}

interface Props {
  plan: DayPlan | null
}

export default function PredictionPanel({ plan }: Props) {
  const slots = plan?.slots ?? []

  return (
    <section className="panel model sf-panel">
      <header className="panel-head">
        <h2>Candle Forecast</h2>
        <span className="tag">Model-generated</span>
      </header>

      {!plan || slots.length === 0 ? (
        <p style={{ color: 'var(--muted)', fontSize: 13, textAlign: 'center', padding: '20px 0' }}>
          Select a session to see per-candle forecast.
        </p>
      ) : (
        <>
          <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10 }}>
            {plan.date} · {slots.length} candles · pre-open forecast
            {plan.in_sample && <span style={{ marginLeft: 8, color: 'var(--warn)' }}>⚠ in-sample</span>}
          </p>

          <div className="sf-table-wrap">
            <table className="sf-table">
              <thead>
                <tr>
                  <th>Time (ET)</th>
                  <th style={{ color: 'var(--down)' }}>↓ Down</th>
                  <th style={{ color: 'var(--up)' }}>↑ Up</th>
                  <th>Call</th>
                </tr>
              </thead>
              <tbody>
                {slots.map(s => {
                  const p_up = s.p_up
                  const p_down = 1 - p_up
                  const isUp = p_up >= 0.5
                  const faint = Math.abs(p_up - 0.5) < 0.05
                  return (
                    <tr key={s.slot} className={`sf-row sf-row-${isUp ? 'up' : 'down'} ${faint ? 'sf-row-faint' : ''}`}>
                      <td className="sf-time-col">{s.time}</td>
                      <td><Bar value={p_down} color="var(--down)" /></td>
                      <td><Bar value={p_up} color="var(--up)" /></td>
                      <td>
                        {isUp
                          ? <span style={{ color: 'var(--up)', fontWeight: 700, fontSize: 13 }}>↑ UP</span>
                          : <span style={{ color: 'var(--down)', fontWeight: 700, fontSize: 13 }}>↓ DN</span>}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <p className="basis" style={{ marginTop: 8 }}>
            Pre-open forecast using sessions through {plan.uses_sessions_through}.
            Faint rows ≈ 50/50.
          </p>
        </>
      )}
    </section>
  )
}
