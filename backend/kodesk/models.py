"""Candidate models behind one interface: fit(train, val) then predict_proba."""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

MODEL_NAMES = ["logreg", "random_forest", "extra_trees", "lightgbm", "xgboost", "catboost"]


class Model:
    """Wraps a classifier. Boosters use the validation tail for early stopping;
    every model then gets its probabilities calibrated on that same tail."""

    def __init__(self, name: str, seed: int = 7):
        self.name, self.seed = name, seed
        self.clf = None
        self.cal: LogisticRegression | None = None

    def fit(self, Xtr, ytr, Xva, yva, calibrate: bool = True):
        n, s = self.name, self.seed
        if n == "logreg":
            # Scaler statistics come from the training rows only.
            self.clf = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=0.05, max_iter=400))
            self.clf.fit(Xtr, ytr)
        elif n in ("random_forest", "extra_trees"):
            cls = RandomForestClassifier if n == "random_forest" else ExtraTreesClassifier
            self.clf = make_pipeline(
                SimpleImputer(strategy="median"),
                cls(n_estimators=200, max_depth=8, min_samples_leaf=100, max_features=0.3,
                    bootstrap=True, max_samples=0.25, n_jobs=-1, random_state=s),
            )
            self.clf.fit(Xtr, ytr)
        elif n == "lightgbm":
            import lightgbm as lgb
            self.clf = lgb.LGBMClassifier(
                n_estimators=1500, learning_rate=0.02, num_leaves=15, min_child_samples=300,
                subsample=0.7, subsample_freq=1, colsample_bytree=0.5, reg_lambda=10.0,
                random_state=s, n_jobs=2, verbose=-1)
            self.clf.fit(Xtr, ytr, eval_set=[(Xva, yva)], callbacks=[lgb.early_stopping(100, verbose=False)])
        elif n == "xgboost":
            import xgboost as xgb
            self.clf = xgb.XGBClassifier(
                n_estimators=1500, learning_rate=0.02, max_depth=4, min_child_weight=200,
                subsample=0.7, colsample_bytree=0.5, reg_lambda=10.0, tree_method="hist",
                early_stopping_rounds=100, random_state=s, n_jobs=2)
            self.clf.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
        elif n == "catboost":
            from catboost import CatBoostClassifier
            self.clf = CatBoostClassifier(
                iterations=1000, learning_rate=0.04, depth=5, l2_leaf_reg=10.0, rsm=0.5,
                loss_function="MultiClass", early_stopping_rounds=100, random_seed=s,
                thread_count=2, verbose=False)
            self.clf.fit(Xtr, ytr, eval_set=(Xva, yva))
        else:
            raise ValueError(n)

        if calibrate:
            # A small logistic layer on the log-probabilities, learned on rows the model did
            # not train on. It is smooth, so it can never output an exact 0% or 100%.
            self.cal = LogisticRegression(C=10.0, max_iter=500).fit(self._logp(Xva), yva)
        return self

    def _raw(self, X) -> np.ndarray:
        return np.asarray(self.clf.predict_proba(X), dtype=float)

    def _logp(self, X) -> np.ndarray:
        return np.log(np.clip(self._raw(X), 1e-6, 1.0))

    def predict_proba(self, X, calibrated: bool = True) -> np.ndarray:
        if calibrated and self.cal is not None:
            return self.cal.predict_proba(self._logp(X))
        return self._raw(X)
