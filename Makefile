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
.PHONY: ribbon
ribbon:  ## Observed against counterfactual passage dates -> web/public/counterfactual.json
	$(RUN) migratlas build-ribbon

.PHONY: detectability
detectability:  ## Where change could ever be measured -> web/public/detectability.json
	$(RUN) migratlas build-detectability

.PHONY: sandbox
sandbox:  ## Recompute the analysis with each safeguard off -> web/public/sandbox.json
	$(RUN) migratlas build-sandbox

.PHONY: provenance
provenance:  ## Regenerate docs/data/PROVENANCE.md from the source registry
	$(RUN) migratlas catalog provenance

# No taxon-index target: the search index is written by build-layers, from what was
# actually published. A second command writing that file is how it got clobbered once.

.PHONY: taxon-names
taxon-names:  ## Resolve display names for published taxa into the cache (slow, resumable)
	$(RUN) migratlas taxonomy warm-names

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

.PHONY: ingest-fishglob
ingest-fishglob:  ## FISHGLOB bottom-trawl surveys -> lake (SURVEY_INDEX, marine)
	$(RUN) migratlas ingest fishglob

.PHONY: ingest-ebird
ingest-ebird:  ## eBird Status & Trends weekly abundance -> lake (analysis only, never published)
	$(RUN) migratlas ingest ebird-st

.PHONY: ingest-narr
ingest-narr:  ## NARR night winds at the radar stations -> lake (driver samples, gridded)
	$(RUN) migratlas ingest-narr

.PHONY: report-phase2a-attrici
report-phase2a-attrici:  ## ATTRICI against DAMIP, with the control that licenses the comparison
	$(RUN) migratlas report phase2a-attrici

.PHONY: ingest-attrici
ingest-attrici:  ## ISIMIP3a factual + ATTRICI counterfactual daily temperature -> lake
	$(RUN) migratlas ingest-attrici

.PHONY: ingest-era5
ingest-era5:  ## ERA5 monthly precipitation at the radar stations -> lake (driver samples)
	$(RUN) migratlas ingest-era5

.PHONY: build-findings
build-findings:  ## Recompute what the research established, for the globe to render
	$(RUN) migratlas build-findings

.PHONY: build-layers
build-layers:  ## Export the globe's layers from the lake, through the ethics gate
	$(RUN) migratlas build-layers --out web/public/layers

.PHONY: phase1-report
phase1-report:  ## Replicate Horton et al. 2020 phenology, then extend
	$(RUN) migratlas report phase1

.PHONY: phase1-hierarchical
phase1-hierarchical:  ## Station random effects rather than averaged per-station OLS
	$(RUN) migratlas report phase1-hierarchical

.PHONY: phase1-ebird
phase1-ebird:  ## Radar seasonal cycle vs birds-only eBird abundance (the insect question)
	$(RUN) migratlas report phase1-ebird

.PHONY: phase1-robustness
phase1-robustness:  ## Break sensitivity, daytime placebo and permutation null
	$(RUN) migratlas report phase1-robustness

.PHONY: phase1b-report
phase1b-report:  ## Marine distribution shift from FISHGLOB trawl surveys
	$(RUN) migratlas report phase1b

.PHONY: phase1c-report
phase1c-report:  ## Speed-weighting control and precipitation-screening test
	$(RUN) migratlas report phase1c

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

.PHONY: web-test
web-test:  ## Browser smoke test -- asks the map what it actually drew
	cd web && npm test

.PHONY: clean
clean:  ## Remove build/test caches (never touches the data lake)
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov dist
	find src tests -type d -name __pycache__ -prune -exec rm -rf {} +

.PHONY: phase2a-thermal
phase2a-thermal:  ## Thermal tracking: did a species keep its temperature or its place?
	$(RUN) migratlas report phase2a-thermal

.PHONY: phase2a-attribution
phase2a-attribution:  ## The causal step: human share of the advance, CMIP6 historical vs hist-nat
	$(RUN) migratlas report phase2a-attribution

.PHONY: phase2a-timing
phase2a-timing:  ## Does warming explain the autumn advance? S x W against observed
	$(RUN) migratlas report phase2a-timing

.PHONY: ingest-sabap2
ingest-sabap2:  ## SABAP2 atlas cards -> SURVEY_INDEX (terrestrial, southern hemisphere)
	$(RUN) migratlas ingest sabap2

.PHONY: ingest-bbs
ingest-bbs:  ## Breeding Bird Survey route counts -> SURVEY_INDEX (terrestrial, 1966-2025)
	$(RUN) migratlas ingest bbs

.PHONY: ingest-sabap1
ingest-sabap1:  ## SABAP1 atlas cards -> SURVEY_INDEX (terrestrial, southern hemisphere)
	$(RUN) migratlas ingest sabap1

.PHONY: ingest-cmip6
ingest-cmip6:  ## CMIP6 historical + DAMIP hist-nat pre-season temperature -> lake (simulated)
	$(RUN) migratlas ingest-cmip6
