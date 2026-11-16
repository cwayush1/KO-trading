import type { Cone, ConeScores } from '../lib/types'
import { clockIn, dayLabel, parseEt, type Zone } from '../lib/time'

interface Props {
  cone: Cone | null
  scores: ConeScores | null
  tz: Zone
  show: boolean
  onShow: (v: boolean) => void
  /** Offered only when replaying a past moment, where later candles exist. */
  canReveal: boolean
  reveal: boolean
  onReveal: (v: boolean) => void
  /** Close of the candle that starts at this ET time, once revealed. */
  closeAt: (t: number) => number | undefined
}

const WINDOWS = [30, 60, 120]
const windowName = (m: number) => (m < 60 ? `${m} min` : m === 60 ? '1 hour' : `${m / 60} hours`)
const pct = (x: number) => `${Math.round(x * 100)}%`
const pct1 = (x: number) => `${(x * 100).toFixed(1)}%`
const dayName = (iso: string) => dayLabel(parseEt(`${iso} 00:00`), false)

/** Reads the cone out in words and numbers above the chart: the likely price
 *  range for the next 30 minutes, 1 hour and 2 hours, and how wide that is against normal. */
export default function RangeConeStrip({ cone, scores, tz, show, onShow, canReveal, reveal, onReveal, closeAt }: Props) {
  if (!cone) return null
  const opening = cone.kind === 'opening'
  const rows = cone.horizons.filter((h) => WINDOWS.includes(h.minutes))
  const r = cone.width_vs_usual
  const mood = r == null ? null : r >= 1.15 ? 'Busier than usual' : r <= 0.87 ? 'Quieter than usual' : 'About as busy as usual'
  const all = scores?.since_training, day = scores?.session

  return (
    <div className="cone">
      <div className="cone-head">
        <div>
          <h2>Range cone <span className="tag">Model-generated</span></h2>
          {!opening && (
            <p className="cone-lead">
              <strong className={r != null && r >= 1.15 ? 'warn' : ''}>{mood}.</strong> The model draws the next hour {r!.toFixed(2)}x as wide as a normal one.
            </p>
          )}
        </div>
        <div className="chips" role="group" aria-label="Range cone display">
          <button className={show ? 'on' : ''} aria-pressed={show} onClick={() => onShow(!show)}>
            <span className="sw"><i style={{ background: 'var(--model)' }} /></span>Cone on chart
          </button>
          {canReveal && (
            <button className={reveal ? 'on' : ''} aria-pressed={reveal} onClick={() => onReveal(!reveal)}>What happened next</button>
          )}
        </div>
      </div>

      {!opening && <dl className="cone-cells">
        {rows.map((h) => {
          const end = parseEt(h.time) + 300          // the candle closes five minutes after it starts
          const got = reveal ? closeAt(parseEt(h.time)) : undefined
          const inside = got != null && got >= h.lo80 && got <= h.hi80
          return (
            <div key={h.minutes}>
              <dt>Next {windowName(h.minutes)}, by {clockIn(end, tz)} {tz}</dt>
              <dd>
                <span className="cone-range">{h.lo50.toFixed(2)} to {h.hi50.toFixed(2)}</span>
                <span className="cone-pm">±{((h.hi50 - h.lo50) / 2).toFixed(2)}</span>
              </dd>
              <dd className="cone-sub">
                {got != null
                  ? <span className={inside ? 'up' : 'down'}>Closed {got.toFixed(2)}, {got >= h.lo50 && got <= h.hi50 ? 'inside the core' : inside ? 'inside the wide band' : 'outside both'}</span>
                  : <>Wide band {h.lo80.toFixed(2)} to {h.hi80.toFixed(2)}</>}
              </dd>
            </div>
          )
        })}
        {rows.length === 0 && <div><dt>Too close to the bell for a 30-minute range</dt><dd className="cone-sub">The chart shows the minutes that are left.</dd></div>}
      </dl>}

      {all && all['60'].n > 0 && (
        <div className="cone-record">
          <dl>
            <div>
              <dt>Track record, 1-hour cones</dt>
              <dd><strong>{pct1(all['60'].in80 / all['60'].n)}</strong> closed inside the wide band</dd>
              <dd className="cone-sub">{all['60'].in80.toLocaleString()} of {all['60'].n.toLocaleString()} over {all.days} sessions the model never trained on. Target 80%.</dd>
            </div>
            <div>
              <dt>Dark core, same cones</dt>
              <dd><strong>{pct1(all['60'].in50 / all['60'].n)}</strong> closed inside</dd>
              <dd className="cone-sub">Target 50%. 30-minute cones {pct1(all['30'].in80 / all['30'].n)}, 2-hour cones {pct1(all['120'].in80 / all['120'].n)} in the wide band.</dd>
            </div>
            <div>
              <dt>This session so far</dt>
              {day && day['60'].n > 0
                ? <><dd><strong>{day['60'].in80} of {day['60'].n}</strong> inside the wide band</dd><dd className="cone-sub">{pct(day['60'].in80 / day['60'].n)}. Only cones whose hour has finished are counted.</dd></>
                : <dd className="cone-sub">No 1-hour cone has finished yet.</dd>}
            </div>
          </dl>
          {scores && scores.recent.length > 1 && (
            <div className="cone-days">
              <div className="plan-days" role="img" aria-label="Share of 1-hour closes inside the wide band on recent sessions">
                {scores.recent.map((d) => {
                  const hit = d.in80 / d.n
                  return <i key={d.date} className={hit >= 0.8 ? 'hi' : 'lo'} style={{ height: `${Math.max(4, Math.min(100, ((hit - 0.6) / 0.4) * 100))}%` }}
                    title={`${dayName(d.date)}: ${d.in80} of ${d.n} inside, ${pct(hit)}`} />
                })}
              </div>
              <p>Last {scores.recent.length} sessions, one bar per day. The line is the 80% target; one day can sit well off it.</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
