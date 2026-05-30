# Startup Map Ranker — Tutorial

A hands-on walkthrough of the ML layer: what it does, how each piece works, and
exactly where to change things. Read top to bottom once; after that it's a reference.

---

## 1. The problem (and why it mirrors ad ranking)

Startup Map shows students a list of startup internships. The ML job: **order
that list so the internships a student is most likely to engage with come
first.** That's *learning-to-rank*, the same shape as ad ranking / recommendation:

```
features(student, company)  ->  model  ->  relevance score  ->  sort  ->  ranked list
                                   ^                                  ^
                          trained on click labels         judged by NDCG@k
```

- **Label:** a click in the `events` table (CTR-style relevance).
- **Objective:** put relevant items at the top of *each* student's list.
- **Metric:** NDCG@k / precision@k per session (not just global accuracy).

---

## 2. File map

```
ml/
├── Makefile            # make setup | train | test | serve | recommend | torch | tf
├── requirements.txt
├── README.md           # quickstart
├── TUTORIAL.md         # this file
├── tests/test_ranker.py
└── ranker/
    ├── data.py         # load: live Supabase OR synthetic fallback
    ├── features.py     # feature engineering + sklearn preprocessor
    ├── models.py       # baselines, pointwise CTR, LambdaMART — uniform .fit/.score
    ├── metrics.py      # AUC, NDCG@k, precision@k, MAP
    ├── evaluate.py     # GroupKFold cross-validation + permutation importance
    ├── train.py        # orchestrates: CV benchmark -> importance -> save best
    ├── recommend.py    # offline inference: top-k for a student
    ├── serve.py        # FastAPI: GET /rank  (the seam your Next.js app calls)
    ├── torch_ranker.py # PyTorch RankNet (pairwise) — alt model
    └── tf_ranker.py    # TensorFlow/Keras CTR — alt model (Python <= 3.12)
```

---

## 3. Setup & run

```bash
cd ml
make setup          # builds venvs in ~/Library/Caches/startup-map (OUTSIDE iCloud)
                    # and symlinks them in as .venv / .venv-tf
                    # (macOS xgboost also needs: brew install libomp)
make train          # cross-validated benchmark on synthetic data, saves best model
make recommend SECTOR=Fintech
make test           # pytest (28 tests across Track A + Track B Phase 0B + 1B)
make serve          # FastAPI on http://127.0.0.1:8000/docs
```

> **Why the venv lives outside the repo:** `~/Documents/...` is iCloud-managed
> on most Macs; iCloud evicts site-packages `.pyc` files when idle, then
> imports hit a 60s timeout. We keep venvs in `~/Library/Caches/startup-map/`
> and symlink them in. If you already have an in-tree venv from before this
> change, run `make relocate-venv` once.

### Track B Phase 5B — daily momentum + anomaly leaderboard

After applying migration 008 (`schema/008_company_momentum_daily.sql`) the
nightly job computes per-company momentum + a per-company z-score against
that company's own ~30-day history. Companies with `z >= 2.5` get flagged
as anomalies.

```bash
# Dry-run (synthetic baseline + today; no DB writes)
make momentum-snapshot
python scripts/daily_momentum.py --top 20

# Apply: write one row per company to company_momentum_daily for today
make momentum-snapshot APPLY=1
python scripts/daily_momentum.py --apply
```

Schedule it (Vercel Cron / GH Actions / launchd) once a day; idempotent on
same-day re-run.

The API endpoint:

```bash
make serve
curl 'http://127.0.0.1:8000/momentum?sector=AI/ML&n=10'
curl 'http://127.0.0.1:8000/momentum?only_anomalies=true&n=10'
```

`/momentum` prefers the persisted snapshot (`company_momentum_today` view);
falls back to a live compute from `company_events`; falls back to synthetic
data if neither is reachable. `?only_anomalies=true` honestly returns `[]`
on synthetic / live-compute sources (no anomaly column on those paths) so
the frontend never shows top-momentum rows as if they were anomalies.

### Track B Phase 2B — news ingestion (external coverage beyond the scraper)

