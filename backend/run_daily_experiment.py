"""Can the direction of the whole day be called before the open?

Walk-forward by day, then one look at the last 126 sessions.
Usage:  python run_daily_experiment.py      (writes reports/daily_results.json and .md)
"""
from __future__ import annotations

import json

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from kodesk.config import FINAL_TEST_SESSIONS, REPORTS
from kodesk.daily import build_daily_features, daily_bars
from kodesk.data import load_candles

START, BLOCK = 252, 63


def make(name):
    if name == "logreg":
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=0.05, max_iter=500))
    if name == "random_forest":
        return make_pipeline(SimpleImputer(strategy="median"),
                             RandomForestClassifier(n_estimators=400, max_depth=3, min_samples_leaf=25, max_features=0.4, random_state=7, n_jobs=-1))
    import lightgbm as lgb
    return lgb.LGBMClassifier(n_estimators=150, learning_rate=0.03, num_leaves=4, min_child_samples=40, subsample=0.8,
                              subsample_freq=1, colsample_bytree=0.6, reg_lambda=10, random_state=7, verbose=-1, n_jobs=2)


def wilson(hits, n):
    if n == 0:
        return [float("nan")] * 2
    p, z = hits / n, 1.96
    den = 1 + z * z / n
    mid, half = (p + z * z / (2 * n)) / den, z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [float(mid - half), float(mid + half)]


def score(p_up, y, min_conf=0.5):
    call = np.maximum(p_up, 1 - p_up) >= min_conf
    n = int(call.sum())
    hits = int(((p_up[call] > 0.5).astype(int) == y[call]).sum())
    return {"n": n, "hit": hits / n if n else float("nan"), "ci": wilson(hits, n), "coverage": float(call.mean())}


def main():
    d, feats = build_daily_features(daily_bars(load_candles()))
    d = d[d["bars"] >= 70].dropna(subset=["vs_sma50"]).reset_index(drop=True)   # full sessions with enough history
    X, y = d[feats].to_numpy(float), d["y"].to_numpy(int)
    n = len(d)
    ft = n - FINAL_TEST_SESSIONS
    blocks = [(a, min(a + BLOCK, ft)) for a in range(START, ft, BLOCK)] + [(ft, n)]
    names = ["always_up", "same_as_yesterday", "opposite_of_yesterday", "logreg", "random_forest", "lightgbm"]
    P = {k: np.full(n, np.nan) for k in names}
    for a, b in blocks:
        P["always_up"][a:b] = 1.0
        prev_green = (d["candle_1d"].to_numpy()[a:b] > 0).astype(float)
        P["same_as_yesterday"][a:b] = prev_green
        P["opposite_of_yesterday"][a:b] = 1 - prev_green
        for name in ("logreg", "random_forest", "lightgbm"):
            P[name][a:b] = make(name).fit(X[:a], y[:a]).predict_proba(X[a:b])[:, 1]
    wf, te = slice(START, ft), slice(ft, n)
    res = {"days": n, "first_day": str(d["date"].iloc[0].date()), "last_day": str(d["date"].iloc[-1].date()),
           "green_share": float(y.mean()), "wf_days": ft - START, "test_days": n - ft, "models": {}}
    for k in names:
        res["models"][k] = {"wf": score(P[k][wf], y[wf]), "test": score(P[k][te], y[te]),
                            "wf_conf55": score(P[k][wf], y[wf], 0.55), "test_conf55": score(P[k][te], y[te], 0.55),
                            "wf_conf60": score(P[k][wf], y[wf], 0.60), "test_conf60": score(P[k][te], y[te], 0.60)}
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "daily_results.json").write_text(json.dumps(res, indent=1))
    pc = lambda x: "n/a" if x != x else f"{100 * x:.1f}%"
    L = ["# Pre-market day outlook: will the day candle be green?", "",
         f"{n} full sessions, {res['first_day']} to {res['last_day']}. Green days: {pc(res['green_share'])}.",
         f"Walk-forward on {res['wf_days']} days, final test on the last {res['test_days']}. Features use prior sessions only.", "",
         "| Model | WF accuracy (95% CI) | Test accuracy (95% CI) | WF at 55%+ confidence (days) | Test at 55%+ confidence (days) |", "|---|---|---|---|---|"]
    for k, m in res["models"].items():
        L.append(f"| {k} | {pc(m['wf']['hit'])} ({pc(m['wf']['ci'][0])} to {pc(m['wf']['ci'][1])}) | {pc(m['test']['hit'])} ({pc(m['test']['ci'][0])} to {pc(m['test']['ci'][1])}) | "
                 f"{pc(m['wf_conf55']['hit'])} ({m['wf_conf55']['n']}) | {pc(m['test_conf55']['hit'])} ({m['test_conf55']['n']}) |")
    (REPORTS / "daily_results.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    for k in ("logreg", "random_forest", "lightgbm"):
        m = res["models"][k]
        print(k, "conf60 wf", pc(m["wf_conf60"]["hit"]), m["wf_conf60"]["n"], "test", pc(m["test_conf60"]["hit"]), m["test_conf60"]["n"])


if __name__ == "__main__":
    main()
