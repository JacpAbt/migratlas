# Phase 1n — with the footprint held equal, what is the protocol difference made of?

**Status: pre-registered 2026-09-01, before any shared-cell restriction has been computed.** No
paired difference on a shared footprint exists in this repository, no decomposition of that
difference has been fitted, and neither covariate below has been joined to a paired difference. What
*was* looked at is in §1, and it is everything Phase 1l and 1m published.

Phase 1l's and Phase 1m's successor, on the item both of them named and neither did:
**restrict to shared cells first, then ask what the remainder is.**

---

## Why this note exists

Phase 1l measured two Swedish bird programmes disagreeing about the *same species* more than species
disagree with each other: a noise-corrected method-to-species scatter of **1.17**, with 73 of 166
species getting opposite-signed answers. Its stop condition fired and Phase 1k's three latitude
medians have been withheld ever since.

Phase 1m then established that the remainder does **not average out**: grouping seventeen species at
a time moved the ratio from 1.17 to 1.15, and a difference that survives averaging is systematic
rather than species-specific noise.

Both notes closed with the same unfinished item, and it has now been open for three phases:

> **Footprint remains confounded** — 33 consistently sampled cells against 84 — for the third phase
> running. It should be restricted before any of the above.

So `protocol-disagreement`, a published ledger finding with `direction="limit"`, rests on a
comparison in which the two programmes were measured over **different areas**. Part of what it calls
protocol is geography, and nobody knows what part.

And #67 is the question after that one: *a constant offset is a calibration and correctable; a
difference that varies with something names that something.* Neither has been looked at.

---

## 1. What was looked at before this was written

All published:

| what | value | where |
| --- | --- | --- |
| noise-corrected method-to-species scatter | **1.17** | `protocol-disagreement`, Phase 1l |
| share of the raw paired disagreement that is estimation error | 24% | Phase 1l |
| sign disagreements | 73 of 166 species; 62 involve an estimate that cannot be told from zero | Phase 1l |
| a single species' precision | median trend **1.69** standard errors from zero | Phase 1l |
| the same ratio at group level | 1.15 across ten groups | Phase 1m |
| consistent cells kept | **33** (point counts) against **84** (fixed routes) | Phase 1k |
| shared window | 1996–2024, 29 years | Phase 1l |
| species qualifying in both | 166 | Phase 1l |
| coherence of the free grouping axes | 0.076–0.189 against a floor of 0.10 | Phase 1m |

**What was not looked at:** any shared-cell footprint, any paired difference computed on one, any
decomposition of a difference into offset and slope, and neither covariate joined to anything.

---

## 2. Estimand and units, with the known problems first

**The unit is a species measured by both networks on the shared footprint.** Phase 1l's unit with
one restriction added.

**The footprint rule.** Both networks are restricted to the **intersection** of their consistent
cells before any centroid is computed — the cells each network sampled in at least 80% of its years
*and* which the other network also kept. `consistent_footprint` is applied per network first, exactly
as Phase 1k applies it, and the intersection taken afterwards, so neither network's consistency rule
is relaxed to manufacture overlap.

**Two estimands, and the second is #67.**

1. **The ratio, again.** Phase 1l's noise-corrected method-to-species scatter, recomputed on the
   shared footprint. The question it answers is how much of `1.17` was geography.
2. **The shape of the remainder.** The paired difference per species, decomposed into
   - a **constant offset** — the mean paired difference, which is a calibration if it is all there is;
   - and a **varying part** — whether the difference depends on either covariate below.

### The two covariates, fixed here

Both are properties of the species, neither is a property of the difference, and grouping on a level
while measuring a slope is non-circular for the reason Phase 1m gave: `shift_per_decade` centres the
year, so intercept and slope estimates are uncorrelated.

- **Detectability, as mean count per unit effort** across the shared footprint, pooled over both
  networks so the covariate is not itself one programme's view. **This is the substantive
  candidate**: a point count and a line transect should differ most for the species that are hardest
  to detect, and if the difference is a detection effect it will show here.
- **Where the species lives**, as its mean latitude on the shared footprint. Phase 1m's axis, kept
  because a difference that varies with latitude would be geography surviving the footprint
  restriction rather than protocol.

### Known problems, before any fit

- **Restricting the footprint shrinks the panel, and the panel was already the binding constraint.**
  33 cells against 84 means the intersection is at most 33 and probably fewer. Species that
  qualified on 20 years within a network may not qualify on the intersection, and the count of
  survivors is a graded prediction rather than an assumption.
