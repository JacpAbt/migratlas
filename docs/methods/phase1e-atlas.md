# Phase 1e — did southern African bird distributions change between two atlases?

**Status:** pre-registered 2026-08-01. Written before any occupancy is estimated, before any
species is looked at individually, and before the two epochs have been compared in any way. What
*was* looked at first is set out in §1, because the design depends on structure that had to be
confirmed to exist and saying "pre-registered" without naming what was already known would be worth
nothing.

## Why this note exists

Every claim this project publishes is northern-hemisphere, and it publishes that fact as a finding
in its own right: `coverage-bias` reports that 0.0% of the radar record and 0.0% of the survey
record lie south of the equator, and its caveat says no model fitted on that should be trusted
elsewhere without being tested there first. SABAP1 landed on 2026-07-30 and SABAP2 the same week.
They have been in the lake, uncompared, ever since.

This is the first southern-hemisphere question the project asks, the first terrestrial one, and the
first that does not run on a weather radar.

## 1. What was looked at before this was written

Structure only, and all of it from `lake.reader.scan` over `SURVEY_INDEX`:

| | `sabap1` | `sabap2` |
| --- | --- | --- |
| rows | 3,123,626 | 16,618,692 |
| sites | 1,568 quarter-degree cells | 25,945 pentads |
| taxa | 757 | 1,107 |
| period per row | one calendar month | one calendar month |
| `effort` | atlas cards submitted, 1–91 | atlas cards submitted, 1–82 |
| `count` | cards the species appeared on, 0–87 | cards the species appeared on, 0–78 |
| protocol | one | `BirdMAP fullprot` 13.2M, `BirdMAP adhocprot` 3.5M |
| bulk of rows | 1980s and 1990s | 2000s onward |

Two structural facts, and the design turns on both.

**`count` never exceeds `effort`, on any of the 19.7 million rows.** A row is therefore "this
species was recorded on *k* of the *n* cards submitted for this cell in this month", which is a
binomial with a known denominator rather than a bare presence record.

**That is a replicate structure, so detection is identifiable.** This was the open question and the
stop condition attached to it. `ca779de` records that SABAP2's SIMPLE_CSV export carries no card
identifier, which is why the Darwin Core archive was used instead, and the worry was that the
aggregation to cell-months had thrown the replicates away. It has not: *(k, n)* is exactly what a
single-season occupancy model consumes. **No card identifier is needed and the stop condition in §6
does not fire.**

What was **not** looked at: any occupancy estimate, any detection probability, any species by name,
any per-cell number, and any quantity computed from both sources at once. The tables above are
counts of rows and distinct values.

## 2. The estimand

For each species, the **proportion of the common footprint it occupies**, estimated separately in
each epoch, and the difference between the two.

Occupancy rather than reporting rate, and the distinction is the entire point of doing this
properly. A reporting rate is `count / effort`: it falls when a species declines and it also falls
when observers get worse, get busier, or change what they write down. Between 1987 and now,
southern African atlassing went from paper cards returned by post to a phone app, the observer pool
turned over completely, and the cell size changed. A reporting-rate comparison across that cannot
tell "the birds changed" from "the observers changed", and it would report the second as the first.

## 3. The unit, and its known problems

**Species × quarter-degree cell**, reported as species × region, and never as a single pooled number
standing alone.

That last clause is Phase 1b's finding applied as a design rule rather than remembered as a lesson.
The marine null is `median -0.011 °latitude per decade` and individual surveys inside it reach
-0.22 and +0.26 in opposite directions: pooling destroyed the result. A pooled southern-African
occupancy change would do the same thing, and this note commits in advance to publishing the spread
alongside any median.

Known problems, stated now rather than discovered in the results:

- **The grids differ.** SABAP1 is quarter-degree; SABAP2 is pentads of five arc-minutes, nine to a
  quarter-degree cell. Comparison is at quarter-degree, because pentads aggregate up and quarter
  degrees cannot be split down. SABAP2's finer resolution is discarded, deliberately.
- **Closure is violated.** A single-season occupancy model assumes a cell's occupancy does not
  change within the epoch. Over a five-year atlas period it does. The standard consequence is that
  ψ is read as "probability the cell was used at some point in the epoch" rather than as a snapshot,
  and that reading is what will be published.
- **A species detected everywhere carries no information about detection.** Where `count == effort`
  in every cell, *p* is at its boundary and ψ is unidentifiable from below. Those species are
  reported as "occupied throughout, no change measurable" rather than as an estimate.
