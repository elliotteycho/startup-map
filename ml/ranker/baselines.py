"""Trivial baselines. A ranking model only earns its keep if it beats these.

- RandomRanker: scores at random -> the NDCG floor for the data.
- PopularityRanker: scores every company by its global click rate in the
  training set (no personalization, no features). A strong, dumb baseline:
  if your fancy model can't beat "show the popular thing," it isn't doing much.

Both expose `fit(frame)` and `score(frame)` so the eval harness treats them
like any model.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class RandomRanker:
    def __init__(self, seed: int = 0):
        self.rng = np.random.default_rng(seed)

    def fit(self, frame: pd.DataFrame):
        return self

    def score(self, frame: pd.DataFrame) -> np.ndarray:
        return self.rng.random(len(frame))


class PopularityRanker:
    """Score = historical click-through rate of the company (Bayesian-smoothed)."""

    def __init__(self, alpha: float = 1.0, beta: float = 4.0):
        self.alpha, self.beta = alpha, beta  # prior ~ alpha/(alpha+beta)
        self.ctr_: dict = {}
        self.global_ctr_: float = 0.0

    def fit(self, frame: pd.DataFrame):
        self.global_ctr_ = float(frame["y"].mean())
        g = frame.groupby("company_id")["y"].agg(["sum", "count"])
        self.ctr_ = ((g["sum"] + self.alpha) / (g["count"] + self.alpha + self.beta)).to_dict()
        return self

    def score(self, frame: pd.DataFrame) -> np.ndarray:
        prior = (self.alpha) / (self.alpha + self.beta)
        return frame["company_id"].map(self.ctr_).fillna(prior).to_numpy()
