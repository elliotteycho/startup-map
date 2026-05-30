"""Ranking evaluation: grouped AUC, NDCG@k, precision@k, MAP.

Pointwise AUC measures calibration; the ranking metrics measure what the product
actually cares about -- did we put the relevant companies at the top of each
student's list. All ranking metrics are computed per session and averaged.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import ndcg_score, roc_auc_score


def precision_at_k(rel: np.ndarray, k: int) -> float:
    k = min(k, len(rel))
    return float(np.sum(rel[:k]) / k) if k else 0.0


def average_precision(rel: np.ndarray) -> float:
    if rel.sum() == 0:
        return 0.0
    hits = np.cumsum(rel)
    prec = hits / (np.arange(len(rel)) + 1)
    return float(np.sum(prec * rel) / rel.sum())


def evaluate(df: pd.DataFrame, scores: np.ndarray, k: int = 5) -> dict:
    """df needs columns: session_id, y. `scores` aligns row-for-row with df."""
    d = df.copy()
    d["score"] = scores

    # Pointwise AUC (guard single-class).
    try:
        auc = roc_auc_score(d["y"], d["score"])
    except ValueError:
        auc = float("nan")

    ndcgs, precs, aps = [], [], []
    for _, g in d.groupby("session_id"):
        if g["y"].sum() == 0 or len(g) < 2:
            continue  # no relevant item or nothing to rank
        y_true = g["y"].to_numpy().reshape(1, -1)
        y_score = g["score"].to_numpy().reshape(1, -1)
        ndcgs.append(ndcg_score(y_true, y_score, k=k))
        order = np.argsort(-g["score"].to_numpy())
        rel_sorted = g["y"].to_numpy()[order]
        precs.append(precision_at_k(rel_sorted, k))
        aps.append(average_precision(rel_sorted))

    return {
        "AUC": round(auc, 4),
        f"NDCG@{k}": round(float(np.mean(ndcgs)), 4) if ndcgs else float("nan"),
        f"P@{k}": round(float(np.mean(precs)), 4) if precs else float("nan"),
        "MAP": round(float(np.mean(aps)), 4) if aps else float("nan"),
        "eval_sessions": len(ndcgs),
    }
