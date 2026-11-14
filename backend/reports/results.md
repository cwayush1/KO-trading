# KO forecast experiments (neutral band k = 0.35)

Directional accuracy = of the forecasts that said UP or DOWN, the share where price really
finished on that side. Coverage = share of moments that got an UP or DOWN call at all.
WF = walk-forward on the development period. Test = final ~6 months, scored once.

## 10-minute horizon

| Model | WF 3-class acc | WF balanced acc | WF macro F1 | WF directional | WF coverage | WF fold range | Test directional (95% CI) | Test coverage | Test ECE |
|---|---|---|---|---|---|---|---|---|---|
| majority | 37.8% | 33.3% | 0.183 | n/a | 0.0% | n/a | n/a (n/a to n/a) | 0.0% | 0.607 |
| always_up | 31.7% | 33.3% | 0.160 | 49.1% | 100.0% | 47.4% to 50.6% | 48.6% (47.3% to 49.9%) | 100.0% | 0.696 |
| momentum | 31.2% | 33.4% | 0.256 | 48.5% | 100.0% | 46.7% to 50.0% | 48.7% (47.5% to 49.9%) | 100.0% | 0.695 |
| reversal | 31.0% | 33.2% | 0.255 | 48.5% | 100.0% | 47.1% to 50.0% | 48.9% (47.7% to 50.1%) | 100.0% | 0.698 |
| logreg | 41.5% | 39.1% | 0.364 | 49.7% | 34.8% | 47.8% to 51.3% | 50.7% (49.1% to 52.4%) | 40.7% | 0.010 |
| random_forest | 42.0% | 39.7% | 0.374 | 49.6% | 38.0% | 45.8% to 51.3% | 49.7% (47.8% to 51.8%) | 39.5% | 0.013 |
| extra_trees | 41.5% | 39.0% | 0.360 | 49.4% | 34.0% | 48.5% to 51.2% | 50.8% (48.8% to 52.7%) | 35.6% | 0.011 |
| lightgbm | 42.3% | 40.0% | 0.377 | 49.9% | 37.6% | 48.3% to 51.4% | 50.1% (48.4% to 51.8%) | 43.7% | 0.011 |
| xgboost | 42.3% | 40.0% | 0.377 | 49.8% | 38.2% | 48.6% to 51.7% | 50.0% (48.3% to 51.7%) | 43.4% | 0.009 |
| catboost | 42.1% | 39.8% | 0.376 | 49.6% | 38.3% | 47.9% to 51.3% | 50.1% (48.5% to 51.6%) | 44.5% | 0.006 |

## 15-minute horizon

| Model | WF 3-class acc | WF balanced acc | WF macro F1 | WF directional | WF coverage | WF fold range | Test directional (95% CI) | Test coverage | Test ECE |
|---|---|---|---|---|---|---|---|---|---|
| majority | 38.0% | 33.3% | 0.183 | n/a | 0.0% | n/a | n/a (n/a to n/a) | 0.0% | 0.602 |
| always_up | 31.6% | 33.3% | 0.160 | 49.5% | 100.0% | 47.4% to 51.1% | 49.0% (47.3% to 50.6%) | 100.0% | 0.701 |
| momentum | 31.0% | 33.3% | 0.255 | 48.6% | 100.0% | 46.9% to 50.0% | 49.4% (48.1% to 50.9%) | 100.0% | 0.694 |
| reversal | 31.0% | 33.3% | 0.255 | 48.9% | 100.0% | 48.0% to 50.3% | 48.7% (47.3% to 50.0%) | 100.0% | 0.704 |
| logreg | 41.2% | 38.6% | 0.356 | 49.8% | 33.4% | 46.4% to 52.2% | 50.6% (48.2% to 53.2%) | 38.4% | 0.012 |
| random_forest | 41.4% | 39.0% | 0.367 | 49.7% | 37.3% | 48.5% to 50.9% | 50.2% (47.5% to 52.7%) | 37.9% | 0.012 |
| extra_trees | 41.1% | 38.5% | 0.357 | 49.3% | 34.5% | 47.3% to 51.5% | 50.7% (47.9% to 53.4%) | 35.0% | 0.014 |
| lightgbm | 41.9% | 39.5% | 0.373 | 50.3% | 38.1% | 48.9% to 51.9% | 51.4% (49.2% to 53.6%) | 41.1% | 0.016 |
| xgboost | 41.8% | 39.5% | 0.373 | 50.3% | 37.9% | 49.1% to 51.3% | 50.8% (48.6% to 52.9%) | 41.4% | 0.015 |
| catboost | 41.7% | 39.4% | 0.371 | 50.4% | 37.7% | 48.8% to 52.1% | 51.3% (49.2% to 53.5%) | 41.5% | 0.014 |