- **A constant offset in a *trend* is not a calibration in the ordinary sense.** Two programmes
  disagreeing by a fixed number of degrees per decade is not an instrument reading high; it is one
  programme's footprint drifting relative to the other's, or one protocol's detection changing over
  time. So "offset" here names a shape, not a mechanism, and §6 says so.
- **Two covariates is two tests**, and neither is added after this line.
- **Sweden is still one case.** Whatever this finds is Sweden's, for birds, on a latitude centroid.
  Phase 1l's own §5 binds here unchanged.
- **The ratio inherits Phase 1l's conservatism.** A paired difference carries both slopes' error, and
  Phase 1l's decomposition removes it from both sides; the same `split_difference` is called, not
  reimplemented.

---

## 3. The design, fixed before any fit

- **Calibration rung.** Recomputing Phase 1l's ratio on the **unrestricted** footprint must reproduce
  **1.17** to two significant figures, by calling `phase1l.decompose` itself. If it does not, the
  harness is not the one that produced the published number and nothing below is read.
- **The restriction**, then Phase 1l's pairing and decomposition unchanged.
- **The decomposition of the remainder**: ordinary least squares of the paired difference on each
  covariate separately, standardised, with a bootstrap interval clustered on nothing — the unit is
  the species and species are the independent thing here, which is the one place in this project
  where that is true rather than assumed.
- **ADR 0016 applies to both slopes.** 166 species is above the rule's floor of 30, so it does not
  bind; it is computed and reported anyway because the panel may fall below 30 after the restriction.
- **Seed** `SEED = 1`, as Phase 1k, 1l and 1m.

---

## 4. Predictions

1. **The calibration reproduces `1.17` to two significant figures.**
2. **At least 60 species survive the shared-footprint restriction at 20 years each.** Below that the
   phase publishes as a coverage statement; 60 is a third of Phase 1l's 166 and is set here rather
   than against the answer.
3. **The ratio falls.** Removing the footprint difference removes part of what Phase 1l called
   protocol, so the shared-footprint ratio is **below 1.17**. Registered as the expected direction:
   both predecessor notes named the footprint as a live confound.
4. **The ratio stays above 1.** Registered as the second half of a bracket, so that prediction 3
   passing cannot be read as "it was all geography". If it falls below 1, Phase 1l's stop condition
   is satisfied and Phase 1k's three withheld medians can be reconsidered — which is the outcome that
   would change the most.
5. **The difference varies with detectability**, and the slope on it is distinguishable from zero.
   This is #67's substantive answer if it holds: the two protocols differ most for the species they
   detect least well.
6. **The difference does not vary with latitude.** If it does, geography survived the footprint
   restriction and the restriction did not do its job.

---

## 5. Stop conditions

- **The calibration misses.** Stop; nothing below is interpreted.
- **Fewer than 60 species survive.** Publish as a coverage statement and grade nothing but
  prediction 2.
- **The ratio falls below 1.** Then report it, and say plainly that Phase 1l's stop condition no
  longer binds on the footprint-matched panel — *without* republishing Phase 1k's medians in the same
  commit. Lifting a withholding is its own decision with its own registration, and doing it in the
  commit that produced the licence is how a stop condition becomes decorative.
- **Both covariate slopes are null.** Then #67 is answered negatively: the remainder is a constant
  offset on these two axes, which is the calibratable case, and the note says so rather than reaching
  for a third axis.
- No covariate, footprint rule, floor or seed is revisited after any number is seen.

---

## 6. What this cannot establish

- **Not which programme is right.** Phase 1l's §5 binds: agreement would license comparison, never
  accuracy, and disagreement identifies neither party.
- **Not a mechanism.** "Varies with detectability" is a shape. Whether it is flushing, distance
  sampling, observer skill or time of day is not in this data.
- **Not that an offset is correctable.** See §2: a constant difference in a *trend* is not an
  instrument reading high, and calling it a calibration would be the over-reading this note is
  guarding against.
- **Not anything about the other networks.** `bbs` has no twin and the butterfly scheme has none.
  Sweden is the only place this question can be asked at all, which is itself the finding Phase 1l
  recorded.
- **Not the taxonomic axis.** #66's rank ingest is a different note.

---

# Results — run 2026-09-01

`make report-phase1n`. **Calibration PASS**: Phase 1l's ratio on the unrestricted footprint comes
back at **1.1722** against the published 1.17, by calling `phase1l.decompose` itself.

