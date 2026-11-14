import type { Alert, Bars, Level, MarketRead, Prediction, ReadRow, Tone } from './types'
import type { Indicators } from './indicators'
import { hhmm } from './time'

// Turns indicator values into a plain-language read of the market.
// Everything is evaluated at the last candle of the window, using only
// candles up to that point, so a replayed moment never sees its future.

const f2 = (x: number) => x.toFixed(2)
const pct = (x: number) => `${x >= 0 ? '+' : ''}${x.toFixed(2)}%`
const median = (a: number[]) => {
  const s = a.filter(isFinite).sort((x, y) => x - y)
  return s.length ? s[Math.floor(s.length / 2)] : NaN
}

interface Pivot { i: number; price: number; high: boolean }

/** Swing highs and lows that were already confirmed by `span` later candles. */
function pivots(b: Bars, from: number, span = 5): Pivot[] {
  const out: Pivot[] = []
  const n = b.c.length
  for (let j = Math.max(span, from); j <= n - 1 - span; j++) {
    let hi = true, lo = true
    for (let k = j - span; k <= j + span && (hi || lo); k++) {
      if (k === j) continue
      if (b.h[k] >= b.h[j]) hi = false
      if (b.l[k] <= b.l[j]) lo = false
    }
    if (hi) out.push({ i: j, price: b.h[j], high: true })
    if (lo) out.push({ i: j, price: b.l[j], high: false })
  }
  return out
}

interface RawLevel { price: number; label: string; fixed: boolean }

