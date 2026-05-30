"""Synthetic `companies` + `company_events` generator.

Used both by the momentum demo (`ranker.momentum`) and the offline events
explorer CLI (`scripts/events_explorer.py`) when no live Supabase data is
available. Kept in its own module so neither caller has to import the other.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

_SECTORS = ["AI/ML", "Fintech", "Climate", "DevTools", "Consumer", "SaaS", "Healthcare", "Robotics"]
_PREFIXES = ["Acme", "Helix", "Lumen", "Forge", "Quill", "Atlas", "Nova", "Echo", "Vela", "Onyx"]


def synth_companies(n: int = 80, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "id": np.arange(1, n + 1),
        "name": [f"{rng.choice(_PREFIXES)}-{i:02d}" for i in range(n)],
        "sector": rng.choice(_SECTORS, n),
    })


def synthesize_events(seed: int = 7, n_companies: int = 80, days: int = 30) -> list[dict]:
    """Realistic synthetic event stream. Most companies are quiet; a minority
    show a recent burst (round + hiring + headcount), so momentum has real
    signal to surface."""
    rng = np.random.default_rng(seed)
    companies = synth_companies(n_companies, seed)
    now = datetime.now(timezone.utc)
    out: list[dict] = []

    # background activity for everyone
    for _, c in companies.iterrows():
        for _ in range(rng.integers(0, 2)):
            kind = rng.choice(["press_mention", "pitch_change", "new_careers_role"],
                              p=[0.5, 0.2, 0.3])
            age = float(rng.uniform(5, days))
            out.append({
                "company_id": int(c["id"]), "_company_name": c["name"], "_sector": c["sector"],
                "observed_at": (now - timedelta(days=age)).isoformat(),
                "kind": kind, "before_value": None, "after_value": None,
                "magnitude": None, "source": "synthetic", "confidence": 0.9,
            })

    # rising stars: a recent multi-event burst
    risers = rng.choice(companies["id"].to_numpy(), size=max(3, n_companies // 8), replace=False)
    for cid in risers:
        c = companies[companies["id"] == cid].iloc[0]
        burst_anchor = float(rng.uniform(1, 10))
        for kind, mag in [
            ("new_round", float(rng.choice([5_000_000, 12_000_000, 25_000_000, 60_000_000]))),
            ("headcount_growth", 1.0),
            ("hiring_status_change", 1.0),
        ]:
            jitter = float(rng.uniform(-2, 2))
            out.append({
                "company_id": int(cid), "_company_name": c["name"], "_sector": c["sector"],
                "observed_at": (now - timedelta(days=max(0.1, burst_anchor + jitter))).isoformat(),
                "kind": kind, "before_value": None, "after_value": None,
                "magnitude": mag, "source": "synthetic", "confidence": 1.0,
            })

    # a couple of negatives so the model also surfaces decline
    decliners = rng.choice([cid for cid in companies["id"].to_numpy() if cid not in risers],
                           size=2, replace=False)
    for cid in decliners:
        c = companies[companies["id"] == cid].iloc[0]
        out.append({
            "company_id": int(cid), "_company_name": c["name"], "_sector": c["sector"],
            "observed_at": (now - timedelta(days=float(rng.uniform(1, 8)))).isoformat(),
            "kind": "headcount_decline", "before_value": None, "after_value": None,
            "magnitude": -1.0, "source": "synthetic", "confidence": 1.0,
        })
    return out
