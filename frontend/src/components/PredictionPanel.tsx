import type { DayPlan } from '../lib/types'

const pct = (v: number) => `${(v * 100).toFixed(1)}%`

/** Neutral half-width: at exactly p_up=0.5, neutral gets 2*HALF_N = 10%.
 *  Neutral mass → 0 linearly as the model moves ≥5% from center. */
const HALF_N = 0.05

/** Call shows "— N" only when truly near 50/50 (within 2% of center). */
const NEUTRAL_CALL = 0.02

function Bar({ value, color }: { value: number; color: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <div style={{ flex: 1, height: 7, background: 'var(--line)', borderRadius: 4, overflow: 'hidden' }}>
        <div style={{ width: `${value * 100}%`, height: '100%', background: color, borderRadius: 4 }} />
      </div>
      <span style={{ fontSize: 11, fontWeight: 600, minWidth: 36, textAlign: 'right', color }}>
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
                  <th style={{ color: '#8894a1' }}>— Neutral</th>
                  <th style={{ color: 'var(--up)' }}>↑ Up</th>
                  <th>Call</th>
                </tr>
              </thead>
              <tbody>
                {slots.map(s => {
                  const p_up = s.p_up
                  const p_down = 1 - p_up
                  const conf = Math.abs(p_up - 0.5)

                  // Carve neutral from the centre of the down/up split
                  const half_neutral = Math.max(0, HALF_N - conf)
                  const p_neutral = 2 * half_neutral
                  const p_down_d = p_down - half_neutral   // display down
                  const p_up_d   = p_up   - half_neutral   // display up

                  // Call label & styling
                  const isNeutralCall = conf < NEUTRAL_CALL
                  const isUp = p_up >= 0.5
                  const callType = isNeutralCall ? 'neutral' : isUp ? 'up' : 'down'

                  // Faint background tint scaled by confidence
                  const bgTint = isNeutralCall
                    ? 'rgba(136, 148, 161, 0.05)'
                    : isUp
                      ? `rgba(14, 138, 95, ${(0.035 + Math.min(1, conf / 0.06) * 0.055).toFixed(3)})`
                      : `rgba(200, 55, 45, ${(0.035 + Math.min(1, conf / 0.06) * 0.055).toFixed(3)})`

                  return (
                    <tr
                      key={s.slot}
                      className={`sf-row sf-row-${callType}`}
                      style={{ background: bgTint }}
                    >
                      <td className="sf-time-col">{s.time}</td>
                      <td><Bar value={Math.max(0, p_down_d)} color="var(--down)" /></td>
                      <td><Bar value={Math.max(0, p_neutral)} color="#8894a1" /></td>
                      <td><Bar value={Math.max(0, p_up_d)} color="var(--up)" /></td>
                      <td>
                        <span className={`sf-call-badge sf-call-${callType}`}>
                          {isNeutralCall ? '— N' : isUp ? '↑ UP' : '↓ DN'}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <p className="basis" style={{ marginTop: 8 }}>
            Pre-open forecast using sessions through {plan.uses_sessions_through}.
            Down + Neutral + Up = 100%. Neutral peaks at 10% when model is 50/50.
          </p>
        </>
      )}
    </section>
  )
}
