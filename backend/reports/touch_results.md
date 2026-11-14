# Touch ladder: chance that price touches a level inside the window

Each cell is how often levels with that label were really touched (up side / down side). It should match the label.

| Period | Window | Labelled 75% | Labelled 50% | Labelled 25% | Labelled 10% | Skill vs fixed distance (50%) |
|---|---|---|---|---|---|---|
| Walk-forward | 30 min | 75.8% / 74.5% | 50.5% / 49.5% | 25.0% / 25.1% | 9.7% / 10.0% | 4.3% |
| Walk-forward | 60 min | 75.8% / 74.7% | 50.2% / 49.5% | 24.8% / 25.2% | 9.9% / 10.4% | 3.1% |
| Walk-forward | 120 min | 75.5% / 74.6% | 50.3% / 50.0% | 24.9% / 25.3% | 9.6% / 10.0% | 1.7% |
| Final held-out | 30 min | 71.6% / 73.7% | 45.8% / 48.3% | 20.6% / 22.0% | 7.0% / 7.7% | 4.8% |
| Final held-out | 60 min | 71.8% / 73.3% | 45.1% / 47.5% | 20.6% / 22.1% | 6.5% / 7.9% | 3.4% |
| Final held-out | 120 min | 70.9% / 73.3% | 44.7% / 47.3% | 20.7% / 23.3% | 7.9% / 8.9% | 1.9% |

## Does the ladder stretch at the right times?

Moments split into thirds by how far out the model put its 25% level. Each should still be touched about 25% of the time.

| Period | Window | Near third: touched / distance | Far third: touched / distance | Fixed distance: near / far |
|---|---|---|---|---|
| Walk-forward | 30 min | 24.1% at 0.76x | 26.3% at 1.40x | 13.6% / 40.0% |
| Walk-forward | 60 min | 24.8% at 0.80x | 26.3% at 1.31x | 15.4% / 37.5% |
| Walk-forward | 120 min | 25.0% at 0.84x | 27.2% at 1.19x | 17.7% / 34.8% |
| Final held-out | 30 min | 20.6% at 0.79x | 22.9% at 1.54x | 11.9% / 40.9% |
| Final held-out | 60 min | 20.3% at 0.85x | 24.0% at 1.42x | 13.7% / 38.7% |
| Final held-out | 120 min | 20.8% at 0.89x | 26.2% at 1.25x | 16.6% / 36.0% |
