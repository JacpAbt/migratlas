# Phase 1l — when two programmes count the same birds, how much of the difference is the counting?

**Status:** pre-registered 2026-08-23. Written before any paired difference has been computed, before
the two Swedish networks have been restricted to a shared window, and before any species has been
matched between them. What is known is Phase 1k's unpaired result and the species overlap measured on
2026-08-23: **173 species qualify in both Swedish networks**, 16 in point counts only and 24 in fixed
routes only.

Phase 1k's successor, on the first item of its own "what the successor has to fix", and on an owner
correction that reframed it.

---

## Why this note exists

Phase 1k compared two Swedish bird programmes and found their median latitude trends 3× apart —
`+0.0968` against `+0.0335` °lat/decade, neither point estimate inside the other's interval. It
graded that as a bound on the project's comparative method: if two protocols on one country's birds
disagree that much, a difference between fish and birds might be a difference between nets and
binoculars.

**The owner's correction: that diagnosis was reached by comparing two averages, which is the error it
was warning about.** Point counts qualified 189 species and fixed routes 197; they share 173. The two
medians summarise **different mixtures of animals**, and the 40 species that differ could produce the
whole gap without the counting method contributing anything. Treating "birds" as one mass is exactly
what hides that, and Phase 1k's own result says so — two thirds of `bbs` species carry a real trend
and they do not share a direction.

So the gap has at least four candidate causes, confounded in 1k: **species composition**, **footprint**
(33 cells against 84), **window** (1975–2024 against 1996–2025), and **protocol**. This phase removes
the first three by design and measures what is left.

---

## 1. Estimand and unit, with the known problems first

**The unit is a species measured by both networks.** 173 of them, and the count is inherited from the
overlap measured on 2026-08-23 rather than rediscovered.

**The estimand is the paired difference**: for one species, its point-count slope minus its
fixed-route slope, in °latitude per decade. The quantity of interest is the *distribution* of those
173 differences — not their mean, and explicitly not a single summary, which is the mistake this
phase exists to correct.

**Both networks are restricted to their shared years** before any slope is fitted, so window cannot
contribute. Footprint is *not* restricted, and §5 says why that is a limitation rather than an
oversight.

**The headline quantity is a ratio.** The interquartile spread of the paired differences, over the
interquartile spread of the slopes themselves. It answers the only question that matters for every
comparative claim this project makes:

- **Ratio well below 1** — the method matters much less than which animal you are looking at.
  Comparisons between networks, legs and realms are informative, and Phase 1k's 3× gap was
  composition.
- **Ratio near or above 1** — two ways of counting one species disagree about as much as two species
  disagree. Then every cross-unit claim in this project, `transfer-fails` included, is reporting
  instrument differences and must say so.

### Known problems, before any result

- **Two protocols in one country is one case.** Whatever the ratio is, it is Sweden's, for birds, on
  a latitude centroid. It bounds nothing about radar against trawls except by analogy, and the
  analogy is not evidence.
- **Footprints still differ.** Point counts keep 33 consistent cells and fixed routes 84. A species
  can genuinely shift differently in two overlapping-but-unequal areas, so part of any residual
  difference is real geography rather than method. Restricting to shared cells would fix it and would
  also shrink the panel; it is registered as the successor's job, not smuggled in here.
- **Agreement would not mean correctness.** Two protocols run by the same organisation in the same
  country can share a bias. A low ratio licenses comparison, not accuracy.
- **A paired difference inherits both slopes' noise.** Each species' two slopes are each estimated
  from a finite series, so the differences are wider than the true method effect. This makes the
  ratio *conservative* in the direction that would condemn the project's comparisons — stated so a
  high ratio is not over-read.

---

## 2. The design, fixed before any fit

Everything reuses Phase 1k: `phase1k.load_counts`, then `to_cells`, `consistent_footprint`,
`centroids` and `shift_per_decade`, at the same 20-year floor. The only additions are the shared-year
restriction and the pairing.

**No calibration arm.** Phase 1k's arms A and D passed today on this machine, and this phase computes
no quantity that a published finding also publishes, so there is nothing to reproduce. Recorded
because every other phase in this series has one.

**Seed** `SEED = 1`, as Phase 1k.

---

## 3. Predictions

1. **The paired median difference is smaller in magnitude than the unpaired gap of `0.0633`.** If the
   two medians differ mostly because they summarise different species, pairing shrinks it.
2. **At least a quarter of the 173 species disagree in sign between the two networks.** Two
   programmes, one bird, opposite directions — for a large minority of species. Registered because a
   small number here would be the more comfortable result and is not what 1k's dispersion suggests.
3. **The ratio is below 1** — the interquartile spread of paired differences is narrower than the
   interquartile spread of the slopes. Method matters less than species identity.
4. **The ratio is above 0.25.** Not negligible either. Registered as a two-sided bracket so that
   prediction 3 passing cannot be read as "the method is free".

---

## 4. Stop conditions

- **Fewer than 100 species clear the 20-year floor in both networks after the shared-year
  restriction.** Publish as a coverage statement; a ratio on a small panel would not bound anything.
