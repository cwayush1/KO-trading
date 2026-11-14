# KO market desk: models and API

Python side of the project: data checks, features, targets, model comparison,
saved models and a FastAPI server for the dashboard. Analysis only, no orders.

## Run it

    pip install -r requirements.txt
    python train_final.py              # about a minute; writes artifacts/forecaster.joblib
    uvicorn api:app --port 8000

Then start the dashboard (`npm run dev` in `../frontend`). Its forecast panel
fills in because `frontend/.env.local` points at http://localhost:8000.

To redo the full comparison (about 20 minutes on 2 cores):

    python -m tests.test_no_leakage    # proves no feature looks ahead
    python run_experiments.py
    python build_report.py             # writes reports/results.md and results.json

## What was tested

- Data: 74,755 five-minute candles, 967 sessions, 3 Jan 2023 to 9 Nov 2026.
- Target: UP / NEUTRAL / DOWN over 10, 15, 30, 60 and 120 minutes. A move is
  NEUTRAL when it is smaller than 0.35 x (typical 5-minute move) x sqrt(candles).
  Targets never cross the 16:00 close or an overnight gap.
- 44 features, each using only candles up to the forecast moment.
- Models: logistic regression, random forest, extra trees, LightGBM, XGBoost,
  CatBoost, against four simple baselines.
- Evaluation: 7 expanding walk-forward folds on the first 841 sessions, then one
  look at the final 126 sessions (12 May to 9 Nov 2026). No random splits.
- Not run: LSTM, GRU, TCN (no PyTorch in the build environment), feature
  ablations, other neutral-band widths.

## Result: 60% directional accuracy was not reached

Directional accuracy = when the model says UP or DOWN, how often price ends on
that side. LightGBM, all moments:

| Horizon | Walk-forward | Final 6 months (95% interval) |
|---|---|---|
| 10 min | 49.9% | 50.1% (48.4% to 51.8%) |
| 15 min | 50.3% | 51.4% (49.2% to 53.6%) |
| 30 min | 48.4% | 49.4% (46.0% to 53.0%) |
| 60 min | 49.7% | 49.2% (44.1% to 54.5%) |
| 120 min | 48.9% | 47.3% (40.6% to 54.1%) |

Every model and every horizon lands between 47% and 52%. That is a coin flip.
No model is meaningfully better than another; logistic regression is within a
point of the boosters.

What the models can do is tell busy stretches from quiet ones. Scored as
"will price move outside the neutral band" (AUC, 0.50 = chance):

| Horizon | Walk-forward | Final 6 months |
|---|---|---|
| 10 min | 0.629 | 0.627 |
| 15 min | 0.619 | 0.628 |
| 30 min | 0.605 | 0.619 |
| 60 min | 0.578 | 0.612 |
| 120 min | 0.550 | 0.597 |

That skill is modest, and it held up from walk-forward to the final test.
It comes mostly from time of day and recent volatility. Three-class accuracy
(about 42% at 10 minutes against 38% for always guessing NEUTRAL) is this same
skill, not direction. Probabilities are well calibrated (error under 0.03).

One lead worth a closer look, not a result: when LightGBM is at least 45% sure of
a direction at 15 minutes, it was right 56.4% in walk-forward (509 calls) and
58.1% in the final test (308 calls, interval 51.3% to 65.2%). That is about 1.5%
of moments, the interval is wide, and it was noticed after looking at several
cut-offs, so it needs fresh data before anyone relies on it.

Why direction fails: KO is a large, heavily traded stock, and price and volume
history alone is the most picked-over information there is. Any edge left in it
is smaller than this sample can detect.

## Pre-market day outlook

Question: before the 09:30 New York open, can the model say whether the day
candle will be green (close above open)? Features use earlier sessions only,
not today's open or gap. `python run_daily_experiment.py` reproduces this.

| Model | Walk-forward, 529 days (95% interval) | Final 126 days (95% interval) |
|---|---|---|
| Always say green | 51.4% (47.2% to 55.7%) | 49.2% (40.6% to 57.8%) |
| Logistic regression | 50.1% (45.8% to 54.3%) | 47.6% (39.1% to 56.3%) |
| Random forest | 51.8% (47.5% to 56.0%) | 50.0% (41.4% to 58.6%) |
| LightGBM | 51.8% (47.5% to 56.0%) | 54.0% (45.3% to 62.4%) |

No model beats "always say green" by more than noise. With about 900 days, an
edge of a few points could not be confirmed even if it existed. The dashboard
shows the outlook with these numbers beside it. The file has regular-hours
candles only; pre-market price and news, which would help most, are not in it.

## Day plan: every 5-minute candle, called before the open

All 78 candles of a session are called green or red before 09:30 New York, from
earlier sessions only. `python run_plan_experiment.py` reproduces this.

| Model | Walk-forward, 539 days (95% interval) | Final 126 days (95% interval) |
|---|---|---|
| Call every candle green | 50.6% (50.1% to 51.1%) | 49.9% (48.8% to 50.9%) |
| Whatever that time slot usually does | 50.5% (50.0% to 51.0%) | 50.5% (49.4% to 51.4%) |
| Logistic regression | 50.2% (49.7% to 50.8%) | 49.5% (48.5% to 50.5%) |
| LightGBM | 50.4% (49.9% to 50.9%) | 51.0% (50.0% to 52.0%) |

This is a coin flip. Single days ranged from 29% to 71% with no skill involved,
so a 60% day will happen now and then by luck. The dashboard shows the plan,
scores it candle by candle as the day unfolds, and keeps a running total.

## Range cone: the indicator on the chart

Direction is near a coin flip, but the size of the coming move is forecastable. The range cone uses
that: at each candle close it draws, to the right of the last candle, the band the price is likely to
stay in for the next 15 to 120 minutes. A pale band should hold 80% of future closes, a darker core 50%.
It is centred on the current price because no direction skill was found.