| quantity | value |
| --- | --- |
| consistent cells, point counts | 38 |
| consistent cells, fixed routes | 84 |
| **shared** | **37** |
| species on the shared footprint | **159** (floor 60) |
| ratio, unrestricted | 1.17 |
| **ratio, shared footprint** | **1.189** |
| estimation error, share of the raw paired disagreement | 18% (24% unrestricted) |
| **constant offset** | **+0.1688 ± 0.0999** °lat/decade — clears zero |
| slope on detectability | +0.0184 ± 0.1107 per sd — inside zero |
| slope on where it lives | +0.1103 ± 0.2257 per sd — inside zero |

## The answer, and it is not the one three phases expected

**The footprint was never the confound.** Restricting both programmes to the cells they share does
not reduce the disagreement — the ratio goes from 1.17 to **1.189**, which is up rather than down.
Phase 1l named the footprint as the successor's first job, Phase 1m repeated it, and this note was
written on the same assumption. All three were wrong about it.

**Because the two footprints were nested, not overlapping.** 37 of point counts' 38 consistent cells
are also fixed-route cells — **97%**. The restriction therefore removes almost nothing from the
smaller programme and trims 56% of the larger one, and it costs only 7 of 166 species. "33 cells
against 84" reads like two partly-overlapping areas and is actually one area inside another, so the
comparison was already very nearly footprint-matched and nobody had checked.

That is a correction to three notes rather than a result about birds, and it is the useful kind:
a confound that everybody could see and nobody had measured turns out to be small.

**And #67 has an answer: the remainder is a constant offset.** The paired difference has a mean of
**+0.1688 ± 0.0999** degrees of latitude per decade whose interval clears zero, and neither covariate
explains any variation in it. Point counts report species moving north faster than fixed routes do, by
about a sixth of a degree per decade, by roughly the same amount regardless of how readily a species
is counted or where it lives.

## The predictions, graded

**1 — TRUE.** 1.1722 against 1.17.

**2 — TRUE.** 159 species survive, against a floor of 60. The floor was set for a restriction that
turned out to cost almost nothing.

**3 — FALSE.** The ratio did not fall. 1.189 against 1.17, which is a rise of about the size of
nothing — but the registered direction was down and it is graded on what it said.

**4 — TRUE**, and now trivially: the ratio stays above 1 because it did not move. Registered as the
second half of a bracket so that prediction 3 passing could not be read as "it was all geography";
prediction 3 failed instead, so the bracket never had to do its work.

**5 — FALSE.** The difference does not vary with detectability: **+0.018 ± 0.111** per standard
deviation, comfortably inside zero. This was the substantive expectation — two protocols should differ
most for the species they detect least well — and it is not what is here.

**6 — TRUE.** It does not vary with latitude either, at +0.110 ± 0.226.

## The stop condition, and what it does

§5 registered: *both covariate slopes are null → #67 is answered negatively: the remainder is a
constant offset on these two axes, which is the calibratable case, and the note says so rather than
reaching for a third axis.*

Applied, and the note does not reach for a third axis. What changes:

- **`protocol-disagreement` loses a hedge.** Its caveat said footprints were left unequal on purpose
  so part of the remainder is geography. Measured: the footprints are 97% nested and matching them
  moves the ratio by +0.02. The claim is *stronger* for it — the disagreement it reports is not
  geography.
- **And gains a number.** The systematic part has a size and a direction: point counts read about
  +0.17 °latitude per decade more northward movement than fixed routes, on the same species over the
  same years and now the same ground.

## What an offset does *not* license, and §2 said this before the run

**A constant difference in a trend is not an instrument reading high.** Two thermometers differing by
a degree can be calibrated; two programmes differing by a sixth of a degree of latitude *per decade*
are disagreeing about a rate, and a rate offset means one programme's view of where a species is
drifting relative to the other's. Candidate mechanisms — one protocol's detection changing over time,
one programme's site turnover, an observer pool that shifted — are all consistent with this and are
not separable here.

So "calibratable in shape" is what has been established. Whether it is correctable in practice needs
to know *which* programme is drifting, and Phase 1l's §5 binds on that unchanged: disagreement
identifies neither party.

## What this does not establish

- **Not which programme is right.** See above.
- **Not that the offset is stable.** It is a mean over 159 species on 29 years; whether it was the
  same size in 1996 as in 2024 is a different estimand and is not fitted here.
- **Not that no covariate explains it.** Two were registered and two came back null. Body size,
  habitat, flocking behaviour and time-of-day of the count are all plausible and none is in the lake.
- **Not anything about the other networks.** Sweden remains the only place this question can be asked.
- **Not that Phase 1k's withheld medians should be republished.** The ratio is still above 1, so Phase
  1l's stop condition still binds, and §5 pre-committed that lifting a withholding is its own decision
  with its own registration.
