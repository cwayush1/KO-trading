// All market times in this app are New York (ET) wall-clock times.
// They are stored as "fake UTC" seconds so formatting never depends on
// the viewer's own timezone. Use etToInstant() to get the real moment.

const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export const OPEN_SEC = 9 * 3600 + 30 * 60 // 09:30
export const CLOSE_SEC = 16 * 3600 // 16:00
export const BAR_SEC = 300
export const SLOTS = (CLOSE_SEC - OPEN_SEC) / BAR_SEC // 78 candles in a full day

const pad = (n: number) => String(n).padStart(2, '0')

/** "YYYY-MM-DD HH:MM" (ET) -> fake-UTC seconds */
export function parseEt(s: string): number {
  return (
    Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10), +s.slice(11, 13), +s.slice(14, 16)) / 1000
  )
}

export const secOfDay = (t: number) => ((t % 86400) + 86400) % 86400
export const slotOf = (t: number) => Math.round((secOfDay(t) - OPEN_SEC) / BAR_SEC)

export function hhmm(t: number): string {
  const d = new Date(t * 1000)
  return `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`
}

export function dayLabel(t: number, withYear = true): string {
  const d = new Date(t * 1000)
  const base = `${DOW[d.getUTCDay()]} ${d.getUTCDate()} ${MON[d.getUTCMonth()]}`
  return withYear ? `${base} ${d.getUTCFullYear()}` : base
}

export function isoDate(t: number): string {
  const d = new Date(t * 1000)
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`
}

const nyFmt = new Intl.DateTimeFormat('en-US', {
  timeZone: 'America/New_York',
  hourCycle: 'h23',
  year: 'numeric',
  month: 'numeric',
  day: 'numeric',
  hour: 'numeric',
  minute: 'numeric',
  second: 'numeric',
})

/** New York wall clock of a real instant, as fake-UTC milliseconds. */
function nyWall(ms: number): number {
  const p: Record<string, number> = {}
  for (const x of nyFmt.formatToParts(new Date(ms))) if (x.type !== 'literal') p[x.type] = +x.value
  return Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second)
}

/** Real moment in time for an ET wall-clock value (handles daylight saving). */
export function etToInstant(t: number): Date {
  const guess = t * 1000
  return new Date(guess - (nyWall(guess) - guess))
}

/** The same moment on the viewer's own clock, e.g. "00:05 Tue 10 Nov". */
export function viewerTime(t: number): string {
  const d = etToInstant(t)
  return `${pad(d.getHours())}:${pad(d.getMinutes())} ${DOW[d.getDay()]} ${d.getDate()} ${MON[d.getMonth()]}`
}

export function viewerZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone.replace(/_/g, ' ')
  } catch {
    return 'your time'
  }
}

/** The clock every time on the page is shown in. Candles stay stored as ET. */
export type Zone = 'ET' | 'IST'

const IST_OFFSET = 5.5 * 3600
const shiftCache = new Map<number, number>()

/** Seconds to add to an ET wall-clock value to get the India clock at the same moment.
 *  9h30 in US summer time, 10h30 in winter; worked out once per day. */
function istShift(t: number): number {
  const day = Math.floor(t / 86400)
  let v = shiftCache.get(day)
  if (v === undefined) {
    const noon = day * 86400 + 12 * 3600
    v = etToInstant(noon).getTime() / 1000 + IST_OFFSET - noon
    shiftCache.set(day, v)
  }
  return v
}

/** An ET wall-clock value moved to the chosen clock. Feed the result to hhmm() or dayLabel(). */
export const inZone = (t: number, z: Zone) => (z === 'IST' ? t + istShift(t) : t)
export const clockIn = (t: number, z: Zone) => hhmm(inZone(t, z))

export function defaultZone(): Zone {
  try {
    const saved = localStorage.getItem('zone')
    if (saved === 'ET' || saved === 'IST') return saved
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
    return tz === 'Asia/Calcutta' || tz === 'Asia/Kolkata' ? 'IST' : 'ET'
  } catch {
    return 'ET'
  }
}

export function saveZone(z: Zone) {
  try { localStorage.setItem('zone', z) } catch { /* private mode: the choice lasts for this visit only */ }
}

export interface MarketClock { t: number; open: boolean; weekend: boolean; nextOpen: number }

/** Clock-based NYSE status, as ET wall-clock values. Regular hours only; exchange holidays are not checked. */
export function nyNow(): MarketClock {
  const w = Math.floor(nyWall(Date.now()) / 1000)
  const dowOf = (x: number) => new Date(x * 1000).getUTCDay()
  const s = secOfDay(w)
  const weekday = dowOf(w) >= 1 && dowOf(w) <= 5
  let d = w - s
  if (!(weekday && s < OPEN_SEC)) d += 86400
  while (dowOf(d) === 0 || dowOf(d) === 6) d += 86400
  return { t: w, open: weekday && s >= OPEN_SEC && s < CLOSE_SEC, weekend: !weekday, nextOpen: d + OPEN_SEC }
}

export function sessionPhase(t: number): string {
  const slot = slotOf(t)
  if (slot < 6) return 'Opening 30 minutes'
  if (slot < 12) return 'Opening hour'
  if (slot >= SLOTS - 12) return 'Final hour'
  return 'Midday'
}
