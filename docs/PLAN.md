# Plan, revised after Phase 1

**Recorded 2026-07-29.** The original plan was written before any data was in hand. Phase 1 changed
what is worth doing next, mostly by narrowing claims that looked broader on paper. This is the
revision, the holes it leaves, and what happens to each hole.

## What Phase 1 established

Measured, not asserted. Each row constrains everything after it.

| Established | Consequence for the plan |
| --- | --- |
| The aerial autumn advance survives every confound test, but only at **37–50°N** (0.6–0.7 d/decade). Spring does not survive. The 2012 step is latitude-graded and **unexplained** — truncation, panel composition and curvature were each tested and each failed to explain it. | The result is regional. "Continental advance" is not available, and the step is an open question sitting inside the headline. |
| The radar measures **aerial biomass**. The July share (3.5% against 8.8% for a flat year) rules out resident insect biomass dominating the annual signal. Bats are not excluded, and nothing yet bounds the migratory insect share *night by night*. | The taxonomic caveat is still load-bearing. |
| The marine pooled shift is **null** (−0.011 ± 0.019 °lat/decade) while individual surveys reach −0.22 and +0.26 in **opposite directions**. | Pooling destroys findings. Species × region is the unit of analysis, which `phase2a-design.md` already fixes. |
| Every source with a usable time axis is northern-temperate; the two sources with global coverage (MegaMove, OBIS speciesgrids) have no time axis. | Global extent and global change are disjoint properties of this lake. |
| `TRACK`, `OCCURRENCE`, `DETECTION` and `MARK_RECAPTURE` are unused, and the terrestrial realm is empty. | The evidence-type core is proven on three types, not seven. |

## The holes

Researched 2026-07-29. Verdict on each, with the reason, including the ones being declined.

