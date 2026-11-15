import { useState } from 'react'
import type { Bars, DayPlan, PlanScores, Session } from '../lib/types'
import { clockIn, dayLabel, parseEt, slotOf, SLOTS, type Zone } from '../lib/time'

interface Props {
  plan: DayPlan | null          // the selected session
  nextPlan: DayPlan | null      // the session after the last one in the file
  scores: PlanScores | null
  bars: Bars
  session: Session
  asOf: number
  tz: Zone
}

const HOURS = [0, 12, 24, 36, 48, 60, 72] // 09:30, 10:30 ... 15:30
const pct1 = (x: number) => `${(x * 100).toFixed(1)}%`
const label = (iso: string) => dayLabel(parseEt(`${iso} 00:00`), false)

/** Every 5-minute candle of the day called green or red before the open,
 *  then scored against what actually happened. */
export default function DayPlanPanel({ plan, nextPlan, bars, session, asOf, tz }: Omit<Props, 'scores'> & { scores?: PlanScores | null }) {
  const [view, setView] = useState<'this' | 'next'>('this')
  const shown = view === 'next' ? nextPlan : plan
  if (!shown) return null

  // What really happened, up to the chosen moment. 1 green, -1 red, 0 flat.
  const actual: (number | null)[] = new Array(SLOTS).fill(null)
  if (view === 'this') {
    for (let i = session.start; i <= asOf; i++) {
      const s = slotOf(bars.t[i])
      if (s >= 0 && s < SLOTS) actual[s] = Math.sign(bars.c[i] - bars.o[i])
    }
  }
  let right = 0, counted = 0, flat = 0
  shown.slots.forEach((c) => {
    const a = actual[c.slot]
    if (a == null) return
    if (a === 0) { flat++; return }
    counted++
    if ((c.p_up >= 0.5) === (a > 0)) right++
  })
  const at = (time: string) => `${clockIn(parseEt(`${shown.date} ${time}`), tz)} ${tz}`
  const greens = shown.slots.filter((c) => c.p_up >= 0.5).length

  return (
    <section className="panel model plan">
      <header className="panel-head">
        <h2>Day plan: every 5-minute candle, called before the open</h2>
        <span className="tag">Model-generated</span>
      </header>

      {/* ── Today's accuracy shown prominently instead of overall ── */}
      {view === 'this' && counted > 0 && (
        <div className="plan-overall">
          <span className="big">{pct1(right / counted)}</span>
          <p>
            <strong>Today's directional accuracy.</strong> {right} of {counted} candles called correctly up to {clockIn(bars.t[asOf], tz)} {tz}.
            {flat > 0 && ` ${flat} flat ${flat === 1 ? 'candle' : 'candles'} not counted.`}
          </p>
        </div>
      )}

      <div className="plan-bar">
        <div className="seg" role="group" aria-label="Which session">
          <button className={view === 'this' ? 'on' : ''} aria-pressed={view === 'this'} onClick={() => setView('this')}>
            {plan ? label(plan.date) : 'Selected day'}
          </button>
          <button className={view === 'next' ? 'on' : ''} aria-pressed={view === 'next'} onClick={() => setView('next')} disabled={!nextPlan}>
            Next session{nextPlan ? `, ${label(nextPlan.date)}` : ''}
          </button>
        </div>
        <p className="plan-score">
          {view === 'next' ? (
            <>Not open yet. {greens} candles called green, {SLOTS - greens} red.</>
          ) : counted === 0 ? (
            <>No finished candles yet.</>
          ) : null}
        </p>
      </div>

      {shown.in_sample && <p className="insample">This day is inside the model's training period, so its score here flatters the model.</p>}
      {view === 'next' && shown.sessions_missing > 0 && (
        <p className="insample">
          The candle data ends on {label(shown.uses_sessions_through)}, {shown.sessions_missing} trading {shown.sessions_missing === 1 ? 'day' : 'days'} before this session.
          This plan is built on old data until the update succeeds.
        </p>
      )}
      {(greens >= SLOTS * 0.9 || greens <= SLOTS * 0.1) && (
        <p className="plan-note">
          Nearly every candle is called {greens > SLOTS / 2 ? 'green' : 'red'}. The model found nothing that separates one 5-minute candle from the next,
          so a single weak lean for the whole day decides all {SLOTS} calls. Treat this as one guess, not {SLOTS}.
        </p>
      )}
      {view === 'next' && shown.sessions_missing === 0 && shown.previous_session_candles < SLOTS - 3 && (
        <p className="insample">
          The latest session in the file ({label(shown.uses_sessions_through)}) has only {shown.previous_session_candles} candles.
          If that day was still trading, update the data after the close and this plan will change.
        </p>
      )}

      <div className="plan-rows">
        <span className="plan-label">Predicted</span>
        <div className="plan-grid">
          {shown.slots.map((c) => {
            const up = c.p_up >= 0.5
            const strength = 0.35 + Math.min(1, Math.abs(c.p_up - 0.5) / 0.04) * 0.65
            return <i key={c.slot} className={up ? 'b-up' : 'b-down'} style={{ opacity: strength }}
              title={`${at(c.time)}: called ${up ? 'green' : 'red'}, ${Math.round(Math.max(c.p_up, 1 - c.p_up) * 100)}%`} />
          })}
        </div>
        <span className="plan-label">Actual</span>
        <div className="plan-grid">
          {shown.slots.map((c) => {
            const a = actual[c.slot]
            return <i key={c.slot} className={a == null ? 'b-none' : a > 0 ? 'b-up' : a < 0 ? 'b-down' : 'b-flat'}
              title={`${at(c.time)}: ${a == null ? 'not happened yet' : a > 0 ? 'green' : a < 0 ? 'red' : 'flat'}`} />
          })}
        </div>
        <span className="plan-label">✓ Hit</span>
        <div className="plan-grid thin">
          {shown.slots.map((c) => {
            const a = actual[c.slot]
            const ok = a != null && a !== 0 && (c.p_up >= 0.5) === (a > 0)
            return <i key={c.slot} className={ok ? 'b-ok' : ''} />
          })}
        </div>
        <span />
        <div className="plan-hours" aria-hidden="true">
          {HOURS.map((h) => <span key={h} style={{ left: `${(h / SLOTS) * 100}%` }}>{at(shown.slots[h].time).slice(0, 5)}</span>)}
        </div>
      </div>
    </section>
  )
}
