# Phase 1a — nocturnal passage phenology from weather radar

**Status:** replication complete, extension provisional · 2026-07-28

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

## Extension to 2025, and why it is provisional

| | 1995–2018 | 1995–2025 |
| --- | --- | --- |
| Spring q50 | −0.48 ± 0.32 | **−0.11 ± 0.22** |
| Autumn q50 | −0.23 ± 0.31 | **−0.46 ± 0.25** |

Adding seven years attenuates the spring advance and strengthens the autumn one. That is a
genuinely new observation, and it is the reason for extending a published analysis at all.
It is **not yet a finding**, for reasons that are all fixable and none of which are
cosmetic:

1. **The dual-polarisation break is unmodelled.** Every NEXRAD station was upgraded between
   March 2011 and June 2013. That is an instrument change in the middle of the series which
   can manufacture or mask a trend. The daily product does not label hardware generation, so
   per-station upgrade dates have to come from NOAA's Radar Operations Center. Until that
   term is in the model, any trend spanning 2011–2013 is confounded.
2. **Station coverage is not constant.** Reporting stations rise from 104 in 1995 to 159 by
   2017. Per-station OLS is robust to this in the sense that each station is its own series,
   but the *average across stations* changes composition over time.
3. **No hierarchical model.** Averaging per-station slopes weights a station with 15 usable
   years the same as one with 31, and discards the latitude structure the paper models with
   a GAMM. Station random effects and a latitude interaction are needed.
4. **The extension is not blind.** An exploratory pass over the full 1995–2025 series was
   run *before* the target method was known, so the extension result was seen before the
   analysis was frozen. The 1995–2018 replication is unaffected — its target was published
   in advance — but the extension carries this caveat permanently and honestly.

## What the signal is, and is not

The measurement is **aerial biomass**, not birds. MistNet separates precipitation from
biology, not birds from bats from insects. Both filtered and unfiltered `traffic` are
ingested precisely so that the precipitation-sensitivity comparison is available; the
insect contribution is not separable with this product at all and is a standing limitation
on any biological interpretation.

## Next, in order

1. Per-station dual-polarisation upgrade dates, as a break term.
2. Hierarchical model: station random effects, latitude interaction, coverage weighting.
3. Falsification tests — the day-window placebo (a trend in *daytime* passage indicates the
   instrument, not migration) and year-shuffled nulls.
4. Independent cross-check against eBird Status & Trends phenology.

## Reproduce

```bash
make phase1-report
```
