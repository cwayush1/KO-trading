"""Bring the candle file up to date from Alpaca.

    python update_data.py           # add sessions after the last complete one in the file
    python update_data.py --full    # re-download everything from 2023-01-03 (then retrain)
    python update_data.py --from-csv newer_export.csv   # no Alpaca call: use a file you exported

Keys are read from the environment, or from a file named `.env` next to this script:
    APCA_API_KEY_ID=...
    APCA_API_SECRET_KEY=...
Optional: ALPACA_FEED=sip or iex (default: the best feed your plan allows).
Prices are requested split- and dividend-adjusted, to match the existing file.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from kodesk.config import BAR_MIN, DATA_CSV

URL = "https://data.alpaca.markets/v2/stocks/KO/bars"
FIRST_DAY = "2023-01-03"
NY = "America/New_York"


class UpdateError(RuntimeError):
    pass


def load_keys() -> tuple[str, str]:
    env = Path(__file__).with_name(".env")
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    key, secret = os.environ.get("APCA_API_KEY_ID"), os.environ.get("APCA_API_SECRET_KEY")
    if not key or not secret:
        raise UpdateError("Alpaca keys not found. Set APCA_API_KEY_ID and APCA_API_SECRET_KEY (see update_data.py).")
    return key, secret


def fetch_bars(start: str) -> list[dict]:
    """All 5-minute KO bars from `start` (YYYY-MM-DD) to now, following pagination."""
    key, secret = load_keys()
    params = {"timeframe": "5Min", "start": f"{start}T00:00:00Z", "adjustment": "all", "limit": "10000", "sort": "asc"}
    if os.environ.get("ALPACA_FEED"):
        params["feed"] = os.environ["ALPACA_FEED"]
    bars: list[dict] = []
    token = None
    while True:
        q = dict(params, **({"page_token": token} if token else {}))
        req = urllib.request.Request(f"{URL}?{urllib.parse.urlencode(q)}",
                                     headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret, "accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raise UpdateError(f"Alpaca answered {e.code}: {e.read().decode()[:200]}") from e
        except (urllib.error.URLError, TimeoutError, OSError):
            raise UpdateError("Could not connect to data.alpaca.markets (timed out). Check that this network or a firewall "
                              "is not blocking it, or use: python update_data.py --from-csv yourfile.csv")
        bars += body.get("bars") or []
        token = body.get("next_page_token")
        if not token:
            return bars


def to_frame(bars: list[dict], now_utc: datetime | None = None) -> pd.DataFrame:
    """Alpaca bars (UTC) -> our layout: New York wall-clock time, regular hours, finished candles only."""
    if not bars:
        return pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])
    d = pd.DataFrame(bars)
    t_utc = pd.to_datetime(d["t"], utc=True)
    now_utc = now_utc or datetime.now(timezone.utc)
    done = t_utc + pd.Timedelta(minutes=BAR_MIN) <= pd.Timestamp(now_utc)        # drop the candle still forming
    t = t_utc.dt.tz_convert(NY).dt.tz_localize(None)                             # handles daylight saving
    mins = t.dt.hour * 60 + t.dt.minute
    keep = done & (mins >= 9 * 60 + 30) & (mins < 16 * 60) & (t.dt.minute % BAR_MIN == 0) & (t.dt.dayofweek < 5)
    out = pd.DataFrame({"time": t, "open": d["o"], "high": d["h"], "low": d["l"], "close": d["c"], "volume": d["v"]})[keep]
    return out.drop_duplicates("time").sort_values("time").reset_index(drop=True)


def merge(old: pd.DataFrame, new: pd.DataFrame, full: bool) -> tuple[pd.DataFrame, dict]:
    """Old history + new download. The last session in the old file is replaced, since it may be partial."""
    info: dict = {"warnings": []}
    if full or old.empty:
        return new, info
    last_day = old["time"].iloc[-1].normalize()
    keep_old = old[old["time"] < last_day]
    overlap = keep_old.merge(new, on="time", suffixes=("_old", "_new"))
    if len(overlap) < 50:
        raise UpdateError("Too little overlap with the existing file to check consistency. Run: python update_data.py --full")
    price_gap = float((overlap["close_new"] / overlap["close_old"] - 1).abs().median())
    vol_ratio = float((overlap["volume_new"].sum() + 1) / (overlap["volume_old"].sum() + 1))
    info.update(overlap_candles=int(len(overlap)), price_gap=price_gap, volume_ratio=vol_ratio)
    if price_gap > 0.001:
        raise UpdateError(f"Downloaded prices differ from the file by {price_gap:.2%} on the same candles (a new dividend adjustment "
                          "or a different data source). Appending would put a false jump in the history. Run: python update_data.py --full")
    if not 0.5 <= vol_ratio <= 2.0:
        raise UpdateError(f"Downloaded volume is {vol_ratio:.1f}x the file's on the same candles (different data feed). "
                          "Run: python update_data.py --full, or set ALPACA_FEED to match the original.")
    return pd.concat([keep_old, new[new["time"] >= last_day]], ignore_index=True), info


def read_export(csv_path: str) -> pd.DataFrame:
    """A candle file you exported yourself. Accepts the original layout
    (Datetime as DD-MM-YYYY HH:MM, Open, High, Low, Close, Volume) or this project's own layout.
    Times must already be New York time."""
    raw = pd.read_csv(csv_path)                       # .csv or .csv.gz
    raw.columns = [c.strip().lower() for c in raw.columns]
    tcol = "datetime" if "datetime" in raw.columns else "time"
    if tcol not in raw.columns or not {"open", "high", "low", "close", "volume"} <= set(raw.columns):
        raise UpdateError("That file needs columns: Datetime (or time), Open, High, Low, Close, Volume.")
    first = str(raw[tcol].iloc[0])
    fmt = "%d-%m-%Y %H:%M" if first[2] == "-" else "%Y-%m-%d %H:%M"
    t = pd.to_datetime(raw[tcol], format=fmt)
    mins = t.dt.hour * 60 + t.dt.minute
    keep = (mins >= 9 * 60 + 30) & (mins < 16 * 60) & (t.dt.minute % BAR_MIN == 0) & (raw["volume"] > 0)
    out = pd.DataFrame({"time": t, "open": raw["open"], "high": raw["high"], "low": raw["low"], "close": raw["close"], "volume": raw["volume"]})[keep]
    return out.drop_duplicates("time").sort_values("time").reset_index(drop=True)


def update(full: bool = False, path: Path = DATA_CSV, fetch=fetch_bars, from_csv: str | None = None) -> dict:
    old = pd.read_csv(path)
    old["time"] = pd.to_datetime(old["time"], format="%Y-%m-%d %H:%M")
    start = FIRST_DAY if full else (old["time"].iloc[-1].normalize() - timedelta(days=10)).strftime("%Y-%m-%d")
    if from_csv:
        new = read_export(from_csv)
        full = full or new["time"].iloc[0] <= old["time"].iloc[0]      # a complete export replaces the history
        if not full:
            new = new[new["time"] >= pd.Timestamp(start)]
    else:
        new = to_frame(fetch(start))
    if new.empty:
        raise UpdateError("No candles found in the download.")
    merged, info = merge(old, new, full)
    bad = (merged["high"] < merged[["open", "close"]].max(axis=1)) | (merged["low"] > merged[["open", "close"]].min(axis=1)) | ~np.isfinite(merged["close"])
    merged = merged[~bad]
    backup = path.with_name("ko_5min.before_update.csv")
    if not backup.exists():
        shutil.copy(path, backup)                                    # the file as it was before the first update
    tmp = path.with_suffix(".tmp")
    out = merged.copy()
    out["time"] = out["time"].dt.strftime("%Y-%m-%d %H:%M")
    out["volume"] = out["volume"].round().astype("int64")
    out.to_csv(tmp, index=False)
    os.replace(tmp, path)
    info.update(candles=int(len(merged)), added=int(len(merged) - len(old)), last_candle=str(merged["time"].iloc[-1]), full=full)
    return info


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--from-csv", help="use a candle file you exported yourself instead of calling Alpaca")
    a = ap.parse_args()
    try:
        r = update(full=a.full, from_csv=a.from_csv)
    except UpdateError as e:
        raise SystemExit(f"Update stopped: {e}")
    print(f"{r['candles']} candles, {r['added']:+d} vs before, last candle {r['last_candle']} New York time")
    if a.full:
        print("History was rebuilt. Retrain: python train_final.py")
