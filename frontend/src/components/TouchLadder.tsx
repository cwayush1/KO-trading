import { useState } from 'react'
import type { Touch, TouchWindow } from '../lib/types'
import { clockIn, parseEt, type Zone } from '../lib/time'

interface Props {
  touch: Touch
  /** The window in use; chosen by the caller so the chart can draw the same one. */
  win: TouchWindow | null
  onWindow: (minutes: number) => void
  tz: Zone
  target: string
  stop: string
  onTarget: (v: string) => void
  onStop: (v: string) => void
}

const windowName = (m: number) => (m < 60 ? `${m} min` : m === 60 ? '1 hour' : `${m / 60} hours`)
const pct = (x: number) => `${Math.round(x * 100)}%`
const WORDS: Record<string, string> = { '75': '3 times in 4', '50': '1 time in 2', '25': '1 time in 4', '10': '1 time in 10' }

/** Chance that a price `dist` away from the current one is touched, read off the ladder.
 *  Straight lines between the rungs; null beyond the last rung. */
export function touchOdds(win: TouchWindow, price: number, level: number): number | null {
  const dist = Math.abs(level - price)
  const pts: [number, number][] = [[0, 1], ...win.levels!.map((l): [number, number] => [l.up - price, l.odds])]
  for (let k = 1; k < pts.length; k++) {
    if (dist <= pts[k][0]) {
      const [d0, o0] = pts[k - 1], [d1, o1] = pts[k]
      return o0 + ((dist - d0) / (d1 - d0)) * (o1 - o0)
    }
  }
  return null
}

/** Ladder of price levels with the chance each is touched inside the window,
 *  plus a planner that reads a target and a stop off that ladder. */