## 30-minute horizon

| Model | WF 3-class acc | WF balanced acc | WF macro F1 | WF directional | WF coverage | WF fold range | Test directional (95% CI) | Test coverage | Test ECE |
|---|---|---|---|---|---|---|---|---|---|
| majority | 37.1% | 33.3% | 0.180 | n/a | 0.0% | n/a | n/a (n/a to n/a) | 0.0% | 0.608 |
| always_up | 31.9% | 33.3% | 0.161 | 50.0% | 100.0% | 47.2% to 52.0% | 49.0% (46.8% to 51.3%) | 100.0% | 0.698 |
| momentum | 31.9% | 33.8% | 0.261 | 49.6% | 100.0% | 47.3% to 51.9% | 51.2% (49.6% to 52.8%) | 100.0% | 0.678 |
| reversal | 31.0% | 32.9% | 0.254 | 48.6% | 100.0% | 46.2% to 50.7% | 47.6% (46.1% to 49.1%) | 100.0% | 0.713 |
| logreg | 39.8% | 37.7% | 0.341 | 48.5% | 33.2% | 44.7% to 54.7% | 50.5% (47.2% to 54.0%) | 42.8% | 0.008 |
| random_forest | 40.0% | 38.1% | 0.355 | 48.4% | 38.0% | 45.3% to 51.3% | 49.9% (46.4% to 53.4%) | 42.8% | 0.030 |
| extra_trees | 39.9% | 37.9% | 0.345 | 47.9% | 34.9% | 44.5% to 50.6% | 51.8% (48.4% to 55.1%) | 37.6% | 0.018 |
| lightgbm | 40.0% | 38.2% | 0.358 | 48.4% | 39.0% | 45.8% to 51.8% | 49.4% (46.0% to 53.0%) | 45.4% | 0.012 |
| xgboost | 39.9% | 38.1% | 0.355 | 48.1% | 38.5% | 44.3% to 52.4% | 49.8% (46.3% to 53.4%) | 44.3% | 0.018 |
| catboost | 40.5% | 38.6% | 0.360 | 49.5% | 37.7% | 45.6% to 53.4% | 49.7% (46.3% to 53.2%) | 44.4% | 0.020 |

## 60-minute horizon

| Model | WF 3-class acc | WF balanced acc | WF macro F1 | WF directional | WF coverage | WF fold range | Test directional (95% CI) | Test coverage | Test ECE |
|---|---|---|---|---|---|---|---|---|---|
| majority | 37.1% | 33.3% | 0.180 | n/a | 0.0% | n/a | n/a (n/a to n/a) | 0.0% | 0.615 |
| always_up | 32.2% | 33.3% | 0.162 | 50.4% | 100.0% | 46.3% to 54.1% | 48.8% (45.6% to 52.0%) | 100.0% | 0.699 |
| momentum | 31.8% | 33.7% | 0.260 | 49.9% | 100.0% | 48.0% to 52.2% | 50.1% (47.5% to 52.6%) | 100.0% | 0.687 |
| reversal | 31.1% | 33.0% | 0.255 | 48.9% | 100.0% | 46.5% to 50.7% | 49.1% (46.5% to 51.6%) | 100.0% | 0.698 |
| logreg | 38.7% | 36.9% | 0.342 | 48.8% | 36.6% | 45.3% to 55.6% | 50.3% (45.4% to 55.5%) | 42.9% | 0.014 |
| random_forest | 39.6% | 37.6% | 0.348 | 49.7% | 35.4% | 46.6% to 53.3% | 49.1% (43.9% to 54.5%) | 40.2% | 0.017 |
| extra_trees | 39.7% | 37.7% | 0.347 | 50.7% | 34.5% | 48.4% to 53.9% | 51.2% (46.3% to 56.2%) | 36.4% | 0.022 |
| lightgbm | 39.5% | 37.6% | 0.348 | 49.7% | 35.6% | 44.1% to 54.5% | 49.2% (44.1% to 54.5%) | 43.1% | 0.014 |
| xgboost | 39.3% | 37.4% | 0.346 | 48.8% | 36.0% | 43.3% to 54.2% | 49.2% (44.1% to 54.4%) | 43.0% | 0.013 |
| catboost | 39.5% | 37.5% | 0.345 | 49.4% | 34.8% | 44.2% to 55.2% | 48.9% (43.5% to 54.3%) | 37.2% | 0.021 |

