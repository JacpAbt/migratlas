# Phase 3k — is the marine signal a property of the fish rather than of the sea?

**Status: pre-registered 2026-09-01, before any fit under this design.** Nothing below has been
computed. What *was* looked at is in §1 and it is a great deal: three unregistered diagnostics ran
today and their numbers are quoted there, because a note claiming innocence about them would be
worthless.

Phase 3e's successor, on the two things its own diagnostics found and could not properly test.

---

## Why this note exists

`seas-disagree` published Cochran's Q at 235.7 against a bar of 27.6, and read it as the seas doing
genuinely different things. Two unregistered diagnostics, run after publication, changed what that
sentence can mean:

- **About 45% of the heterogeneity is where the ships went.** Each survey's own mean haul latitude
  per year, with no fish in it, trends from −0.210 to +0.337 °latitude per decade — as wide as the
  fish signal — and correlates with that survey's fish trend at **+0.699**, slope **+0.516**.
  Regressing it out takes Q from 235.7 to **130.9**.
- **The species explains 2.8× what the sea does.** On 1,570 pairs over 297 taxa caught in three or
  more surveys, the noise-corrected coherence is **0.430** grouped by species against **0.156**
  grouped by survey. 0.430 is the highest this project has measured on any axis.

Both were computed after the fact and neither can bear weight. The first says a published finding is
about half survey design; the second says the strongest signal in the marine record has been sitting
inside `marine-null` since July, unexamined, and is a property of the animals. **Each deserves a
design rather than a diagnostic**, and this is it.

---

## 1. What was looked at before this was written

Everything above, plus everything `marine-null`, `seas-disagree`, Phase 3g and Phase 3j published:
the pooled median of −0.011 °lat/decade over 2,240 pairs; Q 235.7 and the warming null
`+0.039 ± 0.179`; oxygen carried by one sea of sixteen with no dose-response among the next four;
and Phase 3j's three environmental cluster axes, none of which beat its null.

**This note cannot claim to be blind and does not.** The diagnostics are the reason it exists, so its
predictions are written knowing their direction, and §4 says which of them are therefore checks rather
than discoveries. That distinction is the whole value of registering this at all.

**What has not been computed:** any fit with sampling drift as a covariate; any species-level
coherence under a pre-registered floor; any species-level estimate that admits survey dependence.

---

## 2. Estimand and units, with the known problems first

**Two estimands, one per diagnostic.**

**A. The heterogeneity, with the drift in the design.** Per survey, the cross-taxa median latitude
trend as `seas-disagree` computes it, and the survey's own mean-haul-latitude trend as a covariate in
the cross-unit fit — not regressed out afterwards. The question is what between-survey variation
survives once the stations' own movement is a term rather than a correction.

**B. The species, with a floor fixed in advance.** For taxa caught in at least **five** surveys, the
coherence of their latitude trends grouped by species against grouped by survey, both through
`phase1m._icc`. Five rather than the diagnostic's three, chosen now: three surveys is the minimum at
which the question is askable at all and five is where a species mean stops being two numbers and an
outlier. The count of taxa this admits is a graded prediction.

### Known problems, before any fit

- **The drift covariate is measured on the same rows as the response.** A survey's haul latitudes and
  its fish centroids come from one table, so this is not an independent instrument — it is a
  decomposition of one quantity into where the ship was and what it caught there. That is legitimate
  and it is not causal identification, and §6 says so.
- **A species caught in five surveys is not a random species.** It is widespread, probably abundant,
  probably tolerant. So estimand B describes the widespread fish and says nothing about the others,
  which is the same selection `marine-null`'s fifteen-year floor already imposes and is worth stating
  twice rather than once.
- **The two estimands can disagree and that is informative.** If the species share survives the drift
  correction and the survey share does not, the marine story is about animals. If both fall, the
  spread was largely bookkeeping and the ledger's marine claims all shrink together.
- **Survey dependence is unadmitted in every marine interval this project publishes.** Phase 3j
  measured the price at 3.0–3.1×, and the residual Q's margin on its weights is only **2.18×**. So
  every interval here gets a **survey-clustered bootstrap** and the naive one beside it, as Phase 3j
  required.
- **Eighteen surveys is eighteen points**, and ADR 0016 binds on every cross-unit coefficient.
- **Nothing causal, in either estimand.**

---

## 3. The design, fixed before any fit

- **Calibration.** Reproducing `seas-disagree`'s Q of 235.7 and the warming slope
  `+0.039 ± 0.179` on the same units, by calling `phase3e` itself. If either misses, nothing below is
  read.
- **A**: `latitude_trend ~ 1 + sampling_drift + warming_trend`, weights and the Q machinery Phase 3b's,
  unchanged. Reported with the residual Q and its own weight margin.
