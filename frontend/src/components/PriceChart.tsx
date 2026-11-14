import { useEffect, useRef, useState } from 'react'
import {
  CandlestickSeries, CrosshairMode, HistogramSeries, LineSeries, LineStyle, createChart,
  type IChartApi, type IPrimitivePaneRenderer, type ISeriesApi, type ISeriesPrimitive, type SeriesAttachedParameter, type Time, type UTCTimestamp,
} from 'lightweight-charts'
import type { Bars, RangeKey, Toggles } from '../lib/types'
import type { Indicators } from '../lib/indicators'
import { SLOTS, dayLabel, hhmm, inZone, type Zone } from '../lib/time'

export const COLORS = {
  up: '#0E8A5F', down: '#C8372D', ink: '#16202B', muted: '#5E6B78', line: '#E3E8ED', grid: '#F1F4F7',
  ema9: '#D98200', ema20: '#2F6FDE', ema50: '#008C9E', vwap: '#16202B', bb: '#9AA6B2', model: '#5B3FD6',
}

/** Touch ladder to draw to the right of the last candle. */
export interface Ladder {
  /** ET start time of the window's last candle. */
  end: number
  /** Symmetric rungs, nearest first. */
  rungs: { up: number; down: number; odds: number }[]
  /** The trader's own levels, e.g. target and stop. */
  marks: { price: number; label: string; color: string }[]
}

/** Rungs of the touch ladder with their odds, and the trader's target and stop. */
class LadderDraw implements ISeriesPrimitive<Time> {
  private host: SeriesAttachedParameter<Time> | null = null
  private data: { from: UTCTimestamp; to: UTCTimestamp; ladder: Ladder } | null = null
  attached(p: SeriesAttachedParameter<Time>) { this.host = p }
  detached() { this.host = null }
  set(d: { from: UTCTimestamp; to: UTCTimestamp; ladder: Ladder } | null) { this.data = d; this.host?.requestUpdate() }
  paneViews() {
    const renderer: IPrimitivePaneRenderer = {
      draw: (target) => target.useMediaCoordinateSpace(({ context: ctx }) => {
        const host = this.host, d = this.data
        if (!host || !d) return
        const ts = host.chart.timeScale()
        const x0 = ts.timeToCoordinate(d.from), x1 = ts.timeToCoordinate(d.to)
        if (x0 == null || x1 == null) return
        ctx.font = "500 11px 'IBM Plex Sans', system-ui, sans-serif"
        ctx.textBaseline = 'bottom'
        const rule = (price: number, color: string, width: number, dash: number[], text: string, align: CanvasTextAlign) => {
          const y = host.series.priceToCoordinate(price)
          if (y == null) return
          ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = width; ctx.setLineDash(dash)
          ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke()
          ctx.setLineDash([])
          ctx.textAlign = align
          ctx.fillText(text, align === 'right' ? x1 - 4 : x0 + 6, y - 2)
        }
        // Shade between the nearest rungs so the eye reads "ordinary movement" at a glance.
        const near = d.ladder.rungs[0]
        const yu = host.series.priceToCoordinate(near.up), yd = host.series.priceToCoordinate(near.down)
        if (yu != null && yd != null) { ctx.fillStyle = 'rgba(91, 63, 214, 0.10)'; ctx.fillRect(x0, yu, x1 - x0, yd - yu) }
        for (const r of d.ladder.rungs) {
          const color = `rgba(91, 63, 214, ${0.35 + r.odds * 0.65})`
          const text = `${Math.round(r.odds * 100)}%`
          rule(r.up, color, 1.5, [], text, 'right')
          rule(r.down, color, 1.5, [], text, 'right')
        }
        for (const m of d.ladder.marks) rule(m.price, m.color, 1.5, [5, 4], m.label, 'left')
      }),
    }
    return [{ renderer: () => renderer, zOrder: () => 'top' as const }]
  }
}

export interface ConePoint { t: number; lo80: number; lo50: number; hi50: number; hi80: number }
type Band = { time: UTCTimestamp; lo80: number; lo50: number; hi50: number; hi80: number }