## 120-minute horizon

| Model | WF 3-class acc | WF balanced acc | WF macro F1 | WF directional | WF coverage | WF fold range | Test directional (95% CI) | Test coverage | Test ECE |
|---|---|---|---|---|---|---|---|---|---|
| majority | 37.7% | 33.3% | 0.182 | n/a | 0.0% | n/a | n/a (n/a to n/a) | 0.0% | 0.622 |
| always_up | 31.8% | 33.3% | 0.161 | 50.6% | 100.0% | 48.3% to 56.0% | 48.6% (43.8% to 53.4%) | 100.0% | 0.699 |
| momentum | 31.6% | 33.8% | 0.260 | 50.3% | 100.0% | 46.6% to 55.1% | 49.8% (46.4% to 53.4%) | 100.0% | 0.686 |
| reversal | 30.7% | 32.8% | 0.252 | 48.9% | 100.0% | 44.1% to 52.1% | 49.7% (46.0% to 53.1%) | 100.0% | 0.691 |
| logreg | 38.6% | 35.6% | 0.292 | 48.8% | 21.5% | 38.6% to 57.4% | 49.2% (42.1% to 56.3%) | 32.4% | 0.014 |
| random_forest | 39.2% | 36.8% | 0.338 | 50.3% | 33.2% | 45.3% to 55.9% | 47.2% (39.9% to 54.5%) | 35.8% | 0.012 |
| extra_trees | 38.8% | 36.2% | 0.319 | 49.4% | 28.8% | 44.3% to 58.4% | 49.5% (42.3% to 56.2%) | 31.6% | 0.007 |
| lightgbm | 38.1% | 35.5% | 0.313 | 48.9% | 28.4% | 45.6% to 55.2% | 47.3% (40.6% to 54.1%) | 39.3% | 0.027 |
| xgboost | 38.6% | 36.1% | 0.325 | 49.3% | 31.3% | 44.6% to 54.0% | 47.7% (40.0% to 54.7%) | 37.0% | 0.018 |
| catboost | 38.5% | 36.1% | 0.329 | 49.2% | 32.6% | 43.8% to 53.4% | 46.3% (39.4% to 53.5%) | 36.0% | 0.024 |

## Two skills, measured separately (AUC: 0.50 = coin flip, 1.00 = perfect)

Move = can the model tell an active period from a quiet one. Direction = given price moved, did the model favour the right side.

