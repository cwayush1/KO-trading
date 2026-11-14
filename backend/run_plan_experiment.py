"""Test the day plan: every 5-minute candle called green or red before the open.

Directional accuracy = share of non-flat candles whose colour was called correctly.
Usage:  python run_plan_experiment.py     (writes reports/plan_results.json and .md)
"""
from __future__ import annotations

import json

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from kodesk.config import FINAL_TEST_SESSIONS, REPORTS
from kodesk.data import load_candles
from kodesk.dayplan import PlanData, make_plan_model

BLOCK = 63


def day_ci(hit, sess, n_boot=2000):
    ids, inv = np.unique(sess, return_inverse=True)
    h, c = np.bincount(inv, weights=hit), np.bincount(inv).astype(float)
    draw = np.random.default_rng(0).integers(0, len(ids), size=(n_boot, len(ids)))
    v = h[draw].sum(1) / c[draw].sum(1)
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))], h / c


def main():
    pd_ = PlanData(load_candles())
    f = pd_.training_frame()
    X, y, sess = f[pd_.feats].to_numpy(float), f["y"].to_numpy(int), f["session"].to_numpy()
    n_sessions = int(pd_.days.index.max()) + 1
    ft = n_sessions - FINAL_TEST_SESSIONS
    first = int(sess.min()) + 252
    blocks = [(a, min(a + BLOCK, ft)) for a in range(first, ft, BLOCK)] + [(ft, n_sessions)]
    names = ["always_green", "slot_habit", "same_as_yesterday", "logreg", "lightgbm"]
    P = {k: np.full(len(y), np.nan) for k in names}
    yesterday = np.array([pd_.green.loc[s - 1].to_numpy()[int(j)] for s, j in zip(sess, f["slot"])])
    for a, b in blocks:
        tr, te = sess < a, (sess >= a) & (sess < b)
        P["always_green"][te] = 1.0
        P["slot_habit"][te] = (f["slot_green_60"].to_numpy()[te] >= 0.5).astype(float)   # this slot is usually green
        P["same_as_yesterday"][te] = np.where(np.isnan(yesterday[te]), 1.0, yesterday[te])
        lr = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=0.02, max_iter=500))
        P["logreg"][te] = lr.fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
        P["lightgbm"][te] = make_plan_model().fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
        print("block", a, b, "done", flush=True)

    wf, te = (sess >= first) & (sess < ft), sess >= ft
    flat_share = float(pd_.green.isna().to_numpy()[pd_.days["bars"].to_numpy() >= 70].mean())
    res = {"flat_or_missing_share": flat_share, "green_share": float(y.mean()), "models": {},
           "wf_days": int(len(np.unique(sess[wf]))), "test_days": int(len(np.unique(sess[te]))),
           "wf_candles": int(wf.sum()), "test_candles": int(te.sum())}
    for k in names:
        hit = ((P[k] >= 0.5).astype(int) == y).astype(float)
        m = {}
        for tag, mask in (("wf", wf), ("test", te)):
            ci, per_day = day_ci(hit[mask], sess[mask])
            m[tag] = {"hit": float(hit[mask].mean()), "ci": ci, "candles": int(mask.sum()),
                      "day_min": float(per_day.min()), "day_max": float(per_day.max()),
                      "days_60_plus": float((per_day >= 0.60).mean()), "days_under_40": float((per_day < 0.40).mean()),
                      "day_std": float(per_day.std())}
            conf = np.abs(P[k] - 0.5) >= 0.05                       # calls at 55%+ only
            mm = mask & conf
            m[tag + "_conf55"] = {"hit": float(hit[mm].mean()) if mm.any() else float("nan"), "candles": int(mm.sum())}
        res["models"][k] = m
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "plan_results.json").write_text(json.dumps(res, indent=1))
    pc = lambda x: "n/a" if x != x else f"{100 * x:.1f}%"
    L = ["# Day plan: every 5-minute candle called before the open", "",
         f"Walk-forward: {res['wf_days']} days, {res['wf_candles']} candles. Final test: {res['test_days']} days, {res['test_candles']} candles.",
         f"Green candles: {pc(res['green_share'])} of non-flat ones.", "",
         "| Model | WF accuracy (95% CI) | Test accuracy (95% CI) | Best / worst single day (WF) | Days at 60%+ (WF) | WF at 55%+ confidence (candles) | Test at 55%+ confidence (candles) |", "|---|---|---|---|---|---|---|"]
    for k, m in res["models"].items():
        L.append(f"| {k} | {pc(m['wf']['hit'])} ({pc(m['wf']['ci'][0])} to {pc(m['wf']['ci'][1])}) | {pc(m['test']['hit'])} ({pc(m['test']['ci'][0])} to {pc(m['test']['ci'][1])}) | "
                 f"{pc(m['wf']['day_max'])} / {pc(m['wf']['day_min'])} | {pc(m['wf']['days_60_plus'])} | {pc(m['wf_conf55']['hit'])} ({m['wf_conf55']['candles']}) | {pc(m['test_conf55']['hit'])} ({m['test_conf55']['candles']}) |")
    (REPORTS / "plan_results.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
