# AI Trading Indicator — KO Market Desk

A market-analysis dashboard for Coca-Cola (NYSE: KO) five-minute candles. It puts actual price history beside a pre-open candle plan, a forecast range for future closes, and recent checks of how those forecasts performed. The application is for analysis and education; it does not place orders.

- **Live dashboard:** https://creative-lokum-0c1d4e.netlify.app/
- **Backend health check:** https://ko-trading.onrender.com/api/health

## What the dashboard shows

| Panel | What it means |
| --- | --- |
| Candlestick chart | Real KO open, high, low, close, and volume bars. Pick a session and replay an earlier moment. The chart offers 1D, 5D, 1M, and 3M views. |
| Range cone | A dark 50% core and a wider 80% band for future closing prices. In replay, **What happened next** reveals the later price path against the original forecast. |
| Day plan | A green/red call for each of the regular session's 78 five-minute candles, made before the open from earlier sessions. Predicted and observed candle colours are shown together. |
| Candle Forecast | Per-slot Down, Neutral, and Up percentages derived for display from the **binary day-plan probability**. Neutral is a display rule, not a separately trained third class. |
| Directional accuracy | The day plan's percentage of correct calls on each of the latest 20 scored trading sessions. Hover for the exact date and percentage. |

The page can display clocks in New York time (ET) or India time (IST). It uses [TradingView Lightweight Charts](https://tradingview.github.io/lightweight-charts/) to draw the chart; **there is no Pine Script in this project**.

## How it works

```text
KO five-minute OHLCV CSV ──> validated, time-aware features ──> saved models
          │                                                   │
          └─────────────────> FastAPI on Render <──────────────┘
                                   │
                                   v
                         React/Vite site on Netlify
```

The day plan uses a binary LightGBM classifier. For a target session, its inputs are calculated from the *previous* session and earlier same-time-of-day behaviour, so all 78 calls are fixed before 09:30 ET. Flat candles (close equal to open) are excluded from directional-accuracy scoring.

The intraday cone uses LightGBM quantile models to estimate the size of future close-to-close moves at 15, 30, 60, and 120 minutes. The predicted widths are adjusted on a later validation period to aim for 50% and 80% coverage. At the end of a session, the cone for the next opening period uses a separate method based on recent daily volatility and includes the overnight gap. A range is a forecast interval for future *closes*, not a guarantee about every price tick.

The frontend first requests candles and forecasts from the API. It can fall back to the bundled CSV for chart data if the backend is unavailable. About once a minute, it asks the backend to check Alpaca for new, **completed** five-minute bars. Appending candles refreshes data and features; it does **not** retrain the saved model weights.

## Data and evaluation

The CSV at `frontend/public/data/ko_5min.csv` in the current repository snapshot contains 75,264 candles over 970 session dates, from 3 January 2023 through 13 November 2026. It uses regular US market hours (09:30–16:00 ET). The loader sorts times, removes duplicates, and rejects off-grid or invalid OHLCV rows. The historical CSV and saved experiment reports were updated at different times, so their row counts are not necessarily identical.

Experiments use chronological walk-forward evaluation and a later held-out period, rather than randomly shuffling candles. The saved day-plan report scores 542 walk-forward days and 126 final-test days:

| Day-plan method | Walk-forward | Final held-out |
| --- | ---: | ---: |
| Always green | 50.5% | 49.9% |
| Logistic regression | 50.6% | 49.6% |
| LightGBM | 50.3% | 50.7% |

The held-out LightGBM result is close to the baselines and does not establish a reliable directional edge. For the range cone, 84.3% of one-hour future closes in the saved final test fell inside its nominal 80% band. This is evidence about interval coverage, **not** trading profitability. See `backend/reports/plan_results.md` and `backend/reports/cone_results.md` for the full measurements.

## Run locally

Requirements: Python 3.10+ and Node.js 20+ are sensible starting points; the deployed frontend build uses Node 20. The repository already includes a candle CSV and a saved model artifact, so Alpaca credentials are only needed to fetch *new* bars.

1. Start the Python API:

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn api:app --reload --port 8000
   ```

   The health endpoint is at http://localhost:8000/api/health. If the saved artifact is missing, run `python train_final.py` before starting the API.
   On Windows PowerShell, activate the environment with `.\.venv\Scripts\Activate.ps1` instead of `source .venv/bin/activate`.

2. In a second terminal, start the frontend:

   ```bash
   cd frontend
   cp .env.example .env.local
   npm ci
   npm run dev
   ```

   Open http://localhost:5173. `VITE_API_URL` in `.env.local` points the frontend to the local API. Without the API, the chart can still use the bundled CSV, but model panels require the backend.

3. To update candles from Alpaca, copy `backend/.env.example` to `backend/.env`, add your own `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY`, then run `python update_data.py` from `backend/`. Keep `.env` private. If an update changes the history or you want new model weights, retrain deliberately with `python train_final.py` and review the evaluation again.

## Reproduce saved experiments

From `backend/`, after installing dependencies:

```bash
python -m tests.test_no_leakage
python run_plan_experiment.py
python run_cone_experiment.py
```

The experiment scripts write tables and JSON under `backend/reports/`. Re-running them on the **current** CSV may produce different counts or numbers from reports saved on an earlier data snapshot.

## Repository layout

```text
backend/
  api.py                 FastAPI endpoints
  kodesk/                data checks, features, models, and inference
  run_plan_experiment.py chronological day-plan evaluation
  run_cone_experiment.py chronological cone evaluation
  update_data.py         Alpaca candle updater
  artifacts/             saved model bundle
  reports/               saved results
frontend/
  src/App.tsx            dashboard layout and state
  src/components/        chart and visible forecast panels
  public/data/           bundled KO candle CSV
netlify.toml             frontend deployment configuration
render.yaml              backend deployment configuration
```

The site is deployed with Netlify for the frontend and Render for the API. Model performance can change over time, and historical accuracy or cone coverage does not imply that any trading strategy will make money.
