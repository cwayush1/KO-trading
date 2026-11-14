"""Pre-market day outlook: will today's regular session close above its open?

The forecast is meant to be made before the 09:30 New York open, so every
feature for day D is built from sessions up to D-1 only. Today's open, gap and
candles are NOT used: an hour before the bell they do not exist yet.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def daily_bars(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("session", sort=True)
    d = g.agg(date=("date", "first"), open=("open", "first"), high=("high", "max"), low=("low", "min"),
              close=("close", "last"), volume=("volume", "sum"), bars=("bar", "size"))
    last_hour = df[df["slot"] >= 66].groupby("session").agg(lh_open=("open", "first"), lh_close=("close", "last"))
    first_hour = df[df["slot"] < 12].groupby("session").agg(fh_open=("open", "first"), fh_close=("close", "last"))
    return d.join(last_hour).join(first_hour)


def daily_state(d: pd.DataFrame) -> pd.DataFrame:
    """Features describing the market as of the END of each session (row k = known after day k closes)."""
    o, h, l, c, v = d["open"], d["high"], d["low"], d["close"], d["volume"].astype(float)
    ret = np.log(c / c.shift(1))                       # close to close
    intraday = np.log(c / o)                           # open to close: the "day candle"
    gap = np.log(o / c.shift(1))
    vol20 = ret.rolling(20).std()
    F: dict[str, pd.Series] = {}
    for k in (1, 2, 3, 5, 10, 20):
        F[f"ret_{k}d"] = ret.rolling(k).sum() / (vol20 * np.sqrt(k))
    F["candle_1d"] = intraday / vol20
    F["candle_3d"] = intraday.rolling(3).sum() / vol20
    F["gap_1d"] = gap / vol20
    F["up_streak"] = (intraday > 0).astype(float).groupby((intraday <= 0).cumsum()).cumsum()
    F["down_streak"] = (intraday < 0).astype(float).groupby((intraday >= 0).cumsum()).cumsum()
    for n in (5, 10, 20, 50):
        F[f"vs_sma{n}"] = (c / c.rolling(n).mean() - 1) / vol20
    delta = c.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    dn = (-delta).clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    F["rsi14"] = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    F["close_in_range"] = (c - l) / (h - l).replace(0, np.nan)        # where the last close sat in its day
    F["range_vs_avg"] = ((h - l) / c) / ((h - l) / c).rolling(20).mean()
    F["vol_5_vs_20"] = ret.rolling(5).std() / vol20
    F["volume_vs_avg"] = v / v.rolling(20).mean()
    F["last_hour_ret"] = np.log(d["lh_close"] / d["lh_open"]) / vol20
    F["first_hour_ret"] = np.log(d["fh_close"] / d["fh_open"]) / vol20
    F["pos_in_20d_range"] = (c - l.rolling(20).min()) / (h.rolling(20).max() - l.rolling(20).min())
    return pd.DataFrame(F).replace([np.inf, -np.inf], np.nan)


def build_daily_features(d: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    feats = daily_state(d).shift(1)                    # day D sees only days up to D-1
    feats["day_of_week"] = pd.to_datetime(d["date"]).dt.dayofweek.astype(float)   # known in advance
    out = pd.concat([d, feats], axis=1)
    out["y"] = (d["close"] > d["open"]).astype(int)    # 1 = green day candle
    out["day_ret"] = np.log(d["close"] / d["open"])
    return out, list(feats.columns)
