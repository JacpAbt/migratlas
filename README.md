# Migratlas

A globe of animal movement — where animals are, how their movements have changed over decades,
what is driving the change, and where they are heading.

> **Status: Phase 0.** Foundations and the ethics gate. Nothing is published yet.

---

## What this is

An interactive globe backed by a research pipeline. The globe is the visible half; the half that
matters is the attempt to answer *why* movements are changing, rather than only showing that they are.

Three things have to be true at once, or the project isn't worth doing:

1. **A shipped artifact** — a globe that is pleasant to use and cheap to host.
2. **Sound research** — change detection that replicates a published result before extending it,
   attribution with a real identification strategy, forecasts that admit where they extrapolate.
3. **Engineering that holds up** — typed, tested, reproducible from a clean clone.

Two constraints govern everything else, in this order.

### 1. Animal safety and legality outrank every other consideration

Publishing animal locations can get animals killed. This is not a disclaimer — it is a **fail-closed
gate** that runs before data enters the pipeline and again before any tile is written. A species with
no sensitivity classification is **not publishable**, full stop.

The gate implements a published standard rather than a house policy:
[GBIF's *Current Best Practices for Generalizing Sensitive Species Occurrence
Data*](https://docs.gbif.org/sensitive-species-best-practices/master/en/), the
[TDWG Sensitive Species Extension](https://www.tdwg.org/community/dwc/sensitive-species/), and the
`dwc:dataGeneralizations` field for recording what was done.

Two decisions inside it are worth naming:

- **Sensitivity is a property of (taxon × realm × evidence type)**, not of a species. A shark
  occurrence record and a shark satellite track are not the same disclosure, so one flag per species
  cannot express the difference.
- **Generalisation is aggregation plus delay, never coordinate jitter alone.** A camera-trap study
  showed naive 1 km obfuscation could be narrowed to roughly 13% of the candidate area using public
  satellite imagery. Grid snapping destroys information; jitter hides it behind a solvable puzzle.

Full procedure in [`docs/ETHICS.md`](docs/ETHICS.md).

### 2. The core is taxon-agnostic

Birds have the best data by a wide margin and are the first vertical, but no bird assumption may
enter the core. The guarantee is mechanical rather than cultural:

- **Evidence types, not taxa.** Every source reduces to one of seven canonical shapes. Metrics,
  models and tile builders dispatch on the evidence type and never see the taxon.
- **The GBIF Backbone is the taxonomy spine**, not a bird-specific checklist.
- **A second realm lands early.** Marine data goes in during Phase 1, because a second realm forced
  through the same code is the only thing that actually prevents a bird-shaped core.
- **A test enforces it.** `tests/test_taxon_agnostic.py` scans the core's syntax tree for
  taxon-specific identifiers. It caught a real leak on its first run.

| Evidence type | Birds | Marine | Terrestrial | Bats / insects |
| --- | --- | --- | --- | --- |
| `TRACK` individual telemetry | ✓ | ✓ | ✓ | — |
| `OCCURRENCE` presence points | ✓ | ✓ | ✓ | ✓ |
| `ABUNDANCE_SURFACE` gridded | ✓ | ✓ | ✓ | — |
| `FLUX` instrumented passage | ✓ | ✓ | — | ✓ |
| `DETECTION` station-based | ✓ | ✓ | ✓ | ✓ |
| `MARK_RECAPTURE` | ✓ | ✓ | — | — |
| `SURVEY_INDEX` repeated counts | ✓ | ✓ | ✓ | ✓ |

One consequence worth stating: `taxon_key` is nullable throughout, because weather radar measures
aerial *biomass* and does not separate birds from bats from insects. A schema demanding a taxon there
would be quietly mislabelling the signal.

---

## Architecture

Static-first. Every heavy computation is a batch job producing immutable tiles; the browser only
range-requests them. There is no application server to run, secure or pay for.

```
sources ──► ingest ──► evidence lake ──► metrics / models ──► ethics gate ──► tiles ──► CDN
            (Parquet, evidence-typed, realm-tagged)                                      │
                                                                                         ▼
                                                                       MapLibre globe (static)
```

The frontend is **MapLibre GL JS v5 with globe projection, and no deck.gl in globe mode** — an
evidence-based choice, not a preference. deck.gl's `GlobeView` is still experimental with no basemap
provider and degrades above zoom 12, and a 2026 ISPRS benchmark measured CesiumJS at ~21,000 ms total
blocking time on large point data. Reasoning in [`docs/adr/`](docs/adr/).

Python for ingest, ETL, ML and tiling; R for the inferential statistics where the trustworthy
implementations live. Parquet is the interchange format, so neither language depends on the other's
runtime.

---

## Research programme

Ordered so each phase is the foundation of the next, rather than the most exciting thing first.

| Phase | Question | Status |
| --- | --- | --- |
| **0** | Can the ethics gate and the evidence core hold two realms? | in progress |
| **1** | What has *actually* changed, with proper uncertainty? | — |
| **2a** | How much of the change is attributable to human influence? | — |
| **2b** | What drives an individual animal's decisions? | — |
| **3** | Where will they be? | — |

Phase 1 replicates a published continental-scale result before extending it — reproducing a known
finding first is what makes the extension believable.

Phase 2a's counterfactual comes from climate model runs with human forcing removed, which turns
"movement correlates with warming" into an estimate of the anthropogenic share of the observed shift.

Method choices are frozen in [`docs/methods/`](docs/methods/) *before* held-out years are touched.

---

## Development

```bash
make sync     # create the environment from the lockfile
make check    # lint, typecheck, test
make help     # every target
```

Requires Python 3.14 and `uv`. Node for the frontend. Every Python dependency must be
wheel-installable — no build-from-source steps, which is a real constraint on the geospatial stack
and so far a satisfiable one.

---

## Data sources and credit

Every source is registered with its licence, required citation, and sensitivity classification.
Nothing enters the pipeline without an entry, and
[`docs/data/PROVENANCE.md`](docs/data/PROVENANCE.md) is generated from that registry.

This project is a consumer of other people's decades of fieldwork — radar archives, ringing records,
tag deployments, checklists. None of it is ours. Attribution is a build step, not a courtesy.

## Licence

Code is MIT. **Data is not** — each source carries its own terms, and several prohibit
redistribution. Cloning this repo gives you the code, not the data.
