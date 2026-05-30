"""Test suite for the internship ranker. Run:  python -m pytest -q"""
import numpy as np
import pandas as pd
import pytest

from ranker.data import make_synthetic
from ranker.features import engineer
from ranker.metrics import average_precision, evaluate, precision_at_k
from ranker.models import make_models


# ── feature engineering ──────────────────────────────────────────────────────

def test_engineer_synthetic_schema():
    comp, ev = make_synthetic(n_companies=50, n_sessions=80, seed=1)
    f = engineer(comp, ev)
    assert {"session_id", "company_id", "y"}.issubset(f.columns)
    assert f["y"].isin([0, 1]).all()
    assert len(f) > 0
    assert not f.isnull().any().any()  # no NaNs leak into features


def test_engineer_live_schema_no_crash():
    """Regression: production `companies` lacks founded_year / vandy_alumni_count /
    has_careers_page / days_since_round, and events lack fav_sector."""
    companies = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "sector": ["AI/ML", "Fintech", None, "SaaS"],
        "stage": ["seed", "series-a", None, "growth"],
        "headcount_range": ["11-50", None, "1-10", "51-200"],
        "location": ["SF Bay Area", None, "Remote", "Austin"],
        "intern_hiring_status": ["hiring", "open_to", None, "not_hiring"],
        "last_round_size_usd": [5_000_000, None, 1_000_000, 80_000_000],
        "last_round_date": ["2025-09-01", None, "2026-01-10", "2023-03-01"],
        "careers_page_url": ["https://x/careers", None, "https://y/jobs", None],
    })
    events = pd.DataFrame({
        "session_id": ["s1", "s1", "s2", "s2"],
        "company_id": [1, 2, 3, 4],
        "event_type": ["company_click", "impression", "company_click", "impression"],
    })
    f = engineer(companies, events)
    assert len(f) == 4
    assert set(f["has_careers_page"].unique()) <= {0.0, 1.0}
    assert (f["sector_match"] == 0.0).all()      # no fav_sector -> clean 0, not garbage
    assert f["y"].tolist() == [1, 0, 1, 0]


def test_has_careers_page_derived_from_url():
    companies = pd.DataFrame({
        "id": [1, 2], "sector": ["AI/ML", "SaaS"], "stage": ["seed", "seed"],
        "headcount_range": ["1-10", "1-10"], "location": ["Remote", "Remote"],
        "intern_hiring_status": ["hiring", "hiring"], "last_round_size_usd": [1, 1],
        "careers_page_url": ["https://x/careers", None],
    })
    events = pd.DataFrame({"session_id": ["s", "s"], "company_id": [1, 2],
                           "event_type": ["company_click", "impression"]})
    f = engineer(companies, events).set_index("company_id")
    assert f.loc[1, "has_careers_page"] == 1.0
    assert f.loc[2, "has_careers_page"] == 0.0


# ── metrics ──────────────────────────────────────────────────────────────────

def test_precision_at_k():
    assert precision_at_k(np.array([1, 0, 1, 0]), 2) == 0.5
    assert precision_at_k(np.array([1, 1]), 5) == 1.0  # k clamps to length


def test_average_precision():
    assert average_precision(np.array([1, 1, 0])) == pytest.approx(1.0)
    assert average_precision(np.array([0, 0, 0])) == 0.0


def test_evaluate_perfect_vs_worst_ranking():
    df = pd.DataFrame({"session_id": ["s"] * 4, "y": [1, 1, 0, 0]})
    perfect = evaluate(df, np.array([0.9, 0.8, 0.2, 0.1]), k=2)
    worst = evaluate(df, np.array([0.1, 0.2, 0.8, 0.9]), k=2)
    assert perfect["NDCG@2"] == pytest.approx(1.0)
    assert perfect["P@2"] == pytest.approx(1.0)
    assert worst["NDCG@2"] < perfect["NDCG@2"]


# ── models ───────────────────────────────────────────────────────────────────

def test_all_models_fit_and_score_shape():
    comp, ev = make_synthetic(n_companies=60, n_sessions=120, seed=2)
    f = engineer(comp, ev)
    feat = [c for c in f.columns if c not in ("session_id", "company_id", "y")]
    for name, factory in make_models().items():
        scores = factory().fit(f, feat).score(f)
        assert len(scores) == len(f), name
        assert np.isfinite(scores).all(), name


def test_real_models_beat_random_baseline():
    comp, ev = make_synthetic(n_companies=120, n_sessions=500, seed=3)
    f = engineer(comp, ev)
    feat = [c for c in f.columns if c not in ("session_id", "company_id", "y")]
    sessions = f["session_id"].unique()
    cut = int(len(sessions) * 0.75)
    train = f[f["session_id"].isin(sessions[:cut])]
    test = f[f["session_id"].isin(sessions[cut:])]
    models = make_models()

    rand = models["random (baseline)"]().fit(train, feat)
    logreg = models["logreg"]().fit(train, feat)
    rand_ndcg = evaluate(test, rand.score(test), k=5)["NDCG@5"]
    lr_ndcg = evaluate(test, logreg.score(test), k=5)["NDCG@5"]
    assert lr_ndcg > rand_ndcg + 0.1  # comfortably beats the random floor