| Model | Horizon | WF move AUC | WF direction AUC | Test move AUC | Test direction AUC |
|---|---|---|---|---|---|
| logreg | 10 | 0.616 | 0.511 | 0.615 | 0.532 |
| random_forest | 10 | 0.629 | 0.512 | 0.628 | 0.520 |
| extra_trees | 10 | 0.623 | 0.509 | 0.625 | 0.519 |
| lightgbm | 10 | 0.629 | 0.523 | 0.627 | 0.532 |
| xgboost | 10 | 0.630 | 0.523 | 0.627 | 0.532 |
| catboost | 10 | 0.630 | 0.526 | 0.628 | 0.527 |
| logreg | 15 | 0.605 | 0.511 | 0.620 | 0.524 |
| random_forest | 15 | 0.619 | 0.512 | 0.629 | 0.524 |
| extra_trees | 15 | 0.613 | 0.507 | 0.623 | 0.516 |
| lightgbm | 15 | 0.619 | 0.515 | 0.628 | 0.534 |
| xgboost | 15 | 0.620 | 0.514 | 0.629 | 0.534 |
| catboost | 15 | 0.620 | 0.524 | 0.629 | 0.534 |
| logreg | 30 | 0.594 | 0.493 | 0.599 | 0.534 |
| random_forest | 30 | 0.605 | 0.499 | 0.618 | 0.527 |
| extra_trees | 30 | 0.599 | 0.500 | 0.614 | 0.528 |
| lightgbm | 30 | 0.605 | 0.496 | 0.619 | 0.510 |
| xgboost | 30 | 0.605 | 0.493 | 0.618 | 0.519 |
| catboost | 30 | 0.604 | 0.504 | 0.620 | 0.522 |
| logreg | 60 | 0.574 | 0.502 | 0.596 | 0.513 |
| random_forest | 60 | 0.579 | 0.506 | 0.616 | 0.489 |
| extra_trees | 60 | 0.579 | 0.505 | 0.613 | 0.542 |
| lightgbm | 60 | 0.578 | 0.491 | 0.612 | 0.517 |
| xgboost | 60 | 0.581 | 0.492 | 0.614 | 0.506 |
| catboost | 60 | 0.577 | 0.499 | 0.622 | 0.492 |
| logreg | 120 | 0.548 | 0.504 | 0.577 | 0.504 |
| random_forest | 120 | 0.563 | 0.502 | 0.592 | 0.472 |
| extra_trees | 120 | 0.561 | 0.502 | 0.584 | 0.525 |
| lightgbm | 120 | 0.550 | 0.485 | 0.597 | 0.505 |
| xgboost | 120 | 0.560 | 0.492 | 0.594 | 0.499 |
| catboost | 120 | 0.560 | 0.498 | 0.590 | 0.498 |

## Directional accuracy when only confident calls count

