"""Phase 2B tests: RSS parser + extractor + entity linker + dedup."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# `scraper/` is a sibling of `ml/`
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scraper"))

from news import techcrunch                             # noqa: E402
from news_extractor import (                            # noqa: E402
    dedup_key, dedup_rows, extract_event_proposals,
    link_to_companies, to_company_events_rows,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "techcrunch_sample.xml"


# ─── RSS parser ────────────────────────────────────────────────────────────

def test_rss_parses_all_items():
    items = techcrunch.fetch(xml_text=FIXTURE.read_text(encoding="utf-8"))
    assert len(items) == 4
    assert items[0]["source"] == "techcrunch"
    assert items[0]["title"].startswith("Decagon raises $65M")
    # ISO 8601 UTC normalized
    assert items[0]["published_at"].endswith("+00:00") or items[0]["published_at"].endswith("Z")
    assert items[0]["url"].startswith("https://techcrunch.com/")
    assert items[0]["external_id"]  # guid OR url


def test_rss_strips_html_from_body():
    items = techcrunch.fetch(xml_text=FIXTURE.read_text(encoding="utf-8"))
    body = items[0]["body"]
    assert "<p>" not in body and "</p>" not in body
    assert "Bain Capital Ventures" in body


# ─── Extractor (regex over title + body) ───────────────────────────────────

def test_extractor_finds_new_round():
    items = techcrunch.fetch(xml_text=FIXTURE.read_text(encoding="utf-8"))
    props = extract_event_proposals(items[0])  # Decagon raises $65M Series B
    assert any(p["kind"] == "new_round" for p in props)
    rnd = next(p for p in props if p["kind"] == "new_round")
    assert rnd["mentioned_company"].startswith("Decagon")
    assert rnd["magnitude"] == 65_000_000
    assert rnd["payload"]["round_type"] in {"series b", "series b "}  # tolerant of trailing ws


def test_extractor_finds_acquisition():
    items = techcrunch.fetch(xml_text=FIXTURE.read_text(encoding="utf-8"))
    props = extract_event_proposals(items[1])  # Stripe acquires Privy
    assert any(p["kind"] == "acquisition" for p in props)
    acq = next(p for p in props if p["kind"] == "acquisition")
    assert acq["mentioned_company"] == "Privy"
    assert acq["payload"]["acquirer"] == "Stripe"


def test_extractor_no_match_returns_empty():
    items = techcrunch.fetch(xml_text=FIXTURE.read_text(encoding="utf-8"))
    assert extract_event_proposals(items[3]) == []   # opinion piece — no event


# ─── Entity linker ─────────────────────────────────────────────────────────

CANDIDATES = [
    {"id": 11, "name": "Decagon"},
    {"id": 12, "name": "Cresta"},
    {"id": 13, "name": "Anthropic"},
    {"id": 14, "name": "Privy"},
]


def test_linker_matches_known_company():
    props = [{"kind": "new_round", "mentioned_company": "Decagon",
              "magnitude": 65_000_000, "confidence_floor": 0.75, "payload": {}}]
    linked = link_to_companies(props, CANDIDATES)
    assert len(linked) == 1
    assert linked[0]["company_id"] == 11
    assert linked[0]["matched_name"] == "Decagon"
    assert linked[0]["confidence"] >= 0.85   # strict-score bump applied


def test_linker_drops_unknown_company():
    props = [{"kind": "new_round", "mentioned_company": "Nonexistent Inc.",
              "magnitude": 1, "confidence_floor": 0.7, "payload": {}}]
    assert link_to_companies(props, CANDIDATES) == []


def test_linker_tolerates_company_suffix():
    """'Decagon Inc.' should still resolve to Decagon (token_set_ratio)."""
    props = [{"kind": "acquisition", "mentioned_company": "Decagon Inc.",
              "magnitude": None, "confidence_floor": 0.7, "payload": {}}]
    linked = link_to_companies(props, CANDIDATES)
    assert linked and linked[0]["company_id"] == 11


# ─── Render + dedup ────────────────────────────────────────────────────────

def test_render_produces_company_events_rows():
    items = techcrunch.fetch(xml_text=FIXTURE.read_text(encoding="utf-8"))
    props = extract_event_proposals(items[0])
    linked = link_to_companies(props, CANDIDATES)
    rows = to_company_events_rows(linked, items[0])
    assert rows and rows[0]["source"] == "news_techcrunch"
    assert rows[0]["observed_at"] == items[0]["published_at"]
    assert rows[0]["payload"]["news_url"].startswith("https://techcrunch.com/")
    assert rows[0]["payload"]["matched_name"] == "Decagon"


def test_dedup_collapses_same_company_kind_date():
    items = techcrunch.fetch(xml_text=FIXTURE.read_text(encoding="utf-8"))
    # Build two rows for the same (company, kind, date) — should collapse to 1.
    rows = []
    for it in (items[0], items[0]):
        props = extract_event_proposals(it)
        linked = link_to_companies(props, CANDIDATES)
        rows.extend(to_company_events_rows(linked, it))
    assert len(rows) == 2
    final = dedup_rows(rows)
    assert len(final) == 1


def test_dedup_respects_existing_keys():
    items = techcrunch.fetch(xml_text=FIXTURE.read_text(encoding="utf-8"))
    props = extract_event_proposals(items[0])
    linked = link_to_companies(props, CANDIDATES)
    rows = to_company_events_rows(linked, items[0])
    existing = {dedup_key(rows[0])}
    assert dedup_rows(rows, already_present_keys=existing) == []


# ─── End-to-end on the fixture ─────────────────────────────────────────────

def test_end_to_end_fixture_yields_expected_events():
    items = techcrunch.fetch(xml_text=FIXTURE.read_text(encoding="utf-8"))
    all_rows: list[dict] = []
    for it in items:
        props = extract_event_proposals(it)
        linked = link_to_companies(props, CANDIDATES)
        all_rows.extend(to_company_events_rows(linked, it))
    final = dedup_rows(all_rows)
    kinds = sorted((r["kind"], r["payload"].get("matched_name")) for r in final)
    # 3 of the 4 items map to known companies; opinion piece drops out.
    assert ("acquisition", "Privy") in kinds
    assert ("new_round", "Decagon") in kinds
    assert ("new_round", "Cresta") in kinds
