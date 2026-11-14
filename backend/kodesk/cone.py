"""Range cone: how far price is likely to travel over the next 15 to 120 minutes.

Direction on this data is close to a coin flip, but the SIZE of the coming move
is forecastable. So the cone is centred on the current price and only its width
is modelled: for each horizon, a half-width that should contain the future close
50% of the time and a wider one for 80% of the time.

Inside a session the half-widths come from LightGBM quantile models on the
leak-free candle features. After the last candle of a session the cone covers
the first two hours of the NEXT session (overnight gap included), sized from
the last 20 days of daily volatility.
"""
from __future__ import annotations

import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd

from .config import BAR_MIN, BARS_PER_DAY

CONE = {15: 3, 30: 6, 60: 12, 120: 24}        # minutes ahead -> candles ahead, inside a session
OPENING = {5: 0, 15: 2, 30: 5, 60: 11, 120: 23}   # minutes after the next open -> slot whose close is used
LEVELS = (0.5, 0.8)


def add_cone_labels(frame: pd.DataFrame) -> pd.DataFrame:
    """z_<minutes> = size of the move over that horizon in units of the typical move
    known now (sigma * sqrt(candles)). NaN when the horizon leaves the session or hits a hole."""
    d = frame.copy()
    for minutes, bars in CONE.items():
        valid = (d["time"].shift(-bars) - d["time"]) == pd.Timedelta(minutes=bars * BAR_MIN)
        fwd = np.log(d["close"].shift(-bars) / d["close"]).where(valid)
        d[f"z_{minutes}"] = fwd.abs() / (d["sigma"] * np.sqrt(bars))
    return d


def _fit_quantile(Xtr, ytr, Xva, yva, level: float):
    m = lgb.LGBMRegressor(objective="quantile", alpha=level, n_estimators=400, learning_rate=0.03, num_leaves=15,
                          min_child_samples=200, subsample=0.8, subsample_freq=1, colsample_bytree=0.7, reg_lambda=5,
                          random_state=7, verbose=-1, n_jobs=2)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m.fit(Xtr, ytr, eval_set=[(Xva, yva)], callbacks=[lgb.early_stopping(40, verbose=False)])
    return m


def train_cone(d: pd.DataFrame, feats: list[str], val_start: int, train_end: int) -> dict:
    """One quantile model per horizon and level, trained on sessions before `val_start`.
    Each is then rescaled by one number so that it covers exactly its level on the
    validation tail [val_start, train_end) (split conformal calibration)."""
    models, base = {}, {}
    for minutes in CONE:
        r = d[d[f"z_{minutes}"].notna()].dropna(subset=feats)
        tr, va = r[r.session < val_start], r[(r.session >= val_start) & (r.session < train_end)]
        Xtr, Xva = tr[feats].to_numpy("float32"), va[feats].to_numpy("float32")
        ztr, zva = tr[f"z_{minutes}"].to_numpy(), va[f"z_{minutes}"].to_numpy()
        for level in LEVELS:
            m = _fit_quantile(Xtr, ztr, Xva, zva, level)
            pred = np.maximum(m.predict(Xva), 1e-6)
            models[(minutes, level)] = {"model": m, "scale": float(np.quantile(zva / pred, level))}
            base[(minutes, level)] = float(np.quantile(np.concatenate([ztr, zva]), level))   # same width at every moment
    return {"models": models, "features": feats, "usual": base}


def cone_z(cone: dict, X) -> dict:
    """Half-widths in typical-move units for every (minutes, level)."""
    return {k: np.maximum(v["model"].predict(X), 1e-6) * v["scale"] for k, v in cone["models"].items()}


# ---- After the close: the first two hours of the next session ------------------------------

def opening_table(candles: pd.DataFrame) -> pd.DataFrame:
    """One row per session with a full close: last close, 20-day daily volatility known at
    that close, and the size of the move to each early close of the following session."""
    c = candles
    last = c[c["slot"] == BARS_PER_DAY - 1].set_index("session")["close"]
    daily = c.groupby("session")["close"].last()
    vol20 = np.log(daily / daily.shift(1)).rolling(20).std()
    out = pd.DataFrame({"last": last, "vol20": vol20.reindex(last.index)})
    for minutes, slot in OPENING.items():
        nxt = c[c["slot"] == slot].set_index("session")["close"]
        nxt.index = nxt.index - 1                                   # line up with the session before it
        out[f"z_{minutes}"] = np.log(nxt.reindex(out.index) / out["last"]).abs() / out["vol20"]
    return out


def train_opening(table: pd.DataFrame, train_end: int) -> dict:
    t = table[table.index < train_end - 1]
    return {(m, lv): float(t[f"z_{m}"].dropna().quantile(lv)) for m in OPENING for lv in LEVELS}
