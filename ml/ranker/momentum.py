"""B5 prototype — momentum / anomaly detection from the `company_events` stream.

Idea: weight each event by kind and decay by recency, then sum per company.
Companies with multiple recent strong-signal events (round + hiring + headcount
all in the last few weeks) rise to the top of a "what's moving in your space"
leaderboard. Operates on real `company_events` rows when present; falls back to
a synthetic stream so the demo runs immediately:

    python -m ranker.momentum                 # synthetic; print top-10
    python -m ranker.momentum --sector AI/ML  # synthetic, filtered
    python -m ranker.momentum --live          # if creds present; else synthetic
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

# Each event kind contributes its own weight to the momentum score.
# Positive weights = good news; negative = bad news.
EVENT_WEIGHTS = {
    "new_round":            5.0,
    "round_size_increase":  3.5,
    "stage_advance":        4.0,
    "acquisition":          5.0,
    "headcount_growth":     3.0,
    "headcount_decline":   -3.0,
    "hiring_status_change": 2.5,    # multiplied by sign(magnitude) below
    "new_careers_role":     1.5,
    "location_change":      0.3,
    "pitch_change":         0.5,
    "press_mention":        1.0,
    "initial_state":        0.0,
    "shutdown":            -10.0,
}

DECAY_DAYS = 14.0  # half-life-ish; older events fade smoothly


# ────────────────────────────────────────────────────────────────────────────
# Scoring
# ────────────────────────────────────────────────────────────────────────────

def compute_momentum(events: pd.DataFrame, now: datetime | None = None,
                     decay_days: float = DECAY_DAYS) -> pd.DataFrame:
    """Per-company momentum score from a long-form events frame.

    `events` columns: company_id, observed_at (ISO str or datetime), kind, magnitude.
    Returns: company_id, momentum, n_recent_events, top_kinds (list).
    """
    if events.empty:
        return pd.DataFrame(columns=["company_id", "momentum", "n_recent_events", "top_kinds"])

    now = now or datetime.now(timezone.utc)
    e = events.copy()
    e["observed_at"] = pd.to_datetime(e["observed_at"], utc=True, errors="coerce")
    e = e.dropna(subset=["observed_at"])
    e["age_days"] = ((now - e["observed_at"]).dt.total_seconds() / 86400.0).clip(lower=0)
    e = e[e["age_days"] <= decay_days * 5]  # ignore very old; their weight is ~0

    e["weight"] = e["kind"].map(EVENT_WEIGHTS).fillna(0.0)
    # signed application for hiring status (positive moves up, negative down)
    is_signed = e["kind"] == "hiring_status_change"
    if is_signed.any():
        mag = pd.to_numeric(e.loc[is_signed, "magnitude"], errors="coerce").fillna(0.0)
        e.loc[is_signed, "weight"] = e.loc[is_signed, "weight"] * np.sign(mag)

    e["decay"] = np.exp(-e["age_days"] / decay_days)
    e["contribution"] = e["weight"] * e["decay"]

    grouped = e.groupby("company_id").agg(
        momentum=("contribution", "sum"),
        n_recent_events=("kind", "size"),
        top_kinds=("kind", lambda s: list(pd.Series(s).value_counts().head(3).index)),
    ).reset_index()
    return grouped.sort_values("momentum", ascending=False, ignore_index=True)


def top_n(events: pd.DataFrame, companies: pd.DataFrame, n: int = 10,
          sector: str | None = None) -> pd.DataFrame:
    scored = compute_momentum(events)
    out = scored.merge(companies[["id", "name", "sector"]],
                       left_on="company_id", right_on="id", how="left")
    if sector:
        out = out[out["sector"] == sector]
    return out.head(n)[["company_id", "name", "sector", "momentum", "n_recent_events", "top_kinds"]]


# Synthetic data generator lives in `ranker.synth` so both the momentum demo
# and the offline events explorer can share it without a cross-tree import.
from .synth import synth_companies as _synth_companies, synthesize_events  # noqa: F401


# ────────────────────────────────────────────────────────────────────────────
# Anomaly layer (used by Phase 5B's daily snapshot job)
# ────────────────────────────────────────────────────────────────────────────

ANOMALY_Z_THRESHOLD = 2.5
ANOMALY_MIN_BASELINE_SAMPLES = 14   # need at least this many prior snapshots


def anomaly_z_score(current: float, baseline_series: list[float]) -> tuple[float | None, float | None, float | None]:
    """Return (mean, std, z) for `current` against `baseline_series`.

    z = (current - mean) / std, or None if the baseline is too short or
    degenerate (std == 0). Designed for per-company comparison against the
    company's OWN history, not catalog-wide — a Bain-funded AI shop that
    always has momentum 8 should not look "anomalous" forever.
    """
    if not baseline_series or len(baseline_series) < ANOMALY_MIN_BASELINE_SAMPLES:
        return None, None, None
    arr = np.asarray(baseline_series, dtype=float)
    mean = float(arr.mean())
    std = float(arr.std(ddof=1))
    if std <= 1e-9:
        return mean, std, None
    return mean, std, float((current - mean) / std)


def is_anomaly(z: float | None, threshold: float = ANOMALY_Z_THRESHOLD) -> bool:
    return z is not None and z >= threshold


# ────────────────────────────────────────────────────────────────────────────
# Live loader (optional)
# ────────────────────────────────────────────────────────────────────────────

def _try_load_live() -> tuple[pd.DataFrame, pd.DataFrame] | None:
    try:
        from pathlib import Path
        import os
        from dotenv import load_dotenv  # type: ignore
        from supabase import create_client  # type: ignore
    except Exception:
        return None
    env = Path(__file__).resolve().parents[2] / "scraper" / ".env"
    if env.exists():
        load_dotenv(env)
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not (url and key):
        return None
    try:
        client = create_client(url, key)
        ev = pd.DataFrame(client.table("company_events").select("*").execute().data or [])
        co = pd.DataFrame(client.table("companies").select("id,name,sector").execute().data or [])
        if ev.empty or co.empty:
            return None
        return ev, co
    except Exception:
        return None


# ────────────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="use live company_events if available")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--sector", default=None)
    args = ap.parse_args()

    source = "synthetic"
    if args.live:
        live = _try_load_live()
        if live is None:
            print("[no live data — falling back to synthetic]")
            events, companies = pd.DataFrame(synthesize_events()), _synth_companies()
        else:
            events, companies = live
            source = "live"
    else:
        events, companies = pd.DataFrame(synthesize_events()), _synth_companies()

    print(f"[source: {source}]  events: {len(events)}  companies: {len(companies)}\n")
    board = top_n(events, companies, n=args.n, sector=args.sector)
    if board.empty:
        print("(no rising companies in window)"); return

    print(f"{'rank':<5}{'company':<22}{'sector':<14}{'momentum':>10}{'recent_events':>15}  top_kinds")
    print("-" * 96)
    for i, (_, r) in enumerate(board.iterrows(), 1):
        kinds = ", ".join(r["top_kinds"][:3]) if isinstance(r["top_kinds"], list) else ""
        print(f"{i:<5}{(r['name'] or '')[:21]:<22}{(r['sector'] or ''):<14}"
              f"{r['momentum']:>10.2f}{int(r['n_recent_events']):>15}  {kinds}")


if __name__ == "__main__":
    main()
