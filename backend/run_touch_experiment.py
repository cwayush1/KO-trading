"""Out-of-sample test of the touch ladder. Writes reports/touch_results.{json,md}.

A level labelled 25% should be touched about 25% of the time. The table shows how
often each label came true, above and below the price, on sessions the models never saw.
  python run_touch_experiment.py
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from kodesk.config import REPORTS
from kodesk.data import load_candles
from kodesk.evaluate import final_test_start, split_train_val, walk_forward_folds
from kodesk.features import build_features
from kodesk.touch import ODDS, SIDES, WINDOWS, add_touch_labels, touch_z, train_touch, usual_z


def pinball(y, q, level):
    return float(np.mean(np.maximum(level * (y - q), (level - 1) * (y - q))))


def summarize(r: pd.DataFrame) -> dict:
    out = {"n": int(len(r)), "days": int(r.session.nunique())}
    for side in SIDES:
        for odds in ODDS:
            k = f"{side}{int(odds * 100)}"
            q, b = r[f"q{int(odds * 100)}"], r[f"b{int(odds * 100)}"]
            out[k] = float((r[side] >= q).mean())                           # how often the level was really touched
            out[f"fixed_{k}"] = float((r[side] >= b).mean())
            out[f"skill_{k}"] = 1 - pinball(r[side], q, 1 - odds) / pinball(r[side], b, 1 - odds)
    # Does the ladder stretch at the right times? Split by how far out the model put the 25% level.
    third = pd.qcut(r.q25, 3, labels=["near", "middle", "far"])
    both = lambda g, col: float(((g.up >= g[col]).mean() + (g.down >= g[col]).mean()) / 2)
    out["by_distance"] = {str(name): {"touched25": both(g, "q25"), "fixed_touched25": both(g, "b25"),
                                      "distance_vs_fixed": float((g.q25 / g.b25).mean())} for name, g in r.groupby(third, observed=True)}
    return out


def main():
    frame, feats = build_features(load_candles())
    d = add_touch_labels(frame)
    n_sessions = int(d["session"].max()) + 1
    ft = final_test_start(n_sessions)

    def run(train_end: int, a: int, b: int) -> dict[int, pd.DataFrame]:
        touch = train_touch(d, feats, split_train_val(train_end), train_end)
        res = {}
        for minutes in WINDOWS:
            te = d[(d.session >= a) & (d.session < b) & d[f"up_{minutes}"].notna()].dropna(subset=feats)
            z = touch_z(touch, te[feats].to_numpy("float32"))
            cols = {"session": te.session.to_numpy(), "up": te[f"up_{minutes}"].to_numpy(), "down": te[f"down_{minutes}"].to_numpy()}
            usual = usual_z(touch)
            for odds in ODDS:
                cols[f"q{int(odds * 100)}"] = z[(minutes, odds)]
                cols[f"b{int(odds * 100)}"] = usual[(minutes, odds)]
            res[minutes] = pd.DataFrame(cols)
        return res

    parts = [run(e, a, b) for e, a, b in walk_forward_folds(ft)]
    wf = {m: summarize(pd.concat([p[m] for p in parts])) for m in WINDOWS}
    test = {m: summarize(run(ft, ft, n_sessions)[m]) for m in WINDOWS}
    out = {"wf": wf, "test": test, "model": "LightGBM quantile models, conformal-calibrated", "features": len(feats)}
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "touch_results.json").write_text(json.dumps(out, indent=2))

    pc = lambda x: f"{x * 100:.1f}%"
    lines = ["# Touch ladder: chance that price touches a level inside the window", "",
             "Each cell is how often levels with that label were really touched (up side / down side). It should match the label.", "",
             "| Period | Window | Labelled 75% | Labelled 50% | Labelled 25% | Labelled 10% | Skill vs fixed distance (50%) |", "|---|---|---|---|---|---|---|"]
    for name, s in (("Walk-forward", wf), ("Final held-out", test)):
        for m in WINDOWS:
            x = s[m]
            cells = " | ".join(f"{pc(x[f'up{int(o * 100)}'])} / {pc(x[f'down{int(o * 100)}'])}" for o in ODDS)
            lines.append(f"| {name} | {m} min | {cells} | {pc((x['skill_up50'] + x['skill_down50']) / 2)} |")
    lines += ["", "## Does the ladder stretch at the right times?", "",
              "Moments split into thirds by how far out the model put its 25% level. Each should still be touched about 25% of the time.", "",
              "| Period | Window | Near third: touched / distance | Far third: touched / distance | Fixed distance: near / far |", "|---|---|---|---|---|"]
    for name, s in (("Walk-forward", wf), ("Final held-out", test)):
        for m in WINDOWS:
            n, f = s[m]["by_distance"]["near"], s[m]["by_distance"]["far"]
            lines.append(f"| {name} | {m} min | {pc(n['touched25'])} at {n['distance_vs_fixed']:.2f}x | {pc(f['touched25'])} at {f['distance_vs_fixed']:.2f}x | "
                         f"{pc(n['fixed_touched25'])} / {pc(f['fixed_touched25'])} |")
    (REPORTS / "touch_results.md").write_text("\n".join(lines) + "\n")
    print((REPORTS / "touch_results.md").read_text())


if __name__ == "__main__":
    main()
