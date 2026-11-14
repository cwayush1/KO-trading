import type { Bars, Session } from '../lib/types'
import { BAR_SEC, OPEN_SEC, SLOTS, clockIn, dayLabel, sessionPhase, slotOf, type Zone } from '../lib/time'

interface Props {
  bars: Bars
  sessions: Session[]
  sIdx: number
  asOf: number
  tz: Zone
  onSession: (i: number) => void
  onAsOf: (i: number) => void
}

const MARKS = [0, 18, 36, 54, 78] // 09:30, 11:00, 12:30, 14:00, 16:00

/** Picks the trading day and the moment within it. Everything else on the page
 *  is computed as of that moment, using only candles up to it. */
export default function SessionBar({ bars, sessions, sIdx, asOf, tz, onSession, onAsOf }: Props) {
  const s = sessions[sIdx]
  const t = bars.t[asOf]
  const slot = slotOf(t)
  const lastSlot = slotOf(bars.t[s.end])
  const isLatest = sIdx === sessions.length - 1 && asOf === s.end
  const dayBase = Math.floor(bars.t[s.start] / 86400) * 86400
  const other: Zone = tz === 'IST' ? 'ET' : 'IST'

  const pickDate = (iso: string) => {
    if (!iso) return
    // Snap to the nearest trading day on or before the chosen date.
    let k = sessions.length - 1
    while (k > 0 && sessions[k].date > iso) k--
    onSession(k)
  }
  const scrub = (v: number) => {
    const target = Math.floor(bars.t[s.start] / 86400) * 86400 + OPEN_SEC + v * BAR_SEC
    let k = s.start
    while (k < s.end && bars.t[k + 1] <= target) k++
    onAsOf(k)
  }

  return (
    <section className="session" aria-label="Session time">
      <div className="session-day">
        <button onClick={() => onSession(sIdx - 1)} disabled={sIdx === 0} aria-label="Previous trading day">‹</button>
        <label className="date">
          <span>{dayLabel(t)}</span>
          <input type="date" value={s.date} min={sessions[0].date} max={sessions[sessions.length - 1].date}
            onChange={(e) => pickDate(e.target.value)} aria-label="Choose trading day" />
        </label>
        <button onClick={() => onSession(sIdx + 1)} disabled={sIdx === sessions.length - 1} aria-label="Next trading day">›</button>
      </div>

      <div className="timeline">
        <input type="range" min={0} max={SLOTS - 1} step={1} value={slot}
          onChange={(e) => scrub(Math.min(+e.target.value, lastSlot))}
          style={{ ['--fill' as string]: `${(slot / (SLOTS - 1)) * 100}%`, ['--avail' as string]: `${(lastSlot / (SLOTS - 1)) * 100}%` }}
          aria-label="Time within the session" aria-valuetext={`${clockIn(t, tz)} ${tz}`} />
        <div className="marks" aria-hidden="true">
          {MARKS.map((m) => (
            <span key={m} style={{ left: `${(m / SLOTS) * 100}%` }}>{clockIn(dayBase + OPEN_SEC + m * BAR_SEC, tz)}</span>
          ))}
        </div>
      </div>

      <div className="clock">
        <div className="clock-main">{clockIn(t, tz)} <small>{tz}</small></div>
        <div className="clock-sub">{sessionPhase(t)}. Same moment: {clockIn(t, other)} {other}</div>
      </div>

      <button className="latest" onClick={() => onSession(sessions.length - 1)} disabled={isLatest}>
        Jump to latest
      </button>
    </section>
  )
}
