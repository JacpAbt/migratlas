# Phase 2h — is a marine where-shift a range shift, or a cut through a season?

**Status: pre-registered 2026-09-08, before any seasonal contrast has been computed anywhere in
this repository.** No species' centroid has ever been compared between two seasons of the same
region; no species' decadal trend has ever been estimated twice in the same place. What *was*
looked at is in §1, and all of it is published. The dataset audit that fixed this note's design ran
before it was written and is in ADR 0019; it establishes that no fetch is required.

#85, and the first of the three tests ADR 0019 registers. The owner's observation on 2026-09-08:
a migration is movement and stationary time, two states with different cues, and this project has
been measuring one instant and naming it the whole. A bottom-trawl survey sails in a fixed season.
If a fish moves within its year, a survey samples the same population at the same phase every time,
and a change in *when* the fish arrives is indistinguishable from a change in *where* it lives.

---

**Which leg of the spine this bears on.** Claim 2's marine leg, directly, and Phase 2e's conclusion
that where-shifts are not the population's. Both rest on per-species latitude trends from
`SURVEY_INDEX` rows. If those trends depend on which season measured them, the marine leg gains a
limit it does not have. If they do not, the leg is stronger than it was, and that null is published
beside the change.

---

## 1. What was looked at before this was written

- **Phase 1b** computed the per-species latitude and depth trend for every survey unit on its own
  consistent footprint: pooled median −0.011 ± 0.019 °lat/decade over 2,240 species-survey pairs,
  a permutation null of [−0.009, +0.009], and a stable result across 60/80/95% footprint
  thresholds. Its headline was the **disagreement between survey units**, which reaches opposite
  signs: IE-IGFS −0.217, BITS-1 −0.183, GMEX-Fall −0.119, NEUS-Spring +0.101, WCANN +0.126,
  GSL-N +0.154, SWC-IBTS-4 +0.258 °lat/decade.
- **Phase 1i** measured thermal tracking in the marine realm against each survey's own warming.
- **Phase 2e** found that the *size* of a species' where-shift does not follow the size of its
  change in numbers, and that the registered rarity control is four to five times larger than the
  abundance effect.
- **Phase 3k** measured how much of the marine where-shift travels with the ships: a degree of
  survey movement carries +0.82 ± 0.29 degrees of reported fish movement.
- **`marine-null`** publishes the pooled null with the between-survey disagreement as its caveat.

**Not looked at, anywhere:** any comparison between two seasons of the same region. This is not a
gap that was noticed and postponed. Four of the seven units in Phase 1b's disagreement table are one
season of a two-season family — BITS-1 is the Baltic in February, SWC-IBTS-4 is west Scotland in
autumn, GMEX-Fall is the Gulf of Mexico in autumn, NEUS-Spring is the northeast US in spring — and
that the disagreement table might be comparing seasons rather than places was not asked.

---

## 2. Estimand and unit, with the known problems first

**The unit is a species in a survey family.** A *family* is a region whose shelf is trawled in two
or three seasons under separate survey unit ids. Eight exist in the lake:

| family | units | months | years each | taxa each |
| --- | --- | --- | --- | --- |
| North Sea | NS-IBTS-1 / NS-IBTS-3 | Jan–Mar / Jun–Sep | 53 / 30 | 205 / 176 |
| west Scotland | SWC-IBTS-1 / SWC-IBTS-4 | Jan–Mar / Oct–Dec | 36 / 30 | 128 / 134 |
| Baltic | BITS-1 / BITS-4 | Feb–Mar / Sep–Dec | 29 / 23 | 98 / 110 |
| Gulf of Cádiz | SP-ARSA-1 / SP-ARSA-4 | Feb–Mar / Oct–Dec | 16 / 18 | 126 / 133 |
| Gulf of Mexico | GMEX-Summer / GMEX-Fall | May–Aug / Sep–Dec | 42 / 42 | 721 / 734 |
| northeast US | NEUS-Spring / NEUS-Fall | Feb–Jun / Sep–Dec | 53 / 57 | 447 / 532 |
| southeast US | SEUS-spring / -summer / -fall | Apr–Jun / Jul–Aug / Sep–Nov | 31 each | 196 / 188 / 199 |
| Scotian Shelf | SCS-SPRING / -SUMMER / -FALL | *not dated* | 42 / 51 / 8 | 174 / 351 / 105 |

**Two estimands, and the second is the primary one.**