- **Two epochs is a difference, not a trend.** There is no third point, so nothing here is a rate
  and nothing may be extrapolated from it.

## 4. The windows

- **Epoch 1: 1987-01-01 to 1991-12-31**, SABAP1's own atlas period. Rows outside it exist in the
  archive, back to 1901, and are excluded.
- **Epoch 2: 2008-01-01 to 2012-12-31.** Five years, to match epoch 1's length.

Matching the length is a decision and not a formality. SABAP2 has run for nineteen years and pooling
all of it against five years of SABAP1 would give epoch 2 several times the effort per cell. The
occupancy model corrects for effort, so this would not bias ψ in principle — but it would make the
two epochs differ in how well ψ is *determined*, and the species with the weakest epoch-1 estimate
would be the ones that appear to have changed most. Equal windows make the two estimates equally
uncertain.

**Sensitivity, registered now:** the same comparison against **2019-01-01 to 2023-12-31**. If the
sign of a species' change flips between the two choices of epoch 2, that species carries no result.

**Protocol:** `BirdMAP fullprot` only. The ad-hoc protocol has no fixed observation period behind
its card, so its cards are not exchangeable with full-protocol cards and cannot share a detection
probability with them. Registered as an exclusion rather than a filter to be decided later.

## 5. The model

Single-season occupancy with binomial detection (MacKenzie et al. 2002), one fit per species per
epoch, over the cells in the common footprint.

For species *s* in epoch *e*, with cell *c* contributing *n_c* full-protocol cards of which *k_c*
recorded the species:

```
L(ψ, p) = Π_c [ ψ · Binom(k_c ; n_c, p)  +  (1 − ψ) · 1{k_c = 0} ]
```

- **ψ** — probability a cell in the footprint is occupied.
- **p** — probability the species is recorded on one card of an occupied cell.

Maximum likelihood on the logit scale via `scipy.optimize`, with a profile-likelihood interval on
ψ. Vectorised across species; roughly a thousand species by two epochs is a small problem.

The reported change is **Δψ = ψ₂ − ψ₁** per species, with an interval from the two profiles.

For the map, a cell where the species was never recorded is not the same as a cell where it is
absent, and the model says by how much:

```
Pr(occupied | k_c = 0)  =  ψ(1 − p)^{n_c} / [ ψ(1 − p)^{n_c} + (1 − ψ)]
```

**The naive comparison is computed too, and published beside the corrected one.** Mean reporting
rate per cell, differenced across epochs, with no detection term. Not as a robustness check —
as the exhibit. The gap between the two numbers is what a detection model buys, and this project
has a place for showing the wrong answer next to the right one.

**Rejected:** a dynamic (multi-season) occupancy model with colonisation and extinction
parameters. It is the better tool and it needs the years between the atlases, which do not exist.
Fitting one to two disjoint five-year blocks would estimate a turnover rate over a nineteen-year gap
containing no data.

**Rejected:** pooling SABAP1's cells to a coarser grid to raise the card count per cell. It would
raise ψ mechanically — a bigger cell is more likely to contain the species — and the change between
epochs would then partly be a change in cell size.

## 6. The consistent footprint

A quarter-degree cell enters the analysis only if it carries at least **`MIN_CARDS = 20`
full-protocol cards in both epochs**.

Twenty because detection has to be estimable at the cell that contributes to it, and because it is
the same shape of rule as Phase 1b's consistent-cell requirement, which is what made the marine null
defensible. The number is registered here so that it cannot be chosen after seeing how many cells
each candidate threshold leaves.

`MIN_SPECIES_CELLS = 30`: a species needs thirty footprint cells in each epoch, or its ψ is fitted
on too few cells to carry an interval worth publishing.

## 7. Predictions, registered now

1. **The common footprint is between 300 and 1,200 quarter-degree cells.** SABAP1 has 1,568 cells in
   total and not all of them were well atlassed; SABAP2's 25,945 pentads cover roughly 2,900
   quarter-degree equivalents, so SABAP1 is the binding constraint. Below 300 the design is too thin
   to report and §8 applies.
2. **Between 250 and 700 species clear `MIN_SPECIES_CELLS` in both epochs**, out of the 757 and
   1,107 the two sources carry.
3. **Detection probability is higher in epoch 2 than epoch 1 for a majority of species.** Digital
   recording, better field guides, better optics and a photograph-backed rarities process all push
   the same way. If this fails, the detection model is doing something other than what it is meant
   to and the results are not reportable until it is understood.