| Model | Horizon | Min confidence | WF directional | WF coverage | Test directional (95% CI) | Test coverage | Test calls |
|---|---|---|---|---|---|---|---|
| logreg | 10 | 0.40 | 49.7% | 9.2% | 52.4% (49.3% to 55.9%) | 14.4% | 1366 |
| logreg | 10 | 0.45 | 52.2% | 1.6% | 55.3% (49.8% to 61.1%) | 3.9% | 369 |
| logreg | 10 | 0.50 | 52.4% | 0.5% | 62.1% (51.5% to 73.9%) | 1.0% | 95 |
| logreg | 10 | 0.55 | 53.8% | 0.2% | 76.2% (n/a to n/a) | 0.2% | 21 |
| logreg | 10 | 0.60 | 52.6% | 0.1% | 44.4% (n/a to n/a) | 0.1% | 9 |
| lightgbm | 10 | 0.40 | 51.1% | 12.3% | 51.2% (48.7% to 53.8%) | 19.0% | 1801 |
| lightgbm | 10 | 0.45 | 53.6% | 1.5% | 54.2% (48.8% to 59.7%) | 3.9% | 365 |
| lightgbm | 10 | 0.50 | 60.3% | 0.2% | 58.3% (n/a to n/a) | 0.3% | 24 |
| lightgbm | 10 | 0.55 | 50.0% | 0.0% | 0.0% (n/a to n/a) | 0.0% | 2 |
| lightgbm | 10 | 0.60 | n/a | 0.0% | n/a (n/a to n/a) | 0.0% | 0 |
| logreg | 15 | 0.40 | 48.6% | 8.6% | 53.4% (49.7% to 57.0%) | 12.2% | 1137 |
| logreg | 15 | 0.45 | 48.7% | 1.6% | 54.0% (47.7% to 61.6%) | 3.5% | 326 |
| logreg | 15 | 0.50 | 48.1% | 0.5% | 56.7% (43.5% to 71.1%) | 1.0% | 97 |
| logreg | 15 | 0.55 | 51.4% | 0.3% | 59.3% (n/a to n/a) | 0.3% | 27 |
| logreg | 15 | 0.60 | 47.9% | 0.2% | 85.7% (n/a to n/a) | 0.1% | 7 |
| lightgbm | 15 | 0.40 | 50.9% | 11.0% | 52.1% (48.4% to 55.7%) | 14.6% | 1359 |
| lightgbm | 15 | 0.45 | 56.4% | 1.5% | 58.1% (51.3% to 65.2%) | 3.3% | 308 |
| lightgbm | 15 | 0.50 | 55.6% | 0.1% | 60.0% (46.0% to 74.1%) | 0.6% | 55 |
| lightgbm | 15 | 0.55 | 100.0% | 0.0% | 50.0% (n/a to n/a) | 0.0% | 4 |
| lightgbm | 15 | 0.60 | n/a | 0.0% | n/a (n/a to n/a) | 0.0% | 0 |
| logreg | 30 | 0.40 | 48.4% | 8.4% | 52.4% (48.2% to 56.8%) | 14.9% | 1327 |
| logreg | 30 | 0.45 | 52.4% | 1.4% | 53.8% (46.2% to 61.9%) | 3.7% | 333 |
| logreg | 30 | 0.50 | 60.5% | 0.6% | 56.0% (47.5% to 78.1%) | 1.0% | 91 |
| logreg | 30 | 0.55 | 60.0% | 0.3% | 52.6% (n/a to n/a) | 0.2% | 19 |
| logreg | 30 | 0.60 | 55.4% | 0.2% | 50.0% (n/a to n/a) | 0.0% | 4 |
| lightgbm | 30 | 0.40 | 48.0% | 7.4% | 50.3% (45.3% to 55.4%) | 16.7% | 1486 |
| lightgbm | 30 | 0.45 | 50.6% | 0.8% | 61.3% (51.5% to 72.2%) | 2.1% | 191 |
| lightgbm | 30 | 0.50 | 26.7% | 0.0% | n/a (n/a to n/a) | 0.0% | 0 |
| lightgbm | 30 | 0.55 | n/a | 0.0% | n/a (n/a to n/a) | 0.0% | 0 |
| lightgbm | 30 | 0.60 | n/a | 0.0% | n/a (n/a to n/a) | 0.0% | 0 |
| logreg | 60 | 0.40 | 47.2% | 6.0% | 53.5% (46.6% to 60.0%) | 16.1% | 1298 |
| logreg | 60 | 0.45 | 49.9% | 1.2% | 52.2% (43.5% to 60.0%) | 5.0% | 402 |
| logreg | 60 | 0.50 | 51.6% | 0.5% | 51.0% (35.4% to 64.2%) | 1.9% | 157 |
| logreg | 60 | 0.55 | 51.5% | 0.3% | 53.0% (38.6% to 70.6%) | 1.0% | 83 |
| logreg | 60 | 0.60 | 50.0% | 0.2% | 53.1% (41.7% to 100.0%) | 0.6% | 49 |
| lightgbm | 60 | 0.40 | 51.1% | 5.9% | 51.3% (44.8% to 58.1%) | 15.2% | 1224 |
| lightgbm | 60 | 0.45 | 46.9% | 0.4% | 71.1% (45.8% to 94.0%) | 0.6% | 45 |
| lightgbm | 60 | 0.50 | 80.0% | 0.0% | n/a (n/a to n/a) | 0.0% | 0 |
| lightgbm | 60 | 0.55 | n/a | 0.0% | n/a (n/a to n/a) | 0.0% | 0 |
| lightgbm | 60 | 0.60 | n/a | 0.0% | n/a (n/a to n/a) | 0.0% | 0 |
| logreg | 120 | 0.40 | 54.5% | 4.6% | 48.5% (38.1% to 58.4%) | 12.2% | 784 |
| logreg | 120 | 0.45 | 54.2% | 1.3% | 49.8% (33.3% to 65.2%) | 4.7% | 301 |
| logreg | 120 | 0.50 | 50.0% | 0.7% | 47.4% (26.4% to 70.2%) | 2.1% | 135 |
| logreg | 120 | 0.55 | 42.3% | 0.3% | 37.2% (19.0% to 75.0%) | 1.2% | 78 |
| logreg | 120 | 0.60 | 40.0% | 0.2% | 23.3% (18.2% to 66.7%) | 0.7% | 43 |
| lightgbm | 120 | 0.40 | 45.3% | 2.9% | 47.4% (38.6% to 55.9%) | 21.4% | 1379 |
| lightgbm | 120 | 0.45 | 50.0% | 0.2% | 46.9% (34.6% to 59.8%) | 8.0% | 518 |
| lightgbm | 120 | 0.50 | 0.0% | 0.0% | 45.2% (17.1% to 81.2%) | 1.1% | 73 |
| lightgbm | 120 | 0.55 | n/a | 0.0% | n/a (n/a to n/a) | 0.0% | 0 |
| lightgbm | 120 | 0.60 | n/a | 0.0% | n/a (n/a to n/a) | 0.0% | 0 |

