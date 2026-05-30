"""Serve rankings from the trained model.

    python -m ranker.recommend --sector AI/ML --k 10

Loads the saved pipeline and ranks the current company set for a student whose
preferred sector is given, returning the top-k by predicted click relevance.
This is the inference path the Next.js frontend would call.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd

from .data import load_dataset
from .features import CATEGORICAL, NUMERIC, engineer

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


def rank_for_student(fav_sector: str, k: int = 10, force_synthetic: bool = False) -> pd.DataFrame:
    bundle = joblib.load(ARTIFACTS / "ranker.joblib")
    model = bundle["model"]

    companies, _events, _src = load_dataset(force_synthetic=force_synthetic)
    # Build a one-session "slate" = every company, with this student's taste.
    synth_events = pd.DataFrame({
        "session_id": "live",
        "company_id": companies["id"],
        "event_type": "impression",
        "fav_sector": fav_sector,
    })
    frame = engineer(companies, synth_events)
    frame["score"] = model.score(frame)
    out = frame.sort_values("score", ascending=False).head(k)
    return out[["company_id", "sector", "stage", "intern_hiring_status", "score"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sector", default="AI/ML")
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--synthetic", action="store_true")
    args = ap.parse_args()
    ranked = rank_for_student(args.sector, args.k, args.synthetic)
    print(f"\nTop {args.k} companies for a student who likes '{args.sector}':\n")
    print(ranked.to_string(index=False))


if __name__ == "__main__":
    main()
