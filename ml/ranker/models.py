"""Model zoo with a uniform interface so the eval harness treats every approach
the same way: `.fit(train_frame, feature_cols)` then `.score(frame) -> np.ndarray`.

Covers three families:
  - Baselines (random, popularity)            -- the floor every model must beat
  - Pointwise CTR (LogReg, GradBoost, XGBoost) -- predict P(click) per item
  - LambdaMART (XGBRanker, rank:ndcg)          -- a true learning-to-rank objective
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from .baselines import PopularityRanker, RandomRanker
from .features import build_preprocessor


def _dense(x):
    return np.asarray(x.todense(), dtype="float32") if hasattr(x, "todense") else np.asarray(x, dtype="float32")


class PipelineScorer:
    """Pointwise classifier wrapped in the preprocessing pipeline."""

    def __init__(self, clf):
        self.clf = clf

    def fit(self, frame, feature_cols):
        self.feature_cols = feature_cols
        self.pipe = Pipeline([("prep", build_preprocessor()), ("clf", self.clf)])
        self.pipe.fit(frame[feature_cols], frame["y"])
        return self

    def score(self, frame) -> np.ndarray:
        X = frame[self.feature_cols]
        if hasattr(self.pipe, "predict_proba"):
            return self.pipe.predict_proba(X)[:, 1]
        return self.pipe.decision_function(X)


class BaselineScorer:
    """Adapts a baseline (operates on the frame directly) to the common API."""

    def __init__(self, baseline):
        self.baseline = baseline

    def fit(self, frame, feature_cols):
        self.baseline.fit(frame)
        return self

    def score(self, frame) -> np.ndarray:
        return self.baseline.score(frame)


class LambdaMARTScorer:
    """XGBoost listwise learning-to-rank (objective rank:ndcg).

    Unlike the pointwise models, this optimizes the *ordering* within each
    session directly, using per-session group sizes.
    """

    def __init__(self, **params):
        self.params = dict(
            objective="rank:ndcg", n_estimators=300, max_depth=6,
            learning_rate=0.08, subsample=0.9, colsample_bytree=0.9,
            tree_method="hist", random_state=0, **params,
        )

    def fit(self, frame, feature_cols):
        from xgboost import XGBRanker
        self.feature_cols = feature_cols
        fs = frame.sort_values("session_id", kind="stable")
        self.prep = build_preprocessor().fit(fs[feature_cols])
        X = _dense(self.prep.transform(fs[feature_cols]))
        y = fs["y"].to_numpy()
        groups = fs.groupby("session_id", sort=True).size().to_numpy()
        self.model = XGBRanker(**self.params)
        self.model.fit(X, y, group=groups)
        return self

    def score(self, frame) -> np.ndarray:
        X = _dense(self.prep.transform(frame[self.feature_cols]))
        return self.model.predict(X)


def make_models() -> dict:
    """name -> zero-arg factory that returns a fresh, unfitted scorer."""
    models = {
        "random (baseline)": lambda: BaselineScorer(RandomRanker()),
        "popularity (baseline)": lambda: BaselineScorer(PopularityRanker()),
        "logreg": lambda: PipelineScorer(LogisticRegression(max_iter=1000, class_weight="balanced")),
        "grad_boost": lambda: PipelineScorer(GradientBoostingClassifier(random_state=0)),
    }
    try:
        import xgboost  # noqa: F401
        from xgboost import XGBClassifier
        models["xgboost (pointwise)"] = lambda: PipelineScorer(
            XGBClassifier(n_estimators=300, max_depth=5, learning_rate=0.08,
                          subsample=0.9, colsample_bytree=0.9, eval_metric="logloss",
                          tree_method="hist", random_state=0))
        models["lambdamart (LTR)"] = lambda: LambdaMARTScorer()
    except Exception:
        pass
    return models
