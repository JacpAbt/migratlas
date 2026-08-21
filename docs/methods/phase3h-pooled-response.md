# Phase 3h — was the thing being predicted the problem all along?

**Status, 2026-08-20, written before any fit.** No skill number in this project has ever been
computed against a *regional* passage date. Phase 3a, the Phase 3d rehearsal and Phase 3f all
predicted one radar station's date, 143 or 140 units at a time. Whether pooling the response changes
the answer has not been looked at, because until yesterday nobody knew there was a reason to look.

## Why this note exists

`reports/response_floor.py`, run 2026-08-20, measured something none of the three earlier attempts
had asked for: how much of a station's year-to-year passage date is signal at all.

| | autumn | spring |
| --- | --- | --- |
| median per-station interannual sd | 4.37 d | 3.85 d |
| upper bound on one station's measurement error | 3.54 d | 2.87 d |
| **implied per-station explainable share** | **34%** | **44%** |
| median split-half reliability of a *regional* series | **65%** | **66%** |

The per-station figure is a *lower* bound on the ceiling, because genuine spatial variation between
neighbours inflates the error term. Even so, it says the earlier attempts were fitting seven
covariates to a target of which roughly two-thirds was noise. And the regional figure says the noise
is largely independent between stations while the signal is largely shared — so averaging stations
into a flyway-and-band region roughly doubles the share a driver could reach.

That is a claim about the *target*, and every previous attempt varied the *predictor*. Phase 3f
climbed five rungs of estimator and basis complexity and its stop condition fired on rung one. This
phase changes the one thing the ladder held fixed.

## 1. What was looked at before this was written

Stated because it bears on how much this test can be trusted, and because the honest version is
uncomfortable.

**Fully seen, and it cannot be unseen.** Phase 3f's complete ladder table — 18 rows, both seasons,
five arms, every median and count — is in `phase3f-response.md` and I have read it. Its stop
condition fired, so none of it was interpreted, but "not interpreted" is not "not seen". Any claim
that this phase's design was chosen blind would be false.

**Why the test is nonetheless informative.** Every number in that table is a number about a
*per-station* response. The regional pooled series has never been scored by any harness in this
repository, so no observed skill figure I have seen is a figure about this phase's response
variable. What I have seen constrains the *design* — it is why the estimator ladder is not climbed
again, and why calibration is on a deterministic median — and not the answer.

**Seen, and load-bearing.** Phase 3a's published medians (autumn `+0.005`, spring `−0.031`) and
counts (20 of 143, 11 of 140). Phase 3f's two corrections and the four fixes `TASKS.md` #62 records.
The floor diagnostic in the table above, including its own estimator null.

**Not looked at.** Any skill number for a regional response, in either season, under any arm. Any
per-region null. Whether wind support helps a skill score at any spatial scale — Phase 2a fitted it
as a co-predictor and found `−0.243 ± 0.385`, a null coefficient, but no *skill* harness in this
project has ever included it, and 3f's arms that did were never interpreted.

## 2. Estimand and units, with their known problems first

**The unit is a region-season**: one of `phase1.FLYWAYS` crossed with `phase1.LATITUDE_BANDS`,
eleven of which carry at least four qualifying stations in each season. Not a partition invented
here — the crossing predates this note by months and is used by the descriptive findings, which is
the only reason a result about it is not a result about a boundary somebody tuned.

**The response is the unweighted mean across the region's member stations, per year**, of exactly
the `q50_doy` Phase 3a used, from the same `passage_quantiles` call with the same filters.
Unweighted rather than area- or traffic-weighted, because a weighting scheme is a free parameter and
this phase already spends its novelty on the pooling itself.

Known problems, before any result:

