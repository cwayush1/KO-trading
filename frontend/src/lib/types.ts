/** Column-oriented 5-minute candles. `t` is New York wall-clock time stored as
 *  if it were UTC seconds, so the chart axis reads in market time everywhere. */
export interface Bars {
  t: number[]
  o: number[]
  h: number[]
  l: number[]
  c: number[]
  v: number[]
}

/** One trading day. `start` and `end` are inclusive indices into Bars. */
export interface Session {
  date: string
  start: number
  end: number
}

export type Tone = 'up' | 'down' | 'flat' | 'warn'

export interface ReadRow {
  label: string
  value: string
  tone: Tone
  detail: string
}

export interface Level {
  price: number
  label: string
  side: 'support' | 'resistance'
  distPct: number
}

export interface Alert {
  title: string
  why: string
  tone: Tone
  time: number
}

export interface MarketRead {
  lean: string
  leanTone: Tone
  score: number
  regime: string
  summary: string
  rows: ReadRow[]
  levels: Level[]
  alerts: Alert[]
}

export interface HorizonForecast {
  minutes: number
  p_up: number
  p_down: number
  p_neutral: number
  /** Dollar move that counts as UP or DOWN at this moment. */
  move_threshold: number
  /** How this horizon's model scored on data it never trained on. */
  tested: {
    wf_direction_hit: number | null
    test_direction_hit: number | null
    test_direction_ci: [number, number] | null
    wf_move_auc: number | null
    test_move_auc: number | null
    base_move: number | null
  }
}

/** What the FastAPI backend returns from GET /api/prediction. */
export interface Prediction {
  model: string
  asof: string
  generated_at: string
  trained_through: string
  /** True when the chosen moment lies inside the model's training period. */
  in_sample: boolean
  horizons: HorizonForecast[]
  skipped: { minutes: number; reason: string }[]
}

/** What the backend returns from GET /api/day-outlook: a pre-market view of the whole session. */
export interface DayOutlook {
  model: string
  date: string
  p_up: number
  p_down: number
  uses_sessions_through: string
  trained_through: string
  in_sample: boolean
  tested: { wf_hit: number; wf_ci: [number, number]; wf_days: number; test_hit: number; test_ci: [number, number]; test_days: number } | null
}

export interface PlanTested {
  wf_hit: number; wf_ci: [number, number]; wf_days: number
  test_hit: number; test_ci: [number, number]; test_days: number
  always_green_hit: number; day_min: number; day_max: number
}

/** GET /api/day-plan: every 5-minute candle of one session, called before the open. */
export interface DayPlan {
  model: string
  date: string
  session_exists: boolean
  uses_sessions_through: string
  previous_session_candles: number
  /** Trading days between the last candle in the file and this plan's day. 0 = data is current. */
  sessions_missing: number
  trained_through: string
  in_sample: boolean
  slots: { slot: number; time: string; p_up: number }[]
  tested: PlanTested | null
}

/** GET /api/plan-scores: how those calls scored on sessions already in the file. */
export interface PlanScores {
  recent: { date: string; right: number; total: number }[]
  since_training: { right: number; total: number; from: string; days: number }
}

/** One tested period of the next-candle model. `strong` is the confident top 10% of calls. */
export interface NextPeriod {
  days: number
  all: { hit: number; n: number; ci: [number, number] }
  strong: { hit: number; n: number; ci: [number, number]; per_day: number }
  always_up: number
}

/** GET /api/next-calls: up or down for each following candle of one session. */
export interface NextCalls {
  model: string
  date: string
  trained_through: string
  in_sample: boolean
  /** `slot` and `time` (ET) are the candle being called; the call was made one candle earlier. */
  calls: { slot: number; time: string; p_up: number; strong: boolean }[]
  tested: { wf: NextPeriod; test: NextPeriod } | null
}

interface NextTally { right: number; total: number; strong_right: number; strong_total: number }

/** GET /api/next-scores: how those calls scored on candles already in the file. */
export interface NextScores {
  since_training: NextTally & { days: number; from: string }
  recent: (NextTally & { date: string })[]
}

export interface ConeBand { time: string; lo80: number; lo50: number; hi50: number; hi80: number }

/** GET /api/cone: likely price range over the next two hours. `time` values are ET candle start times. */
export interface Cone {
  model: string
  /** 'session': the rest of today, up to two hours. 'opening': the first two hours of the next session. */
  kind: 'session' | 'opening'
  asof: string
  price: number
  points: ConeBand[]
  horizons: (ConeBand & { minutes: number })[]
  /** Width of the 1-hour cone against a normal one. Null for the opening cone. */
  width_vs_usual: number | null
  trained_through: string
  in_sample: boolean
  tested: {
    wf_days: number; test_days: number
    horizons: Record<string, { wf50: number; wf80: number; test50: number; test80: number }>
    narrow_width: number; wide_width: number; fixed_narrow_cover: number; fixed_wide_cover: number
    opening80: { wf: number; test: number }
  } | null
}

interface ConeTally { n: number; in50: number; in80: number }

/** GET /api/cone-scores: running record of settled cones. Keys '15' to '120' are minutes ahead. */
export interface ConeScores {
  since_training: Record<'15' | '30' | '60' | '120', ConeTally> & { days: number; from: string }
  /** 1-hour cones per recent session. */
  recent: { date: string; n: number; in80: number }[]
  /** The selected session, counting only cones whose result was known by the chosen moment. */
  session: (Record<'15' | '30' | '60' | '120', ConeTally> & { date: string }) | null
}

export interface TouchWindow {
  minutes: number
  /** False when the window would run past the closing bell; the fields below are then absent. */
  fits: boolean
  end?: string
  vs_usual?: number
  /** Nearest first. `odds` is the chance that `up` (and, separately, `down`) is touched inside the window. */
  levels?: { odds: number; up: number; down: number }[]
}

interface TouchTally { n: number; touched: Record<string, number> }

/** GET /api/touch: price levels with their chance of being touched, and the running record. */
export interface Touch {
  model: string
  asof: string
  price: number
  windows: TouchWindow[]
  record: { days: number; since_training: Record<string, TouchTally>; session: Record<string, TouchTally> }
  trained_through: string
  in_sample: boolean
  tested: {
    wf_days: number; test_days: number
    windows: Record<string, { wf: Record<string, number>; test: Record<string, number> }>
    fixed_near: number; fixed_far: number
  } | null
}

/** POST /api/update: result of asking the backend to pull new candles from Alpaca. */
export interface UpdateStatus { ok: boolean; message: string; last_candle: string }

/** One candle's DOWN/NEUTRAL/UP probabilities for a fixed horizon. */
export interface CandleForecast {
  slot: number
  time: string
  p_down: number | null
  p_neutral: number | null
  p_up: number | null
}

/** GET /api/session-forecast: all 78 candles of a session with probabilities. */
export interface SessionForecast {
  date: string
  horizon: number
  candles: CandleForecast[]
  trained_through: string
  in_sample: boolean
}

export type RangeKey = '1D' | '5D' | '1M' | '3M'

export interface Toggles {
  ema: boolean
  vwap: boolean
  bb: boolean
  levels: boolean
  rsi: boolean
  macd: boolean
}