- **B**: `_icc` by species and by survey on the ≥5-survey panel, each with a survey-clustered
  interval.
- **ADR 0016** on every coefficient and on the residual Q, as Phase 3e now computes it.
- **Seed** `SEED = 1`.

---

## 3a. Amendments, written while implementing and before the registered run

Four things §2 and §3 under-specified. All four were settled before any fit — no drift covariate had
been joined to any unit and no coherence had been computed on any five-survey panel when these were
written — and each would otherwise have been a silent choice inside the code.

**A. The drift covariate is trended over the unit's own clipped segment, as distinct haul positions.**
§2 says "the survey's own mean-haul-latitude trend". The 2026-09-01 diagnostic trended it over the
survey's whole consistent record, as a mean over catch rows. The response it sits beside is measured
over the segment Phase 3e clipped to the satellite era, so the covariate is trended over the same
years — Phase 3j's amendment A, for Phase 3j's reason — and over the distinct positions hauled in
each year rather than over catch rows, because a mean over rows weights a haul by how many taxa it
caught, and this is a question about where the ship went. Prediction 2 was written against the
diagnostic's +0.699 and is a weaker check for this change, which is stated rather than hidden.

**B. The residual Q's bar has `units − 3` degrees of freedom.** The plain Q loses one for the pooled
mean; the residual loses one per fitted parameter — intercept, drift, warming. "Still clears its
bar" in prediction 3 means clears that bar, and ADR 0016's extension to Q recomputes both statistic
and bar with each unit dropped, as `phase3b.regression` does for the plain Q. The residual's weight
margin is `sqrt(Q / bar)` on the same arithmetic as `Regression.q_robustness`.

**C. "Falls below the 0.10 floor under the clustered interval" means the lower 2.5th percentile of the
survey-clustered bootstrap of the species coherence is below 0.10.** Prediction 5's factor of two is
graded on the point estimates, with both intervals printed beside it. 1,000 draws per interval,
seeded by `crc32` of the quantity's name mixed with `SEED = 1`, as Phase 3j seeds its nulls.

**D. Estimand B's panel is `marine-null`'s own pooled table**, from `phase1b.analyse` on the same
cells, keyed on `taxon_key` rather than on the label — 95 keys carry two or more verbatim names
across sources, and a species split by spelling would read as two species that disagree — and
filtered to taxa in five or more surveys. Its pooled median is printed beside the registered
calibration as a second check that the table is the published one; it grades nothing.

---

## 4. Predictions

Marked as check or discovery, because three of these are things the diagnostics already indicated and
pretending otherwise would be dishonest.

1. **Calibration reproduces Q 235.7 and the warming null.** *Check.*
2. **The sampling-drift coefficient is positive and its interval excludes zero.** *Check* — the
   diagnostic put the correlation at +0.699. A failure here means the covariate behaves differently
   inside a weighted fit than in a bare regression, which would be worth knowing and would stop the
   phase.
3. **The residual Q still clears its bar, and is below 160.** *Check on the direction, discovery on
   the size.* The diagnostic's post-hoc figure was 130.9; a properly-fitted residual could be larger
   or smaller and 160 is set as a bound rather than a target.
4. **The warming slope remains null with the drift in the model.** *Discovery.* If warming becomes
   distinguishable once station drift is controlled, then the drift was masking a real thermal
   response and Phase 3e's central null is wrong — which is the outcome that would change the most in
   this project.
5. **Species coherence exceeds survey coherence by at least a factor of two on the ≥5-survey panel.**
   *Check on direction, discovery on whether it survives the stricter floor and a clustered
   interval.*
6. **At least 120 taxa clear the five-survey floor.** *Discovery.* Below that, estimand B publishes as
   a coverage statement.

---

## 5. Stop conditions

- **Calibration misses**, or **prediction 2 fails** → nothing above is interpreted.
- **Prediction 4 fails — warming becomes distinguishable.** Then Phase 3e's null was confounded by
  station drift, `seas-disagree`'s second half is withdrawn, and that becomes the finding. It is the
  most consequential outcome here and it is pre-committed rather than left to interpretation.
- **The residual Q stops clearing its bar.** Then the between-survey heterogeneity was survey design,
  `seas-disagree` is withdrawn entirely, and the marine ledger keeps only `marine-null` and whatever
  estimand B supports.
- **Fewer than 120 taxa clear the floor** → estimand B is a coverage statement and prediction 5 is
  graded false rather than dropped.
- **Species coherence falls below the 0.10 floor under the clustered interval** → the diagnostic's
  0.430 was survey dependence wearing a species' clothes, and that is published as the correction.
