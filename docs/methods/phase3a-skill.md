# Phase 3a — where is movement predictable from its environment, and by how much?

**Status:** pre-registered 2026-08-18. Written before any driver–response pair has been fitted,
correlated, or plotted. What *was* looked at first is in §1: unit coverage counts only, because
the era-split design needs to know the units exist before it can split them. The covariate
survey (`covariate-survey-2026-08.md`) and the coupling literature pass
(`literature-2026-08-coupling.md`) precede this note and constrain it.

## Why this note exists

The modeling arc (#54, TASKS) starts here because every later step borrows this one's licence: a
forecast drawn where hindcast skill is zero is decoration, and a coupling edge claimed between
two series neither of which responds to its own local environment is a teleconnection wearing a
costume. The product is a skill map — where movement is predictable, where it is not, and by how
much — with "not predictable" published at the same rank as "predictable", because for a site
whose argument is honesty the empty cells are the argument.

## 1. What was looked at before this was written

Counts only, from `lake.reader.scan`, measured 2026-08-18:

| realm | units | with ≥ 20 years | note |
| --- | --- | --- | --- |
| aerial (radar stations) | 161 | 143 | 4,515 station-years, 1995–2025 |
| marine (survey units) | 39 | 21 | 16 have ≥ 30 years |
| terrestrial (herds) | 2 | — | 17 and 13 usable years (Phase 1h) |

What was **not** looked at: any relationship between any driver and any response, any
correlation, any scatter, any fit, any per-unit value of any driver.

## 2. Estimand and units, with their known problems first

One skill number per unit, from one registered model class, against one registered baseline.

- **Aerial — per station-season.** Response: the year's median passage day (`q50_doy`, the same
  metric Phase 1 published) and, separately, the season's summed intensity. Drivers: monthly
  2 m temperature and total precipitation anomalies (ERA5, in the lake) over the months
  preceding and during the season, plus the climate indices (ONI, NAO, AO, PDO from their
  verified files; AMO computed in-lake from ERSST). Known problem: the 2012 instrument step
  (Phase 1c) sits inside the record; era-split places it in training for most stations, and a
  station whose skill *depends* on the step will be exposed by prediction 5.
- **Marine — per survey-year.** Response: the cross-taxa mean latitude anomaly of the analysed
  taxa, through the same preparation `phase1b.analyse` uses. Driver: in-situ haul temperature
  anomalies (`insitu`, the water the fish were in). Known problem: survey footprints and gear
  changed within some series; the unit inherits FISHGLOB's own flags, and a unit whose years
  are not comparable is excluded rather than modeled.
- **Terrestrial — per herd-year.** Response: the Phase 1h displacement. Drivers: green-up
  timing from the yearly NDVI series (a new reduction over the PKU archives already on disk)
  and ERA5-Land snow. Known problem, stated as prediction 4: Phase 1h measured this response
  flat, and a flat series offers a model nothing to beat the climatology by — the herds are in
  the design to *license the empty cells honestly*, not because skill is expected.

