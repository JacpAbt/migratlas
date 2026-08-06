# Datasets — what each one is for, and what a new one has to earn

**Recorded 2026-07-30**, after the Phase 2a causal step landed and before any forecasting work
starts. Every row count and every availability claim here was measured on that date, not quoted.

The reason for writing it: the candidate list of "interesting" environmental data is effectively
infinite, and most of it cannot enter a forecast even in principle. So this document states the test
a dataset has to pass first, then applies it to what is already in the lake and to what has been
proposed.

## The test

A dataset earns its place by filling one of four roles. Naming the role is what stops the list
growing by enthusiasm.

| Role | What it means | Can it enter a forecast? |
| --- | --- | --- |
| **Response** | Carries the thing being predicted, as a series long enough to fit a trend per unit. | It *is* the forecast target. |
| **Projectable driver** | A driver that also exists **in the future**, under a scenario. | Yes. |
| **Explanatory driver** | A driver that exists only for the past. | **No** — unless held constant, which is an assumption to declare. |
| **Control** | Falsifies, bounds or audits something. | Not directly, and it is often the most valuable role. |

The second and third rows are the distinction this whole document exists for. **A driver you cannot
project cannot appear in a forecasting model.** If passage date is fitted on built-up area, then
forecasting passage date for 2050 requires built-up area for 2050. That is a hard constraint, and it
is the reason "this factor is interesting" and "this factor belongs in the model" are different
claims.

Two further bars, both learned the hard way:

- **Fifteen years per unit, or it cannot carry a trend.** ENRAM was queued as the strongest single
  addition and dropped on this: one radar of ~190 has fifteen usable autumns
  (`geographic-coverage.md`).
- **Effort fixed by design, or the confound points the same way as the hypothesis.** OBIS failed on
  this and FISHGLOB passed (`phase1b-marine.md`). It is why an atlas *card* matters so much.

## What is in the lake

Measured from the lake on 2026-07-30.

| Source | Rows | Span | Role | What it has actually delivered |
| --- | --- | --- | --- | --- |
| `darkecology_daily` (FLUX) | 17,848,788 | 1995–2025, 31 yr | **Response** | The headline: autumn passage −0.56 ± 0.25 d/decade at 37–50°N, surviving four break specifications, a placebo and a permutation null. Also the composition audit. Everything else in Phase 1a/1c/2a hangs off it. |
| `fishglob` (SURVEY_INDEX) | 2,831,609 | 1963–2024, 62 yr | **Response** | The marine null — no pooled poleward shift, surveys disagreeing in *sign* — and the thermal-tracking test. The most useful negative result in the project. |
| `sabap1` (SURVEY_INDEX) | 3,123,626 | 1901–1999, 58 yr | **Response** | Landed 2026-07-30. First southern-hemisphere and first terrestrial source; the early half of an atlas-against-atlas comparison. No result yet. |
| `era5` (driver, gridded) | 76,415 | 1995–2025 | **Projectable** | `W_obs = +0.518 ± 0.047 °C/decade`, the predictor the response function is fitted on, and the independent precipitation record that ruled out drought as the 2012 step. |
| `narr` (driver, gridded) | 2,193,560 | 1995–2025 | **Control** | Airspeed, which bounded the taxonomic caveat: autumn composition is flat, so the trend is not birds turning into insects. Also the wind co-predictor that cleared confound 1. |
| `cmip6_damip` (driver, simulated) | 1,288,760 | 1914–2014 | **Control** | `f = 0.98`: the thermal half of the advance is anthropogenic. The project's novel contribution. |
| `fishglob` (driver, measured) | 240,325 | 1963–2024 | **Projectable** | Bottom and surface temperature *at the haul*, which is what made the thermal-tracking test possible without a reanalysis in the middle. |
| `ebird_status_trends` | 730,003 | 2023 only | **Control** | Independent cross-check on the radar phenology. Analysis-only: the licence forbids redistribution and the gate enforces it. |
| `obis_speciesgrids` | 17,193,004 | one row per taxon-cell | Map layer | Global extent on the globe and breadth in species search. **Cannot** support change: min/max year only, and effort expanded polewards over the same period as the hypothesis. |
| `megamove` | 3,487,176 | 1985 only | Map layer | Global marine extent, and the structural proof that the metric and driver layers are realm-general. One pooled 1985–2018 product, so no series exists to trend. |
| `darkecology` profiles | registered, unused | 1995–2025 | — | 220 GiB of vertical profiles. Would answer the spring airspeed question and permit the full Shi et al. mixture model. **Has delivered nothing so far**, and is honest to list as such. |
| `sabap2` | 25,687,526 queued | 2007–2026 | **Response** | Download requested 2026-07-30 via the GBIF API. The late half of atlas-against-atlas. |

