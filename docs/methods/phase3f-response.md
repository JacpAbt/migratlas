# Phase 3f — is the ceiling on predicting passage timing the data, the drivers, or the model?

**Status:** pre-registered 2026-08-19. Written before any fit in any arm below has been run, and
before any driver–response relationship new to this phase has been computed, correlated or
plotted. What *was* looked at first is in §1: unit counts only, plus one already-published
coefficient that cuts against this phase's easy story and is quoted here so the design cannot
pretend not to know it. The addendum
[`covariate-survey-2026-08-addendum.md`](covariate-survey-2026-08-addendum.md) precedes this note
and constrains it.

## Why this note exists

Phase 3a asked whether passage timing is predictable from its environment and answered mostly no:
autumn above chance at 20 of 143 stations, spring at the false-positive rate. Phase 3d then took
the full two-stage pipeline to eight blind years and refused its own licence. #57 recorded the
condition for reopening: *a future response model earning more observed-driver skill than Phase 3a
found.* This is that attempt.

The reason to expect anything is arithmetic rather than optimism. Phase 3a fitted **143 separate
ridges, each on about nineteen training rows against seven covariates** — 2.7 rows per parameter.
A design at that ratio returns nothing much whether or not there is anything there, so "timing is
not predictable" and "this instrument cannot see whether timing is predictable" are not yet
distinguished. Nothing here is a cleverer model. It is the same model class with the rows put
together, and one driver the harness never had.

The phase is built as a **ladder**, one change per rung, because a single experiment that changed
the estimator and the covariates and the model class at once would produce a number nobody could
attribute. Each rung is measured against the one below it.

## 1. What was looked at before this was written

**Coverage, measured 2026-08-19 from the lake** through `lake.reader`, joining Phase 3a's own
covariate assembly and the response it published. No relationship of any kind was computed.

| season | panel | stations | station-years | clear the era split | their station-years | pooled training rows |
| --- | --- | --- | --- | --- | --- | --- |
| spring | Phase 3a's seven covariates | 145 | 3,970 | 140 | 3,917 | **2,691** |
| spring | + wind support | 145 | 3,970 | 140 | 3,917 | **2,691** |
| autumn | Phase 3a's seven covariates | 145 | 4,026 | 143 | 4,015 | **2,748** |
| autumn | + wind support | 145 | 4,026 | 143 | 4,015 | **2,748** |

Two facts from that table decide the design.

**Wind costs nothing in coverage.** `wind_support` returns 145 stations in both seasons — 4,146
spring station-years and 4,172 autumn — which is *more* than the response has. **Zero stations are
lost** to the join in either season: the binding constraint is the radar panel, not the wind. This
was the phase's main feasibility risk and it is not one. The autumn unit count also reproduces
Phase 3a's 143 exactly, which is the first sign the harness is reading the same panel.

**The pooling contrast is 143-fold.** Nineteen training rows per station against seven covariates,
or 2,748 rows against the same seven. Per parameter that is 2.7 against 392.

**One prior result that cuts against the wind story, quoted before the design that follows.**
Phase 2a already fitted seasonal-mean wind support as a co-predictor of autumn passage date within
station and published the coefficient: **−0.243 ± 0.385 days per m s⁻¹, indistinguishable from
zero**, with the two predictors essentially uncorrelated within station at **+0.025 ± 0.048**. So
the autumn seasonal mean is not an untested driver — it is a *tested and null* one, at nineteen
rows per station. What is untested is narrower, and the ladder is built to separate the three
parts: the same term in **spring**, which no fit in this project has ever seen; the same wind in a
**different form**, since a mean over roughly 120 nights can sit flat while the number of usable
nights moves the date; and the same term judged by **out-of-sample skill** rather than by an
in-sample coefficient, which is what pooling changes. Prediction 4 is written against this
evidence rather than against enthusiasm.

**What was not looked at:** any skill number in any arm, any coefficient in any pooled fit, any
per-station driver value, any spring wind coefficient, any correlation new to this phase.

