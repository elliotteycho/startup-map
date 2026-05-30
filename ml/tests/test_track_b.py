"""Tests for Track B (Market Pulse) pieces: change-log emitter + momentum."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

# `scraper/` is a sibling tree of `ml/`; make it importable from these tests.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scraper.event_emitter import diff_and_emit  # noqa: E402
from ranker.momentum import compute_momentum, top_n  # noqa: E402
from ranker.synth import synth_companies, synthesize_events  # noqa: E402


# ─── event_emitter.diff_and_emit ────────────────────────────────────────────

def test_first_seen_company_emits_initial_state_only():
    after = {"id": 7, "sector": "AI/ML", "stage": "seed"}
    out = diff_and_emit(prior=None, after=after)
    assert len(out) == 1
    assert out[0]["kind"] == "initial_state"
    assert out[0]["company_id"] == 7


def test_unchanged_row_emits_nothing():
    row = {
        "id": 7, "sector": "AI/ML", "stage": "seed",
        "headcount_range": "1-10", "intern_hiring_status": "unknown",
        "last_round_date": "2025-06-01", "last_round_size_usd": 2_000_000,
        "location": "Remote", "one_line_pitch": "AI assistants for sales",
    }
    assert diff_and_emit(prior=row, after=row) == []


def test_multiple_simultaneous_changes_emit_distinct_events():
    prior = {
        "id": 7, "sector": "AI/ML", "stage": "seed", "headcount_range": "1-10",
        "intern_hiring_status": "unknown", "last_round_date": "2025-06-01",
        "last_round_size_usd": 2_000_000, "location": "Remote",
        "one_line_pitch": "AI assistants for sales",
    }
    after = {
        "id": 7, "sector": "AI/ML", "stage": "series-a", "headcount_range": "11-50",
        "intern_hiring_status": "hiring", "last_round_date": "2026-05-01",
        "last_round_size_usd": 15_000_000, "location": "SF Bay Area",
        "one_line_pitch": "Agentic revenue platform",
    }
    kinds = {e["kind"] for e in diff_and_emit(prior, after)}
    assert {"new_round", "stage_advance", "headcount_growth",
            "hiring_status_change", "location_change", "pitch_change"} == kinds


def test_hiring_status_signed_magnitude():
    """+1 when moving INTO hiring/open_to; -1 when leaving."""
    base = {"id": 7}
    on  = diff_and_emit({**base, "intern_hiring_status": "unknown"},
                         {**base, "intern_hiring_status": "hiring"})
    off = diff_and_emit({**base, "intern_hiring_status": "hiring"},
                         {**base, "intern_hiring_status": "not_hiring"})
    assert next(e for e in on  if e["kind"] == "hiring_status_change")["magnitude"] == 1.0
    assert next(e for e in off if e["kind"] == "hiring_status_change")["magnitude"] == -1.0


def test_whitespace_only_pitch_change_does_not_fire():
    """Regression: cosmetic re-scrape of a pitch (extra whitespace, case) must NOT
    emit a pitch_change event. Same for location."""
    prior = {"id": 7,
             "one_line_pitch": "AI assistants for sales",
             "location": "San Francisco, CA"}
    after = {"id": 7,
             "one_line_pitch": "  AI ASSISTANTS for sales  ",  # whitespace + caps
             "location": " san francisco, ca "}
    assert [e["kind"] for e in diff_and_emit(prior, after)] == []


def test_headcount_decline_is_typed():
    prior = {"id": 7, "headcount_range": "51-200"}
    after = {"id": 7, "headcount_range": "11-50"}
    out = diff_and_emit(prior, after)
    assert out[0]["kind"] == "headcount_decline"


# ─── momentum.compute_momentum ──────────────────────────────────────────────

def _fake_events(rows):
    """rows: list of (company_id, kind, days_ago, magnitude or None)."""
    now = datetime.now(timezone.utc)
    return pd.DataFrame([{
        "company_id": cid, "kind": kind,
        "observed_at": (now - timedelta(days=days)).isoformat(),
        "magnitude": mag,
    } for cid, kind, days, mag in rows])


def test_compute_momentum_returns_empty_frame_on_empty_input():
    out = compute_momentum(pd.DataFrame())
    assert out.empty
    assert {"company_id", "momentum"}.issubset(out.columns)


def test_momentum_recent_event_beats_old_event():
    df = _fake_events([(1, "new_round", 1, 10_000_000),
                       (2, "new_round", 60, 10_000_000)])
    m = compute_momentum(df).set_index("company_id")
    assert m.loc[1, "momentum"] > m.loc[2, "momentum"] * 5


def test_momentum_burst_outscores_single_event():
    df = _fake_events([
        (1, "new_round", 3, 10_000_000),
        (1, "headcount_growth", 3, 1.0),
        (1, "hiring_status_change", 3, 1.0),
        (2, "press_mention", 3, None),
    ])
    m = compute_momentum(df).set_index("company_id")
    assert m.loc[1, "momentum"] > m.loc[2, "momentum"] * 3


def test_hiring_status_decline_is_penalized():
    df = _fake_events([
        (1, "hiring_status_change", 2, 1.0),   # moved INTO hiring -> positive
        (2, "hiring_status_change", 2, -1.0),  # left hiring -> negative
    ])
    m = compute_momentum(df).set_index("company_id")
    assert m.loc[1, "momentum"] > 0 > m.loc[2, "momentum"]


def test_top_n_respects_sector_filter_and_orders_correctly():
    events = pd.DataFrame(synthesize_events(seed=11))
    companies = synth_companies(seed=11)
    full = top_n(events, companies, n=10)
    ai = top_n(events, companies, n=10, sector="AI/ML")
    # ordering: descending momentum
    assert (full["momentum"].diff().dropna() <= 1e-9).all()
    # filter actually filters
    assert ai.empty or (ai["sector"] == "AI/ML").all()