Two entries in that table are doing a different job from the rest. `obis_speciesgrids` and
`megamove` are *why the globe looks like a globe* — 20.7M rows of worldwide coverage — and they can
never contribute a trend. That is not a defect as long as nobody asks them to.

This conclusion is now a published layer rather than a paragraph: see
[`detectability.md`](methods/detectability.md), which turns it into a one-degree map and puts a number
on it. **Four per cent of the cells the lake covers could support a trend.**

## What our own results support forecasting

This matters more than the dataset list, because it decides which drivers are needed at all.

**Forecast A — passage date under scenario warming.** We have a fitted response function
(`S = −0.659 ± 0.165` days per °C, within station, 78 stations) and an attribution for the warming
that drives it. Projecting it needs scenario temperature at those stations and nothing else.

- **The data exists and the code almost does.** The Pangeo CMIP6 catalogue `drivers/cmip6.py`
  already reads carries 1,392 ScenarioMIP `Amon tas` stores. Of the 15 models in our DAMIP ensemble,
  **13 have all four SSPs** (14 have ssp126, 15 ssp245, 13 ssp370, 15 ssp585). So this is a new
  experiment list in an existing loader, not a new pipeline.
- **Bias adjustment comes for free from the same trick as the attribution.** Use each model's
  scenario *anomaly* against its own baseline and add it to the observed baseline, and a model
  running warm or cold cancels — the reason `f` was defined as a ratio in the first place.
- **The novelty mask is likely to be the headline.** `S` is fitted over roughly the 1995–2025
  temperature envelope. Under SSP5-8.5 the late century leaves that envelope entirely, so an honest
  map will be masked over most of it. That is a result, not a failure, and it is the single most
  common way range-shift forecasting goes wrong.
- **Skill is testable today**, with no new data: hold out years and beat a climatology baseline.

**Forecast B — occupancy of atlas cells.** SABAP1 against SABAP2 gives two atlas periods twenty
years apart over the same region; fitting occupancy against climate and projecting is the standard
design. It needs scenario climate over southern Africa (same route as A) and, ideally, projectable
land use. It also needs the atlas-against-atlas change measured first, so it is downstream of work
in flight.

**Forecast C — nightly flux, FluxRGNN-style.** A different animal: short-horizon nowcasting, needing
the 220 GiB vertical profiles and a real deep-learning build. It needs **no new environmental data**
at all. Its value is a spectacular globe layer and demonstrated ML engineering, not research
novelty — worth being clear-eyed that those are different currencies.

## The proposed new datasets, judged against that

All availability checked 2026-07-30 by HTTP request.

