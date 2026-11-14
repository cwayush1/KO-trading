"""Train the models the API serves and save them to artifacts/forecaster.joblib.

Default: train on the development period only, so the last ~6 months that the
dashboard can replay are true out-of-sample forecasts.
  python train_final.py
For live use after you are happy with the evaluation, train on everything:
  python train_final.py --all
"""
from __future__ import annotations

import argparse
import json

import joblib

from kodesk.cone import add_cone_labels, opening_table, train_cone, train_opening
from kodesk.config import ARTIFACTS, HORIZONS, K_NEUTRAL, REPORTS
from kodesk.daily import build_daily_features, daily_bars
from kodesk.data import load_candles
from kodesk.dayplan import PlanData, make_plan_model
from kodesk.evaluate import final_test_start, split_train_val
from kodesk.features import build_features
from kodesk.models import Model
from kodesk.nextcandle import add_next_label, train as train_next
from kodesk.targets import add_targets
from kodesk.touch import add_touch_labels, train_touch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="lightgbm")
    ap.add_argument("--all", action="store_true", help="train on every session (no held-out period left)")
    args = ap.parse_args()

    candles = load_candles()
    d, feats = build_features(candles)
    d = add_targets(d)
    n_sessions = int(d["session"].max()) + 1
    train_end = n_sessions if args.all else final_test_start(n_sessions)
    va_a = split_train_val(train_end)

    # Measured performance travels with the model so the dashboard can show it.
    results = json.loads((REPORTS / "results.json").read_text()) if (REPORTS / "results.json").exists() else {"table": []}
    table = {(r["model"], r["horizon"]): r for r in results["table"]}

    models, stats = {}, {}
    for minutes in HORIZONS:
        r = d[d[f"y_{minutes}"].notna() & d["sigma"].notna() & d["dist_ema50"].notna()]
        tr, va = r[r.session < va_a], r[(r.session >= va_a) & (r.session < train_end)]
        m = Model(args.model).fit(tr[feats].to_numpy(float), tr[f"y_{minutes}"].to_numpy(int),
                                  va[feats].to_numpy(float), va[f"y_{minutes}"].to_numpy(int))
        models[minutes] = m
        t = table.get((args.model, minutes), {})
        stats[minutes] = {
            "wf_direction_hit": t.get("wf_dir_hit"), "test_direction_hit": t.get("test_dir_hit"),
            "test_direction_ci": t.get("test_dir_ci"),
            "wf_move_auc": t.get("wf_move_auc"), "test_move_auc": t.get("test_move_auc"),
            "base_move": t.get("wf_base_move"),
        }
        print(f"{minutes:>3} min: trained on {len(tr)} rows, calibrated on {len(va)}")

    # Pre-market day outlook: one small model on daily bars, same training cut-off.
    import lightgbm as lgb
    dd, dfeats = build_daily_features(daily_bars(candles))
    tr = dd[(dd.index < train_end) & (dd["bars"] >= 70)].dropna(subset=["vs_sma50"])
    day_model = lgb.LGBMClassifier(n_estimators=150, learning_rate=0.03, num_leaves=4, min_child_samples=40, subsample=0.8,
                                   subsample_freq=1, colsample_bytree=0.6, reg_lambda=10, random_state=7, verbose=-1, n_jobs=2)
    day_model.fit(tr[dfeats].to_numpy(float), tr["y"].to_numpy(int))
    dres = json.loads((REPORTS / "daily_results.json").read_text()) if (REPORTS / "daily_results.json").exists() else None
    day_stats = None
    if dres:
        m = dres["models"]["lightgbm"]
        day_stats = {"wf_hit": m["wf"]["hit"], "wf_ci": m["wf"]["ci"], "wf_days": m["wf"]["n"],
                     "test_hit": m["test"]["hit"], "test_ci": m["test"]["ci"], "test_days": m["test"]["n"]}
    print(f"day outlook: trained on {len(tr)} sessions")

    # Day plan: every 5-minute candle called before the open, same training cut-off.
    plan = PlanData(candles)
    pf = plan.training_frame()
    pf = pf[pf["session"] < train_end]
    plan_model = make_plan_model().fit(pf[plan.feats].to_numpy(float), pf["y"].to_numpy(int))
    pres = json.loads((REPORTS / "plan_results.json").read_text()) if (REPORTS / "plan_results.json").exists() else None
    plan_stats = None
    if pres:
        m, b = pres["models"]["lightgbm"], pres["models"]["always_green"]
        plan_stats = {"wf_hit": m["wf"]["hit"], "wf_ci": m["wf"]["ci"], "wf_days": pres["wf_days"],
                      "test_hit": m["test"]["hit"], "test_ci": m["test"]["ci"], "test_days": pres["test_days"],
                      "always_green_hit": b["wf"]["hit"], "day_min": m["wf"]["day_min"], "day_max": m["wf"]["day_max"]}
    print(f"day plan: trained on {len(pf)} candles")

    # Next candle: up or down for the following 5-minute candle, same training cut-off.
    nxt = train_next(add_next_label(d), feats, va_a, train_end)
    nres = json.loads((REPORTS / "next_results.json").read_text()) if (REPORTS / "next_results.json").exists() else None
    nxt["stats"] = nres and {"wf": nres["wf"], "test": nres["test"]}
    print(f"next candle: trained on {nxt.pop('rows')} candles")

    # Range cone: how far price is likely to travel in the next 15 to 120 minutes.
    cone = train_cone(add_cone_labels(d), feats, va_a, train_end)
    cone["opening"] = train_opening(opening_table(candles), train_end)
    cone["stats"] = json.loads((REPORTS / "cone_results.json").read_text()) if (REPORTS / "cone_results.json").exists() else None
    print(f"range cone: {len(cone['models'])} quantile models")

    # Touch ladder: chance that price touches a level inside the next 30 to 120 minutes.
    touch = train_touch(add_touch_labels(d), feats, va_a, train_end)
    touch["stats"] = json.loads((REPORTS / "touch_results.json").read_text()) if (REPORTS / "touch_results.json").exists() else None
    print(f"touch ladder: {len(touch['models'])} quantile models")

    last_train_time = d.loc[d.session < train_end, "time"].iloc[-1]
    ARTIFACTS.mkdir(exist_ok=True)
    joblib.dump({
        "models": models, "features": feats, "stats": stats, "k": K_NEUTRAL,
        "daily": {"model": day_model, "features": dfeats, "stats": day_stats},
        "plan": {"model": plan_model, "features": plan.feats, "stats": plan_stats},
        "next": nxt,
        "cone": cone,
        "touch": touch,
        "model_label": {"lightgbm": "LightGBM", "xgboost": "XGBoost", "catboost": "CatBoost", "logreg": "Logistic regression"}.get(args.model, args.model),
        "trained_through": str(last_train_time),
    }, ARTIFACTS / "forecaster.joblib", compress=3)
    print("saved artifacts/forecaster.joblib, trained through", last_train_time)


if __name__ == "__main__":
    main()