## lightgbm, 10 minutes: stability across conditions (all out-of-sample rows)

| Condition | Rows | 3-class acc | Directional | Coverage |
|---|---|---|---|---|
| year: 2024 | 9208 | 42.9% | 49.7% | 40.7% |
| year: 2025 | 18690 | 42.9% | 50.4% | 34.7% |
| year: 2026 | 16159 | 41.5% | 49.6% | 42.9% |
| volatility: calm third | 14671 | 41.6% | 50.2% | 36.2% |
| volatility: middle third | 14715 | 42.6% | 49.5% | 39.6% |
| volatility: volatile third | 14671 | 42.9% | 50.1% | 41.0% |
| time of day: 09:30-10:30 | 6973 | 40.2% | 50.3% | 99.1% |
| time of day: 10:30-14:00 | 24422 | 41.8% | 50.0% | 31.0% |
| time of day: 14:00-16:00 | 12662 | 44.8% | 48.6% | 21.2% |
| regime: not trending | 24531 | 43.4% | 49.2% | 28.3% |
| regime: trending (ADX 25+) | 19526 | 41.2% | 50.4% | 52.3% |

## lightgbm, 15 minutes: stability across conditions (all out-of-sample rows)

| Condition | Rows | 3-class acc | Directional | Coverage |
|---|---|---|---|---|
| year: 2024 | 9064 | 43.0% | 50.2% | 43.8% |
| year: 2025 | 18384 | 42.0% | 49.7% | 33.8% |
| year: 2026 | 15900 | 42.2% | 51.7% | 41.5% |
| volatility: calm third | 14435 | 41.6% | 50.1% | 35.3% |
| volatility: middle third | 14478 | 42.3% | 50.4% | 39.8% |
| volatility: volatile third | 14435 | 42.8% | 51.2% | 41.1% |
| time of day: 09:30-10:30 | 6954 | 40.3% | 51.3% | 98.3% |
| time of day: 10:30-14:00 | 24348 | 41.5% | 50.1% | 32.4% |
| time of day: 14:00-16:00 | 12046 | 44.8% | 50.1% | 17.1% |
| regime: not trending | 24094 | 43.3% | 50.5% | 26.7% |
| regime: trending (ADX 25+) | 19254 | 41.0% | 50.7% | 53.8% |

## lightgbm, 30 minutes: stability across conditions (all out-of-sample rows)

