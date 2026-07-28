# Phase 1a — nocturnal passage phenology from weather radar

**Status:** replication complete; extension robustness-tested · 2026-07-28

Reproduce a published continental result first, then extend it. The published result is
[Horton et al. 2020, *Phenology of nocturnal avian migration has shifted at the continental
scale*](https://doi.org/10.1038/s41558-019-0648-9) (*Nature Climate Change* 10, 63–68).

## Their method, as stated in the paper

- **Metric.** Peak migration = *"the date by which 50% of the cumulative passage occurred"*.
  So their "peak" is the cumulative median, not a smoothed maximum. They also report the
  10th and 90th percentiles to capture the early and late phases.
- **Windows.** Spring March–June, autumn August–November (Fig. 1b,c axes).
- **Extent.** 143 contiguous-US radar stations, 1995–2018, >13 million scans.
- **Decadal trend.** Least-squares linear regression of peak date on year, per station,
  then averaged (Fig. 3a). A generalized additive mixed model is used separately for the
  year × latitude surface (Fig. 2).
- **Reported.** Spring −0.60 ± 0.15 d/decade. Autumn by flyway: western −0.89 ± 0.14,
  central −0.34 ± 0.18, eastern −0.52 ± 0.12. Spring advance at 35/40/45° N but *no change*
  at 30° N. Western flyway strongest in autumn.

## What this analysis does

Same metric, same windows, same per-station least-squares trend. Differences, all
deliberate and all consequential:

| | Horton et al. | Here |
| --- | --- | --- |
| Data product | own migration traffic rate from vertical profiles | published Dark Ecology daily `traffic` (reflectivity × speed, integrated over height and night) |
| Stations | 143 CONUS | 132–145 CONUS after a coverage filter |
| Quality filter | not stated in detail | nights with `coverage_fraction` ≥ 0.9, ≥ 40 nights per season-year, ≥ 15 years per station |
| Flyway bounds | mapped regions | longitude bands read off their Fig. 1a; **approximate** |
| Trend model | per-station OLS, plus a GAMM | per-station OLS only |

## Result: the replication holds

1995–2018, 132 stations:

| Quantity | Here | Horton et al. |
| --- | --- | --- |
| Spring q50 | **−0.48 ± 0.32** | **−0.60 ± 0.15** |
| Spring q10 | −1.63 ± 0.56 | steepest of the three |
| Spring q90 | −0.26 ± 0.43 | shallowest of the three |
| Spring 24–32° N | +0.02 ± 0.86 | "no change at 30° N" |
| Spring 32–37° N | −0.84 ± 0.65 | "considerable advances at 35° N" |
| Autumn q50, western | −0.69 ± 0.68 | −0.89 ± 0.14 (strongest flyway) |
| Autumn q50, central | +0.03 ± 0.55 | −0.34 ± 0.18 |
| Autumn q50, eastern | −0.12 ± 0.42 | −0.52 ± 0.12 |

Spring central estimates overlap within confidence intervals, and three distinctive
qualitative features reproduce independently: the q10 > q50 > q90 ordering of advance
magnitude, the absence of spring change at the lowest latitudes against a clear advance at
mid-latitudes, and the western flyway leading in autumn.

Autumn is weaker here than in the paper, and the central-versus-eastern ordering does not
reproduce. The most likely cause is the data product: `traffic` is reflectivity-weighted,
so it responds to the size distribution of scatterers as well as their number, and autumn
carries proportionally more insect biomass than spring.

## Extension to 2025

| | 1995–2018 | 1995–2025 |
| --- | --- | --- |
| Spring q50 | −0.48 ± 0.32 | **−0.11 ± 0.22** |
| Autumn q50 | −0.23 ± 0.31 | **−0.46 ± 0.25** |

Adding seven years attenuates the spring advance and strengthens the autumn one.

## Robustness (`make phase1-robustness`)

The dual-polarisation upgrade dates are not publicly available per station. NOAA's Radar
Operations Center hosts the deployment schedule behind a login, and the site refuses
anonymous connections. So rather than assert dates, the analysis reports the trend under
**four treatments of the break** and asks whether the answer depends on the choice.

Upgrade dates were also *recovered* from data-availability gaps — each radar went offline
for roughly a week to be fitted, and detecting that uses only whether records exist, never
their values, so it cannot import the trend it controls for. This matched the one
documented non-beta station exactly (KBGM, detected 2012-04-02 against a documented week of
2–7 April 2012), produced a median 7-day outage, and gave a fleet-wide distribution peaking
across 2011Q4–2013Q1 as documented. **But it could not be validated**: the five documented
beta sites show *no* gap near their published modification dates, so those dates evidently
refer to something other than an archive outage. The detected dates are therefore treated
as one specification among four, never as ground truth.

| Specification | Spring | Autumn |
| --- | --- | --- |
| No break term | −0.11 ± 0.22 | −0.46 ± 0.25 |
| Break at detected outage | +0.15 ± 0.40 | −1.10 ± 0.36 |
| Common break at 2012 | +0.26 ± 0.41 | −1.08 ± 0.35 |
| Transition 2011–2013 dropped | −0.13 ± 0.22 | −0.51 ± 0.21 |

| Falsification test | Result | Reading |
| --- | --- | --- |
| Permutation null (year labels shuffled within station) | spring [−0.16, +0.18], autumn [−0.18, +0.19] | autumn is outside; **spring is inside** |
| Placebo: daytime window | spring +0.00 ± 0.58, autumn −0.69 ± 0.65 | autumn **not clean** — but see below |
| Placebo: mid-winter nights (doy 1–45) | −0.21 ± 0.35 | pipeline does **not** manufacture large trends |

## What this supports

**Spring: no detectable trend over 1995–2025.** The estimate sits inside the permutation
null and flips sign depending on the break specification. The 1995–2018 advance that
replicates Horton et al. does not persist when 2019–2025 is added. That is a statement about
the extended window, not a contradiction of their result.

**Autumn: an advance that survives every specification, with uncertain magnitude.** All four
break treatments are negative with intervals excluding zero, the estimate lies outside the
permutation null, and the mid-winter placebo is clean. Magnitude is genuinely uncertain,
−0.46 to −1.10 d/decade: adding a break term roughly doubles it, which suggests the upgrade
imposed a level shift that partly *masked* the underlying trend.

The daytime placebo is the weak point. Autumn daytime passage trends at −0.69 ± 0.65, as
large as the night signal. That would be damning if daytime aerial biomass were zero — but
it is not. Diurnal migrants exist, and insect biomass is substantial and strongly diurnal,
especially in autumn. So the daytime trend may be real biology rather than an instrument
artefact, and this test cannot currently distinguish the two. That is why the mid-winter
placebo was added: it holds the instrument and pipeline fixed while removing the migration
entirely, and it comes back clean.

## Hierarchical model

Averaging per-station OLS slopes is what the paper did, so the replication does it too, but it
weights a station with 15 usable years the same as one with 31 and treats each slope as if it
carried no uncertainty of its own. `make phase1-hierarchical` fits the population trend
directly:

```
q50_doy ~ decade * (latitude - 40) + 1[year >= 2012]
          + (1 + decade | station)
```

`statsmodels` `MixedLM`, not a GAMM: R is unavailable on the development machine (no `sudo`,
and `glmmTMB` needs a system R). Weaker than the paper's GAMM and labelled as such. Random
slopes as well as random intercepts, because forcing every station onto one slope understates
the population standard error. Seasons are fitted separately — spring and autumn passage are
different phenomena with different drivers.

**It corroborates the replication.** Spring 1995–2018 comes to −0.44 ± 0.33 d/decade against
the averaged −0.48 ± 0.32; autumn to −0.23 ± 0.37 against −0.23 ± 0.31. The two estimators
agree, so the averaged number was not carried by a subset of stations.

**The instrument break matters more than expected, and in the opposite direction for the two
seasons.** With a 2012 level shift in the model:

| Window | Season | No break | With break | Break coefficient |
| --- | --- | --- | --- | --- |
| 1995–2018 | spring | −0.44 ± 0.33 | −0.22 ± 0.48 | −0.39 ± 0.62 |
| 1995–2018 | autumn | −0.23 ± 0.37 | **−0.80 ± 0.48** | **+1.04 ± 0.62** |
| 1995–2025 | spring | −0.19 ± 0.23 | +0.08 ± 0.36 | −0.54 ± 0.56 |
| 1995–2025 | autumn | −0.51 ± 0.23 | **−1.03 ± 0.36** | **+1.05 ± 0.57** |

Spring does not survive the break term in either window. Autumn strengthens: the upgrade
shifted measured autumn passage about a day *later*, which had been masking the advance. The
break coefficient is the same size in both windows, which is what a real hardware step should
look like.

**But the break is not latitude-invariant, and that is a problem.** Fitting the same model
inside each latitude band (extension window, autumn):

| Band | d/decade | Break |
| --- | --- | --- |
| 24–32°N | −0.99 ± 1.02 | +2.16 |
| 32–37°N | −1.53 ± 0.70 | +1.80 |
| 37–42°N | −0.74 ± 0.59 | +0.68 |
| 42–50°N | −0.64 ± 0.65 | +0.01 |

A hardware upgrade should not move passage date by two days in Florida and not at all in
Minnesota. In the southern bands that dummy is absorbing something else, most likely season
truncation: 213–334 doy is a northern-migration window, and at 24–32°N autumn passage runs
past its end, so any change in how that tail is captured lands on a year-2012 step. **The
defensible claim is therefore an autumn advance of roughly 0.6–0.7 d/decade at 37–50°N, where
the break coefficient is near zero — not the continent-wide −1.03.**

The linear `decade:latitude` interaction is null in every fit (p 0.29–0.59). That is a
statement about functional form rather than about latitude: the band fits are non-monotonic —
weakest in the far south and far north, strongest at 32–37°N — and a straight line through
latitude cannot represent that shape.

Model-based p-values here are optimistic against the permutation null in
`phase1-robustness`. Where they disagree, prefer the permutation null: it assumes nothing
about the error structure, which a panel of 145 spatially correlated stations plainly violates.

## Remaining limitations

1. **The southern autumn trend is not separable from the instrument.** See the band table
   above. Resolving it needs a season window defined per latitude, which is a change to the
   pre-registered method and so belongs in a fresh pre-registration rather than a patch.
2. **Station composition changes.** Reporting stations rise from 104 in 1995 to 159 by 2017.
3. **The extension is not blind.** An exploratory pass over the full series ran *before* the
   target method was known. The 1995–2018 replication is unaffected — its target was
   published in advance — but the extension carries this permanently.
4. **Insects are not separable.** The single largest interpretive limit, and the reason the
   daytime placebo is ambiguous.

## What the signal is, and is not

The measurement is **aerial biomass**, not birds. MistNet separates precipitation from
biology, not birds from bats from insects. Both filtered and unfiltered `traffic` are
ingested precisely so that the precipitation-sensitivity comparison is available; the
insect contribution is not separable with this product at all and is a standing limitation
on any biological interpretation.

## Next, in order

1. Independent cross-check against eBird Status & Trends phenology, which would also help
   adjudicate the insect question — eBird is birds only. Needs an API key.
2. A latitude-aware season window, pre-registered separately, to settle whether the southern
   autumn advance is real.

## Reproduce

```bash
make phase1-report
make phase1-hierarchical
make phase1-robustness
```
