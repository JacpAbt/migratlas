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