After applying migration 007 (`schema/007_news_items.sql`), the news ingest
pulls TechCrunch RSS, rule-extracts `new_round` / `acquisition` events,
fuzzy-links each mention to a `companies` row (RapidFuzz token-set ratio),
dedups against existing `company_events`, and writes the survivors:

```bash
# Dry-run from the live feed (no DB writes)
python scripts/ingest_news.py --source techcrunch

# Dry-run against a saved RSS fixture (works fully offline)
python scripts/ingest_news.py --source techcrunch \
  --xml-file ml/tests/fixtures/techcrunch_sample.xml

# Apply: writes news_items + derived company_events to Supabase
python scripts/ingest_news.py --source techcrunch --apply
```

Confidence stamping (per PRD §10.1):
- News-extracted events default to **0.75** for `new_round`, **0.7** for `acquisition`.
- A high entity-link score (≥ 92 by token-set ratio) bumps by +0.10.
- The digest path (Phase 4B) refuses anything below the configured threshold.

Adding a new source = drop a `scraper/news/<source>.py` that exports
`fetch(feed_url=None, xml_text=None) -> list[dict]` and register it in
`SOURCES` at the top of `scripts/ingest_news.py`. Tests live in
`ml/tests/test_news.py`; the fixture is `ml/tests/fixtures/techcrunch_sample.xml`.

### Track B Phase 1B — turn on live change-log emission

After applying migration 006 (`schema/006_company_events.sql`) the scraper
auto-emits `company_events` on every upsert. The integration is gated by an
env var (default ON; set to off if you ever want to disable it):

```bash
EMIT_EVENTS=true  python scraper/pipeline.py          # emits on every upsert
EMIT_EVENTS=false python scraper/pipeline.py          # disables emission
```

Backfill historical companies once:

```bash
python scripts/backfill_company_events.py --dry-run   # preview
python scripts/backfill_company_events.py --apply     # write initial_state rows
```

Then inspect what's flowing:

```bash
python scripts/events_explorer.py --since 7d
python -m ranker.momentum --live   # leaderboard from real events
```

`make train` prints a table like:

```
model                       AUC        NDCG@5         P@5         MAP
random (baseline)      0.50+/-0.01  0.52+/-0.02  ...   <- the floor
popularity (baseline)  0.74+/-0.01  0.78+/-0.01  ...   <- dumb-but-strong
logreg                 0.75+/-0.01  0.80+/-0.01  ...   <- must beat baselines
lambdamart (LTR)       0.74+/-0.01  0.79+/-0.00  ...
```
If a model can't beat **popularity**, it isn't earning its complexity.

---

## 4. The data layer (`data.py`)

`load_dataset()` returns `(companies, events, source)`:
- **Live:** if `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` are set (it reads
  `scraper/.env`) and `pip install supabase` is done, it pulls real rows.
- **Synthetic:** otherwise it generates data that mirrors the production schema,
  with clicks drawn from a *hidden relevance function* so the model has real
  signal to recover. Great for developing offline.

**Adjust:** change `make_synthetic(n_companies=, n_sessions=)` to test scale, or
edit the hidden `z = ...` formula to make the problem harder/easier.

---

## 5. Feature engineering (`features.py`)

`engineer(companies, events)` produces one row per `(session, company)` with:

| feature | meaning |
|---|---|
| `sector, stage, headcount_range, location, intern_hiring_status` | one-hot categoricals |
| `log_last_round` | log-scaled last funding round |
| `recency_decay` | `exp(-days_since_round/365)` → 1.0 = fresh raise |
| `company_age` | years since founding |
| `vandy_alumni_count` | alumni at the company (warm-intro signal) |
| `has_careers_page` | derived from `careers_page_url` |
| `sector_match` | does the company match the session's preferred sector |

It is **robust to both schemas** (the `_col()` helper supplies defaults for
columns the live `companies` table lacks).

### Add a feature (the most common change)
1. Compute it on `comp` inside `engineer()` (e.g. `comp["log_headcount"] = ...`).
2. Add its name to `NUMERIC` (or `CATEGORICAL`) at the top of `features.py`.
3. `make train` — it flows through preprocessing, models, and importance automatically.