export default function TouchLadderStrip({ touch, win, onWindow, tz, target, stop, onTarget, onStop }: Props) {
  const [open, setOpen] = useState(false)
  const price = touch.price
  const rec = win ? touch.record.since_training[String(win.minutes)] : null
  const day = win ? touch.record.session[String(win.minutes)] : null
  const t = touch.tested

  // Planner: typed values, or an example from the ladder until something is typed.
  const tVal = parseFloat(target), sVal = parseFloat(stop)
  const example = win && !isFinite(tVal) && !isFinite(sVal)
  const tgt = win ? (isFinite(tVal) ? tVal : example ? +win.levels![2].up.toFixed(2) : NaN) : NaN
  const stp = win ? (isFinite(sVal) ? sVal : example ? +win.levels![1].down.toFixed(2) : NaN) : NaN
  const say = (name: string, level: number) => {
    if (!win || !isFinite(level)) return null
    const o = touchOdds(win, price, level)
    const dist = Math.abs(level - price).toFixed(2)
    return (
      <li>
        <strong>{name} {level.toFixed(2)}</strong>, {dist} away: {o == null ? 'touched less than 1 time in 10' : <>touched about <strong>{pct(o)}</strong> of the time</>} within {windowName(win.minutes)}.
        {name === 'Stop' && o != null && o >= 0.5 && <span className="warn"> That is inside ordinary movement for this window, so noise alone will often take it out.</span>}
        {name === 'Target' && o == null && <span className="warn"> That is a long way for this window.</span>}
      </li>
    )
  }
  const opposite = isFinite(tgt) && isFinite(stp) && (tgt - price) * (stp - price) < 0
  const reward = Math.abs(tgt - price), risk = Math.abs(stp - price)

  return (
    <div className="cone">
      <div className="cone-head">
        <div>
          <h2>Touch ladder <span className="tag">Model-generated</span></h2>
          <p className="cone-lead">
            How likely price is to touch a level at any moment in the window. Targets and stops fill on a touch, not on where the hour closes.
            {win && win.vs_usual != null && <> Right now the levels sit <strong>{win.vs_usual.toFixed(2)}x</strong> as far out as normal.</>}
          </p>
        </div>
        <div className="seg" role="group" aria-label="Window">
          {touch.windows.map((w) => (
            <button key={w.minutes} className={win?.minutes === w.minutes ? 'on' : ''} aria-pressed={win?.minutes === w.minutes}
              disabled={!w.fits} title={w.fits ? '' : 'This window would run past the closing bell'} onClick={() => onWindow(w.minutes)}>
              {windowName(w.minutes)}
            </button>
          ))}
        </div>
      </div>

      {!win ? (
        <p className="cone-lead">Less than 30 minutes to the bell, so no window fits. Switch to the range cone to see the next session's open.</p>
      ) : (
        <>
          <dl className="cone-cells four">
            {win.levels!.map((l) => (
              <div key={l.odds}>
                <dt>Touched {WORDS[String(Math.round(l.odds * 100))]}</dt>
                <dd><span className="cone-range">±{(l.up - price).toFixed(2)}</span></dd>
                <dd className="cone-sub">{l.up.toFixed(2)} above, {l.down.toFixed(2)} below</dd>
              </div>
            ))}
          </dl>

          <div className="planner">
            <div className="planner-in">
              <label>Target<input type="number" step="0.01" inputMode="decimal" value={target} placeholder={win.levels![2].up.toFixed(2)} onChange={(e) => onTarget(e.target.value)} /></label>
              <label>Stop<input type="number" step="0.01" inputMode="decimal" value={stop} placeholder={win.levels![1].down.toFixed(2)} onChange={(e) => onStop(e.target.value)} /></label>
              <p>{example ? 'Type your own levels. Showing an example.' : `Read off the ladder, window ends ${clockIn(parseEt(win.end!) + 300, tz)} ${tz}.`}</p>
            </div>
            <ul className="planner-out">
              {say('Target', tgt)}
              {say('Stop', stp)}
              {opposite && risk > 0 && (
                <li>
                  Reward to risk {(reward / risk).toFixed(1)} to 1. This trade must win {pct(risk / (reward + risk))} of the time to break even,
                  and with no edge on direction that is also about how often the target comes first.
                </li>
              )}
            </ul>
          </div>

          {rec && rec.n > 0 && (
            <div className="cone-record ladder">
              <dl>
                {win.levels!.map((l) => {
                  const k = String(Math.round(l.odds * 100))
                  return (
                    <div key={k}>
                      <dt>Levels labelled {k}%</dt>
                      <dd><strong>{((rec.touched[k] / rec.n) * 100).toFixed(1)}%</strong> were touched</dd>
                    </div>
                  )
                })}
                <div>
                  <dt>This session so far</dt>
                  {day && day.n > 0
                    ? <dd><strong>{day.touched['50']} of {day.n}</strong> of the 50% levels touched</dd>
                    : <dd className="cone-sub">No {windowName(win.minutes)} window has finished yet.</dd>}
                </div>
              </dl>
              <p className="cone-sub">Track record over the {touch.record.days} sessions the model never trained on, {rec.n.toLocaleString()} levels. The closer each figure is to its label, the better.</p>
            </div>
          )}
        </>
      )}

      <p className="cone-trust">
        <strong>How to use it.</strong> Put a target where the odds suit the trade, and keep a stop outside the levels that ordinary movement reaches.
        The ladder is the same above and below because no edge on direction was found.{' '}
        <button className="more" onClick={() => setOpen(!open)} aria-expanded={open}>{open ? 'Hide the test' : 'How it was tested'}</button>
        {open && t && win && (
          <> On {t.wf_days} unseen sessions, {windowName(win.minutes)} levels labelled 75, 50, 25 and 10% were touched{' '}
            {['75', '50', '25', '10'].map((k) => pct(t.windows[String(win.minutes)].wf[k])).join(', ')} of the time;
            on the final {t.test_days} sessions {['75', '50', '25', '10'].map((k) => pct(t.windows[String(win.minutes)].test[k])).join(', ')}, so lately the levels have sat slightly too far out.
            A fixed distance labelled 25% was touched {pct(t.fixed_near)} of the time in quiet markets and {pct(t.fixed_far)} in busy ones.</>
        )}
        {touch.in_sample && <> This moment is inside the training period, so the fit here flatters the model.</>}
      </p>
    </div>
  )
}
