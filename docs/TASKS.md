# Open work

**Started 2026-08-01.** Until now the ordered work lived in `PLAN.md` (research), `DATASETS.md`
(what a new source must earn) and the stop conditions inside each method note — all good documents,
none of them a list you can point at. Two items also arrived from a session handoff numbered #29 and
#30, and those numbers existed nowhere in the repository. This file is where numbered work lives
now; the three documents above keep their jobs and are linked from the entries that depend on them.

Numbers are permanent. A finished item keeps its number and moves to the bottom.

## Now

| # | Item | Notes |
| --- | --- | --- |
| 1 | Housekeeping: `LICENSE`, `CLAUDE.md`, README status line, this file | The README said "Phase 0, nothing is published yet" while five findings shipped. |
| 2 | `composition-stable` computes its own number | `reports/findings.py` returns a literal for this one finding, against the module's own stated rule. Nothing would catch it drifting from `phase1c`. |
| 18 | The second register for the other three documents | `counterfactual.json`'s disagreement paragraph, `detectability.json`'s withheld rationales, `sandbox.json`'s knob explanations. Same treatment as finding 5, and the same rule: a plain sentence may drop precision and may never add reach. |
| 9 | SABAP occupancy-detection model, and the atlas finding | `models/occupancy.py` and `reports/phase1e.py`. First southern, first terrestrial, first non-radar finding. Must recover known parameters from simulated data before it touches SABAP. |
| 10 | Species pages, wave 2 | Bird occupancy change per species, the detection-corrected value beside the naive reporting rate. Depends on #9. |
| 11 | Factor panel and the interpretable model *(handoff #29)* | JRC surface-water change and GHSL built-up as explanatory-only factors, per `DATASETS.md` step 3, feeding an additive model with a drawable response curve per factor. |
| 12 | The transfer test | Three climate-response sensitivities — aerial-north, marine-north, terrestrial-south. Fit on two, predict the third, publish the error. The experiment `coverage-bias` promises and nobody runs. Depends on #9. |

## Queued, with a reason to wait

| # | Item | Why it waits |
| --- | --- | --- |
| 13 | Forecast A: passage date under ScenarioMIP | `DATASETS.md` step 1. One new experiment list in `drivers/cmip6.py`; the novelty mask is the headline. Waits because #9 widens the evidence base it would be built on. |
| 14 | Tighten the multi-realm ledger test to multi-class | `tests/test_findings.py` has the TODO. Land a finding whose realm is terrestrial and whose taxa are not birds first — #9 is birds, so this needs the tracks to produce a finding. |
| 15 | Inline glossary, and a guided path through the five findings | Both strong for a non-technical reader; both explicitly out of scope for the current arc. Pick up on request. |
| 16 | LUH2 route verification | Only if #11 finds a factor effect worth projecting. A projectable driver with no established effect is a solution without a problem. |

## Refused, and why

Kept here so they are not rediscovered as good ideas.

| Item | Reason |
| --- | --- |
| FluxRGNN-style nocturnal-flux nowcast | 220 GiB of vertical profiles, GPU training, and direct competition with BirdCast on the same radar network. `docs/methods/literature-2026-07.md` §2. Revisit only as an explicitly-labelled engineering exercise, never as the novelty claim. |
| ENRAM as a second radar network | One radar of ~190 has fifteen usable autumns, so it cannot carry a trend. Out, not deferred. |
| eBird Status & Trends on the globe | The licence forbids redistribution and the gate enforces it. Analysis only. |
| GRIP4 roads, offshore infrastructure, night lights | `DATASETS.md` gives each its own reason. |
| More attempts at the 2012 latitude-graded step | Four candidate explanations tested, four failed. It stays exposed as an `open` bias domain, which is the honest treatment. Worth one more look only if another source turns up a general instrument-change signature. |

## Done

| # | Item | Outcome |
| --- | --- | --- |
| 25 | The globe under the night sky, and a colour-vision test | Every basemap value moved from warm brown into the page's own slate blue, and the Viénot simulation runs in the suite instead of sitting in a comment. It found `--detect-short` 43 from `--detect-unknown` under deuteranopia, and that the separations recorded in `tokens.css` did not reproduce. |
| 8 | The 617 Missouri bison rows sitting in Berlin | A per-taxon implied-speed ceiling, as filed, plus two things the data showed and the note did not: raw implied speed is unusable across shared timestamps, and the decision has to be per stretch rather than per row. It also found a third artefact — the collars were driven 400 km west on 2022-10-17 — and cost two wrong versions that each deleted real movement. 1,377 rows of 6,047,093 go; MMRV keeps all 1,502. |
| 28 | The detectability layer was drawn while its box read off | Not the diagnosis it was filed with: the initial visibility *was* applied. `exploreView` was handed every layer that loaded and switched them all on, including one declared off, while the panel went on reading the declared value. Explore mode now draws what the layers declare, and a test compares every checkbox against its layer's MapLibre visibility in both directions. |
| 27 | The globe drawn in the same hand | Land hatched in pencil through `fill-pattern`, a hand-ruled graticule, and the coastline drawn twice — each with the bound it needs written as a test, because tiling, closure and positional error are the three things none of this can be eyeballed for. Not the data layers: a circle is a measurement, and wobbling it draws a shape the data does not have. |
| 26 | The paper was not paper | Both textures re-centred on the neutral value of the blend that uses them, and the blend mode added to the two surfaces that painted paper without it and so showed the raw texture. The contrast suite measures the sheet as it is rendered now, not the token underneath it. |
| 24 | The furniture | The scrollbar is a ruled line with a pencil stub on it, the map's zoom and projection buttons are paper chips with drawn marks, and the scale bar is a drawn measure. All generated with the same pen and handed to CSS as data URIs, because none of these can hold an `<svg>`. |
| 23 | Every mark on rough.js | The hand-rolled hash-and-jitter is gone, each mark carries a name the tests can select, and a mark can be regenerated on a palette change rather than restyled. |
| 22 | Type as a setting | Three presets — hand throughout, hand for headings only with Atkinson Hyperlegible under it, and OpenDyslexic — each with its own scale and leading, because the faces do not share an x-height. |
| 21 | The foundation: fonts, textures, tokens | Direction A under the real app. The green split for contrast the way the rust already was, night as a night sky rather than the day page with the lights off, and both the paper texture and the font subsets corrected after both turned out to be measurably not what I had said they were. |
| 1 | Housekeeping | `LICENSE`, `CLAUDE.md`, this file, README status and phase table. |
| 7 | Species pages, wave 1 | 3,669 pages: 755 marine distribution shifts with their per-survey rows, 4 tracked mammals, 2 refusals, and 2,909 that say plainly that nothing here measures this animal. |
| 20 | The sketchbook, finished | The tools panel is on the same torn paper as the claims, the sliders are ruled scales with a pencil-stub thumb, and the last U+2713 on the site is a drawn mark. |
| 6 | The sketchbook rebuild | [ADR 0008](adr/0008-the-sketchbook-rebuild.md). Paper as a torn sheet, every control drawn, the page turn, and a claim with its own address. The architecture stayed; the visual layer was rebuilt. |
| 19 | Night, reachable | A day/night/system switch that survives a reload, black paper in place of the slate blue-grey, a night basemap, and every layer repainting when the surface changes. Six colours that had escaped the token set are in it. |
| 5 | Dual register: plain-language schema v3 | `plain`, `matters` and `plain_caveat` on every `Finding`, required by the schema and by four tests. The plain sentence is the heading, the precise claim is rendered in full underneath behind a "precisely" label, and the site says why a finding is worth knowing for the first time. |
| 4 | Pre-register the SABAP atlas comparison | [`docs/methods/phase1e-atlas.md`](methods/phase1e-atlas.md). The feasibility question it was written to answer came back yes: every row is "recorded on *k* of *n* cards", so detection is identifiable without a card identifier and the stop condition does not fire. |
| 2 | Two published numbers nothing recomputed | The composition claim's airspeed now comes from the fit `phase1c` prints, and is withheld if that fit stops being flat. The coverage limit counted evidence types in use and said five; four are, so it counts them from the lake now. |
| 17 | Delete the *Homo sapiens* rows the lake held | 119 rows in `obis_speciesgrids`, ingested before the never-ingested floor existed, removed from nine year partitions with 17,192,885 kept. `migratlas lake-floor` reports and `--apply` deletes; `make lake-floor` is the report. The pooled `marine-taxa-recorded` layer had been counting them as a marine taxon in 44 ocean cells, which the per-taxon gate never saw. |
| 3 | Re-resolve pre-fix taxon keys *(handoff #30)* | **The premise did not hold.** 1,329 taxon keys appear in more than one source and every one agrees, so a join on `taxon_key` was already safe and nothing was blocked. What was wrong was `taxon_label`: 95 keys carry two or more verbatim names across sources, and the search index took whichever it read first. Display names now resolve from the key. Two things were found underneath it — a live human occurrence surface on the site (see below) and `make taxon-index`, which would have replaced the 3,072-taxon search index with a thirty-animal seed list in a shape the frontend cannot parse. Both fixed. |

History before 2026-08-01 is in the git log, whose messages are long-form findings rather than
change summaries, and in the results sections appended to the method notes.
