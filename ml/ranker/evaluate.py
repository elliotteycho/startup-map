"""Cross-validated evaluation + permutation feature importance.

Single train/test splits are noisy, especially with few sessions. This runs
GroupKFold (sessions never split across folds) and reports mean +/- std for
every model, so differences are trustworthy rather than lucky.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from .metrics import evaluate
from .models import make_models


def cross_validate(frame: pd.DataFrame, feature_cols: list[str],
                   k: int = 5, n_splits: int = 5) -> dict:
    """Returns {model_name: {metric: (mean, std)}} across GroupKFold folds."""
    n_groups = frame["session_id"].nunique()
    n_splits = max(2, min(n_splits, n_groups))
    gkf = GroupKFold(n_splits=n_splits)
    per_model = defaultdict(list)

    for tr, te in gkf.split(frame, frame["y"], groups=frame["session_id"]):
        train, test = frame.iloc[tr], frame.iloc[te]
        if train["y"].nunique() < 2:
            continue
        for name, factory in make_models().items():
            model = factory().fit(train, feature_cols)
            per_model[name].append(evaluate(test, model.score(test), k=k))

    agg = {}
    for name, folds in per_model.items():
        metrics = [m for m in folds[0] if m != "eval_sessions"]
        agg[name] = {
            m: (float(np.nanmean([f[m] for f in folds])),
                float(np.nanstd([f[m] for f in folds])))
            for m in metrics
        }
    return agg


def permutation_importance(model, test: pd.DataFrame, feature_cols: list[str],
                           k: int = 5, n_repeats: int = 4, seed: int = 0) -> list[tuple[str, float]]:
    """Mean AUC drop when each feature column is shuffled. Higher = more important."""
    rng = np.random.default_rng(seed)
    base = evaluate(test, model.score(test), k=k)["AUC"]
    out = {}
    for col in feature_cols:
        drops = []
        for _ in range(n_repeats):
            perm = test.copy()
            perm[col] = rng.permutation(perm[col].to_numpy())
            drops.append(base - evaluate(perm, model.score(perm), k=k)["AUC"])
        out[col] = float(np.mean(drops))
    return sorted(out.items(), key=lambda kv: kv[1], reverse=True)