**Excluded, and why:** the atlases (two time points is not a series); all track-derived timing
(Phase 1d's 46.8-day instrument effect bars it); any unit with fewer than 15 years total or
fewer than 5 test years under the split.

## 3. The design, fixed before any fit

- **Era split.** Per unit: train on the first 70% of its years, test on the last 30%, minimum
  5 test years. No refitting on test years, ever; the test era is touched once.
- **Model class.** Ridge regression on standardized covariates, the covariate list fixed per
  realm as in §2, regularization chosen by leave-one-year-out CV **inside the training era
  only**. One class for every unit. No per-unit model shopping, no additions to the covariate
  list after this line.
- **Baseline.** The training-era climatology (the unit's own mean). Skill is the Murphy score,
  `1 − MSE_model / MSE_climatology`, on the test era: zero means the model knows nothing the
  mean did not.
- **The null.** Per unit, 1,000 fits against year-shuffled drivers (shuffling breaks the
  pairing, keeps both marginals); a unit's skill is reported significant only past the 95th
  percentile of its own null. Map-level honesty: the count of significant units is compared to
  the binomial expectation under no skill anywhere.

## 4. Predictions

1. Radar **spring** passage timing shows significant positive skill at more stations than the
   5% null expects. Spring is the temperature-forced season in the phenology literature; if
   this fails, the aerial skill map is empty and is published empty.
2. Spring skill exceeds autumn skill at the median station. Phase 1's own headline is an autumn
   *trend*; interannual *forcing* is a different property and the literature says it is weaker.
3. In at least half of the marine units with ≥ 20 years, haul-temperature anomalies carry
   significant positive skill for the centroid anomaly.
4. The herd displacement shows **no** significant skill in either herd — the Phase 1h null,
   re-expressed as a prediction. Grading this true publishes the honest empty cells; grading it
   false would be a finding that displacement responds to green-up after all.
5. Adding the climate indices to a station's covariates *reduces* the local-weather
   coefficients' contribution at stations where the indices alone already predict: part of any
   apparent local skill is the shared modes. This grades the coupling graph's central risk on
   this design's own data before #55 commits to anything.

## 5. Stop conditions

- If the aerial map-level count is indistinguishable from the binomial null, the atlas
  publishes the null map and the arc's next steps (#13, #57) do not proceed on aerial timing.
- If fewer than 10 marine units survive the exclusion rules, the marine half is published as a
  coverage statement, not a skill map.
- No prediction is regraded after seeing the test era; a wrong pre-registration is recorded as
  a correction, per house rule.

## 6. What this cannot establish

Causality (the design is predictive; #55 carries the causal question and its own note carries
its limits); skill under futures outside the fitted driver ranges (#13's novelty mask exists
for that); species-level marine stories (the unit is the survey, deliberately); anything about
realms or units the exclusion rules removed — their absence from the map is a statement about
the data, not about the animals.

---

## Results — the aerial half, run 2026-08-18

**Correction first, per house rule.** The first run of `reports/phase3a.py` fitted 0 spring
stations and printed "GRADED FALSE" over that emptiness. The cause was a data gap, not a
verdict: the lake's ERA5 had only ever been fetched for months 3–11, because Phase 2a needed
June–November and nobody had needed January before — so spring's registered pre-season window
(January–February) joined to nothing and the season silently emptied. The render now refuses
to grade an empty season, the full year was fetched (one write, both fields, 107,880 rows),
and the fit re-ran. Autumn's numbers reproduced exactly across the two runs, which is the
determinism the seed promised.

**The fits** (seed 20260818; columns `temp_season`, `temp_pre`, `precip_season`, `oni`,
`nao`, `ao`, `pdo`): 140 spring and 143 autumn stations.

- **Prediction 1 — GRADED FALSE.** Spring timing significant at 11 of 140 stations against a
  chance bar of 11: the spring skill map is indistinguishable from the 5% false-positive rate.
  The registration expected spring to be the predictable season; it is not, at these stations,
  from these covariates, at interannual scale.
- **Prediction 2 — GRADED FALSE.** Median spring skill −0.031 against autumn +0.005. Not only
  does spring fail to beat autumn, its median station predicts *worse* than the training-era
  climatology.
- **Prediction 3 — pending.** The marine fit has not run; it is the next half of this note.
- **Prediction 4 — pending.** The herd fit has not run.
- **Prediction 5 — GRADED TRUE.** At the 22 station-seasons where the modes alone predict,
  the weather's marginal contribution over the modes is +0.007 at the median, against +0.018
  for weather alone: part of what reads as local-weather skill is the shared modes wearing
  local clothes. This is the coupling graph's central risk (#55) measured on this project's
  own data, and its pre-registration must condition accordingly.
- **Autumn, for the record:** 20 of 143 stations significant against a chance bar of 12 —
  a sparse but above-chance map, with a median skill of +0.005, i.e. nothing at the typical
  station. Where autumn timing is predictable, it is predictable at specific stations, not as
  a blanket.

**What this means for the arc, read against §5's stop conditions.** The aerial map is not
indistinguishable from chance as a whole — autumn clears its binomial bar — so the arc
proceeds, but on autumn's terms, not spring's. Two graded-false predictions are the product
working as registered: a trend (Phase 1's −0.56 d/decade) and interannual predictability are
different properties, and this design just measured the difference. The skill map the site
publishes will show mostly empty cells with a scatter of autumn stations, which is the honest
picture.

## Results — the marine half, run 2026-08-18

**A stop condition fires first.** Of the surveys with twenty or more years, eight of fifteen
carried a gear change inside their span and were excluded by §2's comparability rule — the
trend fit absorbs a step with a break term, but the registered model class has none. Seven
units survived, below §5's floor of ten, so **the marine half publishes as a coverage
statement, not a skill map**: the honest sentence is that FISHGLOB's long surveys mostly
changed their instruments mid-record, and a skill claim built on the seven that did not would
be a claim about survey administration.

- **Prediction 3 — GRADED FALSE.** Haul temperature carries significant positive skill in 1 of
  7 fitted units, against the registered bar of half — and 1 is exactly the chance bar for
  seven units. Median skill +0.010. The water the fish were actually in does not predict next
  year's cross-taxa centroid anomaly at these surveys, at interannual scale, through this
  model class.

The response construction is worth restating because it is where this fit could have lied:
each species' anomaly is referenced to its own train-era mean (a full-period reference would
leak the test years into the response, the same leak the harness closes for covariates), and
each survey's temperature columns were fixed blind — both where the survey measured both for
twenty years, surface alone otherwise.
