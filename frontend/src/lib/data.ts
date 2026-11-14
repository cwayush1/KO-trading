import type { Bars, Cone, ConeScores, DayOutlook, DayPlan, NextCalls, NextScores, PlanScores, Prediction, Session, SessionForecast, Touch, UpdateStatus } from './types'
import { isoDate, parseEt } from './time'

const API = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '')
export const apiUrl = API

export interface Dataset {
  bars: Bars
  sessions: Session[]
}

/** Loads candles from the backend when it is reachable, otherwise from the bundled CSV. */
export async function loadDataset(): Promise<Dataset> {
  const local = `${import.meta.env.BASE_URL}data/ko_5min.csv`
  if (API) {
    try {
      const res = await fetch(`${API}/api/candles?symbol=KO`)
      if (res.ok) return parseCsv(await res.text())
    } catch {
      // Backend not running: fall back to the bundled file so the chart still works.
    }
  }
  const res = await fetch(local)
  if (!res.ok) throw new Error(`Could not load candles (${res.status}) from ${local}`)
  return parseCsv(await res.text())
}

/** Expects a header row then: "YYYY-MM-DD HH:MM",open,high,low,close,volume in New York time. */
export function parseCsv(text: string): Dataset {
  const bars: Bars = { t: [], o: [], h: [], l: [], c: [], v: [] }
  const lines = text.split('\n')
  let last = -Infinity
  for (let i = 1; i < lines.length; i++) {
    const p = lines[i].split(',')
    if (p.length < 6) continue
    const t = parseEt(p[0])
    const o = +p[1], h = +p[2], l = +p[3], c = +p[4], v = +p[5]
    // Skip duplicates, out-of-order rows and broken candles.
    if (!(t > last) || !(h >= l) || !isFinite(o + h + l + c + v)) continue
    last = t
    bars.t.push(t); bars.o.push(o); bars.h.push(h); bars.l.push(l); bars.c.push(c); bars.v.push(v)
  }
  const sessions: Session[] = []
  for (let i = 0; i < bars.t.length; i++) {
    const date = isoDate(bars.t[i])
    const s = sessions[sessions.length - 1]
    if (s && s.date === date) s.end = i
    else sessions.push({ date, start: i, end: i })
  }
  if (!sessions.length) throw new Error('The candle file is empty.')
  return { bars, sessions }
}

export function sliceBars(b: Bars, from: number, to: number): Bars {
  return {
    t: b.t.slice(from, to + 1), o: b.o.slice(from, to + 1), h: b.h.slice(from, to + 1),
    l: b.l.slice(from, to + 1), c: b.c.slice(from, to + 1), v: b.v.slice(from, to + 1),
  }
}

/** Asks the backend for the model forecast as of an ET timestamp ("YYYY-MM-DDTHH:MM"). */
export async function fetchPrediction(asOfEt: string, signal: AbortSignal): Promise<Prediction> {
  const res = await fetch(`${API}/api/prediction?symbol=KO&asof=${encodeURIComponent(asOfEt)}`, { signal })
  if (!res.ok) throw new Error(`Model server answered ${res.status}`)
  return res.json()
}

/** Range cone made at an ET timestamp ("YYYY-MM-DDTHH:MM"). */
export async function fetchCone(asOfEt: string, signal: AbortSignal): Promise<Cone> {
  const res = await fetch(`${API}/api/cone?symbol=KO&asof=${encodeURIComponent(asOfEt)}`, { signal })
  if (!res.ok) throw new Error(`Model server answered ${res.status}`)
  return res.json()
}

/** Running record of the cone, with the selected session scored up to an ET timestamp. */
export async function fetchConeScores(asOfEt: string, signal: AbortSignal): Promise<ConeScores> {
  const res = await fetch(`${API}/api/cone-scores?days=20&asof=${encodeURIComponent(asOfEt)}`, { signal })
  if (!res.ok) throw new Error(`Model server answered ${res.status}`)
  return res.json()
}

/** Touch ladder made at an ET timestamp ("YYYY-MM-DDTHH:MM"). */
export async function fetchTouch(asOfEt: string, signal: AbortSignal): Promise<Touch> {
  const res = await fetch(`${API}/api/touch?symbol=KO&asof=${encodeURIComponent(asOfEt)}`, { signal })
  if (!res.ok) throw new Error(`Model server answered ${res.status}`)
  return res.json()
}

/** Asks the backend for the pre-market outlook of one session ("YYYY-MM-DD"). */
export async function fetchDayOutlook(date: string, signal: AbortSignal): Promise<DayOutlook> {
  const res = await fetch(`${API}/api/day-outlook?symbol=KO&date=${date}`, { signal })
  if (!res.ok) throw new Error(`Model server answered ${res.status}`)
  return res.json()
}

/** Pre-open calls for all 78 candles of a session ("YYYY-MM-DD" or "next"). */
export async function fetchDayPlan(date: string, signal?: AbortSignal): Promise<DayPlan> {
  const res = await fetch(`${API}/api/day-plan?symbol=KO&date=${date}`, { signal })
  if (!res.ok) throw new Error(`Model server answered ${res.status}`)
  return res.json()
}

export async function fetchPlanScores(days = 20): Promise<PlanScores> {
  const res = await fetch(`${API}/api/plan-scores?days=${days}`)
  if (!res.ok) throw new Error(`Model server answered ${res.status}`)
  return res.json()
}

/** Next-candle calls for one session ("YYYY-MM-DD"). */
export async function fetchNextCalls(date: string, signal?: AbortSignal): Promise<NextCalls> {
  const res = await fetch(`${API}/api/next-calls?symbol=KO&date=${date}`, { signal })
  if (!res.ok) throw new Error(`Model server answered ${res.status}`)
  return res.json()
}

export async function fetchNextScores(days = 20): Promise<NextScores> {
  const res = await fetch(`${API}/api/next-scores?days=${days}`)
  if (!res.ok) throw new Error(`Model server answered ${res.status}`)
  return res.json()
}

/** Asks the backend to pull new candles from Alpaca. Safe to call every minute. */
export async function requestUpdate(): Promise<UpdateStatus> {
  const res = await fetch(`${API}/api/update`, { method: 'POST' })
  if (!res.ok) throw new Error(`Model server answered ${res.status}`)
  return res.json()
}

/** DOWN/NEUTRAL/UP for every 5-min candle of a session at a given horizon (default 10 min). */
export async function fetchSessionForecast(date: string, horizon = 10, signal?: AbortSignal): Promise<SessionForecast> {
  const res = await fetch(`${API}/api/session-forecast?symbol=KO&date=${date}&horizon=${horizon}`, { signal })
  if (!res.ok) throw new Error(`Model server answered ${res.status}`)
  return res.json()
}