## 2. Estimand and units, with their known problems first

**One skill number per station-season per arm**, on the test era, against the same baseline Phase
3a used.

- **Response:** the year's median passage day `q50_doy`, from the same `passage_quantiles` call
  with the same `MIN_COVERAGE` and `MIN_NIGHTS` filters as `phase3a.aerial()`. Unchanged on
  purpose: if the response moved, the comparison against 20-of-143 would not be a comparison.
- **Unit:** the station-season. 140 spring and 143 autumn stations clear the split.
- **Baseline:** the unit's own training-era mean. Skill is the Murphy score
  `1 − MSE_model / MSE_climatology` on the test era. Identical to Phase 3a, which is what makes
  the rungs commensurable.

Known problems, stated before the design rather than after the result:

- **The 2012 instrument step is now a shared contaminant.** Phase 1c found a latitude-graded step
  around the dual-polarisation rollout that survived four explanations. When each station was
  fitted alone it could only damage its own estimate. A pooled fit shares coefficients, so the
  southern stations' step reaches every station's prediction. This is the single most important
  difference between Phase 3a's design and this one, and §3 handles it explicitly with a term, a
  measurement of that term's effect, and a restricted-band sensitivity.
- **Wind is not forecastable at seasonal lead.** Skill bought with wind licenses a *mechanism*
  claim and not a forecast, which is why §3 requires two skill numbers per unit rather than one.
- **The era split places the step in training for most stations**, as in Phase 3a. Inherited, not
  fixed.
- **Timing only.** Phase 3a also fitted seasonal intensity; this phase does not, so that the
  ladder stays legible. Intensity is a separate registration.

**Excluded, and why:** photoperiod, though the addendum nominated it — in a within-station design
it has no interannual variance at all, so it can enter only as a cross-station interaction, which
asks why *sensitivity* varies rather than whether timing is predictable, and belongs to its own
note. Degree-days and every other new fetch, because this phase deliberately runs on the lake
exactly as it stands. All track-derived timing, per Phase 1d. The atlases, per Phase 3a.

## 3. The design, fixed before any fit

### The ladder

| arm | estimator | covariates |
| --- | --- | --- |
| **A** | per-station ridge, Phase 3a's `hindcast` verbatim | Phase 3a's seven |
| **B** | pooled | Phase 3a's seven **+ post-2012 level shift** |
| **B′** | pooled | Phase 3a's seven, no level shift |
| **C** | pooled | B's, **+ seasonal-mean wind support** |
| **D** | pooled | C's, **+ favourable-night share** |
| **E** | pooled, spline basis | D's covariates, expanded (below) |

Arm A is a **calibration rung**, in the sense `phase3c-coupling.md` established: it must reproduce
a result already published, and if it does not, the harness is wrong and nothing above it is
interpreted. B − A isolates pooling; B − B′ measures what the instrument-step term does; C − B
isolates the wind's inclusion; D − C isolates the wind's *form*; E − D isolates the model class.

### The pooled estimator, stated exactly

1. Split each unit's year-ordered rows by `models.skill.era_split` — first 70% train, minimum 5
   test years, minimum 15 total. Unchanged.
2. Centre the response and every covariate **within station, using training-era means only**. The
   test years never enter a mean. This is Phase 2a's within-station design and it makes the
   intercept per-station by construction, so a pooled slope vector never has to explain why
   Florida and Minnesota differ in level.
3. Stack every unit's centred training rows into one design and solve one ridge in closed form,
   through `models.skill.fit_ridge`.
4. Predict a unit's test years as *its own training mean of the response* plus its centred test
   covariates times the shared coefficients.
5. Score each unit with `models.skill.murphy_score` against that same training mean.

**λ is chosen by leave-one-station-out cross-validation inside the training era**, refitting for
each held-out station. Phase 3a used leave-one-*year*-out, which is the right unit for a
single-station fit and the wrong one here: with rows pooled, the generalisation question is
whether the shared coefficients transfer to a station the fit has not seen.

