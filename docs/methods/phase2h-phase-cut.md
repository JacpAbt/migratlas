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

---

# Results — run 2026-09-08

`make report-phase2h`, run as a pair twice: once as registered, which failed its calibration, and
once after the correction below, which reproduced every published value exactly. Both pairs were
identical line for line.

## Correction 1 — the registered run did not fit the gear break, and the calibration caught it

Prediction 2 **failed as registered**: BITS-1 came out at **−0.098** against a published **−0.183**,
a miss of 0.085, four times the tolerance and not absorbable by widening one. The cause is that
Phase 1b fits a level shift at each unit's own gear change year, read from `protocol`, and this
module did not. The stop condition applied: **nothing above the calibration was interpreted, and the
registered run's family numbers are recorded below as produced-and-not-graded.**

**The correction is larger than the calibration, and that is the point.** A gear refit inside one
season of a family and not the other puts a step in one of the two centroids, and this design would
have read that step as a phase cut — the exact confound it exists to measure. So the break term now
enters *three* places, all of them calling `phase1b.gear_change_year` rather than restating it: the
calibration, each season's trend, and each half of the split-half control. This confound was not
named in §2's known problems, which named the vessel effect and not the gear step, and that omission
is recorded here rather than edited into the design.

**What the correction moved.** Four of the six families' pooled Q did not change at all; two did,
because only their units changed gear inside the shared span:

| family | Q as registered | Q corrected | median \|z\| | verdict |
| --- | --- | --- | --- | --- |
| North Sea | 206.7 | 206.7 | 1.21 | unchanged |
| west Scotland | 93.7 | 93.7 | 0.92 | unchanged |
| Baltic | 83.6 | **68.5** | 1.09 → **0.79** | unchanged |
| Gulf of Mexico | 328.9 | 328.9 | 0.85 | unchanged |
| northeast US | 397.5 | **337.9** | 0.96 → **1.14** | unchanged |
| southeast US | 292.2 | 292.2 | 1.20 | unchanged |

No family's verdict moved. **One prediction's did**: prediction 5's correlation went from +0.172
against a null ceiling of +0.141 (clearing it) to +0.161 against +0.162 (not clearing it, by
0.001). It is graded on the corrected run, and a verdict resting on a margin of 0.001 is recorded
as carrying no weight in either direction.

## Coverage

**Six of eight families pass**, exactly the registered floor. The two that fail are worth naming:

| family | shared cells | shared years | species | outcome |
| --- | --- | --- | --- | --- |
| North Sea | 77 | 1991–2020 | 75 | passes |
| west Scotland | 14 | 1990–2020 | 46 | passes |
| Baltic | 19 | 1996–2020 | 39 | passes |
| Gulf of Cádiz | **3** | 2004–2020 | 0 | dropped |
| Gulf of Mexico | 19 | 1983–2024 | 171 | passes |
| northeast US | 40 | 1968–2019 | 130 | passes |
| southeast US | 14 | 1989–2019 | 80 | passes |
| Scotian Shelf | **2** | 1979–1986 | 0 | dropped |

**"The same region in two seasons" is often not the same water.** The Gulf of Cádiz keeps three
cells of a footprint and the Scotian Shelf two: their seasonal surveys sail different ground, and
the intersection that makes the comparison honest is what removes them. That is an instrument fact
about seasonal survey pairs and it is reported rather than worked around.

## Calibration — PASS, all four

BITS-1 −0.183 against −0.183; GMEX-Fall −0.119 against −0.119; NEUS-Spring +0.101 against +0.101;
SWC-IBTS-4 +0.258 against +0.258. Exact to three decimals through this module's own call path.

## The answer

| family | disagreement Q | bar | median \|z\| | split-half \|z\| | between-season ρ | median amplitude |
| --- | --- | --- | --- | --- | --- | --- |
| North Sea | **206.7** | 96.2 | 1.21 | 0.62 | +0.62 | +0.344° |
| west Scotland | **93.7** | 62.8 | 0.92 | 0.51 | +0.54 | +0.199° |
| Baltic | **68.5** | 54.6 | 0.79 | 0.59 | +0.30 | +0.122° |
| Gulf of Mexico | **328.9** | 202.5 | 0.85 | 0.79 | +0.48 | +0.128° |
| northeast US | **337.9** | 157.6 | 1.14 | 0.63 | +0.32 | +0.383° |
| southeast US | **292.2** | 190.5 | 1.20 | 0.64 | +0.32 | +0.840° |

**In all six regions, the same species' decadal latitude trend depends on which season measured it,
beyond what the two estimates' own errors allow.** Six of six pooled Q values clear their
chi-square bars, by margins of 1.25× to 2.15×.

**And the control is quiet, which is what lets that be read.** The split-half median |z| runs 0.51
to 0.79 against a registered bar of 1.2 — every one of them *below* 1, so on these series the
least-squares trend error is if anything conservative rather than too small. The problem §2 named as
the reason prediction 7 existed did not materialise, and the disagreement between seasons is
therefore not the disagreement between two halves of one season.

