"""Next-candle direction: will the 5-minute candle after this one close higher or lower?

Made at the close of candle t from candles up to and including t, for candle t+1
of the same session. This is the one direction question on this data where the
models beat a coin flip out of sample, and mostly on their most confident calls.
"""
from __future__ import annotations

import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
import xgboost as xgb

STRONG_QUANTILE = 0.90   # a call is "confident" when it is in the top 10% by distance from 50/50


def add_next_label(frame: pd.DataFrame) -> pd.DataFrame:
    """Adds `fwd_next`: log return of the following candle, NaN when the next row is
    another session or the grid has a gap. Uses the next row only to build the label."""
    d = frame.copy()
    same = d["session"].shift(-1) == d["session"]
    step = (d["time"].shift(-1) - d["time"]) == pd.Timedelta(minutes=5)
    d["fwd_next"] = np.where(same & step, np.log(d["close"].shift(-1) / d["close"]), np.nan)
    return d


def fit_ensemble(Xtr, ytr, Xva, yva) -> list:
    """LightGBM and XGBoost, both shallow, stopped early on the validation tail."""
    a = lgb.LGBMClassifier(n_estimators=600, learning_rate=0.02, num_leaves=15, min_child_samples=200, subsample=0.8,
                           subsample_freq=1, colsample_bytree=0.7, reg_lambda=5, random_state=7, verbose=-1, n_jobs=2)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")          # newer LightGBM renames eval_set; both spellings work
        a.fit(Xtr, ytr, eval_set=[(Xva, yva)], callbacks=[lgb.early_stopping(50, verbose=False)])
    b = xgb.XGBClassifier(n_estimators=600, learning_rate=0.02, max_depth=4, min_child_weight=100, subsample=0.8,
                          colsample_bytree=0.7, reg_lambda=5, early_stopping_rounds=50, random_state=7, verbosity=0, n_jobs=2)
    b.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
    return [a, b]


def predict_up(models: list, X) -> np.ndarray:
    return np.mean([m.predict_proba(X)[:, 1] for m in models], axis=0)


def train(d: pd.DataFrame, feats: list[str], val_start: int, train_end: int) -> dict:
    """Train on sessions before `val_start`, stop early and set the confidence
    threshold on [val_start, train_end). Flat candles carry no direction and are left out."""
    r = d[d["fwd_next"].notna() & (d["fwd_next"] != 0)].dropna(subset=feats)
    tr, va = r[r.session < val_start], r[(r.session >= val_start) & (r.session < train_end)]
    X = lambda x: x[feats].to_numpy("float32")
    y = lambda x: (x["fwd_next"].to_numpy() > 0).astype(int)
    models = fit_ensemble(X(tr), y(tr), X(va), y(va))
    threshold = float(np.quantile(np.abs(predict_up(models, X(va)) - 0.5), STRONG_QUANTILE))
    return {"models": models, "features": feats, "threshold": threshold, "rows": len(tr)}