**The λ grid is `numpy.logspace(-2, 4, 13)`**, wider than Phase 3a's five values. Recorded as a
deliberate change with its reason: a ridge penalty competes with the number of rows, so a grid
fixed for a 14-row fit is not the same grid for a 2,748-row fit, and inheriting it would test
pooling with the regularisation effectively switched off. The grid is fixed here and is not
revisited after any skill number is seen.

### The two new covariates, defined before they are computed

- **Seasonal-mean wind support** — `phase2a_timing.wind_support(season)`, the term Phase 2a
  registered and fitted, now called for both seasons. Not a new metric.
- **Favourable-night share** — the share of a unit's usable nights in that season whose support
  exceeded **the station's own training-era median nightly support**. The threshold is per station
  and training-only, so it needs no arbitrary physical constant and cannot read the test era. By
  construction the share sits near 0.5 in training and its interannual movement is the signal.

### Arm E's basis, defined before it is fitted

Each covariate is replaced by a **natural cubic spline basis with three interior knots at its
training-era quartiles**, plus one interaction: temperature × wind support. Splines rather than a
polynomial because the plausible nonlinearity here is a threshold or a saturation, which a
quadratic represents badly. Closed form under the same ridge, the same split, the same null.

**Gradient boosting is deliberately not registered**, and the condition for it is written here so
the decision is not made after seeing a result: if arm E's median skill exceeds arm D's by more
than half the distance from D to its own null bar, the model class is worth pursuing and a
successor registration adds a boosting library — a new dependency justified by a measurement. If
arm E finds nothing, the question "is linearity the limit" has been answered at the honest scale
of 2,748 rows and a larger library would be answering it again with more machinery.

### The null, and the significance rule

Per unit, **1,000 refits against year-shuffled drivers**, shuffling year labels *within each
station* so the pairing breaks and both marginals survive, and refitting the pooled model each
time. A unit is significant only past the 95th percentile of its own null. Map level: the count of
significant units is compared against the binomial expectation under no skill anywhere — the bar
is **11 of 140** in spring and **12 of 143** in autumn, computed today by `binomial_bar`.

Seed `20260819`, fixed here.

### The reporting rule that keeps this honest

Every arm reports **two skill numbers per unit**: from **projectable drivers only** (temperature,
precipitation, the modes — the ones a seasonal forecast can supply) and from **every driver
admitted** (adding wind, which it cannot). The first is the only number that may ever be cited
toward #57 or any forecast; the second is the number that answers *why*. This is §2 of the
addendum turned into a requirement, and it exists because a mechanism gain silently inflating a
forecast claim is exactly the failure Phase 3d's refusal was protecting against.

### Two registered sensitivities

- **B′ against B** — what the instrument-step term is doing to the pooled fit.
- **Arm D restricted to 37–50°N** — the band where Phase 1c found the step near zero. Reported
  beside the full-panel number, never instead of it.

### Amendments, 2026-08-19, written while implementing and before the registered run

Five things §3 above under-specified, resolved here rather than silently in code. All five were
settled **before any significant-unit count existed**, and none of them was chosen by looking at
one.

1. **Scaling.** The design above says *centre* and does not say *scale*. Ridge is not
   scale-invariant, so a single penalty applied to degrees Celsius, millimetres and a
   dimensionless index at once would be arbitrary. Every column is divided by its **pooled
   training-era standard deviation** after centring. Pooled rather than per-station on purpose: a
   per-station scale would equalise the influence of a station with variable weather and one with
   steady weather, throwing away exactly the information that identifies a shared response.
2. **Whose quartiles.** "Its training-era quartiles" did not say whether the knots come from each
   station or from the pool. **Pooled** — nineteen points do not locate a quartile.
