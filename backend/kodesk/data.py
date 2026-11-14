"""Load and validate 5-minute candles. Times are New York wall-clock (naive)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .config import BAR_MIN, DATA_CSV


def load_candles(path: Path | str = DATA_CSV) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%d %H:%M")
    df = df.sort_values("time").drop_duplicates("time").reset_index(drop=True)

    tod = df["time"].dt.hour * 60 + df["time"].dt.minute
    ok = (
        (df["time"].dt.minute % BAR_MIN == 0)                 # on the 5-minute grid
        & (tod >= 9 * 60 + 30) & (tod < 16 * 60)              # regular hours only
        & (df["high"] >= df[["open", "close"]].max(axis=1))   # coherent candle
        & (df["low"] <= df[["open", "close"]].min(axis=1))
        & (df["low"] > 0) & (df["volume"] >= 0)
        & np.isfinite(df[["open", "high", "low", "close", "volume"]]).all(axis=1)
    )
    df = df[ok].reset_index(drop=True)

    df["date"] = df["time"].dt.normalize()
    df["session"] = pd.factorize(df["date"])[0]               # 0, 1, 2 ... per trading day
    df["bar"] = df.groupby("session").cumcount()              # position within the day
    df["slot"] = ((df["time"].dt.hour * 60 + df["time"].dt.minute) - (9 * 60 + 30)) // BAR_MIN
    return df


def describe(df: pd.DataFrame) -> dict:
    per_day = df.groupby("session").size()
    return {
        "candles": int(len(df)),
        "sessions": int(df["session"].nunique()),
        "first": str(df["time"].iloc[0]),
        "last": str(df["time"].iloc[-1]),
        "full_days_78": int((per_day == 78).sum()),
        "days_missing_1_to_3_candles": int(((per_day < 78) & (per_day >= 75)).sum()),
        "short_days_under_75": int((per_day < 75).sum()),
    }
