# Migratlas

A globe of animal movement — where animals are, how their movements have changed over decades,
what is driving the change, and where they are heading.

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

The frontend is **MapLibre GL JS v6 with globe projection, and no deck.gl in globe mode** — an
evidence-based choice, not a preference. deck.gl's `GlobeView` is still experimental with no basemap
provider and degrades above zoom 12, and a 2026 ISPRS benchmark measured CesiumJS at ~21,000 ms total
blocking time on large point data. Reasoning in [`docs/adr/`](docs/adr/).

Python for ingest, ETL, ML and tiling; R for the inferential statistics where the trustworthy
implementations live. Parquet is the interchange format, so neither language depends on the other's
runtime.

---

## Research programme

Ordered so each phase is the foundation of the next, rather than the most exciting thing first.

| Phase | Question | Answer |
| --- | --- | --- |
| **0** | Can the ethics gate and the evidence core hold two realms? | done — three realms, five evidence types in use, 20 sources |
| **1a** | What has *actually* changed, with proper uncertainty? | **autumn passage −0.56 ± 0.25 d/decade**, 37–50°N. Spring: no detectable trend |
| **1b** | Does the marine realm show the poleward shift the literature reports? | **no** — median −0.011 °lat/decade, and surveys disagree in *sign* |
| **1c** | Is the aerial signal an artefact of the instrument, or of what is flying? | neither — airspeed flat at −0.06 ± 0.08 m/s/decade, four confounds tested and rejected |
| **1d** | Can 6M mammal track fixes carry a timing trend? | **no** — 2 of 51 cells reach fifteen years, and changing the collar moves the date by 46.8 days |
| **1e** | Did southern-African bird distributions change between two atlases? | **no net change** — median Δψ −0.007 across 512 species on 496 shared cells |
| **1i** | Does the thermal-tracking measure transfer across realm and hemisphere? | **no** — the two spatial records agree across the equator; the phenological one sits 0.68 from both |
| **2a** | How much of the change is attributable to human influence? | **−0.30 of the −0.56**, `f` = 0.98 across 15 CMIP6 models |
| **2b** | What drives an individual animal's decisions? | not started |
| **3** | Where will they be? | not started |

Phase 1a replicates Horton et al. 2020 on their own window before extending it — reproducing a known
finding first is what makes the extension believable.

Phase 2a's counterfactual comes from climate model runs with human forcing removed, which turns
"movement correlates with warming" into an estimate of the anthropogenic share of the observed shift.
It is a narrow claim and worth stating precisely: **of the portion of the advance that tracks
pre-season temperature, essentially all is attributable to human forcing.** The other half of the
advance does not track temperature at all and remains unexplained.

Two things the table cannot show, both deliberate. A **latitude-graded step change at 2012** in the
southern radar bands is still unexplained after four candidate mechanisms were each tested and each
failed, so those bands are excluded from every claim. And the evidence has crossed the equator while
the data that would explain it has not — **35.9% of the time-series rows are southern, against 0.93%
of the driver samples** — computed rather than estimated, and published as a finding in its own
right. Global extent, measurable change and explainable change are, so far, three different data.

Method choices are frozen in [`docs/methods/`](docs/methods/) *before* held-out years are touched.

---

## Data sources and credit

Every source is registered with its licence, required citation, and sensitivity classification.
Nothing enters the pipeline without an entry, and
[`docs/data/PROVENANCE.md`](docs/data/PROVENANCE.md) is generated from that registry.

This project is a consumer of other people's decades of fieldwork — radar archives, ringing records,
tag deployments, checklists. None of it is ours. Attribution is a build step, not a courtesy.

## Licence

Code is MIT ([`LICENSE`](LICENSE)). **Data is not** — each source carries its own terms, several
prohibit redistribution, and one restricts commercial use of anything derived from it. Cloning this
repo gives you the code, not the data.
