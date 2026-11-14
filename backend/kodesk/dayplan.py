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

SLOT_FEATS = [
    "slot", "slot_sin", "slot_cos",          # cyclic time encoding
    "slot_green_20", "slot_green_60",
    "slot_ret_20", "slot_ret_60",            # longer-window ret average per slot
    "slot_vol_20",                           # typical volatility at this time-of-day
    "slot_green_5",                          # very recent 5-session habit per slot
    "slot_streak",                           # consecutive green/red at this slot
]


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
        # Slot-level rolling windows
        self.g5  = self.green.rolling(5,  min_periods=3).mean()
        self.g20 = self.green.rolling(20, min_periods=10).mean()
        self.g60 = self.green.rolling(60, min_periods=30).mean()
        self.r20 = ret.rolling(20, min_periods=10).mean()
        self.r60 = ret.rolling(60, min_periods=30).mean()
        self.vol20 = ret.rolling(20, min_periods=10).std()
        # Consecutive streak at each slot (green=+1, red=-1 running count)
        self._streak = self._compute_streak(self.green)
        self.feats = self.state_feats + ["day_of_week"] + SLOT_FEATS
        self.dates = pd.to_datetime(self.days["date"])

    @staticmethod
    def _compute_streak(green: pd.DataFrame) -> pd.DataFrame:
        """For each slot column, running consecutive green (+) or red (-) streak."""
        result = pd.DataFrame(index=green.index, columns=green.columns, dtype=float)
        for col in green.columns:
            s = green[col]
            streak = np.zeros(len(s))
            for i in range(1, len(s)):
                if pd.isna(s.iloc[i - 1]):
                    streak[i] = 0.0
                elif s.iloc[i - 1] > 0.5:
                    streak[i] = max(streak[i - 1], 0) + 1
                else:
                    streak[i] = min(streak[i - 1], 0) - 1
            result[col] = streak
        return result

    def features_after(self, session: int, target_date: pd.Timestamp) -> pd.DataFrame:
        """78 feature rows for the session that follows `session` (which may not exist yet)."""
        base = self.state.loc[session]
        X = pd.DataFrame({f: np.full(BARS_PER_DAY, base[f]) for f in self.state_feats})
        X["day_of_week"] = float(target_date.dayofweek)
        slots = np.arange(BARS_PER_DAY, dtype=float)
        X["slot"] = slots
        # Cyclic encoding so model understands slot 0 and slot 77 are equally "edge"
        X["slot_sin"] = np.sin(2 * np.pi * slots / BARS_PER_DAY)
        X["slot_cos"] = np.cos(2 * np.pi * slots / BARS_PER_DAY)
        X["slot_green_5"]  = self.g5.loc[session].to_numpy()
        X["slot_green_20"] = self.g20.loc[session].to_numpy()
        X["slot_green_60"] = self.g60.loc[session].to_numpy()
        X["slot_ret_20"]   = self.r20.loc[session].to_numpy()
        X["slot_ret_60"]   = self.r60.loc[session].to_numpy()
        X["slot_vol_20"]   = self.vol20.loc[session].to_numpy()
        X["slot_streak"]   = self._streak.loc[session].to_numpy()
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
    # More trees, slightly more leaves, lower min_child to find slot-level patterns,
    # stronger L2 to prevent overfitting on the larger feature set.
    return lgb.LGBMClassifier(
        n_estimators=600, learning_rate=0.015, num_leaves=16,
        min_child_samples=200, subsample=0.8, subsample_freq=1,
        colsample_bytree=0.7, reg_lambda=15, reg_alpha=0.5,
        random_state=7, verbose=-1, n_jobs=2,
    )