- No floor, covariate, weight or seed is revisited after any number is seen.

---

## 6. What this cannot establish

- **Not causation, in either estimand.** The drift covariate is measured on the same rows as the
  response; this is a decomposition, not an instrument.
- **Not why a species moves the way it does.** Estimand B would say a fish's tendency travels with it
  between seas. What sets the tendency — thermal tolerance, depth preference, larval dispersal, body
  size, fishing — is untouched, and Phase 3j has already ruled out the three environmental axes this
  lake can build.
- **Not the ocean.** Northern shelf trawl surveys, bottom-dwelling fish, where trawls can go.
- **Not the non-widespread fish.** A five-survey floor selects for widespread species by construction.
- **Not a licence to publish a per-species marine number.** Phase 1l's precision argument binds here
  until somebody measures the marine equivalent of its 1.69, which nobody has.

---

# Results — run 2026-09-02

`make report-phase3k`. Two consecutive runs are identical on every registered quantity, checked
before anything here was written down.

**Calibration — PASS.** Q **235.7** and warming **+0.039 ± 0.179** reproduced exactly, by calling
`phase3e.units_3e` and `phase3b.regression` themselves.

## Estimand A — the drift in the design

| quantity | value |
| --- | --- |
| sampling drift coefficient | **+0.822 ± 0.293** °lat of reported movement per °lat of station movement |
| warming coefficient | **−0.117 ± 0.121** °lat per °C |
| residual Q | **77.3** against a bar of 25.0 (15 degrees of freedom) |
| residual Q survives dropping any one unit | yes |
| residual weight margin | **1.76×** |
| ADR 0016, drift | survives; furthest is GMEX-Fall at +0.740 ± 0.270 |
| ADR 0016, warming | a null; furthest is SCS-SUMMER at −0.162 ± 0.121, **which clears zero** |

## Estimand B — the species at a five-survey floor