- **The shared window leaves under 15 years.** Same.
- **Prediction 3 graded false.** Then stop and do not publish any of Phase 1k's distribution results:
  a project whose method variance exceeds its species variance has to fix that before it compares
  anything, and the finding is the ratio itself with `direction="limit"`.

---

## 5. What this cannot establish

- **Nothing causal, and nothing about why any species moved.**
- **Not that the ratio generalises.** One country, one taxonomic class, one estimand, two protocols
  from a single monitoring tradition.
- **Not that a low ratio makes Phase 1k's numbers right.** It would make them *comparable*, which is
  a weaker and different thing.
- **Not the footprint contribution**, which is left confounded on purpose and named as the successor's
  first job.
- **Not anything about the other three networks.** `bbs` has no twin, and neither does the butterfly
  scheme. Sweden is the only place this project can ask the question at all, which is itself worth
  recording: the ability to check an instrument is a property of the holding, and it exists once.

---

## Results — run 2026-08-23

| quantity | value |
| --- | --- |
| shared window | 1996–2024, 29 years |
| species qualifying in both networks | 166 |
| paired median difference | **`+0.1528`** °lat/decade |
| paired difference IQR | `[-0.0919, +0.4637]`, spread `0.5556` |
| slope IQR across species | `[-0.1028, +0.2846]`, spread `0.3874` |
| **ratio — method spread / species spread** | **`1.434`** |
| sign disagreements | **73 of 166 (44.0%)** |

166 rather than the 173 measured on the full spans: the shared-window restriction costs seven species
their twenty years.

### Grading

**Prediction 1 — FALSE, and in the direction nobody wanted.** Pairing was supposed to shrink the gap
if composition caused it. The paired median difference is `+0.1528`, **more than double** the unpaired
gap of `+0.0633`. Removing the species mixture did not explain the disagreement away; it made it
larger. Two programmes counting *the same bird* in the same country over the same 29 years differ by
more than their whole-network averages did.

**Prediction 2 — TRUE.** 73 of 166 species — 44% — get opposite-signed answers from the two
programmes. Registered at "at least a quarter" as the uncomfortable outcome, and it is nearly half.

**Prediction 3 — FALSE.** The ratio is `1.434`, above 1. The spread of "how much two methods disagree
about one species" is **wider** than the spread of "how much two species differ from each other".

**Prediction 4 — TRUE**, trivially, and it no longer means anything: it was registered as the lower
bracket in case prediction 3 passed too comfortably.

### The stop condition fires

§4 registered exactly this case:

> **Prediction 3 graded false.** Then stop and do not publish any of Phase 1k's distribution results
> … and the finding is the ratio itself with `direction="limit"`.

So that is what happens. **Phase 1k's three latitude medians are not published as findings.** The
ratio is.

### What it means, and what it cannot distinguish

The registration named the conservatism in advance and it has to be honoured now that the result is
unfavourable: a paired difference inherits **both** slopes' estimation noise. If each slope carries
error variance `e`, the difference carries `2e` plus any true method effect, while the slopes carry
`e` plus the between-species variance. So a ratio above 1 has two readings and this design cannot
separate them:

1. **The counting method genuinely matters more than which species you look at.**
2. **Each individual species slope is so noisy that the difference is mostly noise.**

**Both readings condemn the comparison equally**, which is why the stop condition does not depend on
telling them apart. Under (1) a 3× gap between two network medians is a fact about protocols. Under
(2) it is a fact about nothing — the per-species slopes are too noisy to average into a network median
that means anything. Either way, Phase 1k's `+0.0968` against `+0.0335` was not evidence about birds.

### What this establishes

- **A measured bound on this project's comparative method**, and it is not reassuring: on the one case
  where two instruments observe one population, they disagree about *individual species* more than
  species disagree with each other, and they disagree about direction for 44% of them.
- **`transfer-fails` needs this in its caveat as a number.** That finding already concedes instrument
  as inseparable from realm, hemisphere and response type. It can now say how large the instrument
  term can be: comparable to or larger than the between-species signal, on the only pair this project
  can check.
- **And the owner's correction was the right check to run, even though it did not exonerate anything.**
  Comparing two averages of different species mixtures *was* an error in Phase 1k's diagnosis. Fixing
  it made the problem worse rather than better, which is the outcome a check exists to be capable of.

### What the successor has to fix

1. **Separate method from noise.** Each OLS slope has its own standard error, already computed and
   currently discarded. Subtracting `2e` from the difference variance would split the ratio into a
   method term and a noise term, and decide between the two readings above. This is the single most
   valuable next measurement in the project and it needs no new data.
2. **Restrict to shared cells.** Footprint was left confounded on purpose here — 33 consistent cells
   against 84. Part of the residual may be real geography.
3. **Then, and only then, revisit Phase 1k's distribution numbers.** They are computed, gated and
   waiting; nothing about them was wrong except the confidence with which they could be read.
4. **Phase 3i should not run before item 1.** It is a comparison of skill across spatial units, which
   is the class of claim this result puts in question.