/** Shaded range cone drawn behind the candles: a pale band for 80% and a darker core for 50%. */
class ConeFill implements ISeriesPrimitive<Time> {
  private host: SeriesAttachedParameter<Time> | null = null
  private pts: Band[] = []
  attached(p: SeriesAttachedParameter<Time>) { this.host = p }
  detached() { this.host = null }
  set(pts: Band[]) { this.pts = pts; this.host?.requestUpdate() }
  paneViews() {
    const renderer: IPrimitivePaneRenderer = {
      draw: (target) => target.useMediaCoordinateSpace(({ context: ctx }) => {
        const host = this.host
        if (!host || this.pts.length < 2) return
        const ts = host.chart.timeScale()
        const xy = this.pts.map((p) => ({
          x: ts.timeToCoordinate(p.time),
          lo80: host.series.priceToCoordinate(p.lo80), hi80: host.series.priceToCoordinate(p.hi80),
          lo50: host.series.priceToCoordinate(p.lo50), hi50: host.series.priceToCoordinate(p.hi50),
        })).filter((p) => p.x != null && p.lo80 != null && p.hi80 != null && p.lo50 != null && p.hi50 != null)
        if (xy.length < 2) return
        const band = (hi: 'hi80' | 'hi50', lo: 'lo80' | 'lo50', fill: string) => {
          ctx.beginPath()
          xy.forEach((p, k) => (k ? ctx.lineTo(p.x!, p[hi]!) : ctx.moveTo(p.x!, p[hi]!)))
          for (let k = xy.length - 1; k >= 0; k--) ctx.lineTo(xy[k].x!, xy[k][lo]!)
          ctx.closePath()
          ctx.fillStyle = fill
          ctx.fill()
        }
        band('hi80', 'lo80', 'rgba(91, 63, 214, 0.10)')
        band('hi50', 'lo50', 'rgba(91, 63, 214, 0.16)')
      }),
    }
    return [{ renderer: () => renderer, zOrder: () => 'bottom' as const }]
  }
}

interface Props {
  bars: Bars
  ind: Indicators
  sessStarts: number[]
  toggles: Toggles
  range: RangeKey
  tz: Zone
  /** Range cone to draw to the right of the last candle, or null to hide it. */
  cone: ConePoint[] | null
  /** Closes that came after the last candle, shown on request when replaying. */
  after: { t: number; c: number }[] | null
  /** Touch ladder to draw instead of the cone, or null. */
  ladder: Ladder | null
}

interface Refs {
  chart: IChartApi
  candles: ISeriesApi<'Candlestick'>
  volume: ISeriesApi<'Histogram'>
  ema9: ISeriesApi<'Line'>; ema20: ISeriesApi<'Line'>; ema50: ISeriesApi<'Line'>
  vwap: ISeriesApi<'Line'>
  bbUp: ISeriesApi<'Line'>; bbMid: ISeriesApi<'Line'>; bbLo: ISeriesApi<'Line'>
  coneHi: ISeriesApi<'Line'>; coneLo: ISeriesApi<'Line'>; afterLine: ISeriesApi<'Line'>; coneFill: ConeFill; ladderDraw: LadderDraw
  rsi?: ISeriesApi<'Line'>
  macd?: ISeriesApi<'Line'>; macdSig?: ISeriesApi<'Line'>; macdHist?: ISeriesApi<'Histogram'>
}

interface Hover { t: number; o: number; h: number; l: number; c: number; v: number }

