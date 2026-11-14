# Range cone: how far price travels in the next 15 to 120 minutes

Share of future closes that landed inside the cone. Targets are 50% and 80%.
Skill is how much lower the model's quantile loss is than a cone of one fixed width (in typical-move units).

| Period | Horizon | Inside 50% cone | Inside 80% cone | Skill vs fixed, 80% | Narrow third: cover / width | Wide third: cover / width |
|---|---|---|---|---|---|---|
| Walk-forward | 15 min | 50.3% | 80.2% | 11.6% | 80.3% at 0.71x | 80.1% at 1.41x |
| Walk-forward | 30 min | 50.0% | 80.2% | 9.8% | 80.3% at 0.73x | 79.3% at 1.36x |
| Walk-forward | 60 min | 49.7% | 79.9% | 7.8% | 79.6% at 0.75x | 78.8% at 1.31x |
| Walk-forward | 120 min | 49.3% | 79.9% | 3.7% | 78.7% at 0.79x | 79.8% at 1.24x |
| Final held-out | 15 min | 54.5% | 84.2% | 12.1% | 84.3% at 0.74x | 83.3% at 1.50x |
| Final held-out | 30 min | 55.1% | 84.7% | 9.3% | 84.1% at 0.76x | 84.4% at 1.50x |
| Final held-out | 60 min | 54.4% | 84.3% | 8.6% | 82.4% at 0.78x | 83.4% at 1.47x |
| Final held-out | 120 min | 51.5% | 82.2% | 7.6% | 83.1% at 0.81x | 80.2% at 1.33x |

A fixed-width cone, scored on the same thirds (final held-out, 60 min): narrow 91.6%, wide 66.5%. It is too wide when the market is quiet and too narrow when it is busy.

## Opening cone (made at the close, for the next session)

| Period | Minutes after the open | Inside 50% cone | Inside 80% cone | Sessions |
|---|---|---|---|---|
| Walk-forward | 5 | 51.1% | 81.8% | 440 |
| Walk-forward | 15 | 53.8% | 80.6% | 448 |
| Walk-forward | 30 | 53.9% | 76.4% | 449 |
| Walk-forward | 60 | 52.6% | 78.5% | 447 |
| Walk-forward | 120 | 57.2% | 77.3% | 449 |
| Final held-out | 5 | 44.1% | 67.8% | 118 |
| Final held-out | 15 | 47.9% | 76.9% | 121 |
| Final held-out | 30 | 47.5% | 73.8% | 122 |
| Final held-out | 60 | 47.5% | 78.7% | 122 |
| Final held-out | 120 | 51.6% | 77.9% | 122 |
