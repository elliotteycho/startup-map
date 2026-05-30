"""FastAPI inference service -- the seam the Next.js frontend calls.

    pip install fastapi "uvicorn[standard]"
    uvicorn ranker.serve:app --reload
    # then: http://127.0.0.1:8000/rank?sector=AI/ML&k=10
            http://127.0.0.1:8000/docs   (interactive)

Loads the trained model once at startup and serves ranked internships per
student. Defaults to synthetic data; flip `synthetic=false` once the live
Supabase load is wired and a model has been trained on real events.
"""
from __future__ import annotations

try:
    from fastapi import FastAPI, Query
except Exception:  # pragma: no cover
    raise SystemExit('FastAPI not installed. Run: pip install fastapi "uvicorn[standard]"')

import os
from pathlib import Path

import pandas as pd

from .momentum import compute_momentum, top_n
from .recommend import rank_for_student
from .synth import synth_companies, synthesize_events

app = FastAPI(title="Startup Map Internship Ranker", version="1.1")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/rank")
def rank(
    sector: str = Query("AI/ML", description="the student's preferred sector"),
    k: int = Query(10, ge=1, le=100),
    synthetic: bool = Query(True, description="set false to use live Supabase data"),
):
    df = rank_for_student(sector, k=k, force_synthetic=synthetic)
    return {"sector": sector, "k": k, "results": df.to_dict(orient="records")}


# ─── Phase 5B: rising-companies leaderboard ────────────────────────────────

def _load_momentum_snapshot(use_live: bool):
    """Return (rows_df, source). Prefers `company_momentum_today` view (Phase
    5B steady state); falls back to live-computing from `company_events`;
    falls back to synthetic data if nothing else is available."""
    if use_live:
        try:
            from dotenv import load_dotenv  # type: ignore
            from supabase import create_client  # type: ignore
            env = Path(__file__).resolve().parents[2] / "scraper" / ".env"
            if env.exists():
                load_dotenv(env)
            url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            if url and key:
                client = create_client(url, key)
                snap = pd.DataFrame(client.table("company_momentum_today").select("*").execute().data or [])
                if not snap.empty:
                    return snap, "snapshot"
                # Fall back: live compute from raw events
                events = pd.DataFrame(client.table("company_events").select("*").execute().data or [])
                co = pd.DataFrame(client.table("companies").select("id,name,sector").execute().data or [])
                if not events.empty and not co.empty:
                    board = top_n(events, co, n=100)
                    return board, "live_compute"
        except Exception:
            pass
    events = pd.DataFrame(synthesize_events(seed=11))
    co = synth_companies(seed=11)
    return top_n(events, co, n=100), "synthetic"


@app.get("/momentum")
def momentum(
    sector: str | None = Query(None, description="filter by company sector"),
    n: int = Query(10, ge=1, le=50),
    only_anomalies: bool = Query(False, description="return only rows flagged is_anomaly"),
    synthetic: bool = Query(True, description="set false to use live Supabase data"),
):
    rows, source = _load_momentum_snapshot(use_live=not synthetic)
    if rows.empty:
        return {"source": source, "results": []}
    if sector:
        rows = rows[rows["sector"] == sector]
    if only_anomalies:
        # Anomaly info only exists in the persisted snapshot. If the source
        # is a live-compute or synthetic fallback (no `is_anomaly` column),
        # return an empty list rather than falsely surfacing top-momentum
        # rows as if they were anomalies.
        if "is_anomaly" not in rows.columns:
            return {"source": source, "sector": sector, "n": n, "results": []}
        rows = rows[rows["is_anomaly"]]
    rows = rows.sort_values("momentum", ascending=False).head(n)
    return {"source": source, "sector": sector, "n": n,
            "results": rows.to_dict(orient="records")}
