# Migratlas task runner. Run `make help` for the target list.
#
# The environment and the data lake both live outside the working tree, under
# $HOME. Repos are often checked out on a mount that is slower than the local
# disk and does not support cross-filesystem hardlinks, and the raw data runs to
# tens of gigabytes, so neither belongs next to the source.
#
# Always go through make rather than calling uv directly: a bare `uv run` will
# create a ./.venv in the working tree instead of using the one below.

SHELL := /bin/bash
.DEFAULT_GOAL := help

export UV_PROJECT_ENVIRONMENT ?= $(HOME)/.venvs/migratlas
export UV_LINK_MODE ?= copy

# Data locations deliberately live in .env and config.py, not here. Exporting
# MIGRATLAS_DATA_DIR from make would silently outrank .env, since real environment
# variables beat dotenv values -- one source of truth is worth more than the shortcut.

UV := $(HOME)/.local/bin/uv
RUN := $(UV) run --

.PHONY: help
help:  ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
.PHONY: sync
sync:  ## Create/update the venv from the lockfile and the data directories
	$(UV) sync --all-extras --group dev
	@echo "venv: $(UV_PROJECT_ENVIRONMENT)"
	@$(RUN) migratlas init

.PHONY: paths
paths:  ## Show where data actually lives, as resolved from .env and defaults
	$(RUN) migratlas paths

.PHONY: lock
lock:  ## Refresh uv.lock
	$(UV) lock

# ---------------------------------------------------------------------------
# Quality gates -- what CI runs
# ---------------------------------------------------------------------------
.PHONY: check
check: lint typecheck test  ## Run every gate

.PHONY: lint
lint:  ## ruff check + format check
	$(RUN) ruff check src tests
	$(RUN) ruff format --check src tests

.PHONY: format
format:  ## Apply ruff formatting and safe fixes
	$(RUN) ruff check --fix src tests
	$(RUN) ruff format src tests

.PHONY: typecheck
typecheck:  ## mypy strict
	$(RUN) mypy

.PHONY: test
test:  ## Unit tests (no network)
	$(RUN) pytest

.PHONY: test-network
test-network:  ## Tests that hit real remote sources
	$(RUN) pytest -m network --run-network

.PHONY: test-localdata
test-localdata:  ## Tests that need operator-placed raw files
	$(RUN) pytest -m localdata --run-localdata

.PHONY: coverage
coverage:  ## Tests with coverage report
	$(RUN) pytest --cov --cov-report=term-missing

# ---------------------------------------------------------------------------
# Pipelines
# ---------------------------------------------------------------------------
.PHONY: provenance
provenance:  ## Regenerate docs/data/PROVENANCE.md from the source registry
	$(RUN) migratlas catalog provenance

.PHONY: taxon-index
taxon-index:  ## Rebuild the frontend species index from the GBIF Backbone
	$(RUN) migratlas taxonomy build-index --out web/public/taxon-index.json

.PHONY: lake-check
lake-check:  ## Report schema drift between the lake and the canonical schemas
	$(RUN) migratlas lake-check

.PHONY: ingest-darkecology
ingest-darkecology:  ## Dark Ecology radar profiles -> lake (FLUX, aerial)
	$(RUN) migratlas ingest darkecology

.PHONY: ingest-megamove
ingest-megamove:  ## MegaMove 1-degree grids -> lake (ABUNDANCE_SURFACE, marine)
	$(RUN) migratlas ingest megamove

.PHONY: ingest-obis
ingest-obis:  ## OBIS speciesgrids -> lake (ABUNDANCE_SURFACE, marine)
	$(RUN) migratlas ingest obis

.PHONY: build-layers
build-layers:  ## Export the globe's layers from the lake, through the ethics gate
	$(RUN) migratlas build-layers --out web/public/layers

.PHONY: phase1-report
phase1-report:  ## Replicate Horton et al. 2020 phenology, then extend
	$(RUN) migratlas report phase1

.PHONY: phase1-robustness
phase1-robustness:  ## Break sensitivity, daytime placebo and permutation null
	$(RUN) migratlas report phase1-robustness

.PHONY: gpu-check
gpu-check:  ## Confirm a CUDA device is visible from inside the venv
	$(RUN) python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"

# ---------------------------------------------------------------------------
# Frontend (runs on Windows -- node lives there)
# ---------------------------------------------------------------------------
.PHONY: web-install
web-install:  ## npm install for the globe
	cd web && npm install

.PHONY: web-dev
web-dev:  ## Vite dev server
	cd web && npm run dev

.PHONY: web-build
web-build:  ## Production build
	cd web && npm run build

.PHONY: clean
clean:  ## Remove build/test caches (never touches the data lake)
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov dist
	find src tests -type d -name __pycache__ -prune -exec rm -rf {} +
