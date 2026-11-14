import type { Bars, NextCalls, NextScores, Session } from '../lib/types'
import { clockIn, parseEt, slotOf, SLOTS, type Zone } from '../lib/time'

interface Props {
  calls: NextCalls | null
  scores: NextScores | null
  bars: Bars
  session: Session
  asOf: number
  tz: Zone
}

const HOURS = [0, 12, 24, 36, 48, 60, 72]
const pct1 = (x: number) => `${(x * 100).toFixed(1)}%`

/** Up or down for the following 5-minute candle, called at each candle close
 *  and scored one candle later. "Up" means it closes above the close before it. */
export default function NextCandlePanel({ calls, scores, bars, session, asOf, tz }: Props) {
  if (!calls) return null
  const nowSlot = slotOf(bars.t[asOf])
  const at = (time: string) => `${clockIn(parseEt(`${calls.date} ${time}`), tz)} ${tz}`

  // What each candle did against the close before it, up to the chosen moment. 1 up, -1 down, 0 flat.
  const actual: (number | null)[] = new Array(SLOTS).fill(null)
  for (let i = session.start + 1; i <= asOf; i++) {
    const s = slotOf(bars.t[i])
    if (s > 0 && s < SLOTS && slotOf(bars.t[i - 1]) === s - 1) actual[s] = Math.sign(bars.c[i] - bars.c[i - 1])
  }

  // A call exists once the candle before it has closed.
  const bySlot = new Map(calls.calls.filter((c) => c.slot - 1 <= nowSlot).map((c) => [c.slot, c]))
  const pending = bySlot.get(nowSlot + 1)
  let right = 0, total = 0, sRight = 0, sTotal = 0
  bySlot.forEach((c) => {
    const a = actual[c.slot]
    if (a == null || a === 0) return
    const ok = (c.p_up > 0.5) === (a > 0)
    total++; if (ok) right++
    if (c.strong) { sTotal++; if (ok) sRight++ }
  })
  const s = scores?.since_training
  const t = calls.tested
  const slots = Array.from({ length: SLOTS }, (_, k) => k)
  const hourLabel = (k: number) => clockIn(parseEt(`${calls.date} 09:30`) + k * 300, tz)

  return (
    <section className="panel model plan">
      <header className="panel-head">
        <h2>Next 5-minute candle: up or down</h2>
        <span className="tag">Model-generated</span>
      </header>

      {s && s.strong_total > 0 && (
        <div className="plan-overall">
          <span className="big">{pct1(s.strong_right / s.strong_total)}</span>
          <p>
            <strong>Directional accuracy on confident calls.</strong> {s.strong_right.toLocaleString()} of {s.strong_total.toLocaleString()} right
            over the {s.days} sessions the model never trained on. Across every call it is {pct1(s.right / s.total)}{' '}
            ({s.right.toLocaleString()} of {s.total.toLocaleString()}). 50% is what a coin gets.
          </p>
        </div>
      )}

      <p className="next-call">
        {pending ? (
          <>
            Next candle, {at(pending.time)}:{' '}
            <strong className={pending.p_up > 0.5 ? 'up' : 'down'}>
              {pending.p_up > 0.5 ? 'Up' : 'Down'}, {Math.round(Math.max(pending.p_up, 1 - pending.p_up) * 100)}%
            </strong>
            . {pending.strong ? 'Confident call.' : 'Weak call, close to 50/50.'}
          </>
        ) : (
          <>No call is open. The next one comes after the first candle of the next session.</>
        )}
      </p>
      <p className="plan-score">
        {total === 0 ? <>No scored calls yet in this session.</> : (
          <>
            This session up to {clockIn(bars.t[asOf], tz)} {tz}:{' '}
            <strong>confident calls {sRight} of {sTotal} right{sTotal > 0 ? `, ${pct1(sRight / sTotal)}` : ''}</strong>.
            {' '}All calls {right} of {total}, {pct1(right / total)}.
          </>
        )}
      </p>
      {calls.in_sample && <p className="insample">This day is inside the model's training period, so its score here flatters the model.</p>}

      <div className="plan-rows">
        <span className="plan-label">Called</span>
        <div className="plan-grid">
          {slots.map((k) => {
            const c = bySlot.get(k)
            if (!c) return <i key={k} className="b-none" />
            const up = c.p_up > 0.5
            return <i key={k} className={up ? 'b-up' : 'b-down'} style={{ opacity: c.strong ? 1 : 0.3 }}
              title={`${at(c.time)}: called ${up ? 'up' : 'down'}, ${Math.round(Math.max(c.p_up, 1 - c.p_up) * 100)}%${c.strong ? ', confident' : ''}`} />
          })}
        </div>
        <span className="plan-label">Actual</span>
        <div className="plan-grid">
          {slots.map((k) => {
            const a = actual[k]
            return <i key={k} className={a == null ? 'b-none' : a > 0 ? 'b-up' : a < 0 ? 'b-down' : 'b-flat'} />
          })}
        </div>
        <span className="plan-label">Right</span>
        <div className="plan-grid thin">
          {slots.map((k) => {
            const c = bySlot.get(k), a = actual[k]
            const ok = !!c && a != null && a !== 0 && (c.p_up > 0.5) === (a > 0)
            return <i key={k} className={ok ? 'b-ok' : ''} style={{ opacity: c?.strong ? 1 : 0.35 }} />
          })}
        </div>
        <span />
        <div className="plan-hours" aria-hidden="true">
          {HOURS.map((h) => <span key={h} style={{ left: `${(h / SLOTS) * 100}%` }}>{hourLabel(h)}</span>)}
        </div>
      </div>
      <p className="basis">
        Each call is made when the candle before it closes, from candles up to that close only. Solid cells are confident calls; faint cells are weak ones.
        Up means the candle closes above the close before it.
      </p>

      {t && (
        <p className="verdict">
          <strong>How far to trust it.</strong> On {t.wf.days} unseen sessions, confident calls were right {pct1(t.wf.strong.hit)} of the time
          (likely range {pct1(t.wf.strong.ci[0])} to {pct1(t.wf.strong.ci[1])}) and all calls {pct1(t.wf.all.hit)}.
          On the final {t.test.days} held-out sessions: {pct1(t.test.strong.hit)} and {pct1(t.test.all.hit)}.
          Confident means the top 10% of calls by distance from 50/50, about {Math.round(t.wf.strong.per_day)} a day, with the bar set before testing.
          Flat candles are not scored. The edge lasts one candle and is small, so it is a measured result, not a trading signal.
        </p>
      )}
    </section>
  )
}
