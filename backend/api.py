"""FastAPI backend for the KO market desk.

Run:  uvicorn api:app --reload --port 8000
Analysis only: there are no order, account or portfolio endpoints.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from kodesk.config import ARTIFACTS, DATA_CSV
from kodesk.inference import Forecaster

app = FastAPI(title="KO market desk API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_forecaster: Forecaster | None = None
_forecaster_lock = threading.Lock()


def forecaster() -> Forecaster:
    """Thread-safe singleton. Models are loaded from disk once; concurrent requests queue cleanly."""
    global _forecaster
    if _forecaster is None:
        with _forecaster_lock:
            if _forecaster is None:
                if not (ARTIFACTS / "forecaster.joblib").exists():
                    raise HTTPException(503, "No trained model found. Run: python train_final.py")
                _forecaster = Forecaster()
    return _forecaster


@app.on_event("startup")
def preload_forecaster():
    """Warm up models in background at startup so first user request never hits a 30s cold-start."""
    def _warm():
        try:
            forecaster()
            print("Forecaster pre-warmed successfully.")
        except Exception as e:
            print(f"Forecaster pre-warm note: {e}")
    threading.Thread(target=_warm, daemon=True).start()


@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {"message": "KO Trading API is live"}


@app.api_route("/api/health", methods=["GET", "HEAD"])
def health():
    """Lightweight health check — does NOT load the model so UptimeRobot never triggers an OOM."""
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.get("/api/candles", response_class=PlainTextResponse)
def candles(symbol: str = "KO"):
    if symbol.upper() != "KO":
        raise HTTPException(404, "Only KO is available.")
    return DATA_CSV.read_text()


@app.get("/api/prediction")
def prediction(symbol: str = "KO", asof: str = Query(..., description="New York time, e.g. 2026-11-09T13:30")):
    if symbol.upper() != "KO":
        raise HTTPException(404, "Only KO is available.")
    try:
        when = datetime.fromisoformat(asof)
    except ValueError:
        raise HTTPException(422, "asof must look like 2026-11-09T13:30 (New York time).")
    try:
        return forecaster().predict(when)
    except KeyError as e:
        raise HTTPException(404, str(e).strip("'\""))


@app.get("/api/day-outlook")
def day_outlook(symbol: str = "KO", date: str = Query(..., description="Session date, e.g. 2026-11-09")):
    """Pre-market view of the whole session: green or red day candle. Uses earlier sessions only."""
    if symbol.upper() != "KO":
        raise HTTPException(404, "Only KO is available.")
    try:
        when = datetime.fromisoformat(date)
    except ValueError:
        raise HTTPException(422, "date must look like 2026-11-09.")
    try:
        return forecaster().day_outlook(when)
    except KeyError as e:
        raise HTTPException(404, str(e).strip("'\""))


@app.get("/api/day-plan")
def day_plan(symbol: str = "KO", date: str = Query("next", description="Session date like 2026-11-13, or 'next'")):
    """All 78 five-minute candles of one session, called green or red before the open."""
    if symbol.upper() != "KO":
        raise HTTPException(404, "Only KO is available.")
    try:
        return forecaster().day_plan(date)
    except (KeyError, ValueError) as e:
        raise HTTPException(404, str(e).strip("'\""))


@app.get("/api/plan-scores")
def plan_scores(days: int = 20):
    try:
        return forecaster().plan_scores(max(1, min(days, 120)))
    except KeyError as e:
        raise HTTPException(404, str(e).strip("'\""))


@app.get("/api/cone")
def cone(symbol: str = "KO", asof: str = Query(..., description="New York time, e.g. 2026-11-13T13:30")):
    """Range cone: where price is likely to be over the next two hours, as low and high bounds."""
    if symbol.upper() != "KO":
        raise HTTPException(404, "Only KO is available.")
    try:
        when = datetime.fromisoformat(asof)
    except ValueError:
        raise HTTPException(422, "asof must look like 2026-11-13T13:30 (New York time).")
    try:
        return forecaster().cone(when)
    except KeyError as e:
        raise HTTPException(404, str(e).strip("'\""))


@app.get("/api/touch")
def touch(symbol: str = "KO", asof: str = Query(..., description="New York time, e.g. 2026-11-13T13:30")):
    """Touch ladder: price levels with their chance of being touched in the next 30, 60 or 120 minutes."""
    if symbol.upper() != "KO":
        raise HTTPException(404, "Only KO is available.")
    try:
        when = datetime.fromisoformat(asof)
    except ValueError:
        raise HTTPException(422, "asof must look like 2026-11-13T13:30 (New York time).")
    try:
        return forecaster().touch(when)
    except KeyError as e:
        raise HTTPException(404, str(e).strip("'\""))


@app.get("/api/cone-scores")
def cone_scores(asof: str | None = None, days: int = 20):
    """Running record of the range cone: how often price closed inside it."""
    try:
        when = datetime.fromisoformat(asof) if asof else None
    except ValueError:
        raise HTTPException(422, "asof must look like 2026-11-13T13:30 (New York time).")
    try:
        return forecaster().cone_scores(when, max(1, min(days, 120)))
    except KeyError as e:
        raise HTTPException(404, str(e).strip("'\""))


@app.get("/api/next-calls")
def next_calls(symbol: str = "KO", date: str = Query(..., description="Session date, e.g. 2026-11-13")):
    """Up or down for each following 5-minute candle of one session, each call made one candle earlier."""
    if symbol.upper() != "KO":
        raise HTTPException(404, "Only KO is available.")
    try:
        return forecaster().next_calls(date)
    except (KeyError, ValueError) as e:
        raise HTTPException(404, str(e).strip("'\""))


@app.get("/api/next-scores")
def next_scores(days: int = 20):
    try:
        return forecaster().next_scores(max(1, min(days, 120)))
    except KeyError as e:
        raise HTTPException(404, str(e).strip("'\""))


_last_update = {"at": 0.0, "result": None}


@app.post("/api/update")
def update_candles():
    """Pull new candles from Alpaca (at most once a minute), then recompute features."""
    from update_data import UpdateError, update
    now = time.time()
    if now - _last_update["at"] < 55 and _last_update["result"]:
        return _last_update["result"]
    _last_update["at"] = now
    try:
        info = update()
        if info.get("added", 0) > 0:
            forecaster().reload()
        result = {
            "ok": True,
            "message": f"Updated from Alpaca, {info.get('added', 0):+d} candles",
            # The browser uses this to know when it needs to fetch the new CSV.
            "last_candle": str(info["last_candle"]).replace(" ", "T")[:16],
            **health(),
        }
    except (UpdateError, Exception) as e:
        result = {"ok": False, "message": str(e), **health()}
    _last_update.update(at=time.time(), result=result)
    return result


@app.get("/api/session-forecast")
def session_forecast(symbol: str = "KO", date: str = Query(..., description="Session date, e.g. 2026-11-13"), horizon: int = 10):
    """DOWN / NEUTRAL / UP probability for every 5-min candle of a session."""
    if symbol.upper() != "KO":
        raise HTTPException(404, "Only KO is available.")
    try:
        return forecaster().session_forecast(date, horizon)
    except (KeyError, ValueError) as e:
        raise HTTPException(404, str(e).strip("'\""))


@app.post("/api/reload")
def reload():
    """Re-read the candle file after it has been updated."""
    forecaster().reload()
    return health()
