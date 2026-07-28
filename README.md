# Migratlas

A globe of animal movement — where animals are, how their movements have changed over decades,
what is driving the change, and where they are heading.

> **Status: Phase 0.** Foundations and the ethics gate. Nothing is published yet.

---

## What this is

Three things have to be true at once, or the project isn't worth doing:

1. **A shipped artifact.** An interactive globe that is genuinely pleasant to use and cheap to host.
2. **Sound research.** Change detection that replicates a published result before extending it,
   attribution with a real identification strategy, forecasts that admit where they extrapolate.
3. **Engineering that holds up.** Typed, tested, reproducible from a clean clone.

And two constraints govern everything else, in this order:

### 1. Animal safety and legality outrank every other consideration

Publishing animal locations can get animals killed. This is not a disclaimer — it is a
**fail-closed gate** that runs before data enters the lake and again before any tile is written.
A species with no sensitivity classification is **not publishable**, full stop.

The gate implements the published standard rather than a house policy:
[GBIF's *Current Best Practices for Generalizing Sensitive Species Occurrence
Data*](https://docs.gbif.org/sensitive-species-best-practices/master/en/), the
[TDWG Sensitive Species Extension](https://www.tdwg.org/community/dwc/sensitive-species/), and the
`dwc:dataGeneralizations` field for recording what was done. Sensitivity is classified per
**(taxon × realm × evidence type)** — a shark's individual track is far more dangerous to publish
than a shark occurrence record, so one flag per species is not enough.

Generalization is **aggregation plus delay, never coordinate jitter alone**: a camera-trap study
showed naive 1 km obfuscation can be narrowed to roughly 13% of the candidate area using public
satellite imagery. See [`docs/ETHICS.md`](docs/ETHICS.md).

### 2. The core is taxon-agnostic

Birds have the best data by a wide margin and are the first vertical, but no bird assumption may
enter the core. The structural guarantee is not good intentions — it is three concrete decisions:

- **Evidence types, not taxa.** Every source reduces to one of seven canonical shapes. Metrics,
  models and tile builders target the evidence type and never see the taxon.
- **The GBIF Backbone is the taxonomy spine**, not eBird/Clements. eBird, WoRMS and ITIS are
  crosswalk adapters.
- **Marine data lands in Phase 1, not later.** A second realm forced through the same code early is
  the only thing that actually prevents a bird-shaped core.

| Evidence type | Birds | Marine | Terrestrial | Bats / insects |
| --- | --- | --- | --- | --- |
| `TRACK` individual telemetry | Movebank (CC0/CC-BY) | OTN, ATN | Movebank mammals | — |
| `OCCURRENCE` presence points | GBIF | OBIS | GBIF | GBIF |
| `ABUNDANCE_SURFACE` gridded | eBird S&T | MegaMove, MiCO | SDM output | — |
| `FLUX` instrumented passage | Dark Ecology, ENRAM | acoustic arrays | — | Dark Ecology, Motus |
| `DETECTION` station-based | Motus | OTN receivers | camera traps | Motus |
| `MARK_RECAPTURE` | EURING, BBL | turtle/fish tags | — | — |
| `SURVEY_INDEX` repeated counts | BBS, PECBMS, EBBA | surveys | camera arrays | light traps |

---

## Architecture

Static-first. Every heavy computation is a batch job producing immutable tiles; the browser only
range-requests them. There is no server to run, secure or pay for.

```
Sources ──► ingest/ ──► DuckDB + Parquet lake ──► metrics/models ──► redact ──► tiles/ ──► CDN
                        (evidence-typed,            (Python + R)      (gate)   (PMTiles/COG)  │
                         realm-tagged)                                                        ▼
                                                                        MapLibre v5 globe (static)
```

**Frontend is MapLibre GL JS v5 with globe projection, and no deck.gl in globe mode.** That is an
evidence-based choice, not a preference: deck.gl's `GlobeView` is still experimental with no basemap
provider and degrades above zoom 12, and a 2026 ISPRS benchmark measured CesiumJS at ~21,357 ms
total blocking time on large point data. MapLibre v5 renders heatmap, symbol, fill-extrusion and
custom layers directly on the globe. See [`docs/adr/`](docs/adr/).

**Python for ingest, ETL, ML and tiling. R for inferential statistics** where the trustworthy
implementations live (`amt`, `momentuHMM`, `glmmTMB`, `ctmm`). Parquet is the interchange format;
R jobs are subprocesses, not an rpy2 coupling.

---

## Development environment

This repo assumes a specific split, because the machine it was built on has one:

| Runs on | What |
| --- | --- |
| **WSL Ubuntu** | Every Python job. Python 3.14, `uv`, and the RTX 3090 for the ML phases. |
| **Windows** | git, `gh`, node/npm for the frontend, editing. |

The repo lives on the Windows filesystem so git and Vite run natively. Two things deliberately do
**not**: the virtualenv (`~/.venvs/migratlas`) and the data lake (`~/migratlas-data`), both on ext4.
Creating a venv on the `/mnt/c` 9p mount is slow and cross-mount hardlinks fail, and the Dark Ecology
download alone is ~49 GB.

Always go through `make` — it sets `UV_PROJECT_ENVIRONMENT` and `UV_LINK_MODE`. A bare `uv run` in
the repo root will helpfully create a `./.venv` on the slow mount instead.

```bash
make sync          # create the venv from the lockfile, create the data dir
make check         # lint + typecheck + test -- what CI runs
make help          # every target
```

From Windows, prefix with WSL:

```bash
wsl -d Ubuntu -- bash -lc 'cd /mnt/c/Users/*/Desktop/Mine/Programmazione/migratlas && make check'
```

**Python 3.14**, chosen for a specific reason rather than novelty: PEP 649 makes annotations lazy by
default, so `from __future__ import annotations` is obsolete and `TYPE_CHECKING` imports work at
runtime. The tail-call interpreter is a modest free speedup, and PEP 779 free-threading is available
later for parallel ingest and tiling. Every dependency including torch 2.13 was verified by
installing and importing on 3.14, not assumed.

Nothing in this project may require `apt install` — `sudo` is unavailable in the dev WSL, so every
dependency must be wheel-installable. That constraint is load-bearing for the geospatial stack, and
it holds: rasterio, pyogrio, zarr and the rest are all wheels.

---

## Research programme

Ordered so that each phase is the foundation of the next, rather than the most exciting thing first.

| Phase | Question | Status |
| --- | --- | --- |
| **0** | Can the ethics gate and the evidence core hold two realms? | in progress |
| **1** | What has *actually* changed, with proper uncertainty? | — |
| **2a** | How much of the change is attributable to human influence? | — |
| **2b** | What drives an individual animal's decisions? | — |
| **3** | Where will they be? | — |

Phase 1 replicates [Horton et al. 2020](https://www.nature.com/articles/s41558-019-0648-9)
(*Nature Climate Change*; US weather radar network, 1995–2018) **before** extending it to 2025.
Reproducing a known result first is what makes the extension believable.

Phase 2a's counterfactual comes from CMIP6 **DAMIP `hist-nat`** — a simulated world with human
forcing removed — which turns "migration correlates with warming" into an estimate of the
anthropogenic fraction of the observed shift.

Method choices are frozen in [`docs/methods/`](docs/methods/) *before* held-out years are touched.

---

## Data sources and credit

Every source is registered in [`src/migratlas/catalog/registry.yaml`](src/migratlas/catalog/registry.yaml)
with its licence, required citation, and sensitivity classification. Nothing enters the lake without
an entry. [`docs/data/PROVENANCE.md`](docs/data/PROVENANCE.md) is generated from it — run
`make provenance`.

This project is a consumer of other people's decades of fieldwork. The radar archive, the ringing
records, the tag deployments, the checklists: none of it is ours. Attribution is a build step, not a
courtesy.

## Licence

Code is MIT. **Data is not** — each source carries its own terms, recorded in the registry, and
several prohibit redistribution. Cloning this repo gives you the code, not the data.