| quantity | value |
| --- | --- |
| pairs / taxa / surveys | 1,148 / **171** / 23 |
| panel median before the filter | −0.0110 (`marine-null`'s own) |
| coherence by species | **0.326** corrected (0.222 raw); naive [0.400, 0.600]; survey-clustered [0.366, 0.653] |
| coherence by survey | **0.178** corrected (0.121 raw); naive [0.160, 0.319]; survey-clustered [0.090, 0.292] |
| species over survey | **1.83×** |

## The answer

Two answers, one per estimand, and the second is not the one the diagnostic promised.

**A. With the ships' own movement in the design, the seas still differ, and the warming still does
not sort them — by four thousandths.** The drift coefficient is +0.82 ± 0.29: a survey whose
stations moved a degree north reports its fish moving about eight tenths of a degree north. That is
nearly one for one, larger than the diagnostic's +0.52, and it means most of what an effort-weighted
centroid reports for these surveys is where the ship went. What is left is still heterogeneous —
residual Q 77.3 against 25.0, about a third of the published 235.7 — and it survives losing any one
unit. Its weight margin is 1.76×, inside the 2.4× to 4.5× range of dependence corrections this
project has measured on comparable intervals, so the residual heterogeneity clears its bar and not
comfortably, and the finding now says so. Warming stays null at −0.117 ± 0.121, but its sign has
turned negative and the interval's upper end sits at +0.004. Dropping SCS-SUMMER takes it to
−0.162 ± 0.121, which clears zero: one unit from a *negative* warming slope, the faster-warming seas'
fish moving south, the opposite of the literature's expectation. ADR 0016 calls a null unaffected and
it is graded as one; the honest sentence is that the null is fragile in a direction nobody
registered.

**B. The species explains the spread no better than the sea does, once the number of groups is
counted.** On the registered instrument: species 0.326, survey 0.178, ratio 1.83× against a
registered 2× — prediction 5 fails. Then two things about the instrument, both **UNREGISTERED**, run
after the table above was seen, and on Phase 3g's precedent they decide what the phase may claim:

1. **The bootstrap intervals sit above their own point estimates.** Both intervals on the species
   coherence — [0.400, 0.600] and [0.366, 0.653] — exclude the value they are intervals for.
   Resampling with replacement duplicates rows; a duplicated row inside a group adds no within-group
   variance; the between-group share rises. The percentile interval is biased upward, and the
   registered stop condition — clustered lower bound below 0.10 — was built on an instrument that
   could not fall. Read the other way, as a basic interval `2θ̂ − q`, the clustered bound is
   [−0.001, 0.286] and touches zero. Neither reading is trusted. The stop condition is graded on the
   registered reading as written — it does not fire — and this paragraph is why that grade is worth
   little.

2. **A between-group share has a chance level that grows with the number of groups.** `_icc`'s share
   is a one-way unadjusted R², whose null expectation is near `(k − 1) / n`. With species labels
   shuffled within each survey, 171 species over 1,148 pairs score **0.203** (95th percentile 0.238,
   closed form 0.218). With survey labels shuffled within each species, 23 surveys score **0.040**
   (95th 0.083, closed form 0.028). Both observed values beat their 95th percentile, so both groupings
   carry real structure. Over chance the species carries **+0.123** and the survey **+0.138**. The 2.8×
   of the diagnostic and the 1.83× of the registered estimand were mostly 171 groups against 23. On
   one scale they are about equal, and the sea is a hair ahead — inside the permutation spread of
   either, so neither leads.

That reaches back. The *0.430 against 0.156* published in two findings' prose on 2026-09-01 compared
297 groups against 23 and is withdrawn from both in this commit. And the instrument reaches further
than this phase: Phase 1m's floor of 0.10 was set with ten groups over 180 to 550 species, where the
chance level is about 0.02 to 0.05; Phase 1o's family groupings of 14 to 30 groups over 127 to 459
species have chance levels of roughly 0.06 to 0.10 raw, so the floor sits *at chance* for the two
Swedish family panels, and "the first axis to clear the floor twice" needs its own chance level
before it is read again. Recorded here as owed (#78) rather than regraded here, because regrading
another phase's predictions in this note would be authorship.

## The predictions, graded

**1 — TRUE** (check). Calibration reproduced both numbers exactly.

**2 — TRUE** (check). +0.822 ± 0.293, positive and clear of zero, with the drift trended over the
segment and over haul positions per amendment A.

**3 — TRUE** (check on direction, discovery on size). The residual Q clears 25.0 at 77.3 and is
below the 160 bound — well below the diagnostic's post-hoc 130.9, because the diagnostic regressed
the drift out unweighted over the whole record and this fits it weighted over the segment.

**4 — TRUE** (discovery). −0.117 ± 0.121 covers zero, by 0.004, and is one unit from clearing it in
the negative direction. Phase 3e's central null was not confounded by station drift; it is less
comfortable than it was.

**5 — FALSE.** 1.83× against a registered 2×. And, per the diagnostics above, the ratio itself was
the wrong quantity.

**6 — TRUE.** 171 taxa clear the five-survey floor against a registered 120.

Five of six held. The one that failed is the one the spine leaned on.

## The stop conditions, and what they do

- Calibration and prediction 2 held → both estimands are read.
- Prediction 4 held → `seas-disagree`'s second half stands, described as fragile.
- The residual Q clears → `seas-disagree` is **not withdrawn**. Its prose changes in this commit: the
  drift is a fitted coefficient rather than a post-hoc share, the heterogeneity is about a third of
  what it published, its margin is 1.76×, and the warming null's fragility is stated.
- The species coherence's clustered lower bound is 0.366 ≥ 0.10 → the registered condition does not
  fire. The two unregistered diagnostics decide what is claimed anyway: **no species-level marine
  claim is published**, the "species explains 2.8×" sentences are withdrawn from `seas-disagree` and
  `marine-null`, and what replaces them in `marine-null`'s caveat is the comparable statement — over
  chance, the animal and the sea explain about the same, computed from this phase rather than typed.

## What this does to ADR 0018

The spine's third leg — that what organises where-shifts is the animal — rested on the 0.430
diagnostic and on Phase 1o's family result. The first is withdrawn here and the second is exposed to
the same instrument. The leg is not dead: both groupings beat chance, the species carries +0.12 of
coherence it did not have to, and a per-species *response* to a driver was never tested by any of
this — ADR 0018 decision 2 is about responses and every quantity here is a trend. But it is no longer
supported by anything in the marine record, and the ADR carries a dated amendment saying so.

## What the successor has to fix

1. **Chance-level every coherence this project has published** — Phase 1m, 1o, 3j and the 3e
   diagnostic — and re-read the 0.10 floor as an excess over each grouping's own shuffled-label
   baseline. #78.
2. **An interval on a variance share needs a construction that does not duplicate rows**: a
   jackknife over the clustering unit, or a permutation test in place of an interval.
3. The warming slope's fragility is stated in the finding and is not a registration on its own.

## What this does not establish

- **Not causation.** The drift coefficient says how much of the reported movement co-moves with the
  stations; it does not say the stations caused it, and a fleet that follows its fish would produce
  the same coefficient.
- **Not the ocean, and not the non-widespread fish.** A five-survey floor selects widespread species
  by construction, as §2 said before the run.
- **Not that species have no consistent tendency.** +0.12 over chance, beating the 95th percentile, is
  a real signal and a small one.
- **Not a per-species response.** Every quantity here is a trend in a centroid.
