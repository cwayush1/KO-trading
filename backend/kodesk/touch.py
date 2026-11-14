"""Touch ladder: how likely price is to TOUCH a given level within the next 30, 60 or 120 minutes.

The range cone is about where a window closes. Traders place targets and stops,
and those fill on a touch at any moment inside the window, so this model works
on the highest high and lowest low of the window instead of its close.

For each window it predicts the distance that price reaches with a 75%, 50%, 25%
and 10% chance. Up and down are fitted separately and then averaged into one
distance per level: ladders that gave one side more room were tested and picked
the side with more travel only 50% of the time, so the lopsidedness was noise.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .cone import _fit_quantile
from .config import BAR_MIN

WINDOWS = {30: 6, 60: 12, 120: 24}            # minutes -> candles
ODDS = (0.75, 0.5, 0.25, 0.1)                 # chance that the level is touched inside the window
SIDES = ("up", "down")


def add_touch_labels(frame: pd.DataFrame) -> pd.DataFrame:
    """up_<m> / down_<m>: furthest price travelled above / below the current close during the
    next m minutes, in typical-move units (sigma * sqrt(candles)). Never negative.
    NaN when the window leaves the session or hits a hole."""
    d = frame.copy()
    c = d["close"]
    for minutes, bars in WINDOWS.items():
        valid = (d["time"].shift(-bars) - d["time"]) == pd.Timedelta(minutes=bars * BAR_MIN)
        hi = d["high"][::-1].rolling(bars).max()[::-1].shift(-1)       # highest high of the next `bars` candles
        lo = d["low"][::-1].rolling(bars).min()[::-1].shift(-1)
        unit = d["sigma"] * np.sqrt(bars)
        d[f"up_{minutes}"] = (np.log(hi / c).clip(lower=0) / unit).where(valid)
        d[f"down_{minutes}"] = (np.log(c / lo).clip(lower=0) / unit).where(valid)
    return d


def train_touch(d: pd.DataFrame, feats: list[str], val_start: int, train_end: int) -> dict:
    """One quantile model per window, side and odds level, each rescaled by one number on the
    validation tail so that the level is touched as often as its label says."""
    models, usual = {}, {}
    for minutes in WINDOWS:
        for side in SIDES:
            col = f"{side}_{minutes}"
            r = d[d[col].notna()].dropna(subset=feats)
            tr, va = r[r.session < val_start], r[(r.session >= val_start) & (r.session < train_end)]
            Xtr, Xva = tr[feats].to_numpy("float32"), va[feats].to_numpy("float32")
            ytr, yva = tr[col].to_numpy(), va[col].to_numpy()
            for odds in ODDS:
                q = 1 - odds                                           # touched with chance `odds` = the (1 - odds) quantile
                m = _fit_quantile(Xtr, ytr, Xva, yva, q)
                pred = np.maximum(m.predict(Xva), 1e-6)
                models[(minutes, side, odds)] = {"model": m, "scale": float(np.quantile(yva / pred, q))}
                usual[(minutes, side, odds)] = float(np.quantile(np.concatenate([ytr, yva]), q))
    return {"models": models, "features": feats, "usual": usual}


def touch_z(touch: dict, X) -> dict:
    """Distance in typical-move units for every (minutes, odds): the same above and below
    the current price, and widening as the odds fall."""
    raw = {k: np.maximum(v["model"].predict(X), 1e-6) * v["scale"] for k, v in touch["models"].items()}
    z = {(m, o): (raw[(m, "up", o)] + raw[(m, "down", o)]) / 2 for m in WINDOWS for o in ODDS}
    for m in WINDOWS:                                                   # separate models can cross; keep the ladder ordered
        for a, b in zip(ODDS[:-1], ODDS[1:]):
            z[(m, b)] = np.maximum(z[(m, b)], z[(m, a)] * 1.0001)
    return z


def usual_z(touch: dict) -> dict:
    return {(m, o): (touch["usual"][(m, "up", o)] + touch["usual"][(m, "down", o)]) / 2 for m in WINDOWS for o in ODDS}
