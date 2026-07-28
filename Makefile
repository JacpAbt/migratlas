# Migratlas task runner.
#
# Every Python job runs inside WSL Ubuntu, even though the repo lives on the
# Windows filesystem. Two consequences are baked in below:
#
#   * The virtualenv lives on ext4, NOT next to the source. Creating a venv on
#     the /mnt/c 9p mount is slow and hardlinking across the mount boundary
#     fails, so UV_PROJECT_ENVIRONMENT relocates it and UV_LINK_MODE=copy stops
#     uv from retrying hardlinks it cannot make.
#   * The data lake also lives on ext4. The Dark Ecology download alone is
#     ~49 GB and would be painful over 9p.
#
# From WSL:      make lint
# From Windows:  wsl -d Ubuntu -- bash -lc 'cd "$(pwd)" && make lint'

SHELL := /bin/bash
.DEFAULT_GOAL := help

export UV_PROJECT_ENVIRONMENT ?= $(HOME)/.venvs/migratlas
export UV_LINK_MODE ?= copy
export MIGRATLAS_DATA_DIR ?= $(HOME)/migratlas-data

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
sync:  ## Create/update the venv from the lockfile
	$(UV) sync --all-extras --group dev
	@mkdir -p "$(MIGRATLAS_DATA_DIR)"
	@echo "venv: $(UV_PROJECT_ENVIRONMENT)"
	@echo "data: $(MIGRATLAS_DATA_DIR)"

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

.PHONY: coverage
coverage:  ## Tests with coverage report
	$(RUN) pytest --cov --cov-report=term-missing

# ---------------------------------------------------------------------------
# Pipelines
# ---------------------------------------------------------------------------
.PHONY: provenance
provenance:  ## Regenerate docs/data/PROVENANCE.md from the source registry
	$(RUN) migratlas catalog provenance

.PHONY: ingest-darkecology
ingest-darkecology:  ## Dark Ecology radar profiles -> lake (FLUX, aerial)
	$(RUN) migratlas ingest darkecology

.PHONY: ingest-megamove
ingest-megamove:  ## MegaMove 1-degree grids -> lake (ABUNDANCE_SURFACE, marine)
	$(RUN) migratlas ingest megamove

.PHONY: gpu-check
gpu-check:  ## Confirm the RTX 3090 is visible from inside the venv
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
