# Migratlas

A field notebook about animal movement — where animals go, how it has changed over decades, what is
driving the change, and where the evidence runs out. The whole world map is in the back pocket.

> **Status: v1.0.0.** 9 findings published and recomputed from the lake on every build, across
> 3 realms and 35 registered sources. Live at
> [jacpabt.github.io/migratlas](https://jacpabt.github.io/migratlas).
> The counts are guarded by `tests/test_readme_status.py` — they drifted twice when typed freehand.

---

## What this is

A book you read, backed by a research pipeline. Reading it is the visible half; the half that matters
is the attempt to answer *why* movements are changing, rather than only showing that they are.

It is arranged as a notebook because the argument has an order. An opening that says what is being
studied and why, before it says what was found. Chapters that are the argument — what changed, what
did not, what cannot be seen, what can be predicted, why — each filterable by realm, because air, sea
and land are what every source states and "birds" is a label the aerial instrument cannot support.
Every claim in four registers: what we found in plain words, how we found it, a drawn plate, then the
number with its scope and its caveat. And the world in the back pocket, where every published layer
is offered and nothing is argued over the top of it.

One authored book, two containers. A spread on a desk, and a phone that paginates the same pages its
own way — because a 375px column is not a 677px page, and forcing one shape onto both is worse than
letting each be itself.

Three things have to be true at once, or the project isn't worth doing:

1. **A shipped artifact** — a book that is pleasant to read and cheap to host.
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
                                                                    the book (static), and one
                                                                    MapLibre globe in its back
                                                                    pocket
```

Each claim's map is a **drawn plate** rather than a live one — hand-inked coastlines, a graticule and
a ring on the ground the claim is about, with a key for the three marks it actually carries. That is
why a chapter of claims boots no GPU: the globe is mounted once, by the chapter whose subject it is.

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
| **1h** | Do two collared herds show a trend in how far they move between seasons? | **no** — −1.84 ± 3.89 km/decade over 341 elk animal-years, +1.16 ± 2.13 over 219 reindeer |
| **2a** | How much of the change is attributable to human influence? | **−0.30 of the −0.56**, `f` = 0.98 across 15 CMIP6 models |
| **2b** | What drives an individual animal's decisions? | pre-registered — conditional logistic on 2h steps, four covariates fixed in advance; the terrain fetch is next |
| **3a** | Where is movement *predictable* at all? | mostly nowhere — autumn timing above chance at 20/143 radar stations, spring at the false-positive rate; marine and herd halves excluded by their own registered rules |
| **3b** | Does the marine record survive at the scale its own null demanded? | stopped by its own rule — the gear salvage recovered 17 single-gear segments and only 10 carried 20 years of in-situ temperature, against a registered floor of 12 |
| **3c** | What moves together, and what drives it? | one known signal of two — sea-surface temperature to plankton bloom detected cleanly, winter NAO to band green-up not, so the stop condition fired and no hypothesis edge was interpreted |
| **3d** | Would the two-stage forecast have worked, graded on the forecasts actually issued? | **no, and it refused its own licence** — the driver half carries real signal (map-median r +0.344) and the whole pipeline still failed chance |
| **3e** | Marine at its real scale, inside the satellite era | 18 units — the heterogeneity is emphatic (Q 235.7 against a bar of 27.6), and warming does not predict shifting (+0.04 ± 0.18) |
| **3f** | Can a pooled response model earn more skill than 3a found? | pre-registered, not run — the condition #57 named for itself |
| **3** | Where will they be? | not started — licensed only where 3a's map is not empty, and 3d refused that licence on the evidence |

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
the data that would explain it has not — **35.5% of the time-series rows are southern, against 0.80%
of the driver samples** — computed rather than estimated, and published as a finding in its own
right. Global extent, measurable change and explainable change are, so far, three different data.

Four of those phases stopped themselves. 3b fell below a floor it had registered in advance, 3c
interpreted no hypothesis edge because one of its two calibrations failed, 3d graded eight blind
predictions and refused the licence it was written to grant, and 3e found the opposite depth
interaction to the one registered and published it as false. Each is in the ledger or the method note
as a result, not as a delay — a pre-registration that turned out wrong is recorded as a correction
rather than edited away, and that convention is the most valuable thing in this repository.

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

[`CLAUDE.md`](CLAUDE.md) has the working rules and the traps that each cost a run to find.
Open work is in [`docs/TASKS.md`](docs/TASKS.md).

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