**The size of it.** A typical species' two seasons differ by about one standard error (median |z|
0.79–1.21), so this is not every species disagreeing loudly; it is a distribution with a heavy tail,
and the pooled Q clears because a substantial minority disagree strongly. The between-season rank
correlation of a species' trend is **+0.30 to +0.62**. If a where-shift were a clean property of a
species' range, two seasons of the same region should agree far better than that.

**What it does not say.** It does not say the marine where-numbers are wrong. It says a single
season's trend carries a season-specific component of a size comparable to its own standard error,
and that a published per-species trend is therefore a property of a species *and a survey season*
rather than of a species and a place.

## The predictions, graded

**1 — TRUE** (check). Six of eight families, the registered floor exactly.

**2 — FALSE as registered, TRUE after correction 1.** Graded FALSE: the registration's own
consequence fired and the correction it forced is recorded above rather than edited into §3.

**3 — FALSE.** Both halves of the prediction hold in only **three** families against a floor of
four: median amplitude clears 0.2° in the North Sea (+0.344), northeast US (+0.383) and southeast US
(+0.840), and west Scotland (+0.199) misses by a thousandth of a degree. Amplitude's Q clears its
bar in four families (North Sea, Baltic, northeast US, southeast US) and not in west Scotland or the
Gulf of Mexico. **The likely reason is in the design and not the animals:** amplitude is measured on
the *intersected* footprint, 14 to 77 cells, which is the part of the region both seasons trawl —
precisely the water a seasonally moving fish is least likely to have left.

**4 — TRUE**, in six of six against a floor of half. The registered expectation, and the one that
carries the limit.

**5 — FALSE**, by 0.001. Pooled Spearman between |amplitude| and |z| is **+0.161** against a
within-family shuffle null of **[+0.014, +0.162]**. The null is worth reading: it is entirely
positive, because shuffling inside a family removes the within-family relation and leaves the
between-family alignment — families with larger amplitudes also have larger disagreements. So the
pooled correlation is explained by differences *between* regions and not by a relation *inside*
one. That is the confound the within-family null was registered to expose, and it exposed it.

**6 — TRUE**, in six of six. Every between-season correlation is positive and every one is far
below the 0.9 ceiling: a real shared shift plus a large season-specific part.

**7 — TRUE.** Maximum split-half median |z| is 0.79 against a bar of 1.2.

Five of seven, with one correction. The two that failed are both about *amplitude* — the covariate —
and neither touches the primary estimand.

## The stop conditions, and what they do

- Prediction 1 held → the comparison was interpreted.
- **Prediction 2 failed as registered → nothing was interpreted on that run**, and correction 1 is
  recorded above with what it moved and what it did not.
- Prediction 7 did not fire → prediction 4 is interpretable.
- **Prediction 4 true and 7 quiet → the registered consequence applies.** Claim 2's marine leg gains
  a phase-cut limit; `marine-null`'s caveat gains one computed sentence carrying the median
  standardised disagreement and the number of families it holds in; and Phase 1b's between-survey
  disagreement table gains a pointer saying that four of its seven printed units are one season of a
  two-season family, and that six of six such families disagree with their own other season.
- Prediction 5 changed no claim, as registered, and its margin is recorded as too thin to read.
- No family, floor, window or bar was revisited after any number was seen. One correction is
  recorded; it is not a revision.

## What the successor has to fix

1. **Amplitude on each season's own footprint, not the intersection.** The intersection is the water
   both seasons trawl, which is where a seasonal migrant is least visible, and prediction 3 probably
   failed on that. A per-season footprint with a stated non-comparability is the honest version.
2. **Which species disagree, and whether that is a trait.** 541 species have a `z` and this note
   publishes six medians. The animal-specific outlook says the tail is the result, and it needs a
   trait table — depth range, spawning season, pelagic or demersal — which the lake does not hold.
3. **A phase-aware trend.** If a season's trend carries a phenology component, the estimand worth
   having is the trend in the *annual* centroid, which needs the seasons modelled jointly rather
   than compared. That is a different note and a harder one.
4. **The two dropped families** need a coarser cell or a stated sub-region, not a lower floor.

## What this does not establish

- **Not causation**, in either estimand.
- **Not that a phase cut is the whole of the disagreement.** Gear is controlled by a break term,
  vessels are not, and Phase 3k measured that the ships carry +0.82 degrees per degree of their own
  movement. A season-specific vessel effect would look exactly like a phase cut here.
- **Not a seasonal migration in absolute terms.** Catchability confounds amplitude, and amplitude
  is only ever a covariate and a sign.
- **Not the whole ocean.** Six continental-shelf trawl families, all northern-hemisphere.
- **Not the other realms**, which have no seasonal replicate of this kind. That is why ADR 0019
  registers two more tests.
