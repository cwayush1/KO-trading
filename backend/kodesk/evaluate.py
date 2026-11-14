"""Chronological splits and metrics. Nothing here shuffles rows."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support

from .config import FINAL_TEST_SESSIONS, VAL_FRACTION, WF_INITIAL_TRAIN, WF_TEST_BLOCK


def final_test_start(n_sessions: int) -> int:
    return n_sessions - FINAL_TEST_SESSIONS


def walk_forward_folds(n_dev_sessions: int) -> list[tuple[int, int, int]]:
    """Expanding window over the development sessions.
    Each fold is (train_end, test_start, test_end): train on sessions [0, train_end),
    test on [test_start, test_end). Targets never cross a session, so splitting on
    session boundaries leaves no label overlap between train and test."""
    folds, start = [], WF_INITIAL_TRAIN
    while start + WF_TEST_BLOCK <= n_dev_sessions:
        end = start + WF_TEST_BLOCK
        if n_dev_sessions - end < WF_TEST_BLOCK:       # fold the remainder into the last block
            end = n_dev_sessions
        folds.append((start, start, end))
        start = end
    return folds


def split_train_val(train_end: int) -> int:
    """Session index where the validation tail begins."""
    return int(train_end * (1 - VAL_FRACTION))


def ece(p: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    """Expected calibration error of the top-class probability."""
    conf, pred = p.max(axis=1), p.argmax(axis=1)
    hit = (pred == y).astype(float)
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for a, b in zip(edges[:-1], edges[1:]):
        m = (conf > a) & (conf <= b)
        if m.any():
            total += m.mean() * abs(hit[m].mean() - conf[m].mean())
    return float(total)


def directional(p: np.ndarray, fwd: np.ndarray, min_conf: float = 0.0) -> dict:
    """Directional accuracy: of the times the model called UP or DOWN (with at
    least `min_conf` probability), how often did price actually end that side
    of where it started? Coverage is the share of rows that got a call."""
    pred, conf = p.argmax(axis=1), p.max(axis=1)
    call = (pred != 1) & (conf >= min_conf)
    n = int(call.sum())
    if n == 0:
        return {"hit": np.nan, "coverage": 0.0, "n": 0}
    side = np.where(pred[call] == 2, 1.0, -1.0)
    return {"hit": float((np.sign(fwd[call]) == side).mean()), "coverage": float(call.mean()), "n": n}


def metrics(p: np.ndarray, y: np.ndarray, fwd: np.ndarray) -> dict:
    y = y.astype(int)
    pred = p.argmax(axis=1)
    prec, rec, _, _ = precision_recall_fscore_support(y, pred, labels=[0, 1, 2], zero_division=0)
    d = directional(p, fwd)
    return {
        "n": int(len(y)),
        "accuracy": float((pred == y).mean()),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "macro_f1": float(f1_score(y, pred, average="macro", labels=[0, 1, 2], zero_division=0)),
        "precision_down": float(prec[0]), "precision_neutral": float(prec[1]), "precision_up": float(prec[2]),
        "recall_down": float(rec[0]), "recall_neutral": float(rec[1]), "recall_up": float(rec[2]),
        "dir_hit": d["hit"], "dir_coverage": d["coverage"], "dir_n": d["n"],
        "ece": ece(p, y),
        "confusion": confusion_matrix(y, pred, labels=[0, 1, 2]).tolist(),
    }


def baseline_probs(kind: str, ytr: np.ndarray, Xte_ret: np.ndarray, n: int) -> np.ndarray:
    """Simple reference forecasts every model has to beat."""
    p = np.zeros((n, 3))
    if kind == "majority":                     # always the most common class in training
        p[:, np.bincount(ytr.astype(int), minlength=3).argmax()] = 1.0
    elif kind == "always_up":
        p[:, 2] = 1.0
    elif kind == "momentum":                   # whatever the last move did, expect more
        p[np.arange(n), np.where(Xte_ret > 0, 2, 0)] = 1.0
    elif kind == "reversal":                   # whatever the last move did, expect the opposite
        p[np.arange(n), np.where(Xte_ret > 0, 0, 2)] = 1.0
    return p