| Candidate | Availability | Role | What it could add |
| --- | --- | --- | --- |
| **CMIP6 ScenarioMIP** (`tas`, four SSPs) | Confirmed: 1,392 stores in the catalogue already cached; 13 of our 15 models carry all four SSPs | **Projectable** | **Forecast A exists or does not exist because of this dataset.** Nothing else on this list is load-bearing in the same way. |
| **JRC Global Surface Water** | Confirmed open, no account: `occurrence` 51.6 MB, **`change`** 52.5 MB and `transitions` 17.5 MB per 10° tile, 30 m, 1984–2021 | Explanatory | The strongest of the factor ideas, because the question and the data coincide. Southern Africa is arid, SABAP1/SABAP2 straddle 1984–2021 almost exactly, and the `change` layer says directly which water was lost between the two epochs. This is the elephant question in a form we can actually test on birds. **Cannot enter a forecast**: no future surface water exists. |
| **GHSL built-up** (`GHS-BUILT-S`, R2023A) | Confirmed open: 145.7 MB (1995) and 152.5 MB (2020) per epoch, five-yearly 1975–2030 | Explanatory | Urbanisation around radar stations and atlas cells. South Africa's built-up area grew substantially between the two atlases. Runs to 2030 only, so even its "future" stops before any interesting horizon. |
| **Hansen Global Forest Change** | Confirmed open: 116.2 MB per 10° tile, v1.12 to 2024, annual loss year from 2001 | Explanatory | Deforestation as a factor for atlas cells — the miombo belt has real loss inside SABAP2's window. Weak for the radar: CONUS forest change 1995–2025 is modest and not systematically near stations. |
| **GRIP4 global roads** | Confirmed open: 909 MB for region 1 | — | **Reject for change detection.** One snapshot, so it cannot describe change at all, which is the only thing we are asking. Keep only if a barrier *baseline* is ever needed. |
| **Offshore infrastructure** (Global Fishing Watch) | Needs a free API token; gateway returns 401 | — | **Reject for now.** SAR detection starts 2017, against a marine record running 1963–2024 — seven years cannot speak to a sixty-year distribution question. The user's point that a platform can *attract* is right and worth testing one day; it is not testable on this record. |
| **Night lights** (DMSP-OLS + VIIRS) | Needs an EOG account; the two instruments are not comparable without a harmonised product | Explanatory | The factor with the most specific mechanism for *nocturnal* migration. Also the most work: an account, a splice, and a calibration argument. Second step, not first. |
| **LUH2 land use** | **Unverified — `luh.umd.edu` did not respond at all (http 000)** | **Projectable** | The one factor class with a genuine scenario form, because CMIP6 models are *forced* with it: gridded land use to 2100 under every SSP, including urban and forest fractions. If any factor effect turns out worth projecting, this is the only way to project it. Coarse (0.25°) where GHSL and Hansen are 30 m–1 km, so the observed and projectable forms of the same factor differ in resolution by two orders of magnitude, which is itself a caveat to state. Route must be verified before this is scheduled; ISIMIP and ESGF both redistribute it. |

## The plan

Ordered by what unlocks the most, and each step has a reason to stop.

1. **ScenarioMIP into the lake, then a skill test and a novelty mask.** One new experiment list in
   `drivers/cmip6.py`. After this, Forecast A is a report rather than an aspiration. *Stop if* the
   held-out skill does not beat climatology — then say so and the forecast chapter is a negative.
2. **Finish SABAP2** (download queued) and measure the atlas-against-atlas change. *Stop if* the
   consistent-footprint rule leaves too few comparable cells, which is the failure mode Phase 1b
   already demonstrated is real.
3. ~~**Surface-water change as the first factor, as attribution only.**~~ **Run 2026-08-05, and
   dropped.** [`methods/phase1g-water.md`](methods/phase1g-water.md). The effect is not detectable:
   partial *r* −0.036 over 496 cells, spatial nulls at p 0.59 and 0.79, and a one-sd water change
   moving the response by 3.2% of one sd. Dropped as this step pre-committed. Two things are worth
   keeping from it. The per-year water that would have matched the atlas windows is not
   downloadable — 2015 onward only, earlier years are Earth Engine — so the test ran on a product
   comparing 1984–1999 with 2000–2021 and is attenuated by construction; the null therefore means
   "not detectable with this instrument", not "no association". And the placebo returned a naive
   p of 0.031 in a subset chosen to show nothing, which the spatial null then dismissed at 0.085 —
   the clearest demonstration this project has that an ordinary p-value over two autocorrelated
   maps over-rejects.
4. **Only if step 3 finds something worth projecting**, verify a LUH2 route and add the projectable
   form of that factor. Not before — a projectable driver with no established effect is a solution
   without a problem.

Deliberately not scheduled: roads, offshore infrastructure, night lights, and the 220 GiB profiles.
Each has a stated reason above, and each can be picked up if a result asks for it.

## How this constrains the forecast, concretely

- **No map publishes without its novelty mask.** Non-negotiable, and with a fitted envelope of
  thirty years the mask will be large.
- **Every driver held constant must be named in the output**, not in a footnote. A projection that
  holds built-up area at 2020 is making a claim about the future of urbanisation.
- **The marine null forbids a pooled marine forecast.** Surveys disagree in sign; species × region is
  the unit, and a global marine projection would be confidently wrong.
- **`obis_speciesgrids` and `megamove` cannot enter any model.** They are the globe's coverage, and
  the moment a model reads them as a time series it is reading reporting history.
- **The southern bands stay excluded.** The 2012 step is unexplained after four candidate
  explanations, and a forecast fitted through an unexplained discontinuity inherits it.