export function analyze(b: Bars, ind: Indicators, sessStarts: number[], prediction: Prediction | null): MarketRead {
  const i = b.c.length - 1
  const c = b.c[i]
  const today = sessStarts[sessStarts.length - 1]
  const prevStart = sessStarts.length > 1 ? sessStarts[sessStarts.length - 2] : -1
  const atr = isFinite(ind.atr[i]) ? ind.atr[i] : c * 0.001
  const rows: ReadRow[] = []
  const alerts: Alert[] = []
  let score = 0

  // ---- Trend -------------------------------------------------------------
  const e9 = ind.ema9[i], e20 = ind.ema20[i], e50 = ind.ema50[i]
  const e20Rising = e20 > ind.ema20[Math.max(0, i - 3)]
  let shortDir = 0
  if (c > e9 && e9 > e20 && e20Rising) shortDir = 1
  else if (c < e9 && e9 < e20 && !e20Rising) shortDir = -1
  score += shortDir
  rows.push({
    label: 'Short-term trend',
    value: shortDir > 0 ? 'Up' : shortDir < 0 ? 'Down' : 'No clear direction',
    tone: shortDir > 0 ? 'up' : shortDir < 0 ? 'down' : 'flat',
    detail: shortDir > 0 ? 'Price is above the 9 and 20 averages and the 20 is rising.'
      : shortDir < 0 ? 'Price is below the 9 and 20 averages and the 20 is falling.'
      : 'Price and the 9 and 20 averages are tangled together.',
  })

  const prevClose = prevStart >= 0 ? b.c[today - 1] : NaN
  const dayChg = isFinite(prevClose) ? (c / prevClose - 1) * 100 : NaN
  const aboveVwap = c > ind.vwap[i]
  let dayDir = 0
  if (aboveVwap && !(dayChg < 0)) dayDir = 1
  else if (!aboveVwap && !(dayChg > 0)) dayDir = -1
  score += dayDir
  rows.push({
    label: 'Today',
    value: dayDir > 0 ? 'Buyers in control' : dayDir < 0 ? 'Sellers in control' : 'Contested',
    tone: dayDir > 0 ? 'up' : dayDir < 0 ? 'down' : 'flat',
    detail: `${isFinite(dayChg) ? `${pct(dayChg)} vs the previous close, ` : ''}${aboveVwap ? 'above' : 'below'} VWAP (${f2(ind.vwap[i])}).`,
  })

  const fiveAgo = sessStarts.length > 5 ? b.c[sessStarts[sessStarts.length - 5] - 1] : NaN
  const fiveChg = isFinite(fiveAgo) ? (c / fiveAgo - 1) * 100 : NaN
  let multiDir = 0
  if (fiveChg > 1 && c > e50) multiDir = 1
  else if (fiveChg < -1 && c < e50) multiDir = -1
  score += multiDir
  rows.push({
    label: 'Last 5 days',
    value: multiDir > 0 ? 'Up' : multiDir < 0 ? 'Down' : 'Flat',
    tone: multiDir > 0 ? 'up' : multiDir < 0 ? 'down' : 'flat',
    detail: isFinite(fiveChg) ? `${pct(fiveChg)} over five sessions.` : 'Not enough history yet.',
  })

  // ---- Trend strength (ADX) ---------------------------------------------
  const adx = ind.adx[i]
  const adxFalling = adx < ind.adx[Math.max(0, i - 6)]
  const strength = adx >= 40 ? 'Very strong' : adx >= 25 ? 'Strong' : adx >= 15 ? 'Developing' : 'Weak'
  rows.push({
    label: 'Trend strength',
    value: strength,
    tone: adx >= 25 ? (shortDir >= 0 ? 'up' : 'down') : 'flat',
    detail: `ADX ${adx.toFixed(0)}${adxFalling ? ', fading' : ', building'}. Above 25 means a real trend, below 15 means drift.`,
  })

  // ---- Momentum ----------------------------------------------------------
  const r = ind.rsi[i], hist = ind.macdHist[i], histPrev = ind.macdHist[Math.max(0, i - 2)]
  const histRising = hist > histPrev
  let momDir = 0, momValue = 'Neutral'
  if (hist > 0 && histRising) { momDir = 1; momValue = 'Buying pressure building' }
  else if (hist > 0) { momValue = 'Buying pressure easing' }
  else if (hist < 0 && !histRising) { momDir = -1; momValue = 'Selling pressure building' }
  else if (hist < 0) { momValue = 'Selling pressure easing' }
  score += momDir
  const stretched = r >= 70 ? ' RSI is stretched to the upside.' : r <= 30 ? ' RSI is stretched to the downside.' : ''
  rows.push({
    label: 'Momentum',
    value: momValue,
    tone: momDir > 0 ? 'up' : momDir < 0 ? 'down' : r >= 70 || r <= 30 ? 'warn' : 'flat',
    detail: `RSI ${r.toFixed(0)}, MACD histogram ${hist >= 0 ? 'positive' : 'negative'} and ${histRising ? 'rising' : 'falling'}.${stretched}`,
  })

  // ---- Volatility --------------------------------------------------------
  const baseAtr = median(ind.atr.slice(Math.max(0, i - 1560), i))
  const volRatio = atr / baseAtr
  const widthWin = ind.bbWidth.slice(Math.max(0, i - 390), i + 1).filter(isFinite)
  const widthRank = widthWin.length ? widthWin.filter((x) => x <= ind.bbWidth[i]).length / widthWin.length : 0.5
  const squeeze = widthRank <= 0.1 && adx < 20
  const volState = volRatio >= 1.5 ? 'High' : volRatio <= 0.7 ? 'Quiet' : 'Normal'
  rows.push({
    label: 'Volatility',
    value: squeeze ? 'Quiet, range tightening' : volState,
    tone: volRatio >= 1.5 ? 'warn' : 'flat',
    detail: `A typical candle moves ${f2(atr)} (${((atr / c) * 100).toFixed(2)}%), ${isFinite(volRatio) ? `${volRatio.toFixed(1)}x` : 'about 1x'} its 20-day norm.`,
  })

  // ---- Volume ------------------------------------------------------------
  const cr = ind.cumRvol[i], br = ind.rvol[i]
  rows.push({
    label: 'Volume',
    value: !isFinite(cr) ? 'Not enough history' : cr >= 1.5 ? 'Heavy' : cr >= 1.1 ? 'Above average' : cr <= 0.7 ? 'Light' : 'Average',
    tone: cr >= 1.5 ? 'warn' : 'flat',
    detail: isFinite(cr)
      ? `${cr.toFixed(1)}x the usual volume by this time of day. Volume shows activity, not who is buying or selling.`
      : 'Needs at least five earlier sessions to compare against.',
  })

  // ---- Regime ------------------------------------------------------------
  const trending = adx >= 25
  const regimeDir = trending && shortDir > 0 && c > e50 ? 'Trending up' : trending && shortDir < 0 && c < e50 ? 'Trending down' : 'Sideways'
  const regime = `${regimeDir}, ${volState.toLowerCase()} volatility`

  // ---- Support and resistance -------------------------------------------
  const raw: RawLevel[] = []
  if (prevStart >= 0) {
    let ph = -Infinity, pl = Infinity
    for (let k = prevStart; k < today; k++) { ph = Math.max(ph, b.h[k]); pl = Math.min(pl, b.l[k]) }
    raw.push({ price: ph, label: "Previous day's high", fixed: true })
    raw.push({ price: pl, label: "Previous day's low", fixed: true })
    raw.push({ price: prevClose, label: 'Previous close', fixed: true })
  }
  if (i - today >= 6) {
    let oh = -Infinity, ol = Infinity
    for (let k = today; k < today + 6; k++) { oh = Math.max(oh, b.h[k]); ol = Math.min(ol, b.l[k]) }
    raw.push({ price: oh, label: 'Opening 30-min high', fixed: true })
    raw.push({ price: ol, label: 'Opening 30-min low', fixed: true })
  }
  const tol = Math.max(atr, c * 0.0008)
  const lookFrom = sessStarts.length > 5 ? sessStarts[sessStarts.length - 5] : 0
  const piv = pivots(b, lookFrom)
  const sorted = [...piv].sort((x, y) => x.price - y.price)
  let group: Pivot[] = []
  const flush = () => {
    if (group.length >= 2) {
      const price = group.reduce((s, p) => s + p.price, 0) / group.length
      raw.push({ price, label: `Tested ${group.length} times this week`, fixed: false })
    }
    group = []
  }
  for (const p of sorted) {
    if (group.length && p.price - group[group.length - 1].price > tol) flush()
    group.push(p)
  }
  flush()
  // Drop swing clusters that sit on top of a named level.
  const kept = raw.filter((lv) => lv.fixed || !raw.some((o) => o.fixed && Math.abs(o.price - lv.price) <= tol))

  let dayHigh = -Infinity, dayLow = Infinity
  for (let k = today; k <= i; k++) { dayHigh = Math.max(dayHigh, b.h[k]); dayLow = Math.min(dayLow, b.l[k]) }
  const withDay: RawLevel[] = [...kept]
  if (!kept.some((o) => Math.abs(o.price - dayHigh) <= tol)) withDay.push({ price: dayHigh, label: "Today's high", fixed: true })
  if (!kept.some((o) => Math.abs(o.price - dayLow) <= tol)) withDay.push({ price: dayLow, label: "Today's low", fixed: true })

  const toLevel = (lv: RawLevel): Level => ({
    price: lv.price, label: lv.label,
    side: lv.price >= c ? 'resistance' : 'support',
    distPct: (lv.price / c - 1) * 100,
  })
  const all = withDay.map(toLevel)
  const levels = [
    ...all.filter((l) => l.side === 'resistance').sort((x, y) => x.price - y.price).slice(0, 3).reverse(),
    ...all.filter((l) => l.side === 'support').sort((x, y) => y.price - x.price).slice(0, 3),
  ]

  // ---- Alerts: each needs context, not just one threshold ---------------
  const t = b.t[i]
  const add = (title: string, why: string, tone: Tone, time = t) => alerts.push({ title, why, tone, time })

  // Break of a known level, judged by the volume on the candle that broke it.
  for (const lv of kept) {
    for (let k = Math.max(today + 1, i - 2); k <= i; k++) {
      const up = b.c[k - 1] <= lv.price && b.c[k] > lv.price && c > lv.price
      const dn = b.c[k - 1] >= lv.price && b.c[k] < lv.price && c < lv.price
      if (!up && !dn) continue
      const rv = ind.rvol[k]
      const where = `${lv.label.toLowerCase()} (${f2(lv.price)})`
      if (rv >= 1.5) {
        add(`${up ? 'Breakout above' : 'Breakdown below'} ${f2(lv.price)}`,
          `Closed ${up ? 'above' : 'below'} ${where} at ${hhmm(b.t[k])} ET on ${rv.toFixed(1)}x normal volume, so the move has participation behind it.`,
          up ? 'up' : 'down', b.t[k])
      } else {
        add(`Unconfirmed ${up ? 'break above' : 'break below'} ${f2(lv.price)}`,
          `Closed ${up ? 'above' : 'below'} ${where} at ${hhmm(b.t[k])} ET, but volume was only ${isFinite(rv) ? `${rv.toFixed(1)}x` : 'around'} normal. Breaks on thin volume often fail.`,
          'warn', b.t[k])
      }
      break
    }
  }

  if (squeeze) {
    add('Range is tightening', `Bollinger Band width is in the lowest 10% of the past week and ADX is ${adx.toFixed(0)}. Tight ranges tend to end with a sharp move; direction is not implied.`, 'warn')
  }
  if (volRatio >= 1.5) {
    add('High volatility', `Candles are moving ${volRatio.toFixed(1)}x their 20-day norm. Expect wider swings and less reliable levels.`, 'warn')
  }
  if (br >= 3) {
    add('Unusual volume spike', `The ${hhmm(t)} ET candle traded ${br.toFixed(1)}x the usual volume for this time of day.`, 'warn')
  }

  // Trend losing steam: still pointing one way, but momentum has turned.
  let histRun = 0
  for (let k = i; k > 0 && k > i - 8; k--) {
    if (c > e50 ? ind.macdHist[k] < ind.macdHist[k - 1] : ind.macdHist[k] > ind.macdHist[k - 1]) histRun++
    else break
  }
  if (c > e50 && e20 > e50 && histRun >= 4 && adxFalling && adx >= 20) {
    add('Uptrend is weakening', `Price is still above the 50 average, but MACD has fallen for ${histRun} candles and ADX is fading from ${ind.adx[Math.max(0, i - 6)].toFixed(0)} to ${adx.toFixed(0)}.`, 'warn')
  } else if (c < e50 && e20 < e50 && histRun >= 4 && adxFalling && adx >= 20) {
    add('Downtrend is weakening', `Price is still below the 50 average, but MACD has risen for ${histRun} candles and ADX is fading from ${ind.adx[Math.max(0, i - 6)].toFixed(0)} to ${adx.toFixed(0)}.`, 'warn')
  }

  // Divergence between the last two confirmed swing points and RSI.
  const recent = piv.filter((p) => p.i >= i - 60)
  const highs = recent.filter((p) => p.high), lows = recent.filter((p) => !p.high)
  if (highs.length >= 2) {
    const [a, z] = highs.slice(-2)
    if (z.i >= i - 15 && z.price > a.price && ind.rsi[z.i] < ind.rsi[a.i] - 3) {
      add('Bearish divergence', `Price made a higher high at ${hhmm(b.t[z.i])} ET (${f2(z.price)} vs ${f2(a.price)}) while RSI made a lower one (${ind.rsi[z.i].toFixed(0)} vs ${ind.rsi[a.i].toFixed(0)}). Buyers are pushing less hard.`, 'down', b.t[z.i])
    }
  }
  if (lows.length >= 2) {
    const [a, z] = lows.slice(-2)
    if (z.i >= i - 15 && z.price < a.price && ind.rsi[z.i] > ind.rsi[a.i] + 3) {
      add('Bullish divergence', `Price made a lower low at ${hhmm(b.t[z.i])} ET (${f2(z.price)} vs ${f2(a.price)}) while RSI made a higher one (${ind.rsi[z.i].toFixed(0)} vs ${ind.rsi[a.i].toFixed(0)}). Sellers are pushing less hard.`, 'up', b.t[z.i])
    }
  }

  if (score >= 3 && adx >= 25 && !(cr < 0.9)) {
    add('Strong bullish conditions', `Short-term trend, today's session and momentum all point up, ADX is ${adx.toFixed(0)}, and volume is ${isFinite(cr) ? `${cr.toFixed(1)}x` : 'near'} normal.`, 'up')
  } else if (score <= -3 && adx >= 25 && !(cr < 0.9)) {
    add('Strong bearish conditions', `Short-term trend, today's session and momentum all point down, ADX is ${adx.toFixed(0)}, and volume is ${isFinite(cr) ? `${cr.toFixed(1)}x` : 'near'} normal.`, 'down')
  }

  // Model view, only when a forecast exists. The model was tested to have some skill at
  // telling active from quiet periods and none at picking direction, so only the first is used.
  if (prediction?.horizons.length) {
    const h = prediction.horizons.find((x) => x.minutes === 30) ?? prediction.horizons[0]
    const pMove = h.p_up + h.p_down
    const base = h.tested.base_move
    if (base != null && Math.abs(pMove - base) >= 0.12) {
      const active = pMove > base
      const agrees = active ? volRatio >= 1.2 || squeeze : volRatio <= 0.9
      add(active ? 'Model expects an active stretch' : 'Model expects a quiet stretch',
        `${Math.round(pMove * 100)}% chance of a move larger than $${h.move_threshold.toFixed(2)} in the next ${h.minutes} minutes, against a usual ${Math.round(base * 100)}%. ` +
        `The volatility indicators ${agrees ? 'agree' : 'do not show this yet'}. The model does not say which way.`,
        active ? 'warn' : 'flat')
    }
  }

  // ---- Headline ----------------------------------------------------------
  const lean = score >= 3 ? 'Bullish' : score >= 1 ? 'Leaning bullish' : score <= -3 ? 'Bearish' : score <= -1 ? 'Leaning bearish' : 'Mixed'
  const leanTone: Tone = score >= 1 ? 'up' : score <= -1 ? 'down' : 'flat'
  const res = levels.filter((l) => l.side === 'resistance').pop()
  const sup = levels.find((l) => l.side === 'support')
  const parts = [
    `KO is ${regimeDir === 'Sideways' ? 'moving sideways' : regimeDir.toLowerCase()} with ${volState.toLowerCase()} volatility.`,
    `${momValue}${isFinite(cr) ? ` on ${cr >= 1.1 ? 'above-average' : cr <= 0.7 ? 'light' : 'average'} volume` : ''}.`,
    res && sup ? `Nearest resistance ${f2(res.price)}, nearest support ${f2(sup.price)}.`
      : res ? `Nearest resistance ${f2(res.price)}; price is at the bottom of its recent range.`
      : sup ? `Nearest support ${f2(sup.price)}; price is at the top of its recent range.` : '',
  ]

  alerts.sort((x, y) => y.time - x.time)
  return { lean, leanTone, score, regime, summary: parts.filter(Boolean).join(' '), rows, levels, alerts }
}