3. **The instrument dummy is not splined.** A two-valued column has no quartiles to put knots at
   and a spline basis on it is rank-deficient. It enters arm E as a single linear column.
4. **The null holds knots and scales fixed across draws.** The shuffle permutes which year a
   covariate row is paired with, so it leaves each station's covariate *marginals* alone, and
   knots and scales are properties of those marginals. Holding them fixed is therefore not a
   shortcut that flatters the observed fit, and it is what makes a thousand pooled refits
   affordable. Per-unit centring *is* recomputed inside each draw, because the shuffled training
   subset genuinely differs — which is what `models.skill.hindcast` does.
5. **A smoke test exposed the observed medians early, and nothing was changed because of it.** A
   crash check with five null draws was run before the registered run, to exercise array shapes
   after Phase 3b's runner had crashed on first contact with its lake. Median skill does not depend
   on the null, so that check displayed every arm's observed autumn median. It is recorded here
   rather than left implicit, and the consequence is binding rather than cosmetic: no covariate,
   threshold, knot count, λ grid or arm was touched afterwards. The significant-unit counts —
   which predictions 1 to 3 are actually graded on — need the null and were not visible.

## 4. Predictions

1. **Arm A reproduces Phase 3a.** Autumn significant at 20 ± 3 of 143 stations, spring at or below
   its bar of 11. This is the calibration and it is not a hypothesis.
2. **Pooling raises the autumn count above Phase 3a's 20.** The mechanism is the 2.7-against-392
   ratio in §1. Graded false, per-station data scarcity was not the binding constraint, and the
   ceiling is the drivers or the response rather than the estimator.
3. **Pooling raises the spring count above its bar of 11.** Spring is the temperature-forced season
   in the phenology literature and it was at the false-positive rate in Phase 3a; this is the
   prediction most likely to fail and the most consequential if it holds.
4. **Wind's marginal contribution in autumn is positive and small** — C − B is above zero at the
   median station but below half of B − A. Written against the evidence in §1: Phase 2a's autumn
   support coefficient was already null, so a *large* autumn gain would be the surprising outcome
   and would need explaining rather than celebrating.
5. **The favourable-night share beats the seasonal mean**: D − C exceeds C − B. If the form of the
   variable matters more than its inclusion, the lesson generalises to every seasonal aggregate in
   this project.
6. **The spline basis does not beat the linear pooled model at the median station.** Linearity is
   not the binding constraint. Graded false, it licenses the boosting escalation in §3.

## 5. Stop conditions

- **Arm A failing its calibration** (autumn outside 20 ± 3, or spring above its bar) → the phase
  publishes as a harness failure and **no arm above A is interpreted**. The published result is
  that this project could not reproduce its own experiment, which would be worth more than any
  skill number.
- **Any arm whose qualifying unit count falls below 100** → that arm publishes as a coverage
  statement, not a skill result.
- **Every arm inside its null** → the published result is a limit finding with `direction="limit"`:
  pooling and the wind were tried, the ceiling is the response model, #57 stays refused, and the
  Phase 3d rehearsal does not re-run.
- No covariate is added, no threshold moved, no λ grid widened, no knot count changed, and no
  season dropped after any skill number in any arm has been seen.
- The test era is touched once, at scoring, in every arm.

## 6. What this cannot establish

- **Whether a forecast is possible.** Only the projectable-only column speaks to that, and even a
  large all-driver gain leaves #57 exactly where Phase 3d left it. A mechanism result is not a
  licence.
- **Why spring behaves as it does.** The ladder measures whether spring timing is predictable, not
  what predicts it. Photoperiod — the standard account of why autumn is plastic and spring is not —
  is excluded here for the reason given in §2 and needs its own design.
- **Anything outside 24–50°N CONUS aerial.** `transfer-fails` measured hold-one-out error at 0.68
  across realms; nothing here transfers to the herds, the seas or the atlases.
