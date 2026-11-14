"""Out-of-sample test of the next-candle model. Writes reports/next_results.{json,md}.

Walk-forward over the development sessions, then one run on the final held-out
period. The confidence threshold for each fold comes from that fold's own
validation tail, never from the test rows it is scored on.
  python run_next_experiment.py
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from kodesk.config import REPORTS
from kodesk.data import load_candles
from kodesk.evaluate import final_test_start, split_train_val, walk_forward_folds
from kodesk.features import build_features
from kodesk.nextcandle import add_next_label, predict_up, train


def day_ci(hit: np.ndarray, days: np.ndarray, n: int = 1000) -> list[float]:
    """Bootstrap over whole sessions, because candles inside one day are not independent."""
    g = pd.DataFrame({"h": hit, "d": days}).groupby("d")["h"].agg(["sum", "count"]).to_numpy()
    rng = np.random.default_rng(0)
    idx = rng.integers(0, len(g), size=(n, len(g)))
    vals = g[idx, 0].sum(axis=1) / g[idx, 1].sum(axis=1)
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def score(parts: list[pd.DataFrame]) -> dict:
    r = pd.concat(parts)
    r = r[r.fwd != 0]
    hit = ((r.p > 0.5) == (r.fwd > 0)).to_numpy()
    s = r.strong.to_numpy()
    days = r.session.nunique()
    return {"days": int(days),
            "all": {"hit": float(hit.mean()), "n": int(len(r)), "ci": day_ci(hit, r.session.to_numpy())},
            "strong": {"hit": float(hit[s].mean()), "n": int(s.sum()), "ci": day_ci(hit[s], r.session.to_numpy()[s]),
                       "per_day": float(s.sum() / days)},
            "always_up": float((r.fwd > 0).mean())}


def main():
    frame, feats = build_features(load_candles())
    d = add_next_label(frame)
    n_sessions = int(d["session"].max()) + 1
    ft = final_test_start(n_sessions)

    def run(train_end: int, a: int, b: int) -> pd.DataFrame:
        m = train(d, feats, split_train_val(train_end), train_end)
        te = d[(d.session >= a) & (d.session < b) & d["fwd_next"].notna()].dropna(subset=feats)
        p = predict_up(m["models"], te[feats].to_numpy("float32"))
        return pd.DataFrame({"session": te.session.to_numpy(), "p": p, "fwd": te.fwd_next.to_numpy(),
                             "strong": np.abs(p - 0.5) >= m["threshold"]})

    wf = score([run(e, a, b) for e, a, b in walk_forward_folds(ft)])
    test = score([run(ft, ft, n_sessions)])
    out = {"wf": wf, "test": test, "models": "LightGBM + XGBoost average", "features": len(feats)}
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "next_results.json").write_text(json.dumps(out, indent=2))
    pc = lambda x: f"{x * 100:.1f}%"
    row = lambda name, s: (f"| {name} | {s['days']} | {pc(s['all']['hit'])} ({pc(s['all']['ci'][0])} to {pc(s['all']['ci'][1])}) | "
                           f"{pc(s['strong']['hit'])} ({pc(s['strong']['ci'][0])} to {pc(s['strong']['ci'][1])}) | {s['strong']['per_day']:.1f} | {pc(s['always_up'])} |")
    (REPORTS / "next_results.md").write_text("\n".join([
        "# Next 5-minute candle: up or down", "",
        "Call made at each candle close for the following candle, from candles up to that close only.",
        "Flat candles are not scored. Ranges are 95% intervals from resampling whole sessions.", "",
        "| Period | Sessions | All calls | Confident calls (top 10%) | Confident calls per day | Always up |",
        "|---|---|---|---|---|---|", row("Walk-forward", wf), row("Final held-out", test), ""]))
    print((REPORTS / "next_results.md").read_text())


if __name__ == "__main__":
    main()