- **Eleven units is a small family.** The binomial chance bar at eleven units and a 5% false
  positive rate is 2, so a count must reach 3 to clear it, and the sampling error on a *share* out
  of eleven is enormous. This is why the primary quantity here is a deterministic median and the
  count is secondary. `TASKS.md` #62 required exactly this and gave the reason: 3f's pooled null was
  half the width of its per-station null, which made its count-based predictions unanswerable rather
  than merely unfavourable.
- **A regional answer is a coarser product than a station answer.** Skill on a regional mean does
  not imply skill at any station in it, and a forecast built on this would forecast regions. That is
  a real reduction in what the project could claim to offer, and it is the price of predicting
  something measurable.
- **The stations are not independent and the regions barely are.** Adjacent regions share weather
  systems. The per-region null handles within-region dependence by construction — it shuffles years,
  so any spatial structure is preserved under the null — but it does not make the eleven counts
  independent of each other.
- **Missing years differ between member stations.** A region-year is the mean of whichever stations
  reported, so the response's own measurement error varies across years with the station count. Not
  corrected, because correcting it needs a weighting scheme; recorded, and the per-region station
  count is printed.
- **The covariates are pooled the same way as the response.** A region's temperature is the mean of
  its member stations' temperature. This is the scale-matched choice, and it is also the one that
  could manufacture skill if a driver's *spatial* mean were smoother, and therefore easier to fit,
  than the response's. Arm A exists to catch that.

## 3. The design, fixed before any fit

### Three arms, and the ladder climbs one step only

| arm | response | covariates | what its difference from the arm below means |
| --- | --- | --- | --- |
| A | **per station**, 143/140 units | Phase 3a's seven | nothing — it is the calibration rung, and must reproduce Phase 3a |
| B | **per region**, 11 units | Phase 3a's seven | the target change, isolated: same drivers, same estimator, different thing predicted |
| C | per region, 11 units | seven **plus** wind support and favourable share | the driver change, isolated: the first skill number in this project's history to see wind |

No estimator arm. Phase 3f spent five rungs on estimator and basis complexity and its result was
uninterpretable for an unrelated reason; repeating that while also changing the response would
produce a difference nobody could attribute. Partial pooling, splines and gradient boosting stay
where #62 left them.

### The estimator, stated exactly

`models.skill.hindcast(x, y, seed=...)` **verbatim**, once per unit — the same function Phase 3a
called. Ridge, leave-one-year-out lambda selected inside the training years only, training-only
standardisation, era split at 70/30 with a five-test-year floor, Murphy score
`1 − MSE_model / MSE_climatology` on the test era.

Nothing about the estimator changes. That is the point: with 21 training years per region instead of
roughly 14 per station, and a narrow seven-column basis, the lambda pathology #62 records for 3f's
arm E cannot arise, and no new lambda rule needs registering.

### The null, and the significance rule

Per unit, 1,000 year-shuffle permutations, keyed by `crc32` of the unit's name so a unit's null is a
property of that unit and not of its position in a list — Phase 3f's correction 1, inherited rather
than rediscovered. A unit is significant when its observed skill exceeds its own 95th null
percentile. The family bar is `phase3a.binomial_bar`, which is 12 at 143 units, 11 at 140, and **2
at 11** — so three regions clear it.

### Calibration, on a deterministic quantity

Arm A must reproduce Phase 3a's **medians**: autumn `+0.0055`, spring `−0.0308`, to three
significant figures. Medians, not counts, because Phase 3f's calibration used a seeded count and one
station crossed the bar between two legitimate seeds, which fired a stop condition over a
coincidence. A median of an observed skill distribution does not depend on the seed at all.

### The reporting split, carried over unchanged

Arm C reports twice: **projectable drivers only** (Phase 3a's seven, which a climate model can
supply) and **all drivers** (plus wind, which no seasonal forecast supplies skilfully). Skill that
appears only in the all-drivers column licenses a *mechanism* claim and not a forecast. This is the
one part of Phase 3f's design that worked exactly as intended, including its internal consistency
check, and it is reused verbatim.

### Seed