`kodesk/cone.py` fits LightGBM quantile models on the leak-free features (target: size of the move in
typical-move units), then rescales each by one number on the validation tail so coverage matches its
level. `run_cone_experiment.py` tests it:

| Period | Horizon | Inside 50% cone | Inside 80% cone |
|---|---|---|---|
| Walk-forward, 462 sessions | 30 min | 50.0% | 80.2% |
| Walk-forward, 462 sessions | 60 min | 49.7% | 79.9% |
| Walk-forward, 462 sessions | 120 min | 49.3% | 79.9% |
| Final held-out, 126 sessions | 30 min | 55.1% | 84.7% |
| Final held-out, 126 sessions | 60 min | 54.4% | 84.3% |
| Final held-out, 126 sessions | 120 min | 51.5% | 82.2% |

The cone earns its place by changing width at the right times. On the final period its narrowest third
was 0.78x a fixed-width band and its widest third 1.47x, and both still held about 83%. A fixed-width
band on the same moments held 92% when quiet and only 66% when busy. On the final period the cone ran
a little wide (84% against a target of 80%).

After the last candle of a session the cone switches to the first two hours of the next session,
overnight gap included. That one is sized from 20 days of daily moves, a rougher method: about 79%
of closes one hour after the open fell inside its 80% band. Full tables: `reports/cone_results.md`.

## Touch ladder: odds for targets and stops

The cone is about where a window closes. Targets and stops fill on a touch at any moment, so the touch
ladder models the highest high and lowest low of the next 30, 60 or 120 minutes instead. It gives the
distance from the current price that is touched 3 times in 4, 1 in 2, 1 in 4 and 1 in 10, draws those
levels on the chart, and reads the touch odds of any target and stop the trader types in.

`kodesk/touch.py` fits LightGBM quantile models and calibrates them on the validation tail, as the cone
does. `run_touch_experiment.py` checks that a level labelled 25% really is touched about 25% of the time:

| Period | Window | Labelled 75% | Labelled 50% | Labelled 25% | Labelled 10% |
|---|---|---|---|---|---|
| Walk-forward, 462 sessions | 60 min | 75.2% | 49.9% | 25.0% | 10.1% |
| Final held-out, 126 sessions | 60 min | 72.5% | 46.3% | 21.3% | 7.2% |

On the final period the levels sat slightly too far out, so they were touched a few points less often
than labelled. A fixed distance labelled 25% was touched about 14% of the time in quiet markets and 39%
in busy ones, which is the error the model removes.

Up and down were fitted separately. Ladders that gave one side more room picked the side with more
travel only 50% of the time (walk-forward), so the two sides are averaged and the ladder is symmetric.
The planner's "target comes first" figure is plain arithmetic for a market with no direction edge
(stop distance divided by target plus stop distance), not a model output. Full tables: `reports/touch_results.md`.

## Next candle: the one place the models beat a coin

`run_next_experiment.py` asks a narrower question: at the close of each 5-minute candle, will the
following candle close higher or lower? Features are the same leak-free set, the model is the average
of a shallow LightGBM and a shallow XGBoost, and flat candles are not scored.

| Period | Sessions | All calls | Confident calls (top 10%) | Confident calls per day |
|---|---|---|---|---|
| Walk-forward | 463 | 51.0% (50.5% to 51.6%) | 55.3% (53.5% to 57.0%) | 6.7 |
| Final held-out | 126 | 52.1% (51.0% to 53.1%) | 55.2% (51.8% to 58.6%) | 6.4 |

"Confident" means the call is in the top 10% by distance from 50/50. That bar is set on each fold's
validation tail before the test rows are touched. Ranges are 95% intervals from resampling whole sessions.

Read it for what it is: about 55% on roughly six calls a day, 51 to 52% on every call. The edge lasts
one candle and is small next to trading costs, so it is a measured result, not a trading signal.
The longer horizons and the pre-open calls above stay at coin-flip level.

## Keeping the data current

    copy .env.example .env        # then put your Alpaca keys in .env
    python update_data.py         # adds sessions after the last complete one

While the server runs, the dashboard asks it to do the same once a minute.
The updater refuses to append if the download disagrees with the file on
overlapping candles (new dividend adjustment or a different feed) and tells you
to run `python update_data.py --full`, then `python train_final.py`.
It was tested against simulated Alpaca responses, not the live service.

## What the dashboard shows as a result

- The chance of a move bigger than a stated dollar amount, against the usual chance.
- The up / neutral / down split, with the measured accuracy next to it.
- A warning when the chosen moment is inside the training period. The saved
  model is trained through 11 May 2026, so later dates are real out-of-sample.

## Files

    kodesk/config.py      horizons, neutral band, split sizes
    kodesk/data.py        load and validate candles
    kodesk/features.py    44 causal features
    kodesk/targets.py     UP / NEUTRAL / DOWN labels
    kodesk/models.py      model factory, early stopping, calibration
    kodesk/evaluate.py    walk-forward splits and metrics
    kodesk/inference.py   load saved models, forecast one moment
    run_experiments.py    model and horizon comparison
    build_report.py       tables from saved predictions
    train_final.py        train and save the served models (--all for live use)
    kodesk/daily.py       daily bars and pre-market features
    run_daily_experiment.py  pre-market day-outlook test
    kodesk/dayplan.py     pre-open calls for all 78 candles
    run_plan_experiment.py   day-plan test
    update_data.py        Alpaca download
    api.py                FastAPI: health, candles, prediction, day-outlook, day-plan, plan-scores, update
    tests/                look-ahead check

Candles are read from and written to `../frontend/public/data/ko_5min.csv`.
