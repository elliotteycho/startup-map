"""Data loading for the internship ranker.

Two paths:
  1. Live  -- pull `companies` and `events` from Supabase (uses scraper/.env creds).
  2. Synthetic -- generate a realistic companies + click-stream dataset that
     mirrors the production schema, so the full train/eval pipeline runs with
     zero setup. The click labels are produced by a hidden relevance function
     so the model has real signal to recover.

`load_dataset()` returns (companies_df, events_df) from whichever path is available.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

SECTORS = ["AI/ML", "Fintech", "Healthcare", "DevTools", "Consumer", "Climate", "SaaS", "Robotics"]
STAGES = ["pre-seed", "seed", "series-a", "series-b", "growth"]
HEADCOUNTS = ["1-10", "11-50", "51-200", "201-500"]
HIRING = ["hiring", "open_to", "not_hiring", "unknown"]
LOCATIONS = ["SF Bay Area", "New York", "Remote", "Boston", "Austin", "Nashville"]


# ─────────────────────────────────────────────────────────────────────────────
# Live path (Supabase)
# ─────────────────────────────────────────────────────────────────────────────

def _try_load_supabase() -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Return (companies, events) from Supabase, or None if unavailable."""
    try:
        from supabase import create_client  # type: ignore
    except Exception:
        return None

    # Reuse the scraper's .env if present.
    env_path = Path(__file__).resolve().parents[2] / "scraper" / ".env"
    if env_path.exists():
        try:
            from dotenv import load_dotenv  # type: ignore
            load_dotenv(env_path)
        except Exception:
            pass

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    if not (url and key):
        return None

    try:
        client = create_client(url, key)
        companies = pd.DataFrame(client.table("companies").select("*").execute().data)
        events = pd.DataFrame(client.table("events").select("*").execute().data)
        if companies.empty or events.empty:
            return None
        return companies, events
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic path (mirrors schema, with recoverable click signal)
# ─────────────────────────────────────────────────────────────────────────────

def make_synthetic(n_companies: int = 400, n_sessions: int = 1200, seed: int = 7
                   ) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)

    comp = pd.DataFrame({
        "id": np.arange(1, n_companies + 1),
        "sector": rng.choice(SECTORS, n_companies),
        "stage": rng.choice(STAGES, n_companies, p=[0.18, 0.34, 0.28, 0.13, 0.07]),
        "headcount_range": rng.choice(HEADCOUNTS, n_companies),
        "location": rng.choice(LOCATIONS, n_companies),
        "intern_hiring_status": rng.choice(HIRING, n_companies, p=[0.30, 0.25, 0.20, 0.25]),
        "last_round_size_usd": (rng.lognormal(mean=15.2, sigma=1.1, size=n_companies)).astype(int),
        "days_since_round": rng.integers(15, 900, n_companies),
        "founded_year": rng.integers(2014, 2025, n_companies),
        "vandy_alumni_count": rng.poisson(1.2, n_companies),
        "has_careers_page": rng.random(n_companies) < 0.7,
    })

    # Hidden relevance: what actually makes a student click. The model must recover this.
    sector_pull = {s: v for s, v in zip(SECTORS, rng.normal(0, 0.8, len(SECTORS)))}
    z = (
        1.4 * (comp["intern_hiring_status"] == "hiring").astype(float)
        + 0.6 * (comp["intern_hiring_status"] == "open_to").astype(float)
        - 1.0 * (comp["intern_hiring_status"] == "not_hiring").astype(float)
        + 0.45 * np.log1p(comp["last_round_size_usd"]) / 3.0
        - 0.004 * comp["days_since_round"]
        + 0.30 * comp["vandy_alumni_count"]
        + 0.50 * comp["has_careers_page"].astype(float)
        + comp["sector"].map(sector_pull).values
        + 0.35 * (comp["stage"].isin(["seed", "series-a"]).astype(float))
    )
    base_ctr = 1.0 / (1.0 + np.exp(-(z - z.mean()) / z.std()))

    # Each session views a slate of companies; clicks ~ Bernoulli(relevance).
    rows = []
    for s in range(n_sessions):
        slate = rng.choice(comp["id"].values, size=rng.integers(12, 25), replace=False)
        # Per-session taste tilt toward one sector (personalization signal).
        fav = rng.choice(SECTORS)
        for cid in slate:
            c = comp.loc[comp["id"] == cid].iloc[0]
            p = base_ctr[cid - 1] * (1.35 if c["sector"] == fav else 1.0)
            clicked = rng.random() < min(p, 0.95)
            rows.append({
                "session_id": f"sess_{s:05d}",
                "school_slug": "vanderbilt",
                "company_id": int(cid),
                "fav_sector": fav,
                "event_type": "company_click" if clicked else "impression",
            })
    events = pd.DataFrame(rows)
    return comp, events


def load_dataset(force_synthetic: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """Returns (companies_df, events_df, source_label)."""
    if not force_synthetic:
        live = _try_load_supabase()
        if live is not None:
            return live[0], live[1], "supabase"
    comp, events = make_synthetic()
    return comp, events, "synthetic"