4. **The naive reporting-rate change is more positive than the occupancy change for a majority of
   species** — because prediction 3 says observers got better, and an uncorrected comparison reads
   that as birds arriving. The size of the gap is the result most worth publishing.
5. **The pooled median Δψ is between −0.10 and +0.10, and individual species reach at least ±0.25 in
   both directions.** Stated as the Phase 1b shape: a small central tendency around a wide,
   sign-disagreeing spread.

## 8. Stop conditions

Each one says what the output becomes, so that "no result" is still a publishable outcome rather
than a silence.

- **Fewer than 300 cells in the common footprint.** Report as a coverage limit: the two atlases
  overlap too little to compare, and say by how much. No species-level result.
- **Fewer than 100 species clear the cell floor.** Same treatment.
- **Detection is at a boundary (p̂ > 0.99 or p̂ < 0.01) for more than a third of species.** The
  model is not identified on this data. Report the naive comparison alone, labelled as
  effort-confounded, and stop.
- **The two choices of epoch 2 disagree in sign for more than a third of species.** The result is a
  property of the window, not of the birds. Publish the disagreement as the finding.
- **The occupancy change and the naive change agree to within 0.01 for nearly every species.** Then
  the detection correction bought nothing here, which is worth saying plainly, and the interesting
  half of this note was wrong.

## 9. What this cannot establish

- **Not a trend.** Two epochs, one difference, no rate. Anything phrased "per decade" from this is
  wrong.
- **Not the southern hemisphere.** South Africa, Lesotho and Eswatini. It narrows `coverage-bias`;
  it does not retire it.
- **Not birds in general, and certainly not animals.** One taxonomic class, one atlas tradition.
- **Not attribution.** This measures whether distributions changed. Why is a later question, and
  the factor work in `DATASETS.md` step 3 is downstream of this note, not part of it.
- **Not comparable to Phase 1a.** The radar measures timing of aerial biomass; this measures
  occupancy of identified species. Two different quantities, and the only thing they will share is
  a climate covariate — which is the whole point of the transfer test, and that is a third note.

## 10. Where the result goes

- A sixth `Finding` in `reports/findings.py`, realm `terrestrial`, with its ROBITT assessment,
  whatever the sign and whether or not there is one. A null here is as publishable as `marine-null`.
- Per-species study cards, which is the first time the site can offer "pick an animal and see what
  is known about it" backed by a result rather than by a range map.
- `coverage-bias` recomputes on every build, so its own numbers move on their own the moment this
  lands.


---

# Results — appended 2026-08-05

Run with the design above unchanged. Every prediction is graded, including the two that failed, and
the one place the note's own wording had to be corrected is recorded here rather than edited into §6.

## What the footprint came to

| | |
| --- | --- |
| SABAP1 cells, 1987-1991 | 1,546 |
| SABAP2 cells, 2008-2012, full protocol | 2,160 |
| cells in both | 1,441 |
| **common footprint, ≥ 20 cards in both** | **496** |
| cards per footprint cell, median | **82** in epoch 1, **68** in epoch 2 |
| taxa with ≥ 30 epoch-1 detection cells | 560 of 742 |
| species fitted and reportable | **512** |
| pinned at a boundary or non-converged | 48 (8.6%) |

## The predictions, graded

**1. Footprint between 300 and 1,200 cells — PASS.** 496.

**2. Between 250 and 700 species clear the cell floor — PASS.** 560.

**3. Detection higher in epoch 2 for a majority of species — FAIL.** It rose for **48.2%**, which is
a coin flip rather than the improvement predicted. Median *p* is 0.125 in epoch 1 and 0.119 in epoch
2, a median change of −0.001.

This is the prediction with a consequence attached: the note said that if it failed, the model was
doing something other than intended and nothing was reportable until that was understood. It is
understood, and §"Why the correction bought nothing" below is the understanding. Two things had to be
separated, and neither happened:

- The predicted *improvement* from digital recording and better optics does not appear at the
  per-card level.
- The *feared* bias from pooling pentad cards into quarter-degree cells does not appear either. A
  SABAP2 full-protocol card covers a ninth of a SABAP1 card's area, which should depress *p*
  mechanically; it did not measurably. The likeliest reason is that a full-protocol card is at least
  two hours of dedicated atlassing in a small area, so intensity per unit area rises about as much as
  area falls. That is an explanation, not a measurement, and it is the loose end this note leaves.