- **Whether the 2012 step is instrument or animal.** Phase 1c tested four explanations and all
  four failed. This phase carries the step as a term and measures what the term does; it does not
  resolve it, and a pooled coefficient conditioned on an unexplained step inherits the mystery.
- **Whether a better response *variable* exists.** The ladder varies the estimator, the covariates
  and the basis. It holds the response fixed, so a ceiling found here is a ceiling on predicting
  *this* quantity — the median passage day — and not on predicting movement.

## Results — run 2026-08-19

**Two corrections first, per house rule, and the second one voids the phase's own headline.**

**Correction 1: the null was not reproducible, and measuring twice is what found it.** The first
run's counts could not be reproduced. Autumn arm B came out 47, then 48, then 50 across three
executions of the same seed. The cause: every unit's permutations were drawn from one generator in
list order, and `units()` does not return a stable order — a probe found **142 of 143 autumn
stations in a different position** between two calls inside one process, because the panel's row
order comes from joins that are not order-stable. Observed skill was identical across orders, as it
must be; the *null thresholds* were not. So the number that moved was the bar, not the score, which
is why nothing looked wrong. The fix keys each unit's permutation stream to `crc32(station_id)`
rather than to its position, making a unit's null a property of that unit; `units()` also sorts, so
the printed table is stable. Two runs of the fixed harness are now byte-identical, and
`tests/test_phase3f.py` pins order-independence directly. **Every number below is from the fixed
harness.** The defect moved counts by up to three and moved no median at all.

**Correction 2: the registration contradicted itself, and it cost the calibration.** §3 says arm A
is "Phase 3a's `hindcast` verbatim" and then fixes seed `20260819`. Those cannot both hold, because
the null is seeded. Measured: under Phase 3a's own seed `20260818`, arm A returns spring **11 of
140** — Phase 3a's published number exactly — and under the registered seed it returns **12**. The
median is `−0.0308` under both. One borderline station flips, and it flips across the bar.

So the harness reproduces Phase 3a on every deterministic quantity: spring median `−0.0308` against
3a's `−0.031`, autumn median `+0.0055` against `+0.005`, autumn count 20 of 143 exactly, and the
same two stations dropped for the same reason (KJAN at 9 years, KHDC at 2). What was wrong was the
registration — twice over. It contained the contradiction above, and it built a calibration
criterion on a *seeded count* when a *deterministic median* was sitting right there. **The seed is
not being changed now.** Picking the seed after seeing which one clears the bar is exactly what this
convention exists to prevent, and the fix belongs to the successor.

### The ladder, both seasons, for the record

Seed `20260819`, 1,000 draws per unit, λ grid 0.01 to 1e4 in 13 steps.

| season | arm | scope | units | signif | bar | median skill | λ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| spring | A | all | 140 | 12 | 11 | −0.0308 | per-unit |
| spring | B | all | 140 | 52 | 11 | **+0.0084** | 100 |
| spring | B′ | all | 140 | 55 | 11 | −0.0175 | 316 |
| spring | C | all | 140 | 53 | 11 | −0.0039 | 316 |
| spring | C | projectable | 140 | 52 | 11 | +0.0084 | 100 |
| spring | D | all | 140 | 54 | 11 | +0.0019 | 316 |
| spring | D | projectable | 140 | 52 | 11 | +0.0084 | 100 |
| spring | E | all | 140 | 38 | 11 | **+0.0239** | 0.01 |
| spring | E | projectable | 140 | 47 | 11 | +0.0158 | 0.01 |
| autumn | A | all | 143 | **20** | 12 | +0.0055 | per-unit |
| autumn | B | all | 143 | 49 | 12 | −0.0351 | 31.6 |
| autumn | B′ | all | 143 | 48 | 12 | −0.0357 | 31.6 |
| autumn | C | all | 143 | 49 | 12 | −0.0535 | 31.6 |
| autumn | C | projectable | 143 | 49 | 12 | −0.0351 | 31.6 |
| autumn | D | all | 143 | 47 | 12 | −0.0621 | 31.6 |
| autumn | D | projectable | 143 | 49 | 12 | −0.0351 | 31.6 |
| autumn | E | all | 143 | 27 | 12 | −0.0784 | 0.01 |
| autumn | E | projectable | 143 | 31 | 12 | −0.0623 | 0.0316 |

