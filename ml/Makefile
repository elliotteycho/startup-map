# Startup Map ranker — common tasks.  Run `make help` for the list.
VENV       := .venv
PY         := $(VENV)/bin/python
# Venvs live OUTSIDE iCloud-managed Documents/, then symlinked in. iCloud
# evicts .pyc files when idle and the 60s import timeout will haunt you.
VENV_HOME  := $(HOME)/Library/Caches/startup-map

.PHONY: help setup relocate-venv train recommend test serve torch tf momentum-snapshot ingest-news clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n",$$1,$$2}'

setup:           ## create main + TF venvs outside iCloud, symlink in, install deps
	@mkdir -p $(VENV_HOME)
	@command -v uv >/dev/null 2>&1 || (echo "Installing uv (needed for TF venv on Python 3.12)..." && curl -LsSf https://astral.sh/uv/install.sh | sh)
	@uv venv --python 3.14 $(VENV_HOME)/venv
	@ln -sfn $(VENV_HOME)/venv $(VENV)
	@uv pip install --python $(VENV)/bin/python -r requirements.txt
	@uv venv --python 3.12 $(VENV_HOME)/venv-tf
	@ln -sfn $(VENV_HOME)/venv-tf .venv-tf
	@uv pip install --python .venv-tf/bin/python tensorflow scikit-learn pandas numpy scipy joblib
	@echo "Done. Main venv: $(VENV) -> $(VENV_HOME)/venv ;  TF venv: .venv-tf -> $(VENV_HOME)/venv-tf"

relocate-venv:   ## one-shot: move existing in-tree venvs out of iCloud, symlink back
	@mkdir -p $(VENV_HOME)
	@if [ -d "$(VENV)" ] && [ ! -L "$(VENV)" ]; then \
	   mv "$(VENV)" "$(VENV_HOME)/venv" && ln -s "$(VENV_HOME)/venv" "$(VENV)"; \
	   echo "Moved $(VENV) -> $(VENV_HOME)/venv (symlinked back)"; \
	 else echo "$(VENV) already a symlink or missing — nothing to do"; fi
	@if [ -d ".venv-tf" ] && [ ! -L ".venv-tf" ]; then \
	   mv ".venv-tf" "$(VENV_HOME)/venv-tf" && ln -s "$(VENV_HOME)/venv-tf" ".venv-tf"; \
	   echo "Moved .venv-tf -> $(VENV_HOME)/venv-tf (symlinked back)"; \
	 else echo ".venv-tf already a symlink or missing — nothing to do"; fi

train:        ## cross-validated benchmark + save best model (synthetic)
	$(PY) -m ranker.train --synthetic

train-live:   ## train on live Supabase data (needs scraper/.env + pip install supabase)
	$(PY) -m ranker.train

recommend:    ## top-k internships for a student (SECTOR=AI/ML)
	$(PY) -m ranker.recommend --sector "$(or $(SECTOR),AI/ML)" --k 10 --synthetic

test:         ## run the pytest suite
	$(PY) -m pytest -q

serve:        ## launch the FastAPI ranking API on :8000
	$(VENV)/bin/uvicorn ranker.serve:app --reload

torch:        ## train the PyTorch RankNet ranker
	$(PY) -m ranker.torch_ranker --synthetic

tf:           ## train the TensorFlow/Keras ranker (needs .venv-tf, Python<=3.12)
	.venv-tf/bin/python -m ranker.tf_ranker --synthetic

momentum-snapshot: ## Phase 5B nightly job (dry-run by default; APPLY=1 to write)
	@if [ "$(APPLY)" = "1" ]; then \
	   $(PY) ../scripts/daily_momentum.py --apply ; \
	 else \
	   $(PY) ../scripts/daily_momentum.py ; \
	 fi

ingest-news:  ## Phase 2B news pull (dry-run; SOURCE=techcrunch by default; APPLY=1 to write)
	@if [ "$(APPLY)" = "1" ]; then \
	   $(PY) ../scripts/ingest_news.py --source $(or $(SOURCE),techcrunch) --apply ; \
	 else \
	   $(PY) ../scripts/ingest_news.py --source $(or $(SOURCE),techcrunch) ; \
	 fi

clean:        ## remove saved artifacts
	rm -rf ranker/artifacts
