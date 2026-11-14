"""Forecast targets: UP / NEUTRAL / DOWN over several horizons.

For a forecast made at the close of candle t with horizon H candles:
  fwd = log(close[t+H] / close[t])
  UP      if fwd >  K * sigma_t * sqrt(H)
  DOWN    if fwd < -K * sigma_t * sqrt(H)
  NEUTRAL otherwise
sigma_t is the typical 5-minute move known at time t, so the "too small to
matter" band widens in volatile markets and narrows in calm ones.
A target never crosses the closing bell: rows too close to the end of the
session (or next to a missing candle) get no label and are dropped.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import BAR_MIN, HORIZONS, K_NEUTRAL


def add_targets(d: pd.DataFrame, k: float = K_NEUTRAL) -> pd.DataFrame:
    d = d.copy()
    for minutes, bars in HORIZONS.items():
        future_time = d["time"].shift(-bars)
        valid = (future_time - d["time"]) == pd.Timedelta(minutes=bars * BAR_MIN)   # same day, no hole
        fwd = np.log(d["close"].shift(-bars) / d["close"]).where(valid)
        thr = k * d["sigma"] * np.sqrt(bars)
        y = pd.Series(1.0, index=d.index)             # NEUTRAL
        y[fwd > thr] = 2.0                            # UP
        y[fwd < -thr] = 0.0                           # DOWN
        d[f"fwd_{minutes}"] = fwd
        d[f"y_{minutes}"] = y.where(valid & thr.notna())
    return d
