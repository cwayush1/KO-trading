"""Features on row t must not change when later candles are removed.
Run:  python -m tests.test_no_leakage   (from the backend folder)"""
import numpy as np

from kodesk.data import load_candles
from kodesk.features import build_features


def main():
    df = load_candles()
    full, feats = build_features(df)
    rng = np.random.default_rng(0)
    worst = 0.0
    for cut in sorted(rng.integers(20_000, len(df) - 1, size=6)):
        part, _ = build_features(df.iloc[: cut + 1].copy())
        a = full[feats].iloc[cut - 400 : cut + 1].to_numpy(float)
        b = part[feats].iloc[cut - 400 : cut + 1].to_numpy(float)
        same_nan = np.array_equal(np.isnan(a), np.isnan(b))
        diff = np.nanmax(np.abs(a - b))
        worst = max(worst, diff)
        assert same_nan and diff < 1e-9, f"feature values changed after truncating at row {cut}: {diff}"
    print(f"OK: no feature looks ahead (largest difference {worst:.2e})")


if __name__ == "__main__":
    main()
