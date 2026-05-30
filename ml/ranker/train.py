"""Train, cross-validate, and save the internship ranker.

    python -m ranker.train                # live data if available, else synthetic
    python -m ranker.train --synthetic    # force synthetic
    python -m ranker.train --k 10 --folds 5

Pipeline:
  1. Load + engineer features.
  2. GroupKFold cross-validation of every model (baselines, pointwise CTR,
     LambdaMART), reporting mean +/- std for AUC / NDCG@k / P@k / MAP.
  3. Pick the best by mean NDCG@k, refit on a train split, report permutation
     feature importance, then refit on ALL data and save to artifacts/.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import joblib
from sklearn.model_selection import GroupShuffleSplit

from .data import load_dataset
from .evaluate import cross_validate, permutation_importance
from .features import engineer
from .models import make_models

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true", help="force synthetic data")
    ap.add_argument("--k", type=int, default=5, help="cutoff for NDCG@k / P@k")
    ap.add_argument("--folds", type=int, default=5, help="GroupKFold splits")
    args = ap.parse_args()

    companies, events, source = load_dataset(force_synthetic=args.synthetic)
    print(f"Data source: {source}  |  companies={len(companies)}  events={len(events)}")

    frame = engineer(companies, events)
    feature_cols = [c for c in frame.columns if c not in ("session_id", "company_id", "y")]
    print(f"Pairs: {len(frame)}  |  sessions: {frame['session_id'].nunique()}  "
          f"|  positive rate: {frame['y'].mean():.3f}")

    # 1) Cross-validated benchmark.
    print(f"\nGroupKFold cross-validation ({args.folds} folds)  [mean +/- std]")
    print("=" * 78)
    print(f"{'model':<24}{'AUC':>13}{f'NDCG@{args.k}':>15}{f'P@{args.k}':>13}{'MAP':>13}")
    print("-" * 78)
    cv = cross_validate(frame, feature_cols, k=args.k, n_splits=args.folds)

    def cell(t):  # (mean, std) -> "0.812 +/- 0.01"
        return f"{t[0]:.3f}+/-{t[1]:.2f}"

    nd_key = f"NDCG@{args.k}"
    pk_key = f"P@{args.k}"
    for name, m in sorted(cv.items(), key=lambda kv: kv[1][nd_key][0], reverse=True):
        print(f"{name:<24}{cell(m['AUC']):>13}{cell(m[nd_key]):>15}"
              f"{cell(m[pk_key]):>13}{cell(m['MAP']):>13}")
    print("=" * 78)

    best = max(cv, key=lambda n: cv[n][nd_key][0])
    print(f"Best by mean NDCG@{args.k}: {best}")

    # 2) Refit best on a holdout split and report feature importance.
    gss = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=0)
    tr, te = next(gss.split(frame, frame["y"], groups=frame["session_id"]))
    train, test = frame.iloc[tr], frame.iloc[te]
    best_model = make_models()[best]().fit(train, feature_cols)

    print(f"\nPermutation feature importance for '{best}' (mean AUC drop):")
    for feat, imp in permutation_importance(best_model, test, feature_cols, k=args.k)[:8]:
        bar = "#" * max(0, int(imp * 200))
        print(f"  {feat:<22}{imp:+.4f}  {bar}")

    # 3) Refit best on ALL data and persist.
    final = make_models()[best]().fit(frame, feature_cols)
    ARTIFACTS.mkdir(exist_ok=True)
    joblib.dump({"model": final, "model_name": best, "feature_cols": feature_cols,
                 "cv": cv, "k": args.k, "source": source},
                ARTIFACTS / "ranker.joblib")
    print(f"\nSaved -> {ARTIFACTS / 'ranker.joblib'}")


if __name__ == "__main__":
    main()