---

## 6. Models (`models.py`)

Every model exposes the same interface: `.fit(train_frame, feature_cols)` →
`.score(frame) -> np.ndarray`. Three families:

- **Baselines** — `RandomRanker`, `PopularityRanker` (in `baselines.py`).
- **Pointwise CTR** — LogReg, GradientBoosting, XGBoost: predict `P(click)` per item.
- **LambdaMART** — `XGBRanker(objective="rank:ndcg")`: a *listwise* LTR objective
  that optimizes the ordering within each session directly, using group sizes.
- **Neural** — `torch_ranker.py` (pairwise RankNet), `tf_ranker.py` (Keras CTR).

### Add a model
In `make_models()` add a factory:
```python
from sklearn.ensemble import RandomForestClassifier
models["random_forest"] = lambda: PipelineScorer(RandomForestClassifier(n_estimators=300))
```
It joins the benchmark automatically.

---

## 7. Evaluation (`evaluate.py`, `metrics.py`)

- **`cross_validate()`** runs **GroupKFold** so a session never appears in both
  train and test (no leakage), and reports **mean ± std** over folds.
- **`metrics.evaluate()`** computes AUC (pointwise) plus NDCG@k / P@k / MAP
  per session, averaged.
- **`permutation_importance()`** shuffles each feature and measures the AUC drop
  → which features actually drive the ranking. (On synthetic data it correctly
  surfaces `recency_decay`, `sector`, `intern_hiring_status` — the true signal.)

**Tune `k`:** `make train` then `python -m ranker.train --synthetic --k 10`.

---

## 8. Inference & serving (`recommend.py`, `serve.py`)

- **Offline:** `python -m ranker.recommend --sector AI/ML --k 10 --synthetic`.
- **API:** `make serve` → `GET /rank?sector=AI/ML&k=10`. This is what the
  **Next.js frontend** calls to order the dashboard. Wire it from `web/`:
  ```ts
  const r = await fetch(`${RANKER_URL}/rank?sector=${sector}&k=20`);
  const { results } = await r.json();   // [{company_id, sector, score, ...}]
  ```
  (For production, host the API and cache the loaded model; right now it loads
  per call for simplicity.)

---

## 9. Tests (`tests/test_ranker.py`)

`make test`. Covers feature engineering on **both** schemas (incl. the live-schema
regression), metric correctness on hand-checked cases, that every model fits and
scores, and that real models beat the random floor. Add a test whenever you add a
feature or model.

---

## 10. Going live (real metrics)

1. `pip install supabase python-dotenv` (in `.venv`).
2. Ensure `scraper/.env` has `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`.
3. `make train-live` — auto-loads real `companies` + `events`.

> Caveat: you need enough **clicks** (positives) and **sessions** for the metric
> to be stable. If the events table is still sparse, keep collecting clicks and
> rerun; the synthetic-validated pipeline is correct and waiting.

---

## 11. Cheat-sheet: common adjustments

| I want to… | Do this |
|---|---|
| Add a feature | compute in `engineer()`, add to `NUMERIC`/`CATEGORICAL` |
| Add a model | add a factory in `make_models()` |
| Change the label (e.g. count `apply_click` only) | edit `click_types` in `features.py` |
| Tune NDCG cutoff | `--k 10` |
| More/less CV rigor | `--folds 3` … `--folds 10` |
| Harder synthetic problem | edit `z = ...` in `data.py::make_synthetic` |
| Serve to the frontend | `make serve`, call `/rank` |

---

## 12. Roadmap (next upgrades, if you want them)

- **LightGBM `LGBMRanker`** as a second LTR model (often beats XGBRanker on tabular).
- **Hyperparameter search** (`GridSearchCV` / Optuna) inside CV.
- **Probability calibration** (`CalibratedClassifierCV`) for the pointwise models.
- **Online metrics**: log served rankings + clicks, compute live NDCG over time.
- **Feature store**: precompute company features nightly in the scraper pipeline.
- **Model registry / versioning**: stamp artifacts with date + CV score.
```
