"""Phase 5B tests: anomaly z-score logic + `/v1/momentum` API contract."""
from __future__ import annotations

import pandas as pd
import pytest

from ranker import serve
from ranker.momentum import (
    ANOMALY_MIN_BASELINE_SAMPLES, ANOMALY_Z_THRESHOLD,
    anomaly_z_score, is_anomaly,
)


# ─── anomaly_z_score ───────────────────────────────────────────────────────

def test_anomaly_returns_none_when_baseline_too_short():
    mean, std, z = anomaly_z_score(5.0, [1.0, 2.0, 3.0])
    assert mean is None and std is None and z is None


def test_anomaly_returns_none_when_baseline_degenerate_std():
    """All-equal baseline -> std==0 -> z undefined."""
    base = [1.0] * (ANOMALY_MIN_BASELINE_SAMPLES + 5)
    mean, std, z = anomaly_z_score(5.0, base)
    assert mean == 1.0 and std == 0.0 and z is None


def test_anomaly_z_score_matches_hand_calculation():
    base = [1.0, 2.0, 3.0, 4.0, 5.0,
            1.5, 2.5, 3.5, 4.5, 5.5,
            1.2, 2.2, 3.2, 4.2]            # 14 values
    mean, std, z = anomaly_z_score(10.0, base)
    assert mean is not None and std is not None and z is not None
    # mean of base ≈ 3.143, std (sample) ≈ 1.4xx, z ~ (10-3.143)/1.45 ≈ 4.7
    assert 4.0 < z < 6.0


def test_is_anomaly_threshold():
    assert is_anomaly(3.0) is True
    assert is_anomaly(ANOMALY_Z_THRESHOLD) is True
    assert is_anomaly(ANOMALY_Z_THRESHOLD - 0.01) is False
    assert is_anomaly(None) is False


# ─── /momentum endpoint ────────────────────────────────────────────────────

def test_momentum_endpoint_synthetic_basic():
    resp = serve.momentum(sector=None, n=5, only_anomalies=False, synthetic=True)
    assert resp["source"] == "synthetic"
    assert resp["n"] == 5
    assert isinstance(resp["results"], list)
    assert 1 <= len(resp["results"]) <= 5
    # results must be sorted descending by momentum
    moms = [r["momentum"] for r in resp["results"]]
    assert moms == sorted(moms, reverse=True)


def test_momentum_endpoint_sector_filter():
    resp = serve.momentum(sector="AI/ML", n=10, only_anomalies=False, synthetic=True)
    assert all(r["sector"] == "AI/ML" for r in resp["results"])


def test_momentum_endpoint_anomaly_filter_returns_subset():
    """With synthetic data there are no real snapshot anomalies (no z column),
    so only_anomalies must safely return an empty list rather than crash."""
    resp = serve.momentum(sector=None, n=10, only_anomalies=True, synthetic=True)
    assert resp["results"] == []


def test_momentum_endpoint_n_caps_results():
    resp = serve.momentum(sector=None, n=3, only_anomalies=False, synthetic=True)
    assert len(resp["results"]) <= 3