const SESS: Record<RangeKey, number> = { '1D': 1, '5D': 5, '1M': 21, '3M': 63 }
const vol = (v: number) => (v >= 1e6 ? `${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `${(v / 1e3).toFixed(1)}K` : String(v))

export default function PriceChart({ bars, ind, sessStarts, toggles, range, tz, cone, after, ladder }: Props) {
  const el = useRef<HTMLDivElement>(null)
  const refs = useRef<Refs | null>(null)
  const barsRef = useRef(bars)
  barsRef.current = bars
  const [hover, setHover] = useState<Hover | null>(null)

  // Build the chart. Rebuilt only when a lower pane is added or removed.
  useEffect(() => {
    if (!el.current) return
    const chart = createChart(el.current, {
      autoSize: true,
      layout: {
        background: { color: '#FFFFFF' }, textColor: COLORS.muted, fontSize: 12,
        fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
        panes: { separatorColor: COLORS.line, enableResize: false },
      },
      grid: { vertLines: { color: COLORS.grid }, horzLines: { color: COLORS.grid } },
      rightPriceScale: { borderColor: COLORS.line },
      timeScale: { borderColor: COLORS.line, timeVisible: true, secondsVisible: false, rightOffset: 3 },
      crosshair: { mode: CrosshairMode.Normal },
    })
    const line = (color: string, width: 1 | 2 = 1, style = LineStyle.Solid, pane = 0) =>
      chart.addSeries(LineSeries, {
        color, lineWidth: width, lineStyle: style,
        priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
      }, pane)

    const bbUp = line(COLORS.bb), bbMid = line(COLORS.bb, 1, LineStyle.Dotted), bbLo = line(COLORS.bb)
    const candles = chart.addSeries(CandlestickSeries, {
      upColor: COLORS.up, downColor: COLORS.down, borderVisible: false,
      wickUpColor: COLORS.up, wickDownColor: COLORS.down, priceLineColor: COLORS.ink,
    })
    const volume = chart.addSeries(HistogramSeries, {
      priceScaleId: 'vol', priceFormat: { type: 'volume' }, priceLineVisible: false, lastValueVisible: false,
    })
    chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.84, bottom: 0 } })
    chart.priceScale('right').applyOptions({ scaleMargins: { top: 0.06, bottom: 0.2 } })
    const coneFill = new ConeFill()
    candles.attachPrimitive(coneFill)
    const ladderDraw = new LadderDraw()
    candles.attachPrimitive(ladderDraw)
    const coneHi = line(COLORS.model), coneLo = line(COLORS.model)
    for (const s of [coneHi, coneLo]) s.applyOptions({ lastValueVisible: true })
    const afterLine = line(COLORS.ink, 2)
    const r: Refs = {
      chart, candles, volume, bbUp, bbMid, bbLo, coneHi, coneLo, afterLine, coneFill, ladderDraw,
      ema9: line(COLORS.ema9, 2), ema20: line(COLORS.ema20, 2), ema50: line(COLORS.ema50, 2),
      vwap: line(COLORS.vwap, 2, LineStyle.Dashed),
    }

    let pane = 1
    if (toggles.rsi) {
      r.rsi = line(COLORS.ema20, 2, LineStyle.Solid, pane)
      r.rsi.applyOptions({ lastValueVisible: true, priceFormat: { type: 'price', precision: 0, minMove: 1 } })
      for (const p of [70, 30]) r.rsi.createPriceLine({ price: p, color: COLORS.bb, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: '' })
      pane++
    }
    if (toggles.macd) {
      r.macdHist = chart.addSeries(HistogramSeries, { priceLineVisible: false, lastValueVisible: false }, pane)
      r.macd = line(COLORS.ema20, 2, LineStyle.Solid, pane)
      r.macdSig = line(COLORS.ema9, 2, LineStyle.Solid, pane)
    }
    chart.panes().forEach((p, k) => p.setStretchFactor(k === 0 ? 3.5 : 1))

    chart.subscribeCrosshairMove((param) => {
      const d = param.seriesData.get(candles) as { open: number; high: number; low: number; close: number } | undefined
      const v = param.seriesData.get(volume) as { value: number } | undefined
      if (!d || typeof param.time !== 'number') return setHover(null)
      setHover({ t: param.time, o: d.open, h: d.high, l: d.low, c: d.close, v: v?.value ?? 0 })
    })

    refs.current = r
    return () => { refs.current = null; chart.remove() }
  }, [toggles.rsi, toggles.macd])

  // Push data, visibility and level lines.
  useEffect(() => {
    const r = refs.current
    if (!r) return
    // The chart draws whatever clock these timestamps carry, so shift them to the chosen one.
    const T = bars.t.map((t) => inZone(t, tz)) as UTCTimestamp[]
    r.chart.applyOptions({ localization: { timeFormatter: (t: number) => `${dayLabel(t, false)}  ${hhmm(t)} ${tz}` } })
    const pts = (a: number[]) => {
      const out: { time: UTCTimestamp; value: number }[] = []
      for (let i = 0; i < a.length; i++) if (isFinite(a[i])) out.push({ time: T[i], value: a[i] })
      return out
    }
    r.candles.setData(T.map((time, i) => ({ time, open: bars.o[i], high: bars.h[i], low: bars.l[i], close: bars.c[i] })))
    r.volume.setData(T.map((time, i) => ({ time, value: bars.v[i], color: bars.c[i] >= bars.o[i] ? '#0E8A5F55' : '#C8372D55' })))
    r.ema9.setData(pts(ind.ema9)); r.ema20.setData(pts(ind.ema20)); r.ema50.setData(pts(ind.ema50))
    r.vwap.setData(pts(ind.vwap))
    r.bbUp.setData(pts(ind.bbUp)); r.bbMid.setData(pts(ind.bbMid)); r.bbLo.setData(pts(ind.bbLo))
    r.rsi?.setData(pts(ind.rsi))
    r.macd?.setData(pts(ind.macd)); r.macdSig?.setData(pts(ind.macdSig))
    r.macdHist?.setData(pts(ind.macdHist).map((p) => ({ ...p, color: p.value >= 0 ? '#0E8A5F88' : '#C8372D88' })))

    for (const s of [r.ema9, r.ema20, r.ema50]) s.applyOptions({ visible: toggles.ema })
    r.vwap.applyOptions({ visible: toggles.vwap })
    for (const s of [r.bbUp, r.bbMid, r.bbLo]) s.applyOptions({ visible: toggles.bb })
  }, [bars, ind, toggles, tz])

  // Range cone and, in replay, what price did next. Both start at the last close.
  useEffect(() => {
    const r = refs.current
    if (!r) return
    const n = bars.t.length - 1
    const start = inZone(bars.t[n], tz) as UTCTimestamp
    const band: Band[] = cone && cone.length
      ? [{ time: start, lo80: bars.c[n], lo50: bars.c[n], hi50: bars.c[n], hi80: bars.c[n] },
         ...cone.map((p) => ({ ...p, time: inZone(p.t, tz) as UTCTimestamp }))]
      : []
    if (ladder && ladder.rungs.length) {
      // The outermost rung is drawn as two real lines so the price axis makes room for the whole ladder.
      const far = ladder.rungs[ladder.rungs.length - 1]
      const times = [start]
      for (let t = bars.t[n] + 300; t <= ladder.end; t += 300) times.push(inZone(t, tz) as UTCTimestamp)
      r.coneHi.setData(times.map((time) => ({ time, value: far.up })))
      r.coneLo.setData(times.map((time) => ({ time, value: far.down })))
      r.coneFill.set([])
      r.ladderDraw.set({ from: start, to: times[times.length - 1], ladder })
    } else {
      r.coneHi.setData(band.map((p) => ({ time: p.time, value: p.hi80 })))
      r.coneLo.setData(band.map((p) => ({ time: p.time, value: p.lo80 })))
      r.coneFill.set(band)
      r.ladderDraw.set(null)
    }
    r.afterLine.setData(after && after.length
      ? [{ time: start, value: bars.c[n] }, ...after.map((a) => ({ time: inZone(a.t, tz) as UTCTimestamp, value: a.c }))]
      : [])
  }, [bars, cone, after, ladder, tz, toggles.rsi, toggles.macd])

  // Zoom to the chosen range. On 1D the rest of the session stays blank.
  useEffect(() => {
    const r = refs.current
    if (!r) return
    const n = SESS[range]
    const from = sessStarts[Math.max(0, sessStarts.length - n)]
    const today = sessStarts[sessStarts.length - 1]
    const ahead = ladder ? Math.round((ladder.end - bars.t[bars.t.length - 1]) / 300) : cone ? cone.length : 0          // room for the cone to the right of the last candle
    const to = range === '1D' ? Math.max(today + SLOTS, bars.t.length + ahead + 2) : bars.t.length + ahead + 2
    r.chart.timeScale().setVisibleLogicalRange({ from: from - 0.5, to })
  }, [range, sessStarts, bars.t.length, toggles.rsi, toggles.macd, cone?.length, ladder?.end])

  const i = bars.c.length - 1
  const h: Hover = hover ?? { t: inZone(bars.t[i], tz), o: bars.o[i], h: bars.h[i], l: bars.l[i], c: bars.c[i], v: bars.v[i] }
  return (
    <div className="chart-wrap">
      <div className="chart-readout" aria-live="off">
        <strong>{dayLabel(h.t, false)} {hhmm(h.t)} {tz}</strong>
        <span>Open {h.o.toFixed(2)}</span><span>High {h.h.toFixed(2)}</span>
        <span>Low {h.l.toFixed(2)}</span>
        <span className={h.c >= h.o ? 'up' : 'down'}>Close {h.c.toFixed(2)}</span>
        <span>Volume {vol(h.v)}</span>
      </div>
      <div ref={el} className="chart" style={{ height: 420 + (toggles.rsi ? 120 : 0) + (toggles.macd ? 120 : 0) }} />
    </div>
  )
}
