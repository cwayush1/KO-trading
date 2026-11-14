# Pre-market day outlook: will the day candle be green?

907 full sessions, 2023-03-16 to 2026-11-06. Green days: 50.8%.
Walk-forward on 529 days, final test on the last 126. Features use prior sessions only.

| Model | WF accuracy (95% CI) | Test accuracy (95% CI) | WF at 55%+ confidence (days) | Test at 55%+ confidence (days) |
|---|---|---|---|---|
| always_up | 51.4% (47.2% to 55.7%) | 49.2% (40.6% to 57.8%) | 51.4% (529) | 49.2% (126) |
| same_as_yesterday | 49.0% (44.7% to 53.2%) | 46.8% (38.3% to 55.5%) | 49.0% (529) | 46.8% (126) |
| opposite_of_yesterday | 51.0% (46.8% to 55.3%) | 53.2% (44.5% to 61.7%) | 51.0% (529) | 53.2% (126) |
| logreg | 50.1% (45.8% to 54.3%) | 47.6% (39.1% to 56.3%) | 53.8% (266) | 50.0% (70) |
| random_forest | 51.8% (47.5% to 56.0%) | 50.0% (41.4% to 58.6%) | 55.2% (221) | 57.1% (21) |
| lightgbm | 51.8% (47.5% to 56.0%) | 54.0% (45.3% to 62.4%) | 50.2% (315) | 54.7% (53) |