- **A — seasonal amplitude.** Per species per family, the difference in abundance-weighted mean
  latitude between two seasons, on the footprint and years both share, in degrees. A second axis in
  metres of depth. This is the species' seasonal displacement *as this instrument sees it*.
- **B — phase dependence of the trend.** Per species per family, `shift_per_decade` fitted
  separately within each season on the shared footprint and shared years, and the difference between
  them, standardised by the combined standard error. This is the quantity that decides whether a
  published where-shift depends on which season measured it.

### Known problems, stated before any number is seen

- **The two seasons are two different surveys.** Different gear, vessel, depth strata and sometimes
  area. A between-season centroid difference therefore contains an instrument difference. The
  shared consistent footprint and shared years reduce it and do not remove it. **Estimand A is an
  upper bound on seasonal movement, and its sign per species is worth more than its size.**
- **Catchability is seasonal, and this is the deepest problem.** A species on the bottom in winter
  and in midwater in summer is caught differently by a bottom trawl at a constant position, so an
  amplitude can exist with no animal having moved. This is why **B is primary and A is only ever a
  covariate**: a catchability difference between seasons is a *level* offset, and a level offset
  cancels in a trend. The design rests on that cancellation and the note says so here rather than
  in a limitations section.
- **Least-squares trend errors are too small on an autocorrelated centroid series.** A centroid
  wanders between years, and prediction 7 exists because of it: without a passing split-half
  control, a spread in the standardised difference cannot be read as disagreement.
- **The Scotian Shelf's rows carry no within-year date.** Every `period_start` is 1 January, so its
  season is a label on the unit and not a fact in the rows. It enters estimand B, where the label is
  all that is needed, and its amplitude is reported as label-based.
- **Phase 3k's ships are not controlled.** A vessel effect is common to both seasons of a family
  only when the vessel is, and it is not always. This test does not re-measure it.
- **Shared years shrink the record.** The North Sea keeps 30 of 53; the Gulf of Cádiz keeps 16.
- **Many species and eight families.** Every count is stated against a chance bar and no single
  species is promoted.
- **Nothing causal**, in either estimand.

**Fixed floors, from the parent phases:** one-degree cells, 80% footprint consistency, at least 10
consistent cells, at least 15 usable years per species per season. Weight is CPUE. `SEED = 1`, 1,000
shuffle draws.

---

## 3. The design, fixed before any number is seen

1. **Load** each unit's `SURVEY_INDEX` rows through `lake.reader.scan` with an explicit
   `source_id`, and `metrics.range.to_cells` for the cell index and CPUE.
2. **Shared footprint.** Per family, keep the cells that clear 80% consistency **in every season of
   the family**, computed per season and intersected. A family whose intersection is under 10 cells
   is dropped, and reported as dropped.
3. **Shared years.** Restrict to the year span present in every season of the family.
4. **Centroids** per species per season per year with `metrics.range.centroids`.
5. **A:** the difference in the per-species mean of those centroids between seasons, over shared
   years.
6. **B:** `shift_per_decade` per species per season, then `z = (b₁ − b₂) / sqrt(se₁² + se₂²)`.
   Pooled per family as Cochran's `Q = Σ z²` against its chi-square bar at `n` species, and as the
   median absolute `z`.
7. **The control:** within the *longer* season of each family, split the shared years into odd and
   even, fit a trend in each half, and form the same `z`. Under a correct error model its spread is
   1.
8. **Calibration:** each unit's own pooled median trend, recomputed here on the unit's own footprint
   with no seasonal restriction, against Phase 1b's published table.

---

## 3a. Amendment, written while implementing and before the registered run

**A. Two of the eight families have three seasons, and §2 names a two-season statistic.** The
generalisation is fixed here, before any number is seen, and it is the only one that reduces to the
registered statistic at two seasons:

- **The disagreement** becomes Cochran's Q across a species' `k` season trends, inverse-variance
  weighted: `Q_i = Σ_s (b_is − b̄_i)² / se_is²` with `b̄_i` the weighted mean, against `chi²(k−1)`.
  At `k = 2` this is exactly `z²` from §3, so nothing about the two-season families changes. A
  family pools as `Σ_i Q_i` against `chi²(Σ_i (k_i − 1))`, and the per-species figure reported
  beside it is `sqrt(Q_i / (k_i − 1))`, which is `|z|` at two seasons.
- **The amplitude** becomes the range of a species' per-season mean centroids, `max − min`, which is
  `|difference|` at two seasons.
