import type { Bars } from './types'
import { secOfDay } from './time'

// Every function here is causal: the value at index i uses candles 0..i only.

const nan = (n: number) => new Array<number>(n).fill(NaN)

/** Exponential moving average. Leading NaNs in the source are skipped. */
export function ema(src: number[], n: number): number[] {
  const out = nan(src.length)
  const k = 2 / (n + 1)
  let seen = 0, sum = 0, e = NaN
  for (let i = 0; i < src.length; i++) {
    const x = src[i]
    if (!isFinite(x)) continue
    if (seen < n) {
      sum += x
      seen++
      if (seen === n) out[i] = e = sum / n
    } else out[i] = e = x * k + e * (1 - k)
  }
  return out
}

export function sma(src: number[], n: number): number[] {
  const out = nan(src.length)
  let sum = 0
  for (let i = 0; i < src.length; i++) {
    sum += src[i]
    if (i >= n) sum -= src[i - n]
    if (i >= n - 1) out[i] = sum / n
  }
  return out
}

export function rollingStd(src: number[], n: number): number[] {
  const out = nan(src.length)
  let s = 0, s2 = 0
  for (let i = 0; i < src.length; i++) {
    s += src[i]; s2 += src[i] * src[i]
    if (i >= n) { s -= src[i - n]; s2 -= src[i - n] * src[i - n] }
    if (i >= n - 1) out[i] = Math.sqrt(Math.max(0, s2 / n - (s / n) ** 2))
  }
  return out
}

/** Wilder's RSI. */
export function rsi(c: number[], n = 14): number[] {
  const out = nan(c.length)
  let g = 0, l = 0
  for (let i = 1; i < c.length; i++) {
    const d = c[i] - c[i - 1]
    const up = Math.max(d, 0), dn = Math.max(-d, 0)
    if (i <= n) {
      g += up / n; l += dn / n
    } else {
      g = (g * (n - 1) + up) / n
      l = (l * (n - 1) + dn) / n
    }
    if (i >= n) out[i] = l === 0 ? 100 : 100 - 100 / (1 + g / l)
  }
  return out
}

function wilder(src: number[], n: number, from: number): number[] {
  const out = nan(src.length)
  let acc = 0
  for (let i = from; i < src.length; i++) {
    const k = i - from
    if (k < n) {
      acc += src[i]
      if (k === n - 1) out[i] = acc = acc / n
    } else out[i] = acc = (acc * (n - 1) + src[i]) / n
  }
  return out
}

/** Average True Range and ADX (trend strength, 0-100) with Wilder smoothing. */
export function atrAdx(b: Bars, n = 14): { atr: number[]; adx: number[] } {
  const len = b.c.length
  const tr = nan(len), pdm = nan(len), mdm = nan(len)
  for (let i = 1; i < len; i++) {
    tr[i] = Math.max(b.h[i] - b.l[i], Math.abs(b.h[i] - b.c[i - 1]), Math.abs(b.l[i] - b.c[i - 1]))
    const up = b.h[i] - b.h[i - 1], dn = b.l[i - 1] - b.l[i]
    pdm[i] = up > dn && up > 0 ? up : 0
    mdm[i] = dn > up && dn > 0 ? dn : 0
  }
  const atr = wilder(tr, n, 1), sp = wilder(pdm, n, 1), sm = wilder(mdm, n, 1)
  const dx = nan(len)
  for (let i = n; i < len; i++) {
    if (!(atr[i] > 0)) { dx[i] = 0; continue }
    const pdi = sp[i] / atr[i], mdi = sm[i] / atr[i]
    dx[i] = pdi + mdi === 0 ? 0 : (100 * Math.abs(pdi - mdi)) / (pdi + mdi)
  }
  return { atr, adx: wilder(dx, n, n) }
}

export interface Indicators {
  ema9: number[]; ema20: number[]; ema50: number[]
  vwap: number[]
  bbMid: number[]; bbUp: number[]; bbLo: number[]; bbWidth: number[]
  rsi: number[]
  macd: number[]; macdSig: number[]; macdHist: number[]
  atr: number[]; adx: number[]
  /** This candle's volume vs the usual volume for the same time of day (last 20 sessions). */
  rvol: number[]
  /** Today's volume so far vs the usual volume by this time of day. */
  cumRvol: number[]
  /** Volume traded so far today. */
  cumVol: number[]
}

export function computeIndicators(b: Bars): Indicators {
  const n = b.c.length
  const ema9 = ema(b.c, 9), ema20 = ema(b.c, 20), ema50 = ema(b.c, 50)

  // VWAP restarts every session, so an overnight gap never leaks into it.
  const vwap = nan(n), cumVol = nan(n)
  let pv = 0, vol = 0, day = -1
  for (let i = 0; i < n; i++) {
    const d = Math.floor(b.t[i] / 86400)
    if (d !== day) { day = d; pv = 0; vol = 0 }
    pv += ((b.h[i] + b.l[i] + b.c[i]) / 3) * b.v[i]
    vol += b.v[i]
    vwap[i] = vol > 0 ? pv / vol : b.c[i]
    cumVol[i] = vol
  }

  const bbMid = sma(b.c, 20), sd = rollingStd(b.c, 20)
  const bbUp = bbMid.map((m, i) => m + 2 * sd[i])
  const bbLo = bbMid.map((m, i) => m - 2 * sd[i])
  const bbWidth = bbMid.map((m, i) => (4 * sd[i]) / m)

  const e12 = ema(b.c, 12), e26 = ema(b.c, 26)
  const macd = e12.map((x, i) => x - e26[i])
  const macdSig = ema(macd, 9)
  const macdHist = macd.map((x, i) => x - macdSig[i])

  const { atr, adx } = atrAdx(b)

  // Relative volume compares like with like: 09:35 against past 09:35 candles.
  const rvol = nan(n), cumRvol = nan(n)
  const hist = new Map<number, number[]>(), cumHist = new Map<number, number[]>()
  const mean = (a: number[]) => a.reduce((x, y) => x + y, 0) / a.length
  const push = (m: Map<number, number[]>, k: number, v: number) => {
    const a = m.get(k) ?? []
    a.push(v)
    if (a.length > 20) a.shift()
    m.set(k, a)
  }
  for (let i = 0; i < n; i++) {
    const slot = secOfDay(b.t[i])
    const a = hist.get(slot), ca = cumHist.get(slot)
    if (a && a.length >= 5) { const m = mean(a); if (m > 0) rvol[i] = b.v[i] / m }
    if (ca && ca.length >= 5) { const m = mean(ca); if (m > 0) cumRvol[i] = cumVol[i] / m }
    push(hist, slot, b.v[i])
    push(cumHist, slot, cumVol[i])
  }

  return { ema9, ema20, ema50, vwap, bbMid, bbUp, bbLo, bbWidth, rsi: rsi(b.c), macd, macdSig, macdHist, atr, adx, rvol, cumRvol, cumVol }
}