| Hole | Verdict |
| --- | --- |
| **Passage dates are computed from a speed-weighted quantity.** `traffic` integrates RTR = reflectivity × **speed** × bin height. A drift in flight speed — across years, or within a season — moves a passage-date quantile with no change in biomass. `reflectivity_hours` integrates VIR = reflectivity × bin height and carries no speed term. | **Fix now.** It is a free control on the headline result and it was never ingested. |
| **Screening severity over the record is unmeasured.** The product ships `fraction_rain` and both filtered and unfiltered quantities; `fraction_rain` was never ingested. | **Fix now.** Directly addresses the unexplained 2012 step: if the step is precipitation screening, it should track rain fraction and be graded by latitude the way rainfall climatology is. |
| **Composition is unmeasured night by night.** Airspeed separates birds (8–15 m s⁻¹) from insects (0–5 m s⁻¹); the method is published ([Shi et al. 2025](https://academic.oup.com/condor/article/127/3/duaf020/8051150)) and was demonstrated on high-insect regions, not on a multi-decade record. The daily product carries reflectivity-weighted `u`, `v` and **ground** speed, so airspeed needs only a wind field. | **Fix now, in the cheap tier.** One mean airspeed per station-night for 1995–2025. Bounds the taxonomic caveat and tests whether the *trend* is a composition trend. |
| **No driver panel exists.** `features/annotate.py` is planned and unbuilt, and the airspeed work, the thermal-tracking test and all of Phase 2a need it. | **Build next.** This is the critical path, not a Phase 2 detail. |
| **The site publishes layers, not findings.** Three raw layers, zero results. | **Fix after the driver panel.** It is the largest gap in the artifact and none of the research depends on it. |
| **Geography.** ENRAM is the strongest single addition and publishes **profiles only** — no integrated nightly product exists, so the height-and-night integration is ours to write. SABAP2 covers southern hemisphere, tropics and a missing continent. | **Queued, in that order.** Unchanged by this revision. |
| **eBird Trends** as an independent bird-only trend. | **Declined — verified unavailable.** The access key returns an empty object list for the trends releases, which is how this API says "no such thing" (it answers 200 with `[]`, never 404). |
| **Southern-hemisphere trawl series** to break the marine null's northern confinement. | **Declined for now, with a reason.** FISHGLOB's public release is North America and Europe by construction; the consortium holds metadata for ~95 surveys and data for ~65, of which 29 are public. New Zealand's open research-trawl data is a ~15k-record Darwin Core archive with catch weight stuffed into `occurrenceRemarks` and no haul-level effort table — not a survey series in the sense Phase 1b needs. There is no low-effort path. The high-value move is to **ask the consortium for the non-public surveys**, which is correspondence, not engineering. |
| **The full mixture model** (airspeed *and* velocity variability, per height bin). | **Deferred to a second tier.** It needs the per-bin VVP fit residuals, which live in the 220 GiB profiles, not the daily product. Worth a station subset only if the cheap tier shows drift. |

## Order of work

Unchanged in principle — change detection, then attribution, then forecasting — but the first item
is now *auditing the change we already detected* rather than detecting more.

1. **Homogenise the radar record before trusting more of it.** Add `reflectivity_hours`,
   `reflectivity_hours_unfiltered` and `fraction_rain` to the ingest — the 159 MiB source file is
   already cached, so this is a re-read, not a download. Then three tests: the speed-weighting
   control, the screening-severity test against the 2012 step, and the airspeed composition series.
   Existing results are unaffected: the Phase 1a report filters `quantity == "reflectivity_traffic"`,
   so new quantities are additive.
2. **`features/annotate.py` and the driver panel.** Required by test three above, and by
   everything in Phase 2a. The wind source is **NARR over OPeNDAP**, not ARCO-ERA5 — every array
   in that bucket is chunked one-timestep-whole-globe, so a single station-hour of 850 hPa wind
   costs a 154 MB read. Measured and reasoned in `adr/0006`, along with why 925 hPa rather than
   850, and verified end to end: 7.9 m/s median airspeed on the busiest nights, all headings
   south-westward. (An earlier draft of this line said 11.5 m/s, from a wind series one day out of
   alignment with the radar night; `adr/0006` records the offset sweep that found it.)
3. **Phase 2a first links, per `phase2a-design.md`.** Thermal tracking in FISHGLOB needs no new
   source; the aerial timing response needs only ERA5.
4. **Surface the findings on the globe** — a change layer and a results panel.
5. **The causal step** — CMIP6 DAMIP `hist-nat` against `historical`, per `phase2a-attribution.md`.
   Not in the 2026-07-29 list because it sat under "Phase 2a first links"; it is separate work and
   it is the plan's novel contribution. **Done 2026-07-30**: 15 models, `f = 0.98`, so the thermal
   half of the autumn advance is essentially all anthropogenic.
6. **SABAP2 and SABAP1**, per `geographic-coverage.md`. ENRAM is out, not merely deferred: one radar
   has ≥15 usable autumns, so it cannot carry a trend at all. Access was tested on 2026-07-30 and
   changes the shape of this item — SABAP1's archive is served by GBIF (133 MiB) and ingestible now,
   SABAP2's own IPT at UCT is **unreachable**, and the atlas API serves per-pentad card counts and
   reporting rates **pooled over 2007–present** rather than per year. So without a GBIF account the
   design is atlas-against-atlas (SABAP1 1987–1991 against SABAP2 pooled, the EBBA1→EBBA2 design)
   and there is no within-SABAP2 trend.
7. **Forecasting**, and `DATASETS.md` now decides what feeds it. The short version: the response
   function and its attribution are fitted, so the only *load-bearing* new dataset is CMIP6
   ScenarioMIP — 13 of the 15 DAMIP models carry all four SSPs in the catalogue `drivers/cmip6.py`
   already reads. Every landscape factor (water, built-up, forest, lights) is explanatory rather than
   projectable: it can attribute the past and cannot appear in a projection unless held constant and
   declared. That is the test each candidate is judged against there, with what it would add and the
   reason to stop.

## Corrections to the record

- **ENRAM is CC BY 4.0, not CC0.** `geographic-coverage.md` said CC0. Redistribution is still
  permitted, so the gate passes it, but with attribution — and the registry entry must say so.
- **aloftdata publishes vertical profiles only.** There is no pre-integrated nightly product, so
  ENRAM is not the drop-in second network the earlier note implied.
- **The Dark Ecology profiles are 100 m bins within 50 km of the station, up to 3000 m** above the
  radar; `speed` and `direction` come from a VVP uniform-velocity fit and are reflectivity-weighted.
  The descriptor states no limitations section, so the record's homogeneity over 1995–2025 is not
  characterised upstream — which is why items 1's three tests are ours to run.