`20260820`, named once, here, and not changed afterwards for any reason.

## 4. Predictions

1. **Calibration.** Arm A returns median skill `+0.0055` autumn and `−0.0308` spring, to three
   significant figures, on 143 and 140 units.
2. **The target change is large and positive.** Arm B's median skill exceeds arm A's by at least
   `+0.05` in **both** seasons. The floor measurement says the pooled target holds roughly twice the
   explainable variance, so drivers carrying any real signal should score visibly better against it.
   This is the falsifiable heart of the phase.
3. **At least three of eleven regions clear their own null in arm B**, in at least one season —
   the binomial bar at eleven units.
4. **Wind adds something, or it does not, and either is publishable.** Arm C's all-drivers median
   exceeds arm B's in at least one season. Registered weakly on purpose: Phase 2a's per-station wind
   coefficient was `−0.243 ± 0.385`, a null, so the prior is genuinely near zero and this prediction
   is as likely to fail as to hold.
5. **Internal consistency.** Arm C restricted to projectable columns reproduces arm B exactly —
   same median, same count, same per-unit lambda — because every column it adds is one a forecast
   cannot supply. If this fails, the harness has a bug and nothing else in the table is trustworthy.

## 5. Stop conditions

- **Arm A off its calibration.** If prediction 1 fails, the harness does not reproduce the run it
  claims to extend and **nothing above arm A is interpreted**. The table is still printed in full,
  as 3f's was: a stop condition is a reason not to draw conclusions, not a reason to hide
  measurements.
- **Prediction 5 fails.** Same treatment, for the same reason — it is a bug detector, not a result.
- **Arm B does not beat arm A in either season.** Then the noise diagnosis is **wrong**: the target
  was not what was limiting these models, and two-thirds of a station's wobble being unexplainable
  did not stop a driver from explaining the third that was. That publishes as a `direction="limit"`
  finding saying so, and the next attempt goes back to drivers and mechanism with the pooling idea
  closed. Pre-committed here so that outcome cannot later be narrated as a partial success.
- **Arm B beats arm A but stays under its binomial bar.** Then the ceiling moved and the drivers
  still are not good enough. That licenses the upstream-driver and pathway work, and licenses no
  forecast.

## 6. What this cannot establish

- **Nothing causal.** Every arm is a fit of covariates to timing. A region whose passage date tracks
  its temperature has told us the two move together at regional scale, which is what Phase 2a
  already said, and no arm here separates a driver from a correlate of a driver.
- **Nothing about a station.** Skill on a regional mean is skill on a regional mean. If this phase
  succeeds, the honest product is a regional response and the site must say so.
- **No forecast.** A licence for Forecast A needs projectable drivers, hindcast skill *and* the
  novelty mask. This phase can supply at most the second, and only for regions.
- **Not the true ceiling.** The floor diagnostic's own estimator over-reads: given a constructed
  true reliability of 0.75 it returned 0.79. So 65% is an over-read of unknown size, the real
  regional ceiling is somewhat lower, and a skill number close to it should be read as suspicious
  rather than as triumphant.
- **Nothing about any realm but the aerial one.** This is CONUS radar, one realm, one taxon group,
  one continent, and it is the fourth pass over that same archive.

## Results — run 2026-08-20

Seed `20260820`, 1,000 year-shuffle draws per unit keyed by `crc32` of the unit's name. **Two
consecutive runs are byte-identical**, checked before anything here was written down, because Phase
3f's null was irreproducible and measuring twice is the only thing that found it.

### Calibration

| season | arm A median | registered | verdict |
| --- | --- | --- | --- |
| autumn | `+0.0055` | `+0.0055` | reproduces |
| spring | `−0.0308` | `−0.0308` | reproduces |