One internal consistency check passes: arms C and D restricted to projectable drivers reproduce arm
B exactly in both seasons — same count, same median, same λ — which is what the design predicts,
since every driver those arms add is one a forecast cannot supply.

### Grading

**Prediction 1 — GRADED FALSE, and its stop condition fires.** Autumn reproduced at 20 of 143
exactly. Spring came in at 12 of 140 against a bar of 11, one station above, for the seeded reason
in Correction 2. §5's condition is written as "autumn outside 20 ± 3, **or spring above its bar**",
so it fires as registered.

**Predictions 2 to 6 — UNGRADEABLE, by the fired stop condition.** No arm above A is interpreted.
The table above is printed in full because a stop condition is a reason not to draw conclusions, not
a reason to hide measurements.

### The design flaw the run exposed, which outlives the seed

This is the part worth more than the phase's own numbers, and it is reportable because it is a fact
about the instrument rather than an interpretation of an arm.

**The ladder's count comparison was never valid.** A pooled fit on year-shuffled drivers cannot
manufacture per-unit skill the way a 19-row per-station fit can, so its null is far tighter.
Measured as the median per-unit null threshold:

| season | arm A (per-station) | arm B (pooled) |
| --- | --- | --- |
| spring | 0.1746 | 0.0880 |
| autumn | 0.1330 | 0.0730 |

Arm B's units clear a bar roughly **half the height** of arm A's. So arm A's 20 and arm B's 49 are
counts against two different bars, and the jump from 20 to 49 is substantially the bar moving rather
than the model improving — which is confirmed by the deterministic column, where autumn's median
skill *falls* from `+0.0055` to `−0.0351` over the same step.

Predictions 2 and 3 were both written as count comparisons across estimators. They are therefore not
merely ungradeable by the fired stop condition; they are **unanswerable as posed**. That is a flaw in
this registration, recorded rather than repaired in place, and any successor must state its
predictions in the units that are comparable across estimators — the Murphy median — or compare
counts only within one estimator.

### What #57 may take from this

Nothing. #57 stays refused exactly where Phase 3d left it, and this phase did not reopen it: the
attempt did not complete. The projectable-only medians are the only column that could ever have
spoken to a forecast, and they are not interpreted. It would be as wrong to read this as "the
response model is confirmed to be the ceiling" as to read it as a gain — a fired calibration means
the experiment did not report, not that it reported nothing.

Two things are nonetheless *measured* facts that a successor inherits, because they are deterministic
and seed-free:

- Autumn median skill is negative under every pooled arm, and pooling alone takes it from `+0.0055`
  to `−0.0351`. Whatever pooling does at these stations, it does not raise typical-station autumn
  skill.
- The spline arm's λ collapsed to the grid **minimum** in three of the four cases it ran
  (0.01, 0.01, 0.01, 0.0316), meaning leave-one-station-out chose essentially no regularisation for a
  37-column design. That is a diagnostic about the λ rule, not about splines, and it should be
  resolved before arm E is read anywhere.

### What the successor has to fix

1. **One seed, named once**, and a calibration criterion built on a **deterministic** quantity — the
   observed median, which reproduces Phase 3a to three significant figures — rather than on a seeded
   count that a single borderline station can flip.
2. **Predictions in comparable units.** Median skill across estimators; counts only within one.
3. **The λ rule for a wide basis**, given arm E's collapse to the grid floor.
4. Everything else in §§1–3 carries over unchanged, including the reporting split, which did its job:
   the projectable and all-driver columns stayed separate and the projectable ones reproduced arm B
   exactly, so no mechanism gain could have leaked into a forecast claim even if there had been one.
