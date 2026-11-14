# KO market desk

A React + TypeScript dashboard for reading Coca-Cola (KO) 5-minute candles.
Chart: TradingView Lightweight Charts. No trading, no orders: analysis only.

## Run it

    npm install
    npm run dev

Opens at http://localhost:5173. Needs Node 18 or newer.

## What you see

- **Time bar** (dark strip): pick a trading day, drag the slider to any moment
  in the session. Everything on the page is recomputed as of that candle,
  using only candles up to it. No future data leaks into a replayed moment.
- **Chart**: real candles, with EMA 9/20/50, VWAP, Bollinger Bands,
  support/resistance lines, RSI and MACD as toggles. All times are New York (ET).
- **Market read**: trend, strength, momentum, volatility and volume in plain words.
- **Alerts**: each one says why it fired (level breaks judged by volume,
  divergences, volatility, tightening ranges).
- **Model forecast**: chance of a meaningful move per horizon, with the model's
  measured accuracy shown beside it. Needs the backend running.

## Files

    public/data/ko_5min.csv   candles: time (ET), open, high, low, close, volume
    src/lib/time.ts           ET handling, session clock
    src/lib/data.ts           loads candles and model forecasts
    src/lib/indicators.ts     EMA, VWAP, Bollinger, RSI, MACD, ATR, ADX, relative volume
    src/lib/analysis.ts       market read, support/resistance, alerts
    src/components/           PriceChart, SessionBar, Panels
    src/App.tsx               page layout and state

## Model forecast panel

`.env.local` points the dashboard at http://localhost:8000. Start the backend
(see `../backend/README.md`) and the panel fills in. If the backend is not
running, the chart and market read still work from the bundled CSV and the
panel says it cannot reach the model.

## Data notes

- 74,755 candles, 3 Jan 2023 to 9 Nov 2026, regular hours 09:30 to 15:55 ET.
- One off-grid, zero-volume row (9 Nov 2026 13:33) was removed from the source file.
- Some sessions have 76 or 77 candles (missing bars) and a few are half days. The app handles both.