- **Prediction 6's correlation** becomes the mean over the family's season pairs of the Spearman
  correlation between their per-species trends, which is the single correlation at two seasons.

**B. The split-half control is run in the season with the most usable species**, not the longest
record, because the control's job is to describe the error model of the trends that prediction 4
actually pools, and a season with a long record but few species contributes few of them.

**C. The split-half control's year floor is eight, half the main floor rounded up.** §2 asks 15
usable years of a species in a season, and a half of a 30-year record cannot meet it. The floor for
each half is therefore half the main one, which keeps the control's unit the same species the main
estimand pools wherever the record allows it, and drops it where it does not. The shared year counts
in §2's table were known when this note was written, so this is a correspondence and not a choice
made to reach a number: it is fixed here, before the run, and the families whose halves fall under
it are reported as uncontrolled rather than quietly pooled.

Nothing about the families, floors, footprint rule, bars or predictions changes.

---

## 4. Predictions

1. **Coverage.** At least 6 of the 8 families yield a shared footprint of ≥10 cells and ≥20 species
   with 15 usable years in every season. *Check.*
2. **Calibration.** The recomputed per-unit medians reproduce Phase 1b's published values for
   BITS-1 (−0.183), GMEX-Fall (−0.119), NEUS-Spring (+0.101) and SWC-IBTS-4 (+0.258) to within
   0.02 °lat/decade. The tolerance is loose because Phase 1b's break-term treatment per unit is
   not re-derived here, and a miss beyond it means the loader disagrees with the published one.
   *Check.*
3. **Amplitude is real and species-specific.** The median absolute amplitude exceeds 0.2 °lat, and
   Cochran's Q across species clears its bar, in at least 4 families. *Discovery, registered as
   expected: shelf fish move within their year.*
4. **The two seasons disagree about the decadal shift, beyond their own errors.** `Q = Σ z²` clears
   its chi-square bar in at least half the families that pass prediction 1. *Registered as the
   expectation, and the prediction that would put a limit on a published claim.*
5. **Amplitude predicts the disagreement.** Pooled over families, the Spearman correlation between
   `|amplitude|` and `|z|` is positive and clears a within-family shuffle null. *Discovery, and the
   mechanism half: a phase cut can only bite a species that has a phase.*
6. **The seasons still agree in direction.** The Spearman correlation between the two seasons'
   per-species trends is positive and below 0.9 in most passing families — a real shift plus phase
   noise, rather than either alone. *Discovery.*
7. **The split-half control is quiet.** The median absolute `z` from the odd/even split does not
   exceed 1.2. *Control, registered as expected quiet.*

---

## 5. Stop conditions

- **Prediction 1 fails** → the coverage table is published and nothing else is interpreted.
- **Prediction 2 fails** → the loader disagrees with the published one; nothing above it is read
  and the disagreement is the result.
- **Prediction 7 fires** → prediction 4 is **not interpreted in either direction**. The note reports
  that this instrument cannot separate a phase cut from an autocorrelated centroid, no limit reaches
  the ledger, and the successor is a trend error that accounts for autocorrelation.
- **Prediction 4 true and 7 quiet** → **claim 2's marine leg gains a phase-cut limit**, and
  `marine-null`'s caveat gains one computed sentence carrying the median standardised disagreement
  and the number of families it holds in. Phase 1b's between-survey disagreement table gains a note
  naming how much of it is between seasons of one region.
- **Prediction 4 false and 7 quiet** → **claim 2's marine leg is strengthened**: the where-numbers
  do not depend on the season that measured them, at this instrument's resolution. Published as a
  null beside the change, with the resolution stated.
- **Prediction 5** changes no claim either way. It is the mechanism, not the licence.
- No family, floor, window or bar is revisited after any number is seen.

---

## 6. What this cannot establish

- **Not causation**, in either estimand.
- **Not a seasonal migration in absolute terms.** Catchability confounds amplitude, which is why
  amplitude is only ever a covariate and a sign.
- **Not the whole ocean.** Eight continental-shelf trawl families, all northern-hemisphere.
- **Not the ships.** Phase 3k's vessel effect is neither re-measured nor removed.
- **Not the other realms.** No aerial, terrestrial or freshwater record has a seasonal replicate of
  this kind, and the other two tests in ADR 0019 exist because of it.
- **Not the depth axis as a claim.** Phase 1b already reports depth and refuses to claim it; a
  one-degree cell can span a shelf break. Depth is reported here for the same reason and with the
  same refusal.