What *did* emerge is worth more than the prediction was: **detection probability is a stable property
of a species**, correlating **0.938** across the thirty-year gap. Whatever else changed about southern
African atlassing, how likely a given bird is to be written on a card did not.

**4. Naive change more positive than corrected for a majority — FAIL.** 36.3%. It follows from 3: the
naive estimate's bias depends on *p*, and *p* did not change, so the bias did not change either.

**5. Median Δψ within ±0.10, individual species reaching ±0.25 both ways — PART PASS.** Median
**−0.0071**, comfortably inside. Deciles −0.075 to +0.048. But only **one** species passes ±0.25, and
it is an increase: nothing reaches −0.25, the largest decline being −0.229. The Phase 1b shape — a
small centre around a wide, sign-disagreeing spread — is present in direction and narrower in
magnitude than predicted.

## The stop conditions

- Fewer than 300 footprint cells — **did not fire** (496).
- Fewer than 100 species — **did not fire** (560).
- Detection at a boundary for more than a third of species — **did not fire** (8.6%).
- The two epoch-2 windows disagree in sign for more than a third of species — **did not fire.**
  19.6% over all shared species, 14.4% among those that moved at all. See the sensitivity section.
- **Corrected and naive agree to within 0.01 for nearly every species — FIRED.** 77.3% agree within
  0.01 and the median difference is **0.0020**. Per §8 this means the detection correction bought
  nothing here, and the interesting half of this note was wrong.

## Why the correction bought nothing

Not because the model is broken — it recovers known parameters from simulated data, which is what
`tests/test_occupancy.py` is for. Because of the footprint rule.

An occupied cell is missed when every one of its *n* cards misses the species, with probability
`(1 − p)^n`. The footprint cells carry a **median of 82 cards** in epoch 1 and 68 in epoch 2, and *p*
is about 0.12. So:

    (1 − 0.125)^82 ≈ 0.00002        (1 − 0.119)^68 ≈ 0.0002

Detection is effectively perfect at this effort. The naive estimate is therefore already almost
unbiased — median `ψ − naive` is **+0.0020** in epoch 1 and **+0.0036** in epoch 2 — and the residue
that survives differencing is **+0.0003**.

**`MIN_CARDS = 20` is the reason, and it is the same threshold that made the model fittable.** It was
registered to guarantee detection could be *estimated* at every contributing cell; it simultaneously
guaranteed there was nothing left for detection to *explain*. Those are the same condition read two
ways, and the note did not notice it was assuming one and getting the other. A design that wanted the
correction to matter would have had to admit thin cells — the very cells that make *p* unidentifiable.

That tension is the most useful thing this note produced, and it generalises: **on atlas data with a
well-atlassed footprint, a detection-corrected occupancy change and a naive reporting-rate change are
the same number.** The elaborate machinery earns its place on *sparse* data, and a footprint rule
strict enough to fit it is strict enough to make it unnecessary.

## The correction to §6, and what it cost

§6 says a species needs "thirty footprint cells in each epoch". Applied literally that selects on the
outcome: a species that declined has few epoch-2 detections *by definition*, so the rule removes
exactly the species with the largest real change.

Measured rather than argued. The literal rule would have dropped **37 species**, and their median
naive change is **−0.153** against **−0.014** across all species — an order of magnitude larger, and
all in one direction. The floor is therefore applied at **baseline only**, which asks "of the species
that were widespread in 1987-1991, what happened", and that is a question with an unbiased answer.

## What the species say

Median Δψ is −0.0071 over 512 species: no net change worth reporting as a headline. The tails are the
result.

| Largest declines | ψ₁ → ψ₂ | Δψ |
| --- | --- | --- |
| *Anthropoides paradiseus* — Blue Crane | 0.604 → 0.375 | −0.229 |
| *Chlidonias leucopterus* — White-winged Tern | 0.604 → 0.384 | −0.219 |
| *Ciconia nigra* — Black Stork | 0.726 → 0.526 | −0.200 |
| *Corvus capensis* — Cape Crow | 0.745 → 0.557 | −0.188 |
| *Calidris ferruginea* — Curlew Sandpiper | 0.518 → 0.340 | −0.178 |