| Condition | Rows | 3-class acc | Directional | Coverage |
|---|---|---|---|---|
| year: 2024 | 8632 | 42.5% | 50.9% | 43.4% |
| year: 2025 | 17475 | 39.5% | 47.7% | 37.3% |
| year: 2026 | 15130 | 40.1% | 48.3% | 42.2% |
| volatility: calm third | 13732 | 39.2% | 48.5% | 35.8% |
| volatility: middle third | 13773 | 40.7% | 48.1% | 41.2% |
| volatility: volatile third | 13732 | 41.1% | 49.2% | 44.1% |
| time of day: 09:30-10:30 | 6894 | 38.8% | 49.7% | 98.1% |
| time of day: 10:30-14:00 | 24119 | 39.7% | 48.0% | 35.1% |
| time of day: 14:00-16:00 | 10224 | 42.9% | 47.6% | 14.1% |
| regime: not trending | 22778 | 41.5% | 48.2% | 28.6% |
| regime: trending (ADX 25+) | 18459 | 38.9% | 48.9% | 55.0% |

## lightgbm, 60 minutes: stability across conditions (all out-of-sample rows)

| Condition | Rows | 3-class acc | Directional | Coverage |
|---|---|---|---|---|
| year: 2024 | 7772 | 42.0% | 53.2% | 39.1% |
| year: 2025 | 15699 | 39.3% | 49.1% | 34.3% |
| year: 2026 | 13643 | 39.2% | 48.1% | 39.6% |
| volatility: calm third | 12359 | 38.9% | 49.4% | 34.7% |
| volatility: middle third | 12396 | 40.3% | 49.1% | 34.7% |
| volatility: volatile third | 12359 | 40.2% | 50.2% | 42.3% |
| time of day: 09:30-10:30 | 6807 | 39.0% | 51.0% | 97.3% |
| time of day: 10:30-14:00 | 23625 | 39.2% | 48.0% | 28.6% |
| time of day: 14:00-16:00 | 6682 | 42.6% | 53.5% | 6.9% |
| regime: not trending | 20162 | 40.9% | 48.6% | 25.6% |
| regime: trending (ADX 25+) | 16952 | 38.5% | 50.2% | 51.1% |

## lightgbm, 120 minutes: stability across conditions (all out-of-sample rows)

| Condition | Rows | 3-class acc | Directional | Coverage |
|---|---|---|---|---|
| year: 2024 | 6127 | 38.9% | 47.4% | 41.4% |
| year: 2025 | 12303 | 38.4% | 51.6% | 20.3% |
| year: 2026 | 10836 | 37.7% | 47.2% | 36.7% |
| volatility: calm third | 9746 | 37.4% | 49.1% | 24.5% |
| volatility: middle third | 9774 | 38.3% | 47.1% | 30.0% |
| volatility: volatile third | 9746 | 39.1% | 49.1% | 37.8% |
| time of day: 09:30-10:30 | 6629 | 34.1% | 51.0% | 66.8% |
| time of day: 10:30-14:00 | 22637 | 39.5% | 46.0% | 20.2% |
| regime: not trending | 15347 | 40.1% | 47.3% | 21.0% |
| regime: trending (ADX 25+) | 13919 | 36.3% | 49.1% | 41.5% |

## Most useful features (LightGBM gain, model trained on the development period)

- 10 min: mins_since_open 13%, vol_6 10%, mins_to_close 7%, vol_24 6%, atr_pct 4%, range_vs_atr 3%, gap 3%, bb_width_rank 3%, cum_rvol 2%, vol_trend 2%
- 15 min: mins_since_open 11%, vol_6 9%, vol_24 7%, mins_to_close 7%, atr_pct 4%, gap 3%, prev_5d_ret 3%, prev_day_ret 3%, cum_rvol 3%, range_vs_atr 3%
- 30 min: vol_6 12%, mins_since_open 10%, vol_24 10%, mins_to_close 6%, gap 6%, prev_day_ret 5%, prev_5d_ret 5%, atr_pct 4%, cum_rvol 4%, dist_prev_high 3%
- 60 min: mins_since_open 11%, vol_24 9%, vol_6 9%, prev_5d_ret 8%, prev_day_ret 7%, gap 7%, mins_to_close 5%, cum_rvol 5%, atr_pct 5%, bb_width_rank 4%
- 120 min: prev_5d_ret 14%, gap 13%, prev_day_ret 12%, vol_6 6%, cum_rvol 6%, vol_24 6%, ret_since_open 4%, dist_prev_low 4%, mins_since_open 4%, ret_vs_prev_close 4%
