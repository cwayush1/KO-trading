import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { apiUrl, fetchCone, fetchConeScores, fetchDayPlan, fetchPlanScores, fetchPrediction, loadDataset, requestUpdate, sliceBars, type Dataset } from './lib/data'
import { computeIndicators } from './lib/indicators'
import { analyze } from './lib/analysis'
import { clockIn, dayLabel, defaultZone, hhmm, inZone, isoDate, nyNow, parseEt, saveZone, type Zone } from './lib/time'
import type { Cone, ConeScores, DayPlan, PlanScores, Prediction, RangeKey, Toggles } from './lib/types'
import PriceChart from './components/PriceChart'
import SessionBar from './components/SessionBar'
import DayPlanPanel from './components/DayPlan'
import RangeConeStrip from './components/RangeCone'
import PredictionPanel from './components/PredictionPanel'
import AccuracyHistory from './components/AccuracyHistory'

const RANGES: RangeKey[] = ['1D', '5D', '1M', '3M']
const HISTORY_SESSIONS = 66

const compact = (v: number) => (v >= 1e6 ? `${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `${(v / 1e3).toFixed(0)}K` : String(v))

export default function App() {
  const [data, setData] = useState<Dataset | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [sIdx, setSIdx] = useState(0)
  const [asOf, setAsOf] = useState(0)
  const [range, setRange] = useState<RangeKey>('1D')
  const [toggles] = useState<Toggles>({ ema: false, vwap: false, bb: false, levels: false, rsi: false, macd: false })
  const [prediction, setPrediction] = useState<Prediction | null>(null)
  const [cone, setCone] = useState<Cone | null>(null)
  const [coneScores, setConeScores] = useState<ConeScores | null>(null)
  const [showCone, setShowCone] = useState(true)
  const [reveal, setReveal] = useState(false)
  const [plan, setPlan] = useState<DayPlan | null>(null)
  const [nextPlan, setNextPlan] = useState<DayPlan | null>(null)
  const [scores, setScores] = useState<PlanScores | null>(null)
  const [update, setUpdate] = useState<{ ok: boolean; message: string; at: number } | null>(null)
  const [tz, setTz] = useState<Zone>(defaultZone)
  const [clock, setClock] = useState(nyNow)
  const live = useRef({ lastCandle: '', atLatest: true })

  // Load candles. `follow` moves the view to the newest candle (first load, or when already there).
  const refresh = useCallback((follow: boolean) => {
    return loadDataset()
      .then((d) => {
        setData(d)
        const t = d.bars.t[d.bars.t.length - 1]
        live.current.lastCandle = `${isoDate(t)}T${hhmm(t)}`
        if (follow) {
          setSIdx(d.sessions.length - 1)
          setAsOf(d.bars.t.length - 1)
        }
        if (apiUrl) {
          fetchDayPlan('next').then(setNextPlan).catch(() => setNextPlan(null))
          fetchPlanScores(20).then(setScores).catch(() => setScores(null))
        }
      })
      .catch((e: Error) => setLoadError(e.message))
  }, [])

  useEffect(() => {
    refresh(true)
    const id = setInterval(() => setClock(nyNow()), 30_000)
    return () => clearInterval(id)
  }, [refresh])

  // Once a minute, ask the backend to pull new candles from Alpaca and pick them up.
  useEffect(() => {
    if (!apiUrl) return
    const tick = () =>
      requestUpdate()
        .then((u) => {
          setUpdate({ ok: u.ok, message: u.message, at: nyNow().t })
          if (u.last_candle && live.current.lastCandle && u.last_candle !== live.current.lastCandle) refresh(live.current.atLatest)
        })
        .catch(() => setUpdate({ ok: false, message: 'the backend is not reachable.', at: nyNow().t }))
    const initialTimer = setTimeout(tick, 10_000)
    const id = setInterval(tick, 60_000)
    return () => { clearTimeout(initialTimer); clearInterval(id) }
  }, [refresh])

  const goSession = (i: number) => {
    if (!data) return
    const k = Math.min(Math.max(i, 0), data.sessions.length - 1)
    setSIdx(k)
    setAsOf(data.sessions[k].end)
  }

  // Everything below is computed from candles up to `asOf` and nothing later.
  const view = useMemo(() => {
    if (!data) return null
    const first = Math.max(0, sIdx - HISTORY_SESSIONS)
    const from = data.sessions[first].start
    const bars = sliceBars(data.bars, from, asOf)
    const sessStarts = data.sessions.slice(first, sIdx + 1).map((s) => s.start - from)
    return { bars, sessStarts, ind: computeIndicators(bars) }
  }, [data, sIdx, asOf])

  const asOfT = data ? data.bars.t[asOf] : 0

  useEffect(() => {
    if (!apiUrl || !asOfT) return
    const ctl = new AbortController()
    const id = setTimeout(() => {
      fetchPrediction(`${isoDate(asOfT)}T${hhmm(asOfT)}`, ctl.signal)
        .then(setPrediction)
        .catch((e: Error) => { if (e.name !== 'AbortError') setPrediction(null) })
      fetchCone(`${isoDate(asOfT)}T${hhmm(asOfT)}`, ctl.signal)
        .then(setCone)
        .catch((e: Error) => { if (e.name !== 'AbortError') setCone(null) })
      fetchConeScores(`${isoDate(asOfT)}T${hhmm(asOfT)}`, ctl.signal)
        .then(setConeScores)
        .catch((e: Error) => { if (e.name !== 'AbortError') setConeScores(null) })
    }, 250)
    return () => { clearTimeout(id); ctl.abort() }
  }, [asOfT])

  // The day plan depends only on the session date, not on the time within it.
  const sessionDate = data ? data.sessions[sIdx].date : ''
  useEffect(() => {
    if (!apiUrl || !sessionDate) return
    const ctl = new AbortController()
    fetchDayPlan(sessionDate, ctl.signal).then(setPlan).catch((e: Error) => { if (e.name !== 'AbortError') setPlan(null) })
    return () => ctl.abort()
  }, [sessionDate])

  // The cone as chart points, and (only when asked for, in replay) the candles that came after.
  const coneView = useMemo(() => {
    if (!data || !cone || cone.asof !== `${isoDate(asOfT)}T${hhmm(asOfT)}`) return null
    const points = cone.points.map((p) => ({ t: parseEt(p.time), lo80: p.lo80, lo50: p.lo50, hi50: p.hi50, hi80: p.hi80 }))
    const last = points.length ? points[points.length - 1].t : 0
    const after: { t: number; c: number }[] = []
    for (let k = asOf + 1; k < data.bars.t.length && data.bars.t[k] <= last; k++) after.push({ t: data.bars.t[k], c: data.bars.c[k] })
    return { points, after }
  }, [data, cone, asOf, asOfT])

  const read = useMemo(
    () => (view ? analyze(view.bars, view.ind, view.sessStarts, prediction) : null),
    [view, prediction],
  )

  if (loadError) return <main className="state"><h1>Couldn't load the candles</h1><p>{loadError}</p><p>Check that public/data/ko_5min.csv exists, then reload.</p></main>
  if (!data || !view || !read) return <main className="state"><p>Loading KO candles…</p></main>

  const { bars, ind, sessStarts } = view
  const i = bars.c.length - 1
  const today = sessStarts[sessStarts.length - 1]
  const price = bars.c[i]
  const prevClose = today > 0 ? bars.c[today - 1] : bars.o[today]
  const chg = price - prevClose
  const chgPct = (chg / prevClose) * 100
  let hi = -Infinity, lo = Infinity
  for (let k = today; k <= i; k++) { hi = Math.max(hi, bars.h[k]); lo = Math.min(lo, bars.l[k]) }
  const isLatest = asOf === data.bars.t.length - 1
  live.current.atLatest = isLatest

  return (
    <div className="app">
      <header className="top">
        {/* Coca-Cola Logo + Identity */}
        <div className="ident">
          <div className="ko-logo">
            <img src="/coca-cola-logo.svg" alt="Coca-Cola" className="ko-img" />
            <div>
              <h1>Coca-Cola Co</h1>
              <p>NYSE · 5-minute candles</p>
            </div>
          </div>
        </div>

        {/* Price quote */}
        <div className="quote">
          <span className="price">{price.toFixed(2)}</span>
          <span className={`chg ${chg >= 0 ? 'up' : 'down'}`}>
            {chg >= 0 ? '▲' : '▼'} {Math.abs(chg).toFixed(2)} ({chg >= 0 ? '+' : ''}{chgPct.toFixed(2)}%)
          </span>
        </div>

        {/* Stats */}
        <dl className="stats">
          <div><dt>Day range</dt><dd>{lo.toFixed(2)} to {hi.toFixed(2)}</dd></div>
          <div><dt>Volume today</dt><dd>{compact(ind.cumVol[i])}</dd></div>
          <div><dt>Latest candle</dt><dd>{dayLabel(inZone(asOfT, tz), false)}, {clockIn(asOfT, tz)} {tz}</dd></div>
        </dl>

        {/* Right controls */}
        <div className="status">
          <div className="header-controls">
            {/* IST / ET zone switch */}
            <div className="seg zone" role="group" aria-label="Clock used for every time on the page">
              {(['IST', 'ET'] as Zone[]).map((z) => (
                <button key={z} className={z === tz ? 'on' : ''} aria-pressed={z === tz} onClick={() => { setTz(z); saveZone(z) }}>
                  {z === 'IST' ? 'India (IST)' : 'New York (ET)'}
                </button>
              ))}
            </div>
            <span className={`pill ${isLatest ? 'ok' : 'replay'}`}>{isLatest ? '● Live' : '⏪ Replay'}</span>
          </div>
          <span className="ny" title="Regular hours by the clock. Exchange holidays are not checked.">
            {clock.open
              ? `Market open · Now ${clockIn(clock.t, tz)} ${tz}`
              : `Market closed${clock.weekend ? ' for the weekend' : ''} · Last session ${dayLabel(data.bars.t[data.bars.t.length - 1], false)} · Opens ${dayLabel(inZone(clock.nextOpen, tz), false)}, ${clockIn(clock.nextOpen, tz)} ${tz}`}
          </span>
          {update && (
            <span className={`update-note ${update.ok ? '' : 'bad'}`}>
              {update.ok ? `✓ Synced with Alpaca at ${clockIn(update.at, tz)} ${tz}` : `⚠ ${update.message}`}
            </span>
          )}
        </div>
      </header>

      <SessionBar bars={data.bars} sessions={data.sessions} sIdx={sIdx} asOf={asOf} tz={tz} onSession={goSession} onAsOf={setAsOf} />

      <main className="grid">
        <div className="col-main">
          <section className="panel chart-panel">
            <div className="toolbar">
              <div className="seg" role="group" aria-label="Chart range">
                {RANGES.map((r) => (
                  <button key={r} className={r === range ? 'on' : ''} aria-pressed={r === range} onClick={() => setRange(r)}>{r}</button>
                ))}
              </div>
              {coneView && (
                <div className="seg" style={{ marginLeft: 'auto' }} role="group" aria-label="Forecast overlay">
                  <button className={showCone ? 'on' : ''} aria-pressed={showCone} onClick={() => setShowCone(!showCone)}>Range cone</button>
                </div>
              )}
            </div>
            {coneView && cone && (
              <RangeConeStrip cone={cone} scores={coneScores} tz={tz} show={showCone} onShow={setShowCone}
                canReveal={coneView.after.length > 0} reveal={reveal} onReveal={setReveal}
                closeAt={(t) => coneView.after.find((a) => a.t === t)?.c} />
            )}
            <PriceChart bars={bars} ind={ind} sessStarts={sessStarts} toggles={toggles} range={range} tz={tz}
              cone={showCone && coneView ? coneView.points : null} after={reveal && coneView ? coneView.after : null} ladder={null} />
            <p className="basis">Candles are actual KO prices. All times are {tz === 'IST' ? 'India time (IST)' : 'New York time (ET)'}. Overnight gaps are not drawn as candles.</p>
          </section>
          {apiUrl && <DayPlanPanel plan={plan} nextPlan={nextPlan} scores={scores} bars={data.bars} session={data.sessions[sIdx]} asOf={asOf} tz={tz} />}
        </div>
        <aside className="col-side">
          <PredictionPanel plan={plan} />
          <AccuracyHistory scores={scores} />
        </aside>
      </main>

      <footer className="foot">Analysis only. This dashboard places no orders and is not financial advice.</footer>
    </div>
  )
}
