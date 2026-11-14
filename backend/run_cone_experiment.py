"""Out-of-sample test of the range cone. Writes reports/cone_results.{json,md}.

For each horizon: how often the future close landed inside the 50% and 80% cones
(it should be close to 50% and 80%), and how the model's cone compares with a
cone of one fixed width for the same job.
  python run_cone_experiment.py
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from kodesk.config import REPORTS
from kodesk.cone import CONE, LEVELS, OPENING, add_cone_labels, cone_z, opening_table, train_cone, train_opening
from kodesk.data import load_candles
from kodesk.evaluate import final_test_start, split_train_val, walk_forward_folds
from kodesk.features import build_features


def pinball(z, q, level):
    return float(np.mean(np.maximum(level * (z - q), (level - 1) * (z - q))))


def summarize(r: pd.DataFrame) -> dict:
    """r has, per row: z (what happened), q50/q80 (model), b50/b80 (fixed-width cone)."""
    out = {"n": int(len(r)), "days": int(r.session.nunique())}
    for lv in LEVELS:
        k = int(lv * 100)
        out[f"cover{k}"] = float((r.z <= r[f"q{k}"]).mean())
        out[f"fixed_cover{k}"] = float((r.z <= r[f"b{k}"]).mean())
        out[f"skill{k}"] = 1 - pinball(r.z, r[f"q{k}"], lv) / pinball(r.z, r[f"b{k}"], lv)
    # Does the cone widen at the right times? Split by how wide the model drew it.
    third = pd.qcut(r.q80, 3, labels=["narrow", "middle", "wide"])
    out["by_width"] = {str(name): {"cover80": float((g.z <= g.q80).mean()), "fixed_cover80": float((g.z <= g.b80).mean()),
                                   "width_vs_fixed": float((g.q80 / g.b80).mean())} for name, g in r.groupby(third, observed=True)}
    return out


def main():
    candles = load_candles()
    frame, feats = build_features(candles)
    d = add_cone_labels(frame)
    n_sessions = int(d["session"].max()) + 1
    ft = final_test_start(n_sessions)
    table = opening_table(candles)

    def run(train_end: int, a: int, b: int) -> dict[int, pd.DataFrame]:
        cone = train_cone(d, feats, split_train_val(train_end), train_end)
        res = {}
        for minutes in CONE:
            te = d[(d.session >= a) & (d.session < b) & d[f"z_{minutes}"].notna()].dropna(subset=feats)
            q = cone_z(cone, te[feats].to_numpy("float32"))
            res[minutes] = pd.DataFrame({"session": te.session.to_numpy(), "z": te[f"z_{minutes}"].to_numpy(),
                                         "q50": q[(minutes, 0.5)], "q80": q[(minutes, 0.8)],
                                         "b50": cone["usual"][(minutes, 0.5)], "b80": cone["usual"][(minutes, 0.8)]})
        return res

    def opening(train_end: int, a: int, b: int) -> dict:
        q = train_opening(table, train_end)
        t = table[(table.index >= a - 1) & (table.index < b - 1)]
        return {m: {f"cover{int(lv * 100)}": float((t[f"z_{m}"].dropna() <= q[(m, lv)]).mean()) for lv in LEVELS} | {"n": int(t[f"z_{m}"].notna().sum())}
                for m in OPENING}

    parts = [run(e, a, b) for e, a, b in walk_forward_folds(ft)]
    wf = {m: summarize(pd.concat([p[m] for p in parts])) for m in CONE}
    test = {m: summarize(run(ft, ft, n_sessions)[m]) for m in CONE}
    first = walk_forward_folds(ft)[0][1]
    out = {"wf": wf, "test": test, "opening": {"wf": opening(first, first, ft), "test": opening(ft, ft, n_sessions)},
           "model": "LightGBM quantile models, conformal-calibrated", "features": len(feats)}
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "cone_results.json").write_text(json.dumps(out, indent=2))

    pc = lambda x: f"{x * 100:.1f}%"
    lines = ["# Range cone: how far price travels in the next 15 to 120 minutes", "",
             "Share of future closes that landed inside the cone. Targets are 50% and 80%.",
             "Skill is how much lower the model's quantile loss is than a cone of one fixed width (in typical-move units).", "",
             "| Period | Horizon | Inside 50% cone | Inside 80% cone | Skill vs fixed, 80% | Narrow third: cover / width | Wide third: cover / width |",
             "|---|---|---|---|---|---|---|"]
    for name, s in (("Walk-forward", wf), ("Final held-out", test)):
        for m in CONE:
            x, n, w = s[m], s[m]["by_width"]["narrow"], s[m]["by_width"]["wide"]
            lines.append(f"| {name} | {m} min | {pc(x['cover50'])} | {pc(x['cover80'])} | {pc(x['skill80'])} | "
                         f"{pc(n['cover80'])} at {n['width_vs_fixed']:.2f}x | {pc(w['cover80'])} at {w['width_vs_fixed']:.2f}x |")
    lines += ["", "A fixed-width cone, scored on the same thirds (final held-out, 60 min): "
              f"narrow {pc(test[60]['by_width']['narrow']['fixed_cover80'])}, wide {pc(test[60]['by_width']['wide']['fixed_cover80'])}. "
              "It is too wide when the market is quiet and too narrow when it is busy.", "",
              "## Opening cone (made at the close, for the next session)", "",
              "| Period | Minutes after the open | Inside 50% cone | Inside 80% cone | Sessions |", "|---|---|---|---|---|"]
    for name, s in (("Walk-forward", out["opening"]["wf"]), ("Final held-out", out["opening"]["test"])):
        for m in OPENING:
            lines.append(f"| {name} | {m} | {pc(s[m]['cover50'])} | {pc(s[m]['cover80'])} | {s[m]['n']} |")
    (REPORTS / "cone_results.md").write_text("\n".join(lines) + "\n")
    print((REPORTS / "cone_results.md").read_text())


if __name__ == "__main__":
    main()
