"""Day plan: before the open, call every 5-minute candle of the coming session green or red.

All 78 calls for day D are fixed before 09:30. They may use:
  - how earlier sessions went (daily features, as of the previous close),
  - how each time-of-day slot has behaved on earlier sessions,
  - the weekday and the slot's clock time.
They may not use anything from day D itself.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import BARS_PER_DAY
from .daily import daily_bars, daily_state

SLOT_FEATS = ["slot", "slot_green_20", "slot_green_60", "slot_ret_20"]


class PlanData:
    """Pre-computed tables. Row k of every table is 'known after session k closes'."""

    def __init__(self, candles: pd.DataFrame):
        self.candles = candles
        self.days = daily_bars(candles)                               # index = session number
        self.state = daily_state(self.days)
        self.state_feats = list(self.state.columns)
        c = candles[candles["slot"].between(0, BARS_PER_DAY - 1)]
        move = np.sign(c["close"] - c["open"])
        green = pd.Series(np.where(move == 0, np.nan, (move > 0).astype(float)), index=c.index)
        self.green = green.groupby([c["session"], c["slot"]]).first().unstack("slot").reindex(columns=range(BARS_PER_DAY))
        ret = (np.log(c["close"] / c["open"]) * 1e4).groupby([c["session"], c["slot"]]).first().unstack("slot").reindex(columns=range(BARS_PER_DAY))
        self.g20 = self.green.rolling(20, min_periods=10).mean()
        self.g60 = self.green.rolling(60, min_periods=30).mean()
        self.r20 = ret.rolling(20, min_periods=10).mean()
        self.feats = self.state_feats + ["day_of_week"] + SLOT_FEATS
        self.dates = pd.to_datetime(self.days["date"])

    def features_after(self, session: int, target_date: pd.Timestamp) -> pd.DataFrame:
        """78 feature rows for the session that follows `session` (which may not exist yet)."""
        base = self.state.loc[session]
        X = pd.DataFrame({f: np.full(BARS_PER_DAY, base[f]) for f in self.state_feats})
        X["day_of_week"] = float(target_date.dayofweek)
        X["slot"] = np.arange(BARS_PER_DAY, dtype=float)
        X["slot_green_20"] = self.g20.loc[session].to_numpy()
        X["slot_green_60"] = self.g60.loc[session].to_numpy()
        X["slot_ret_20"] = self.r20.loc[session].to_numpy()
        return X[self.feats]

    def training_frame(self) -> pd.DataFrame:
        """One row per (session, slot) with the label y = 1 for a green candle (flat candles dropped)."""
        parts = []
        for s in self.days.index[1:]:
            X = self.features_after(s - 1, self.dates.loc[s])
            X["session"] = s
            X["y"] = self.green.loc[s].to_numpy()
            parts.append(X)
        f = pd.concat(parts, ignore_index=True)
        return f[f["y"].notna() & f["vs_sma50"].notna() & f["slot_green_60"].notna()].reset_index(drop=True)


def make_plan_model():
    import lightgbm as lgb
    return lgb.LGBMClassifier(n_estimators=300, learning_rate=0.02, num_leaves=8, min_child_samples=400, subsample=0.7,
                              subsample_freq=1, colsample_bytree=0.6, reg_lambda=20, random_state=7, verbose=-1, n_jobs=2)