Arm A's *count* is 21 of 143 in autumn where Phase 3a published 20, because §3 registered per-unit
`crc32` null keying and Phase 3a used one shared seed. One borderline station sits on the other side
of its bar under the new stream. **This is exactly the discrepancy that fired Phase 3f's stop
condition**, and it is why §3 calibrated on the median instead: the deterministic quantity matched to
four decimal places in both seasons while the seeded one moved by one station. The registration's own
correction worked.

### The ladder

| season | arm | scope | units | signif | bar | median skill |
| --- | --- | --- | --- | --- | --- | --- |
| autumn | A | all | 143 | 21 | 12 | `+0.0055` |
| autumn | B | all | 11 | 3 | 2 | **`+0.0649`** |
| autumn | C | all | 11 | 3 | 2 | `+0.0132` |
| autumn | C | projectable | 11 | 3 | 2 | `+0.0649` |
| spring | A | all | 140 | 12 | 11 | `−0.0308` |
| spring | B | all | 11 | 3 | 2 | **`+0.0114`** |
| spring | C | all | 11 | 4 | 2 | `−0.0168` |
| spring | C | projectable | 11 | 3 | 2 | `+0.0114` |

Arm B minus arm A: **`+0.0595` autumn, `+0.0423` spring**.

### Per region, arm B

| region | autumn skill | its null 95th | spring skill | its null 95th |
| --- | --- | --- | --- | --- |
| central 24-32N | `−0.0065` | `+0.0908` | **`+0.2149`** | `+0.1666` |
| central 32-37N | **`+0.5338`** | `+0.2288` | `+0.1809` | `+0.2951` |
| central 37-42N | `−0.0471` | `+0.2034` | `−0.2184` | `+0.2639` |
| central 42-50N | **`+0.1302`** | `+0.0794` | `+0.1022` | `+0.1656` |
| eastern 24-32N | `−0.0601` | `+0.2457` | `−0.1126` | `+0.2013` |
| eastern 32-37N | **`+0.1220`** | `+0.1070` | `+0.0114` | `+0.2099` |
| eastern 37-42N | `+0.2045` | `+0.2265` | `−1.6270` | `+0.2139` |
| eastern 42-50N | `−0.3852` | `+0.2506` | `−1.2177` | `+0.2347` |
| western 32-37N | `+0.0649` | `+0.0746` | **`+0.0978`** | `+0.0889` |
| western 37-42N | `+0.0737` | `+0.2458` | **`+0.5813`** | `+0.2567` |
| western 42-50N | `−1.1436` | `+0.2258` | `−0.0157` | `+0.1142` |

Bold clears its own null. Every region has 21 training and 10 test years.

`western 24-32N` is absent in both seasons: two stations, under the floor of four. Five stations are
absent from spring and two from autumn for the era split's own reason, the same ones Phase 3a and 3f
dropped.

### Grading

**Prediction 1 — TRUE.** Both medians reproduce to four decimal places on 143 and 140 units.

**Prediction 2 — FALSE.** It was registered as "at least `+0.05` in **both** seasons". Autumn
returned `+0.0595` and cleared it; spring returned `+0.0423` and did not. The direction is right in
both seasons and the threshold held in one, which is a partial result and is graded as a failure
because that is what the registration said.

**Prediction 3 — TRUE.** Three of eleven regions clear their own null in arm B, against a binomial
bar of two, and it happens in **both** seasons rather than the one the prediction asked for.

**Prediction 4 — FALSE, and informatively so.** Arm C's all-drivers median is *worse* than arm B's in
both seasons — `+0.0132` against `+0.0649` in autumn, `−0.0168` against `+0.0114` in spring. Adding
two wind columns to twenty-one training rows costs more in variance than the wind carries in signal.
This is the fourth independent look at wind in this project and the third to find nothing: Phase 2a's
per-station coefficient was `−0.243 ± 0.385`, a null; 3f's wind arms were never interpretable; and
now the first skill harness ever to see wind is made worse by it. Spring's *count* rose to 4 while
its median fell, so wind helps a minority of regions and hurts more of them.

