"""Tests for the scraper's Phase 1B integration (`event_hooks`).

The diff logic itself is covered in test_track_b. These tests pin down the
orchestration around it: pre-fetch, emit gating, idempotent re-scrape,
table-missing graceful-degradation, and feature-flag off behavior.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# `scraper/` is a sibling tree of `ml/`.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scraper"))

from event_hooks import emit_company_events, fetch_prior_companies  # noqa: E402


# ─── helpers ────────────────────────────────────────────────────────────────

def _fake_client():
    """Returns (client_mock, captured) where captured holds calls for asserts."""
    client = MagicMock()
    captured: dict = {"selects": [], "inserts": []}

    def _table(name):
        tbl = MagicMock()
        if name == "companies":
            chained = MagicMock()
            chained.select.return_value = chained
            chained.in_.side_effect = lambda *_a, **_k: chained
            chained.execute.side_effect = lambda *_a, **_k: MagicMock(data=captured["selects_response"])
            tbl.select.return_value = chained
        elif name == "company_events":
            insert_chain = MagicMock()
            insert_chain.execute.return_value = MagicMock(data=None)
            def _insert(rows):
                captured["inserts"].append(rows)
                return insert_chain
            tbl.insert.side_effect = _insert
        return tbl

    client.table.side_effect = _table
    captured["selects_response"] = []
    return client, captured


# ─── fetch_prior_companies ──────────────────────────────────────────────────

def test_fetch_prior_returns_empty_for_no_websites():
    client = MagicMock()
    assert fetch_prior_companies(client, []) == {}


def test_fetch_prior_keys_by_website():
    client, captured = _fake_client()
    captured["selects_response"] = [
        {"id": 1, "website": "https://a.com", "sector": "AI/ML"},
        {"id": 2, "website": "https://b.com", "sector": "Fintech"},
    ]
    out = fetch_prior_companies(client, ["https://a.com", "https://b.com"])
    assert set(out) == {"https://a.com", "https://b.com"}
    assert out["https://a.com"]["sector"] == "AI/ML"


def test_fetch_prior_fails_open_on_db_error():
    client = MagicMock()
    client.table.side_effect = RuntimeError("connection refused")
    assert fetch_prior_companies(client, ["https://x"]) == {}


# ─── emit_company_events ────────────────────────────────────────────────────

def test_emit_off_when_feature_flag_disabled(monkeypatch):
    monkeypatch.setenv("EMIT_EVENTS", "false")
    client = MagicMock()
    after = [{"id": 1, "website": "https://a.com", "sector": "AI/ML"}]
    assert emit_company_events(client, {}, after, "test") == 0
    client.table.assert_not_called()


def test_emit_skips_silently_for_empty_input():
    client = MagicMock()
    assert emit_company_events(client, {}, [], "test") == 0
    client.table.assert_not_called()


def test_first_seen_company_inserts_initial_state(monkeypatch):
    monkeypatch.setenv("EMIT_EVENTS", "true")
    client, captured = _fake_client()
    after = [{"id": 1, "website": "https://new.com", "sector": "AI/ML", "stage": "seed"}]
    n = emit_company_events(client, prior_by_website={}, after_rows=after, source_fund="test")
    assert n == 1
    inserted = captured["inserts"][0]
    assert len(inserted) == 1
    assert inserted[0]["kind"] == "initial_state"
    assert inserted[0]["company_id"] == 1
    assert inserted[0]["source"] == "scraper_diff"


def test_unchanged_rescrape_is_idempotent(monkeypatch):
    """Re-scraping a company with no field changes must insert zero rows."""
    monkeypatch.setenv("EMIT_EVENTS", "true")
    client, captured = _fake_client()
    row = {"id": 1, "website": "https://a.com", "sector": "AI/ML", "stage": "seed",
           "headcount_range": "1-10", "intern_hiring_status": "unknown",
           "last_round_date": "2025-06-01", "last_round_size_usd": 2_000_000}
    n = emit_company_events(client, prior_by_website={"https://a.com": row},
                            after_rows=[row], source_fund="test")
    assert n == 0
    assert captured["inserts"] == []


def test_changes_emit_typed_events(monkeypatch):
    monkeypatch.setenv("EMIT_EVENTS", "true")
    client, captured = _fake_client()
    prior = {"id": 1, "website": "https://a.com", "intern_hiring_status": "unknown",
             "headcount_range": "1-10"}
    after = [{"id": 1, "website": "https://a.com", "intern_hiring_status": "hiring",
              "headcount_range": "11-50"}]
    n = emit_company_events(client, prior_by_website={"https://a.com": prior},
                            after_rows=after, source_fund="test")
    assert n == 2
    kinds = {e["kind"] for e in captured["inserts"][0]}
    assert kinds == {"hiring_status_change", "headcount_growth"}


def test_table_missing_fails_open(monkeypatch, caplog):
    """If migration 006 hasn't been applied, the scraper must not crash."""
    monkeypatch.setenv("EMIT_EVENTS", "true")
    client = MagicMock()
    captured: dict = {"selects_response": [], "inserts": []}

    def _table(name):
        tbl = MagicMock()
        if name == "company_events":
            tbl.insert.return_value.execute.side_effect = RuntimeError(
                "relation \"company_events\" does not exist")
        return tbl

    client.table.side_effect = _table
    after = [{"id": 1, "website": "https://a.com",
              "intern_hiring_status": "hiring",
              "headcount_range": "11-50"}]
    prior = {"id": 1, "website": "https://a.com",
             "intern_hiring_status": "unknown",
             "headcount_range": "1-10"}
    # Must return 0, not raise.
    with caplog.at_level("WARNING"):
        n = emit_company_events(client, {"https://a.com": prior}, after, "test")
    assert n == 0
    assert any("events_insert_failed" in r.message for r in caplog.records)
