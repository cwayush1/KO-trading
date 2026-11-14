"""Load saved models and produce a forecast for one moment in time."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .cone import CONE, LEVELS, OPENING, add_cone_labels, cone_z
from .config import ARTIFACTS, BAR_MIN, BARS_PER_DAY, DATA_CSV, HORIZONS
from .daily import build_daily_features, daily_bars
from .data import load_candles
from .dayplan import PlanData
from .features import build_features
from .nextcandle import predict_up
from .touch import ODDS, WINDOWS, add_touch_labels, touch_z, usual_z

CLOSE_MIN = 16 * 60


class Forecaster:
    def __init__(self, bundle_path: Path | str = ARTIFACTS / "forecaster.joblib", data_path: Path | str = DATA_CSV):
        self.bundle = joblib.load(bundle_path)
        self.feats: list[str] = self.bundle["features"]
        self.trained_through = pd.Timestamp(self.bundle["trained_through"])
        self.data_path = Path(data_path)
        self.reload()

    def reload(self) -> None:
        """Recompute features from the candle file (call again after new candles arrive)."""
        candles = load_candles(self.data_path)
        frame, _ = build_features(candles)
        self.frame = frame.set_index("time", drop=False)
        nxt = self.bundle.get("next")
        if nxt:                                        # one pass over every candle; reused by all next-candle answers
            ok = self.frame[nxt["features"]].notna().all(axis=1).to_numpy()
            p = np.full(len(self.frame), np.nan)
            p[ok] = predict_up(nxt["models"], self.frame.loc[ok, nxt["features"]].to_numpy("float32"))
            self.frame["next_p"] = p
        days, _ = build_daily_features(daily_bars(candles))
        self.days = days.set_index("date", drop=False)
        self.plan = PlanData(candles)
        # Running records of the cone and the ladder. Scored once here for the sessions after
        # training; an older day is scored on request (see _record_for).
        oos = (self.frame["time"] > self.trained_through).to_numpy()
        if self.bundle.get("cone"):
            self._cone_lab = add_cone_labels(self.frame)
            self.cone_record = self._score_cone(oos)
        if self.bundle.get("touch"):
            self._touch_lab = add_touch_labels(self.frame)
            self.touch_record = self._score_touch(oos)
        daily_close = candles.groupby("session")["close"].last()
        self.vol20 = np.log(daily_close / daily_close.shift(1)).rolling(20).std()     # daily volatility, by session
        self._plan_cache: dict[int, np.ndarray] = {}

    def _score_cone(self, mask: np.ndarray) -> pd.DataFrame:
        """Each cone made on the masked rows against what price then did (NaN while unsettled)."""
        cone = self.bundle["cone"]
        ok = mask & self.frame[cone["features"]].notna().all(axis=1).to_numpy()
        rec = pd.DataFrame({"time": self.frame["time"].to_numpy()[ok]})
        if ok.any():
            z = cone_z(cone, self.frame.loc[ok, cone["features"]].to_numpy("float32"))
            for m in CONE:
                real = self._cone_lab[f"z_{m}"].to_numpy()[ok]
                for lv in LEVELS:
                    rec[f"in{int(lv * 100)}_{m}"] = np.where(np.isnan(real), np.nan, real <= z[(m, lv)])
        return rec

    def _score_touch(self, mask: np.ndarray) -> pd.DataFrame:
        """Each ladder made on the masked rows against the highs and lows that followed."""
        touch = self.bundle["touch"]
        ok = mask & self.frame[touch["features"]].notna().all(axis=1).to_numpy()
        rec = pd.DataFrame({"time": self.frame["time"].to_numpy()[ok]})
        if ok.any():
            z = touch_z(touch, self.frame.loc[ok, touch["features"]].to_numpy("float32"))
            for m in WINDOWS:
                up, down = self._touch_lab[f"up_{m}"].to_numpy()[ok], self._touch_lab[f"down_{m}"].to_numpy()[ok]
                rec[f"n_{m}"] = np.where(np.isnan(up), np.nan, 2.0)              # two levels per ladder: above and below
                for o in ODDS:
                    rec[f"t{int(o * 100)}_{m}"] = np.where(np.isnan(up), np.nan, (up >= z[(m, o)]).astype(float) + (down >= z[(m, o)]))
        return rec

    def _record_for(self, day: pd.Timestamp, kind: str) -> pd.DataFrame:
        """Scored rows of one session: from the stored record, or scored now for a day inside training."""
        rec = self.cone_record if kind == "cone" else self.touch_record
        if day > self.trained_through.normalize():
            return rec[rec["time"].dt.normalize() == day]
        mask = (self.frame["time"].dt.normalize() == day).to_numpy()
        return self._score_cone(mask) if kind == "cone" else self._score_touch(mask)

    # ---- Range cone: likely travel of price over the next two hours ----------------------
    def cone(self, asof: datetime) -> dict:
        """Cone made at the close of the candle that starts at `asof`. Inside a session it runs
        to at most two hours ahead and stops at the bell; once no horizon fits before the bell
        it covers the first two hours of the next session instead."""
        cone = self.bundle.get("cone")
        if not cone:
            raise KeyError("This model file has no range cone. Run: python train_final.py")
        ts = pd.Timestamp(asof)
        idx = self.frame.index.searchsorted(ts, side="right") - 1
        if idx < 0 or self.frame.iloc[idx]["time"].normalize() != ts.normalize():
            raise KeyError("No candle on that day at or before that time.")
        row = self.frame.iloc[idx]
        if not np.isfinite(row["sigma"]) or not np.isfinite(row[cone["features"]].to_numpy(float)).all():
            raise KeyError("Not enough history before that time to build features.")
        price, session = float(row["close"]), int(row["session"])
        candle_end = row["time"].hour * 60 + row["time"].minute + BAR_MIN
        fits = [m for m in CONE if candle_end + m <= CLOSE_MIN]

        if fits:
            kind = "session"
            z = cone_z(cone, row[cone["features"]].to_numpy("float32").reshape(1, -1))
            steps = [CONE[m] for m in fits]
            half = {lv: [float(z[(m, lv)][0] * row["sigma"] * np.sqrt(CONE[m])) for m in fits] for lv in LEVELS}
            # Every 5-minute step in between: widths grow with the square root of time.
            grid = np.arange(1, steps[-1] + 1)
            interp = {lv: np.interp(np.sqrt(grid), np.sqrt([0] + steps), [0.0] + half[lv]) for lv in LEVELS}
            times = [row["time"] + pd.Timedelta(minutes=BAR_MIN * int(j)) for j in grid]
            anchors = {m: CONE[m] - 1 for m in fits}
            ref = max(m for m in fits if m <= 60)
            vs_usual = float(z[(ref, 0.8)][0] / cone["usual"][(ref, 0.8)])
        else:
            kind = "opening"
            # Daily volatility known now: today's close only counts once the session has finished.
            vol = self.vol20.get(session if row["slot"] >= BARS_PER_DAY - 1 else session - 1, np.nan)
            if not np.isfinite(vol):
                raise KeyError("Needs 20 earlier sessions of history.")
            dates = self.plan.dates
            day = dates.loc[session + 1] if session + 1 in dates.index else self._next_session_date()
            slots = [OPENING[m] for m in OPENING]
            grid = np.arange(0, slots[-1] + 1)
            interp = {lv: np.interp(grid, slots, [cone["opening"][(m, lv)] * vol for m in OPENING]) for lv in LEVELS}
            times = [day + pd.Timedelta(minutes=570 + BAR_MIN * int(j)) for j in grid]
            anchors = {m: OPENING[m] for m in OPENING if m != 5}
            vs_usual = None

        pt = lambda k: {"time": times[k].strftime("%Y-%m-%d %H:%M"),
                        "lo80": price * float(np.exp(-interp[0.8][k])), "lo50": price * float(np.exp(-interp[0.5][k])),
                        "hi50": price * float(np.exp(interp[0.5][k])), "hi80": price * float(np.exp(interp[0.8][k]))}
        s = cone.get("stats")
        tested = s and {
            "wf_days": s["wf"][60]["days"] if 60 in s["wf"] else s["wf"]["60"]["days"],
            "test_days": (s["test"].get(60) or s["test"]["60"])["days"],
            "horizons": {str(m): {"wf50": v["cover50"], "wf80": v["cover80"], "test50": s["test"][k]["cover50"], "test80": s["test"][k]["cover80"]}
                         for k, v in s["wf"].items() for m in [int(k)]},
            "narrow_width": (s["test"].get(60) or s["test"]["60"])["by_width"]["narrow"]["width_vs_fixed"],
            "wide_width": (s["test"].get(60) or s["test"]["60"])["by_width"]["wide"]["width_vs_fixed"],
            "fixed_narrow_cover": (s["test"].get(60) or s["test"]["60"])["by_width"]["narrow"]["fixed_cover80"],
            "fixed_wide_cover": (s["test"].get(60) or s["test"]["60"])["by_width"]["wide"]["fixed_cover80"],
            "opening80": {"wf": s["opening"]["wf"]["60"]["cover80"], "test": s["opening"]["test"]["60"]["cover80"]},
        }
        return {
            "model": "LightGBM quantile models" if kind == "session" else "20-day daily volatility",
            "kind": kind, "asof": row["time"].strftime("%Y-%m-%dT%H:%M"), "price": price,
            "points": [pt(k) for k in range(len(times))],
            "horizons": [{"minutes": m, **pt(k)} for m, k in anchors.items()],
            "width_vs_usual": vs_usual,
            "trained_through": self.trained_through.strftime("%Y-%m-%d"),
            "in_sample": bool(row["time"] <= self.trained_through),
            "tested": tested,
        }

    # ---- Touch ladder: chance of touching a level inside the window ---------------------
    def touch(self, asof: datetime) -> dict:
        """Ladder made at the close of the candle that starts at `asof`, with its running record.
        A window is offered only if it ends before the bell."""
        touch = self.bundle.get("touch")
        if not touch:
            raise KeyError("This model file has no touch ladder. Run: python train_final.py")
        ts = pd.Timestamp(asof)
        idx = self.frame.index.searchsorted(ts, side="right") - 1
        if idx < 0 or self.frame.iloc[idx]["time"].normalize() != ts.normalize():
            raise KeyError("No candle on that day at or before that time.")
        row = self.frame.iloc[idx]
        if not np.isfinite(row["sigma"]) or not np.isfinite(row[touch["features"]].to_numpy(float)).all():
            raise KeyError("Not enough history before that time to build features.")
        price = float(row["close"])
        candle_end = row["time"].hour * 60 + row["time"].minute + BAR_MIN
        z = touch_z(touch, row[touch["features"]].to_numpy("float32").reshape(1, -1))
        usual = usual_z(touch)
        windows = []
        for m, bars in WINDOWS.items():
            if candle_end + m > CLOSE_MIN:
                windows.append({"minutes": m, "fits": False})
                continue
            unit = float(row["sigma"] * np.sqrt(bars))
            levels = [{"odds": o, "up": price * float(np.exp(z[(m, o)][0] * unit)), "down": price * float(np.exp(-z[(m, o)][0] * unit))} for o in ODDS]
            windows.append({"minutes": m, "fits": True, "end": (row["time"] + pd.Timedelta(minutes=BAR_MIN * bars)).strftime("%Y-%m-%d %H:%M"),
                            "levels": levels, "vs_usual": float(z[(m, 0.5)][0] / usual[(m, 0.5)])})

        # Running record. A ladder counts once its window has closed.
        rec = self.touch_record
        def tally(r: pd.DataFrame, m: int) -> dict:
            return {"n": int(np.nansum(r[f"n_{m}"])), "touched": {str(int(o * 100)): int(np.nansum(r[f"t{int(o * 100)}_{m}"])) for o in ODDS}}
        oos = rec[rec["time"] > self.trained_through]
        today = self._record_for(ts.normalize(), "touch")
        record = {"days": int(oos["time"].dt.normalize().nunique()),
                  "since_training": {str(m): tally(oos, m) for m in WINDOWS},
                  "session": {str(m): tally(today[today["time"] + pd.Timedelta(minutes=m) <= ts], m) for m in WINDOWS}}

        s = touch.get("stats")
        tested = None
        if s:
            both = lambda x, o: (x[f"up{o}"] + x[f"down{o}"]) / 2
            g = lambda part, m: s[part][m] if m in s[part] else s[part][str(m)]
            tested = {"wf_days": g("wf", 60)["days"], "test_days": g("test", 60)["days"],
                      "windows": {str(m): {"wf": {str(int(o * 100)): both(g("wf", m), int(o * 100)) for o in ODDS},
                                           "test": {str(int(o * 100)): both(g("test", m), int(o * 100)) for o in ODDS}} for m in WINDOWS},
                      "fixed_near": g("test", 60)["by_distance"]["near"]["fixed_touched25"],
                      "fixed_far": g("test", 60)["by_distance"]["far"]["fixed_touched25"]}
        return {"model": "LightGBM quantile models", "asof": row["time"].strftime("%Y-%m-%dT%H:%M"), "price": price,
                "windows": windows, "record": record, "trained_through": self.trained_through.strftime("%Y-%m-%d"),
                "in_sample": bool(row["time"] <= self.trained_through), "tested": tested}

    def cone_scores(self, asof: datetime | None = None, n: int = 20) -> dict:
        """Running record of the session cone: share of closes that landed inside it.
        A cone is counted only once its horizon has closed. With `asof`, the selected
        session is also scored using only cones whose result was known by that time."""
        if "cone" not in self.bundle:
            raise KeyError("This model file has no range cone. Run: python train_final.py")
        rec = self.cone_record
        day = rec["time"].dt.normalize()
        cols = [f"in{k}_{m}" for m in CONE for k in (50, 80)]
        tally = lambda r: {str(m): {"n": int(r[f"in80_{m}"].notna().sum()), "in50": int(r[f"in50_{m}"].sum()), "in80": int(r[f"in80_{m}"].sum())} for m in CONE}
        oos = rec[rec["time"] > self.trained_through]
        g = rec.groupby(day)[cols].agg(["sum", "count"])
        recent = [{"date": d.strftime("%Y-%m-%d"), "n": int(row[("in80_60", "count")]), "in80": int(row[("in80_60", "sum")])}
                  for d, row in g.tail(n).iterrows() if row[("in80_60", "count")] > 0]
        out = {"since_training": {**tally(oos), "days": int(day[oos.index].nunique()), "from": self.trained_through.strftime("%Y-%m-%d")},
               "recent": recent, "session": None}
        if asof is not None:
            ts = pd.Timestamp(asof)
            r = self._record_for(ts.normalize(), "cone")
            # The cone made at candle t for m minutes is settled when the candle starting at t + m has closed.
            parts = {}
            for m in CONE:
                done = r[r["time"] + pd.Timedelta(minutes=m) <= ts]
                parts[str(m)] = {"n": int(done[f"in80_{m}"].notna().sum()), "in50": int(done[f"in50_{m}"].sum()), "in80": int(done[f"in80_{m}"].sum())}
            out["session"] = {"date": ts.strftime("%Y-%m-%d"), **parts}
        return out

    # ---- Next candle: called at each candle close for the candle that follows ---------
    def _next_bundle(self) -> dict:
        if "next" not in self.bundle:
            raise KeyError("This model file has no next-candle model. Run: python train_final.py")
        return self.bundle["next"]

    def next_calls(self, date: str) -> dict:
        """Every call of one session. The call for slot s was made at the close of slot s-1,
        so the first candle of the day has none and the last call may be for a candle not printed yet."""
        nxt = self._next_bundle()
        day = pd.Timestamp(date).normalize()
        rows = self.frame[self.frame["date"] == day] if "date" in self.frame else self.frame[self.frame["time"].dt.normalize() == day]
        if rows.empty:
            raise KeyError("No session on that date.")
        calls = []
        for slot, p in zip(rows["slot"].to_numpy(), rows["next_p"].to_numpy()):
            target = int(slot) + 1
            if target >= BARS_PER_DAY or not np.isfinite(p):
                continue
            minute = 570 + BAR_MIN * target
            calls.append({"slot": target, "time": f"{minute // 60:02d}:{minute % 60:02d}", "p_up": float(p),
                          "strong": bool(abs(p - 0.5) >= nxt["threshold"])})
        return {"model": "LightGBM + XGBoost", "date": day.strftime("%Y-%m-%d"), "calls": calls,
                "trained_through": self.trained_through.strftime("%Y-%m-%d"),
                "in_sample": bool(day <= self.trained_through.normalize()), "tested": nxt.get("stats")}

    def next_scores(self, n: int = 20) -> dict:
        """How the next-candle calls scored on candles already in the file. Flat candles are not counted."""
        nxt = self._next_bundle()
        f = self.frame
        same = (f["session"].shift(-1) == f["session"]) & ((f["time"].shift(-1) - f["time"]) == pd.Timedelta(minutes=BAR_MIN))
        move = np.sign(f["close"].shift(-1) - f["close"]).where(same)
        r = pd.DataFrame({"day": f["time"].dt.normalize(), "p": f["next_p"], "move": move}).dropna()
        r = r[r["move"] != 0]
        r["hit"] = (r["p"] > 0.5) == (r["move"] > 0)
        r["strong"] = (r["p"] - 0.5).abs() >= nxt["threshold"]
        r["strong_hit"] = r["hit"] & r["strong"]
        g = r.groupby("day").agg(right=("hit", "sum"), total=("hit", "size"), strong_right=("strong_hit", "sum"), strong_total=("strong", "sum"))
        oos = g[g.index > self.trained_through.normalize()]
        tot = lambda x: {k: int(x[k].sum()) for k in ("right", "total", "strong_right", "strong_total")}
        return {"since_training": {**tot(oos), "days": int(len(oos)), "from": self.trained_through.strftime("%Y-%m-%d")},
                "recent": [{"date": d.strftime("%Y-%m-%d"), **{k: int(v) for k, v in row.items()}} for d, row in g.tail(n).iterrows()]}

    # ---- Day plan: all 78 five-minute candles called before the open -------------------
    def _plan_probs(self, prev_session: int, target: pd.Timestamp) -> np.ndarray:
        if prev_session not in self._plan_cache:
            X = self.plan.features_after(prev_session, target).to_numpy(float)
            self._plan_cache[prev_session] = self.bundle["plan"]["model"].predict_proba(X)[:, 1]
        return self._plan_cache[prev_session]

    def _next_session_date(self) -> pd.Timestamp:
        """The next session by the real New York clock, even when the candle file is behind."""
        d = self.plan.dates.iloc[-1] + pd.Timedelta(days=1)
        now = pd.Timestamp.now(tz="America/New_York").tz_localize(None)
        today = now.normalize() if now.hour < 16 else now.normalize() + pd.Timedelta(days=1)
        d = max(d, today)
        while d.dayofweek >= 5:                       # weekends skipped; exchange holidays are not known here
            d += pd.Timedelta(days=1)
        return d

    def day_plan(self, date: str) -> dict:
        if "plan" not in self.bundle:
            raise KeyError("This model file has no day plan. Run: python train_final.py")
        dates = self.plan.dates
        last = int(dates.index[-1])
        if date == "next":
            target, prev, exists = self._next_session_date(), last, False
        else:
            target = pd.Timestamp(date).normalize()
            hit = dates[dates == target]
            if len(hit):
                prev, exists = int(hit.index[0]) - 1, True
            elif target > dates.iloc[-1]:
                prev, exists = last, False
            else:
                raise KeyError("No session on that date.")
        if prev < 60:
            raise KeyError("Needs 60 earlier sessions of history.")
        p = self._plan_probs(prev, target)
        prev_bars = int(self.plan.days.loc[prev, "bars"])
        return {
            "model": "LightGBM (day plan)",
            "date": target.strftime("%Y-%m-%d"),
            "session_exists": exists,
            "uses_sessions_through": dates.loc[prev].strftime("%Y-%m-%d"),
            "previous_session_candles": prev_bars,           # under 78 can mean that day was still trading
            # Weekdays between the last candle in the file and the target day: 0 means the data is current.
            "sessions_missing": 0 if exists else max(0, int(np.busday_count(dates.loc[prev].date(), target.date())) - 1),
            "trained_through": self.trained_through.strftime("%Y-%m-%d"),
            "in_sample": bool(target <= self.trained_through.normalize()),
            "slots": [{"slot": j, "time": f"{(570 + 5 * j) // 60:02d}:{(570 + 5 * j) % 60:02d}", "p_up": float(p[j])} for j in range(BARS_PER_DAY)],
            "tested": self.bundle["plan"]["stats"],
        }

    def plan_scores(self, n: int = 20) -> dict:
        """How the pre-open calls scored on sessions already in the file."""
        if "plan" not in self.bundle:
            raise KeyError("This model file has no day plan. Run: python train_final.py")
        dates, green = self.plan.dates, self.plan.green
        cutoff = self.trained_through.normalize()
        rows, right_oos, total_oos = [], 0, 0
        for s in dates.index:
            if s < 61 or (dates.loc[s] <= cutoff and s < dates.index[-1] - n):
                continue
            actual = green.loc[s].to_numpy()
            ok = ~np.isnan(actual)
            if not ok.any():
                continue
            call = self._plan_probs(s - 1, dates.loc[s]) >= 0.5
            right, total = int((call[ok] == (actual[ok] > 0.5)).sum()), int(ok.sum())
            if dates.loc[s] > cutoff:
                right_oos, total_oos = right_oos + right, total_oos + total
            rows.append({"date": dates.loc[s].strftime("%Y-%m-%d"), "right": right, "total": total})
        return {"recent": rows[-n:], "since_training": {"right": right_oos, "total": total_oos,
                "from": cutoff.strftime("%Y-%m-%d"), "days": int((dates > cutoff).sum())}}

    def day_outlook(self, date: datetime) -> dict:
        """Chance that the session on `date` closes above its open, as it could have
        been stated before the bell: only earlier sessions feed the features."""
        daily = self.bundle.get("daily")
        if not daily:
            raise KeyError("This model file has no day outlook. Run: python train_final.py")
        day = pd.Timestamp(date).normalize()
        if day not in self.days.index:
            raise KeyError("No session on that date.")
        row = self.days.loc[day]
        x = row[daily["features"]].to_numpy(float).reshape(1, -1)
        if not np.isfinite(row["vs_sma50"]):
            raise KeyError("Needs 50 earlier sessions of history.")
        p_up = float(daily["model"].predict_proba(x)[0, 1])
        pos = self.days.index.get_loc(day)
        return {
            "model": "LightGBM (daily)",
            "date": day.strftime("%Y-%m-%d"),
            "p_up": p_up, "p_down": 1 - p_up,
            "uses_sessions_through": self.days.index[pos - 1].strftime("%Y-%m-%d"),
            "trained_through": self.trained_through.strftime("%Y-%m-%d"),
            "in_sample": bool(day <= self.trained_through.normalize()),
            "tested": daily["stats"],
        }

    def session_forecast(self, date: str, horizon: int = 10) -> dict:
        """DOWN / NEUTRAL / UP for every 5-min candle of one session at a given horizon."""
        if horizon not in self.bundle["models"]:
            raise KeyError(f"No model for the {horizon}-minute horizon. Available: {list(self.bundle['models'].keys())}")
        day = pd.Timestamp(date).normalize()
        rows = self.frame[self.frame["time"].dt.normalize() == day]
        if rows.empty:
            raise KeyError(f"No session on {date}.")
        candles = []
        for _, row in rows.iterrows():
            slot = int(row["slot"])
            time_str = row["time"].strftime("%H:%M")
            candle_end = row["time"].hour * 60 + row["time"].minute + BAR_MIN
            # Skip candles where the horizon would run past the closing bell
            if candle_end + horizon > CLOSE_MIN:
                candles.append({"slot": slot, "time": time_str, "p_down": None, "p_neutral": None, "p_up": None})
                continue
            x = row[self.feats].to_numpy(float).reshape(1, -1)
            if not np.isfinite(row["sigma"]) or not np.isfinite(x).all():
                candles.append({"slot": slot, "time": time_str, "p_down": None, "p_neutral": None, "p_up": None})
                continue
            p = self.bundle["models"][horizon].predict_proba(x)[0]
            candles.append({
                "slot": slot, "time": time_str,
                "p_down": float(p[0]), "p_neutral": float(p[1]), "p_up": float(p[2]),
            })
        return {
            "date": day.strftime("%Y-%m-%d"),
            "horizon": horizon,
            "candles": candles,
            "trained_through": self.trained_through.strftime("%Y-%m-%d"),
            "in_sample": bool(day <= self.trained_through.normalize()),
        }

    def predict(self, asof: datetime) -> dict:
        """Forecast from the close of the candle that starts at `asof` (New York time).
        Only that row's features are used, and they depend on that candle and earlier ones."""
        ts = pd.Timestamp(asof)
        idx = self.frame.index.searchsorted(ts, side="right") - 1
        if idx < 0:
            raise KeyError("No candle at or before that time.")
        row = self.frame.iloc[idx]
        if row["time"].normalize() != ts.normalize():
            raise KeyError("No candle on that day at or before that time.")
        x = row[self.feats].to_numpy(float).reshape(1, -1)
        if not np.isfinite(row["sigma"]):
            raise KeyError("Not enough history before that time to build features.")

        candle_end = row["time"].hour * 60 + row["time"].minute + BAR_MIN
        horizons, skipped = [], []
        for minutes in HORIZONS:
            if minutes not in self.bundle["models"]:
                continue
            if candle_end + minutes > CLOSE_MIN:
                skipped.append({"minutes": minutes, "reason": "Would run past the 16:00 close."})
                continue
            p = self.bundle["models"][minutes].predict_proba(x)[0]
            stats = self.bundle["stats"].get(minutes, {})
            # Size of move that counts as UP or DOWN at this moment, in dollars.
            band = self.bundle["k"] * row["sigma"] * np.sqrt(HORIZONS[minutes]) * row["close"]
            horizons.append({
                "minutes": minutes,
                "p_down": float(p[0]), "p_neutral": float(p[1]), "p_up": float(p[2]),
                "move_threshold": float(band),
                "tested": stats,
            })
        return {
            "model": self.bundle["model_label"],
            "asof": row["time"].strftime("%Y-%m-%dT%H:%M"),
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "trained_through": self.trained_through.strftime("%Y-%m-%d"),
            "in_sample": bool(row["time"] <= self.trained_through),
            "horizons": horizons,
            "skipped": skipped,
        }
