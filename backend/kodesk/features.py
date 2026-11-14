"""Feature engineering.

Rule for every column: the value on row t uses candles up to and including t,
never later ones. Row t is "known" when candle t closes, and that close is the
price a forecast is made from. tests/test_no_leakage.py checks this by
truncating the data and confirming past feature values do not change.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import BARS_PER_DAY, VOL_SPAN_BARS


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def _wilder(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Returns (frame with feature columns added, list of feature names)."""
    d = df.copy()
    g = d.groupby("session", sort=False)
    o, h, l, c, v = d["open"], d["high"], d["low"], d["close"], d["volume"].astype(float)
    first = d["bar"] == 0
    F: dict[str, pd.Series] = {}

    # ---- Returns. The overnight gap is its own feature, never a 5-minute return.
    prev_c = c.shift(1)
    ret1 = np.log(c / prev_c.where(~first, o))          # first candle: open -> close
    d["ret1"] = ret1
    cum = ret1.groupby(d["session"]).cumsum()            # return since today's open
    d["_cum"] = cum
    for k in (3, 6, 12, 24):
        F[f"ret_{k}"] = cum - g["_cum"].shift(k).fillna(0.0)   # capped at today's open
    F["ret_1"] = ret1
    F["ret_since_open"] = cum

    # ---- Volatility scale used to normalise distances.
    sigma = np.sqrt((ret1**2).ewm(span=VOL_SPAN_BARS, adjust=False, min_periods=BARS_PER_DAY * 5).mean())
    d["sigma"] = sigma                                   # typical 5-minute log move
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    tr = tr.where(~first, h - l)                         # no overnight gap inside true range
    atr = _wilder(tr, 14)
    F["atr_pct"] = atr / c
    F["vol_6"] = ret1.rolling(6).std() / sigma
    F["vol_24"] = ret1.rolling(24).std() / sigma
    F["vol_trend"] = F["vol_6"] / F["vol_24"]
    F["range_vs_atr"] = (h - l) / atr

    # ---- Candle shape.
    rng = (h - l).replace(0, np.nan)
    F["body"] = (c - o) / rng
    F["upper_wick"] = (h - np.maximum(o, c)) / rng
    F["lower_wick"] = (np.minimum(o, c) - l) / rng

    # ---- Trend.
    e9, e20, e50 = _ema(c, 9), _ema(c, 20), _ema(c, 50)
    F["dist_ema9"] = (c - e9) / atr
    F["dist_ema20"] = (c - e20) / atr
    F["dist_ema50"] = (c - e50) / atr
    F["ema9_vs_20"] = (e9 - e20) / atr
    F["ema20_vs_50"] = (e20 - e50) / atr
    F["ema20_slope"] = (e20 - e20.shift(3)) / atr
    up, dn = h.diff(), -l.diff()
    pdm = up.where((up > dn) & (up > 0), 0.0)
    mdm = dn.where((dn > up) & (dn > 0), 0.0)
    pdi, mdi = _wilder(pdm, 14) / atr, _wilder(mdm, 14) / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    F["adx"] = _wilder(dx.fillna(0), 14)
    F["di_diff"] = pdi - mdi

    # ---- VWAP (restarts each session).
    tp = (h + l + c) / 3
    vwap = (tp * v).groupby(d["session"]).cumsum() / v.groupby(d["session"]).cumsum().replace(0, np.nan)
    F["dist_vwap"] = (c - vwap) / atr

    # ---- Momentum.
    delta = c.diff()
    rs = _wilder(delta.clip(lower=0), 14) / _wilder((-delta).clip(lower=0), 14).replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    F["rsi"] = rsi
    F["rsi_change"] = rsi - rsi.shift(3)
    macd = _ema(c, 12) - _ema(c, 26)
    hist = macd - macd.ewm(span=9, adjust=False, min_periods=9).mean()
    F["macd_hist"] = hist / atr
    F["macd_hist_change"] = (hist - hist.shift(2)) / atr
    lo14, hi14 = l.rolling(14).min(), h.rolling(14).max()
    F["stoch"] = (c - lo14) / (hi14 - lo14).replace(0, np.nan)

    # ---- Bollinger.
    mid, sd = c.rolling(20).mean(), c.rolling(20).std(ddof=0)
    F["bb_pos"] = (c - mid) / (2 * sd).replace(0, np.nan)
    width = 4 * sd / mid
    F["bb_width_rank"] = width.rolling(BARS_PER_DAY * 5).rank(pct=True)

    # ---- Volume, compared with the same time of day on earlier sessions.
    slot_mean = d.groupby("slot")["volume"].transform(lambda s: s.shift(1).rolling(20, min_periods=5).mean())
    F["rvol"] = v / slot_mean.replace(0, np.nan)
    cumv = v.groupby(d["session"]).cumsum()
    d["_cumv"] = cumv
    slot_cum = d.groupby("slot")["_cumv"].transform(lambda s: s.shift(1).rolling(20, min_periods=5).mean())
    F["cum_rvol"] = cumv / slot_cum.replace(0, np.nan)
    F["vol_change"] = np.log1p(v) - np.log1p(v.rolling(6).mean())
    F["signed_volume"] = (np.sign(ret1) * F["rvol"]).rolling(6).mean()   # crude pressure proxy

    # ---- Where price sits in today's and yesterday's range.
    day_hi, day_lo = g["high"].cummax(), g["low"].cummin()
    F["pos_in_day"] = (c - day_lo) / (day_hi - day_lo).replace(0, np.nan)
    daily = d.groupby("session").agg(dh=("high", "max"), dl=("low", "min"), dc=("close", "last"), do=("open", "first"))
    prev = daily.shift(1)                                 # only finished sessions
    ph, pl, pc = (d["session"].map(prev[k]) for k in ("dh", "dl", "dc"))
    F["dist_prev_high"] = (c - ph) / atr
    F["dist_prev_low"] = (c - pl) / atr
    F["gap"] = np.log(d["session"].map(daily["do"]) / pc) / (sigma * np.sqrt(BARS_PER_DAY))
    F["ret_vs_prev_close"] = np.log(c / pc) / (sigma * np.sqrt(BARS_PER_DAY))
    dret = np.log(daily["dc"] / daily["dc"].shift(1))
    F["prev_day_ret"] = d["session"].map(dret.shift(1))
    F["prev_5d_ret"] = d["session"].map(dret.rolling(5).sum().shift(1))

    # Scale the plain returns by the typical move so they mean the same in calm and busy markets.
    for k in (1, 3, 6, 12, 24):
        F[f"ret_{k}"] = F[f"ret_{k}"] / (sigma * np.sqrt(k))
    F["ret_since_open"] = F["ret_since_open"] / (sigma * np.sqrt(BARS_PER_DAY))

    # ---- Clock.
    F["mins_since_open"] = d["slot"] * 5.0
    F["mins_to_close"] = (BARS_PER_DAY - 1 - d["slot"]) * 5.0
    F["day_of_week"] = d["time"].dt.dayofweek.astype(float)

    feats = pd.DataFrame(F, index=d.index).replace([np.inf, -np.inf], np.nan)
    out = pd.concat([d.drop(columns=["_cum", "_cumv"]), feats], axis=1)
    return out, list(feats.columns)
