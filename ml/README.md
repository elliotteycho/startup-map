# Startup Map — Internship Ranker (learning-to-rank / CTR)

An ML layer on top of Startup Map: given a student session, **rank the startup
internships most likely to be relevant**, learned from the `events` click stream.
This is the same problem shape as production ad ranking — features + an
objective + a ranking metric.

## What it does
- **Labels:** clicks from the `events` table (CTR-style relevance signal).
- **Feature engineering** (`ranker/features.py`): categorical encoding of
  sector / stage / headcount / location / hiring status; log-scaled funding;
  recency decay on last round; company age; alumni count; careers-page flag;
  and a session-personalization interaction (does the company match the
  session's preferred sector).
- **Models** (`ranker/train.py`): scikit-learn Logistic Regression and Gradient
  Boosting, plus XGBoost; benchmarked head-to-head. A PyTorch pairwise
  **RankNet** ranker is in `ranker/torch_ranker.py`.
- **Evaluation** (`ranker/metrics.py`): grouped **AUC**, **NDCG@k**,
  **precision@k**, **MAP**, computed per session and averaged. Train/test use a
  `GroupShuffleSplit` on `session_id` so no session leaks across the split.
- **Serving** (`ranker/recommend.py`): loads the best model and returns the
  top-k internships for a student.

## Run it
```bash
cd ml
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # numpy, pandas, scikit-learn, xgboost, joblib
# xgboost on macOS also needs:  brew install libomp

python -m ranker.train --synthetic       # runs immediately on synthetic data
python -m ranker.recommend --sector AI/ML --k 10 --synthetic
python -m ranker.torch_ranker --synthetic # PyTorch RankNet (pip install torch)
```

### Neural rankers (PyTorch + TensorFlow)
- **PyTorch** (`ranker/torch_ranker.py`) runs in the main `.venv`.
- **TensorFlow** (`ranker/tf_ranker.py`) needs Python <= 3.12 (no 3.13/3.14 wheels
  yet), so it has its own env. Reproduce with [uv](https://docs.astral.sh/uv/):
  ```bash
  uv venv --python 3.12 .venv-tf
  uv pip install --python .venv-tf/bin/python tensorflow scikit-learn pandas numpy scipy joblib
  .venv-tf/bin/python -m ranker.tf_ranker --synthetic
  ```
All four model families (sklearn, XGBoost, PyTorch, TensorFlow) report into the
same NDCG@k / AUC / precision@k benchmark so they compare apples-to-apples.

## Run it on real data
`ranker/data.py` auto-loads from Supabase when `SUPABASE_URL` + a service-role
key are present (it reuses `scraper/.env`) and `pip install supabase` is done.
Otherwise it falls back to a synthetic dataset that mirrors the production
schema, so the pipeline always runs.

```bash
python -m ranker.train      # uses live companies + events if creds are available
```

> The synthetic numbers (~0.82 NDCG@5) validate the pipeline. Run on the live
> `events` table to get the real ranking metrics for the live product.
