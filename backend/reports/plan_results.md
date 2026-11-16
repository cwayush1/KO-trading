# Day plan: every 5-minute candle called before the open

Walk-forward: 542 days, 37840 candles. Final test: 126 days, 9324 candles.
Green candles: 50.5% of non-flat ones.

| Model | WF accuracy (95% CI) | Test accuracy (95% CI) | Best / worst single day (WF) | Days at 60%+ (WF) | WF at 55%+ confidence (candles) | Test at 55%+ confidence (candles) |
|---|---|---|---|---|---|---|
| always_green | 50.5% (50.0% to 51.0%) | 49.9% (48.8% to 50.9%) | 71.4% / 33.3% | 6.8% | 50.5% (37840) | 49.9% (9324) |
| slot_habit | 50.0% (49.5% to 50.5%) | 50.6% (49.7% to 51.6%) | 68.8% / 33.9% | 5.7% | 50.0% (37840) | 50.6% (9324) |
| same_as_yesterday | 50.0% (49.5% to 50.5%) | 51.3% (50.3% to 52.4%) | 71.4% / 22.2% | 4.4% | 50.0% (37840) | 51.3% (9324) |
| logreg | 50.6% (50.1% to 51.1%) | 49.6% (48.6% to 50.7%) | 66.7% / 28.6% | 6.8% | 50.3% (921) | 47.6% (105) |
| lightgbm | 50.3% (49.8% to 50.8%) | 50.7% (49.6% to 51.7%) | 71.1% / 33.9% | 6.3% | 51.3% (4438) | 51.2% (551) |