| Largest increases | ψ₁ → ψ₂ | Δψ |
| --- | --- | --- |
| *Acridotheres tristis* — Common Myna | 0.363 → 0.655 | **+0.292** |
| *Falco peregrinus* — Peregrine Falcon | 0.236 → 0.482 | +0.247 |
| *Anastomus lamelligerus* — African Openbill | 0.115 → 0.322 | +0.207 |
| *Anas platyrhynchos* — Mallard | 0.082 → 0.288 | +0.206 |
| *Cypsiurus parvus* — African Palm Swift | 0.517 → 0.694 | +0.176 |

**Face validity, offered as a check on the pipeline and not as a claim.** The two largest increases
are introduced species — the Common Myna and the Mallard are both established invaders in southern
Africa — and the third is a peregrine, recovering as it has on every continent since organochlorine
pesticides were withdrawn. The largest decline is the Blue Crane, South Africa's national bird and
listed as threatened. A pipeline that put random species at these extremes would not produce that
pattern. Nothing here attributes any of it to a cause; that is `DATASETS.md` step 3 and a later note.

## The sensitivity window — run 2026-08-05

§4 registered a second choice of epoch 2, **2019-2023**, with §8 attaching a stop condition: if the
two windows disagree in sign for more than a third of species, the result is a property of the window
rather than of the birds, and the disagreement is the finding.

**Run as "the same comparison", which means the footprint too.** The footprint is a function of the
epoch-2 window — cells need 20 cards *in both epochs* — so holding the 2008-2012 footprint fixed while
changing the data inside it would test something other than the window. `footprint()` takes the window
for that reason.

| | primary 2008-2012 | sensitivity 2019-2023 |
| --- | --- | --- |
| reportable species | 512 | 521 |
| species in both runs | | **510** |
| median Δψ | −0.0071 | +0.0028 |

**The stop condition does not fire.**

- Sign disagreement over all 510 shared species: **19.6%** (100 species).
- Among the 409 that moved by more than 0.02 under either window: **14.4%** (59). A species at −0.001
  under one window and +0.001 under the other has not flipped, it has no change under either, and
  counting it as a disagreement would inflate the figure with noise.
- Correlation of Δψ between the two windows: **0.852**.
- Median absolute difference between the two estimates: **0.0200**.

Both figures are comfortably under the registered third. The comparison is not an artefact of which
five years of SABAP2 are chosen.

**The median flips sign and that is not a contradiction.** −0.0071 against +0.0028: both are within
0.008 of zero, which is the same statement as "no net change" made twice. What would have mattered is
a median that moved by something like the spread, and it does not.

**Nine of the ten tails hold; one does not.**

| | primary | sensitivity | |
| --- | --- | --- | --- |
| *Chlidonias leucopterus* — White-winged Tern | −0.219 | −0.219 | holds exactly |
| *Ciconia nigra* — Black Stork | −0.200 | −0.291 | stronger |
| *Calidris ferruginea* — Curlew Sandpiper | −0.178 | −0.225 | stronger |
| *Corvus capensis* — Cape Crow | −0.188 | −0.202 | holds |
| *Anthropoides paradiseus* — Blue Crane | −0.229 | −0.126 | same sign, weaker |
| *Acridotheres tristis* — Common Myna | +0.292 | +0.341 | stronger |
| *Falco peregrinus* — Peregrine Falcon | +0.247 | +0.320 | stronger |
| *Cypsiurus parvus* — African Palm Swift | +0.176 | +0.280 | stronger |
| *Anas platyrhynchos* — Mallard | +0.206 | +0.122 | same sign, weaker |
| *Anastomus lamelligerus* — African Openbill | +0.207 | **−0.014** | **withdrawn** |

The African Openbill is the only species in either tail whose sign does not survive, and §4's rule is
explicit: a species that flips carries no result. It is withdrawn from any species-level claim rather
than reported with a caveat. The other nine are reported, and five of them are *larger* under the
window that was not used to choose them, which is the direction a real signal moves in and an artefact
does not.

Fourteen species flip sign while moving more than 0.05 under one of the windows; they are named in the
run output and each carries no result, by the same rule.

## What remains before this becomes a Finding

1. ~~The 2019-2023 sensitivity.~~ **Run, and passed.** See above.
2. **The claim to publish is the methodological one**, because that is where the evidence is: the
   correction and the naive comparison agree, with a stated reason. The species table is the exhibit
   underneath it, and it is honest as "of 512 species, no net change, and these are the tails".
3. **`coverage-bias` moves on its own** when this lands, because it recomputes from the lake on every
   build — which is the point of it being computed rather than typed.
