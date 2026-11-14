# Day plan: every 5-minute candle called before the open

Walk-forward: 539 days, 39666 candles. Final test: 126 days, 9452 candles.
Green candles: 50.5% of non-flat ones.

| Model | WF accuracy (95% CI) | Test accuracy (95% CI) | Best / worst single day (WF) | Days at 60%+ (WF) | WF at 55%+ confidence (candles) | Test at 55%+ confidence (candles) |
|---|---|---|---|---|---|---|
| always_green | 50.6% (50.1% to 51.1%) | 49.9% (48.8% to 50.9%) | 67.9% / 33.8% | 6.3% | 50.6% (39666) | 49.9% (9452) |
| slot_habit | 50.5% (50.0% to 51.0%) | 50.5% (49.4% to 51.4%) | 72.2% / 28.9% | 4.5% | 50.5% (39666) | 50.5% (9452) |
| same_as_yesterday | 50.3% (49.8% to 50.8%) | 51.4% (50.5% to 52.4%) | 68.3% / 30.0% | 4.3% | 50.3% (39666) | 51.4% (9452) |
| logreg | 50.2% (49.7% to 50.8%) | 49.5% (48.5% to 50.5%) | 68.9% / 29.3% | 4.8% | 51.1% (133) | 55.6% (180) |
| lightgbm | 50.4% (49.9% to 50.9%) | 51.0% (50.0% to 52.0%) | 71.1% / 29.3% | 3.5% | 50.8% (884) | 53.3% (15) |
