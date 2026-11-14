"""Turn saved predictions into comparison tables.

Usage:  python build_report.py [--k 0.35]
Writes reports/results.md and reports/results.json.
"""
from __future__ import annotations

import argparse
import json
import pickle

import numpy as np

from kodesk.config import HORIZONS, K_NEUTRAL, REPORTS
from sklearn.metrics import roc_auc_score

from kodesk.evaluate import directional, metrics
from kodesk.models import MODEL_NAMES

BASELINES = ["majority", "always_up", "momentum", "reversal"]
CONF_GRID = [0.0, 0.40, 0.45, 0.50, 0.55, 0.60]


def session_ci(p, fwd, sess, min_conf=0.0, n_boot=2000, seed=0):
    """95% interval for directional accuracy, resampling whole trading days.
    Forecasts inside one day overlap and move together, so days are the honest unit."""
    pred, conf = p.argmax(1), p.max(1)
    call = (pred != 1) & (conf >= min_conf)
    if call.sum() < 30:
        return [float("nan"), float("nan")]
    side = np.where(pred[call] == 2, 1.0, -1.0)
    hit = (np.sign(fwd[call]) == side).astype(float)
    s = sess[call]
    ids, inv = np.unique(s, return_inverse=True)
    hits = np.bincount(inv, weights=hit, minlength=len(ids))
    cnt = np.bincount(inv, minlength=len(ids)).astype(float)
    rng = np.random.default_rng(seed)
    draw = rng.integers(0, len(ids), size=(n_boot, len(ids)))
    vals = hits[draw].sum(1) / cnt[draw].sum(1)
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def pct(x):
    return "n/a" if x is None or not np.isfinite(x) else f"{100 * x:.1f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=float, default=K_NEUTRAL)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    with open(REPORTS / f"predictions_k{args.k}{args.tag}.pkl", "rb") as f:
        out = pickle.load(f)

    models = [m for m in MODEL_NAMES if (m, list(out["rows"])[0]) in out["pred"]]
    res = {"k": args.k, "n_features": len(out["features"]), "table": [], "confidence": [], "breakdown": {}, "folds": {}}
    for minutes, rows in out["rows"].items():
        fold = rows["fold"]
        last = fold.max()
        wf, ft = (fold >= 0) & (fold < last), fold == last
        for name in BASELINES + models:
            p = out["pred"][(name, minutes)]
            praw = out["pred"][(name + "_raw", minutes)]
            row = {"model": name, "horizon": minutes}
            for tag, m in (("wf", wf), ("test", ft)):
                mt = metrics(p[m], rows["y"][m], rows["fwd"][m])
                for k2, v in mt.items():
                    row[f"{tag}_{k2}"] = v
                row[f"{tag}_dir_ci"] = session_ci(p[m], rows["fwd"][m], rows["session"][m])
                if name in models:
                    row[f"{tag}_ece_uncalibrated"] = metrics(praw[m], rows["y"][m], rows["fwd"][m])["ece"]
                    yy = rows["y"][m]
                    moved = m & (rows["y"] != 1)
                    # Two separate skills: will price move at all, and if it moves, which way.
                    row[f"{tag}_move_auc"] = float(roc_auc_score(yy != 1, 1 - p[m, 1]))
                    row[f"{tag}_direction_auc"] = float(roc_auc_score(rows["y"][moved] == 2, p[moved, 2] / (p[moved, 2] + p[moved, 0])))
                    row[f"{tag}_base_move"] = float((yy != 1).mean())
            per_fold = [directional(p[fold == f], rows["fwd"][fold == f])["hit"] for f in range(last)]
            row["wf_dir_by_fold"] = per_fold
            res["table"].append(row)
            if name in models:
                for c in CONF_GRID:
                    a = directional(p[wf], rows["fwd"][wf], c)
                    b = directional(p[ft], rows["fwd"][ft], c)
                    res["confidence"].append({
                        "model": name, "horizon": minutes, "min_conf": c,
                        "wf_hit": a["hit"], "wf_coverage": a["coverage"], "wf_n": a["n"],
                        "test_hit": b["hit"], "test_coverage": b["coverage"], "test_n": b["n"],
                        "test_ci": session_ci(p[ft], rows["fwd"][ft], rows["session"][ft], c),
                    })

    # Stability of the gradient-boosted model across conditions (all out-of-sample rows).
    ref = "lightgbm" if "lightgbm" in models else models[0]
    for minutes, rows in out["rows"].items():
        p = out["pred"][(ref, minutes)]
        oos = rows["fold"] >= 0
        year = rows["time"].astype("datetime64[Y]").astype(int) + 1970
        sig = rows["sigma"]
        cut = np.nanpercentile(sig[oos], [33.3, 66.7])
        volb = np.where(sig <= cut[0], "calm third", np.where(sig <= cut[1], "middle third", "volatile third"))
        slot = rows["slot"]
        tod = np.where(slot < 12, "09:30-10:30", np.where(slot >= 54, "14:00-16:00", "10:30-14:00"))
        trend = np.where(rows["adx"] >= 25, "trending (ADX 25+)", "not trending")
        bd = {}
        for label, key in (("year", year), ("volatility", volb), ("time of day", tod), ("regime", trend)):
            for val in sorted(set(key[oos].tolist())):
                m = oos & (key == val)
                dd = directional(p[m], rows["fwd"][m])
                bd[f"{label}: {val}"] = {
                    "rows": int(m.sum()), "accuracy": float((p[m].argmax(1) == rows["y"][m]).mean()),
                    "dir_hit": dd["hit"], "dir_coverage": dd["coverage"],
                }
        res["breakdown"][minutes] = bd
    res["importance"] = out.get("importance", {})

    # ---------------------------------------------------------------- markdown
    L = [f"# KO forecast experiments (neutral band k = {args.k})", ""]
    L += ["Directional accuracy = of the forecasts that said UP or DOWN, the share where price really",
          "finished on that side. Coverage = share of moments that got an UP or DOWN call at all.",
          "WF = walk-forward on the development period. Test = final ~6 months, scored once.", ""]
    for minutes in out["rows"]:
        L += [f"## {minutes}-minute horizon", "",
              "| Model | WF 3-class acc | WF balanced acc | WF macro F1 | WF directional | WF coverage | WF fold range | Test directional (95% CI) | Test coverage | Test ECE |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for r in [x for x in res["table"] if x["horizon"] == minutes]:
            f = [v for v in r["wf_dir_by_fold"] if v is not None and np.isfinite(v)]
            fr = f"{pct(min(f))} to {pct(max(f))}" if f else "n/a"
            ci = r["test_dir_ci"]
            L.append(f"| {r['model']} | {pct(r['wf_accuracy'])} | {pct(r['wf_balanced_accuracy'])} | {r['wf_macro_f1']:.3f} | "
                     f"{pct(r['wf_dir_hit'])} | {pct(r['wf_dir_coverage'])} | {fr} | {pct(r['test_dir_hit'])} ({pct(ci[0])} to {pct(ci[1])}) | "
                     f"{pct(r['test_dir_coverage'])} | {r['test_ece']:.3f} |")
        L.append("")
    L += ["## Two skills, measured separately (AUC: 0.50 = coin flip, 1.00 = perfect)", "",
          "Move = can the model tell an active period from a quiet one. Direction = given price moved, did the model favour the right side.", "",
          "| Model | Horizon | WF move AUC | WF direction AUC | Test move AUC | Test direction AUC |", "|---|---|---|---|---|---|"]
    for r in res["table"]:
        if "wf_move_auc" in r:
            L.append(f"| {r['model']} | {r['horizon']} | {r['wf_move_auc']:.3f} | {r['wf_direction_auc']:.3f} | {r['test_move_auc']:.3f} | {r['test_direction_auc']:.3f} |")
    L.append("")
    L += ["## Directional accuracy when only confident calls count", "",
          "| Model | Horizon | Min confidence | WF directional | WF coverage | Test directional (95% CI) | Test coverage | Test calls |", "|---|---|---|---|---|---|---|---|"]
    for r in res["confidence"]:
        if r["model"] in ("lightgbm", "logreg") and r["min_conf"] > 0:
            L.append(f"| {r['model']} | {r['horizon']} | {r['min_conf']:.2f} | {pct(r['wf_hit'])} | {pct(r['wf_coverage'])} | "
                     f"{pct(r['test_hit'])} ({pct(r['test_ci'][0])} to {pct(r['test_ci'][1])}) | {pct(r['test_coverage'])} | {r['test_n']} |")
    L.append("")
    for minutes, bd in res["breakdown"].items():
        L += [f"## {ref}, {minutes} minutes: stability across conditions (all out-of-sample rows)", "",
              "| Condition | Rows | 3-class acc | Directional | Coverage |", "|---|---|---|---|---|"]
        L += [f"| {k2} | {v['rows']} | {pct(v['accuracy'])} | {pct(v['dir_hit'])} | {pct(v['dir_coverage'])} |" for k2, v in bd.items()]
        L.append("")
    if res["importance"]:
        L += ["## Most useful features (LightGBM gain, model trained on the development period)", ""]
        for minutes, imp in res["importance"].items():
            tot = sum(imp.values()) or 1.0
            top = sorted(imp.items(), key=lambda kv: -kv[1])[:10]
            L.append(f"- {minutes} min: " + ", ".join(f"{k2} {100 * v / tot:.0f}%" for k2, v in top))
        L.append("")

    (REPORTS / f"results{args.tag}.md").write_text("\n".join(L))
    (REPORTS / f"results{args.tag}.json").write_text(json.dumps(res, indent=1, default=float))
    print("\n".join(L))


if __name__ == "__main__":
    main()