**Prediction 5 — TRUE, exactly.** Arm C restricted to projectable columns reproduces arm B in both
seasons: same median to four decimals, same count. The harness is not confusing its scopes.

### Stop conditions: none fired

- Arm A calibrated, so arms B and C are interpretable.
- Prediction 5 held, so the bug detector is quiet.
- **Arm B beat arm A in both seasons**, so the condition that would have refuted the noise diagnosis
  did not fire. The diagnosis survives: part of what was limiting these models was the target.
- **Arm B cleared its binomial bar in both seasons**, so the "ceiling moved but the drivers are still
  not good enough" condition did not fire either.

### What this establishes, stated no more strongly than it holds

**Predicting a region is better than predicting a station, and the size of the improvement is what
the floor diagnostic predicted.** The autumn median moved from `+0.0055` to `+0.0649`, an order of
magnitude, with no change of driver, estimator, era split, null or filter. The only thing that
changed was what was being predicted. That is the cleanest attribution this project has managed on
the aerial question, and it is the first positive median it has ever recorded there.

**One coherence check nobody registered, and it lands.** `central 32-37N` scores `+0.534` in autumn —
53% of its test-era variance beaten out of climatology. The floor diagnostic, run the same day on the
same panel and looking at nothing but the response, put the pooled regional ceiling at 65%. The best
region lands just under the roof an independent measurement drew, which is what should happen if both
numbers describe the same underlying quantity. Suggestive, not proof: an out-of-sample Murphy score
and a split-half reliability are not the same quantity, and one landing under the other is a
consistency check rather than a validation.

### The three things that keep this modest

**Eight of eleven regions still have no skill, and the dispersion is enormous.** Autumn runs from
`−1.14` to `+0.53`, spring from `−1.63` to `+0.58`. A median of `+0.065` over eleven noisy units is
not a model that works; it is a model that has stopped being uniformly useless.

**The skilful regions do not agree between seasons — not one overlaps.** Autumn's three are central
32-37N, central 42-50N and eastern 32-37N; spring's three are central 24-32N, western 32-37N and
western 37-42N. Two readings, and eleven units cannot separate them. Either autumn and spring are
genuinely different phenomena with different predictable regions — which is this project's own
established asymmetry, so it is not an excuse invented here — or a count of three at a 5% bar is
partly luck and the non-overlap is what luck looks like. Distinguishing them needs more units, which
means either more regions from a finer partition (and then the partition is tuned, which is the thing
§2 refused) or another radar network.

**Nothing here is causal and nothing here is a forecast.** Arm B is seven weather and index columns
fitted to a regional date. A licence for Forecast A needs projectable drivers, hindcast skill *and*
the novelty mask; this supplies the second, for three regions in each season, at a regional scale the
site would have to say out loud.

### What the successor should take

1. **The response variable question is not closed, it is opened.** Pooling to eleven flyway-and-band
   regions was the coarsest available move and it paid. The measurement that licensed it also says
   the per-station ceiling is 34% and the pooled one is 65%; nothing was tried in between. A
   response at an intermediate scale — neighbour clusters, or a spatially smoothed station series —
   is the obvious next question and it is now a question about the response rather than the drivers.
2. **Wind is finished as a timing covariate at this scale.** Four looks, no signal, and the last one
   actively harmful. Anything further on wind needs a different response (nightly, not seasonal) and
   that is the nowcast this project has twice refused for good reasons.
3. **Prediction 2's failure locates the next driver work in spring.** Autumn cleared its threshold
   and spring did not, on the same estimator and the same drivers. Spring is where the drivers are
   missing, and the standing candidates — per-station green-up, upstream conditions along the
   flyway, degree-days rather than monthly means — are all *spring* mechanisms.
4. **Do not raise the estimator until the response stops paying.** #62's partial pooling, splines and
   gradient boosting are still queued, and this run is evidence that the cheaper axis was not
   exhausted.
