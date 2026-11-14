"""Compare models and horizons honestly.

1. Development period (everything except the last ~6 months): expanding-window
   walk-forward. All choices (model, horizon, confidence cut-off) are made here.
2. Final test (last ~6 months): each model is trained once on the development
   period and scored once. Nothing is tuned on it.

Usage:  python run_experiments.py [--models lightgbm,logreg] [--k 0.35]
Writes reports/predictions_k{K}.pkl, which build_report.py turns into tables.
"""
from __future__ import annotations

import argparse
import pickle
import time

import numpy as np

from kodesk.config import HORIZONS, K_NEUTRAL, REPORTS
from kodesk.data import describe, load_candles
from kodesk.evaluate import final_test_start, split_train_val, walk_forward_folds
from kodesk.features import build_features
from kodesk.models import MODEL_NAMES, Model
from kodesk.targets import add_targets

BASELINES = ["majority", "always_up", "momentum", "reversal"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=",".join(MODEL_NAMES))
    ap.add_argument("--horizons", default=",".join(str(m) for m in HORIZONS))
    ap.add_argument("--k", type=float, default=K_NEUTRAL)
    ap.add_argument("--drop", default="", help="comma-separated feature name prefixes to leave out (ablation)")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    models = [m for m in args.models.split(",") if m]
    horizons = [int(m) for m in args.horizons.split(",")]

    df = load_candles()
    print(describe(df), flush=True)
    d, feats = build_features(df)
    d = add_targets(d, k=args.k)
    drops = [x for x in args.drop.split(",") if x]
    feats = [f for f in feats if not any(f.startswith(x) for x in drops)]

    n_sessions = int(d["session"].max()) + 1
    ft = final_test_start(n_sessions)
    folds = walk_forward_folds(ft) + [(ft, ft, n_sessions)]        # last entry = final test
    print(f"{len(feats)} features, {len(folds) - 1} walk-forward folds, final test from session {ft} "
          f"({d.loc[d.session == ft, 'time'].iloc[0].date()})", flush=True)

    out = {"k": args.k, "features": feats, "final_test_session": ft, "rows": {}, "pred": {}, "importance": {}}
    for minutes in horizons:
        ycol, fcol = f"y_{minutes}", f"fwd_{minutes}"
        r = d[d[ycol].notna() & d["sigma"].notna() & d["dist_ema50"].notna()]
        sess = r["session"].to_numpy()
        X, y, fwd = r[feats].to_numpy(float), r[ycol].to_numpy(int), r[fcol].to_numpy(float)
        last_ret = r[f"ret_{min(HORIZONS[minutes], 24) if HORIZONS[minutes] in (3, 6, 12, 24) else 3}"].to_numpy(float)
        out["rows"][minutes] = {
            "time": r["time"].to_numpy(), "session": sess, "slot": r["slot"].to_numpy(),
            "y": y, "fwd": fwd, "sigma": r["sigma"].to_numpy(), "adx": r["adx"].to_numpy(),
            "fold": np.full(len(r), -1),
        }
        for name in BASELINES + models:
            out["pred"][(name, minutes)] = np.full((len(r), 3), np.nan)
            out["pred"][(name + "_raw", minutes)] = np.full((len(r), 3), np.nan)

        for fi, (train_end, te_a, te_b) in enumerate(folds):
            va_a = split_train_val(train_end)
            tr, va, te = sess < va_a, (sess >= va_a) & (sess < train_end), (sess >= te_a) & (sess < te_b)
            out["rows"][minutes]["fold"][te] = fi
            for b in BASELINES:
                p = np.zeros((te.sum(), 3))
                if b == "majority":
                    p[:, np.bincount(y[tr | va], minlength=3).argmax()] = 1
                elif b == "always_up":
                    p[:, 2] = 1
                else:
                    up = last_ret[te] > 0
                    p[np.arange(te.sum()), np.where(up == (b == "momentum"), 2, 0)] = 1
                out["pred"][(b, minutes)][te] = p
            for name in models:
                t0 = time.time()
                m = Model(name).fit(X[tr], y[tr], X[va], y[va])
                out["pred"][(name, minutes)][te] = m.predict_proba(X[te])
                out["pred"][(name + "_raw", minutes)][te] = m.predict_proba(X[te], calibrated=False)
                if name == "lightgbm" and fi == len(folds) - 1:
                    out["importance"][minutes] = dict(zip(feats, m.clf.booster_.feature_importance("gain").tolist()))
                print(f"h={minutes:>3} fold={fi} {name:<14} {time.time() - t0:5.1f}s", flush=True)

    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / f"predictions_k{args.k}{args.tag}.pkl"
    with open(path, "wb") as f:
        pickle.dump(out, f)
    print("saved", path, flush=True)


if __name__ == "__main__":
    main()
