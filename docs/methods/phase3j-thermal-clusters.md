# Phase 3j — is the marine null a mixture? Clusters by thermal exposure, not by taxon or by ocean

**Status: pre-registered 2026-09-01, before any cluster has been formed.** No pair has been assigned
to any group, no cluster median exists in this repository, no coherence has been computed on any
axis, and the pair-level thermal position has never been joined to a pair-level latitude trend. What
*was* looked at is in §1 and it is a great deal, because everything this note is built on is
published.

---

## Why this note exists

The owner's direction of 2026-09-01, and it names a failure mode this project has demonstrated twice:

> a problem we found is to treat the data as too in detail (by single species) or too in general
> (birds as a whole) … remember to check also clusters of data, as temperature or wind or whatever
> might have hit some and not others, and so would still be relevant

Two published results say the same thing from opposite ends. **One species is too noisy**: Phase 1l
measured a median species trend at 1.69 standard errors from zero, short of the two a single estimate
needs. **A whole network is a mixture**: Phase 1k's medians summarise species that do not share a
direction, and Phase 1l showed that comparing two such mixtures produced its own misleading 3× gap.

And the marine record is where the cost is largest. `marine-null` publishes a median of
**−0.011 °latitude per decade across 2,240 species-survey pairs** with an interquartile range
spanning zero, and Phase 3e has now established that the units behind it disagree emphatically —
**Cochran's Q 235.7 against a bar of 27.6** — while the thermometer does not sort them:
`+0.039 ± 0.179 °lat per °C`, graded false against its own registered prediction.

**That null is an average over things that disagree, and this note is the first test of whether it is
a mixture.** A warming that moved a third of the pairs and left the rest alone produces exactly the
number the ledger publishes. Phase 3e could not see it: its unit is the survey, and a linear
interaction with depth was the only within-unit structure it was allowed to look for.

## What this is *not*, and Phase 1m is why

Phase 1m grouped species by where they live and how widely they are spread, and its stop condition
fired: the group signal rose from 1.69 to 5.70 while the noise-corrected coherence cleared its floor
in one network of three. Its own conclusion is the warning this note inherits:

> Averaging seventeen species raises the signal by roughly the square root of seventeen whether or
> not those species belong together … a group signal of 5.70 beside an ICC of 0.08 does not mean the
> grouping worked; it means the groups are precise measurements of aggregates that are mostly
> arbitrary.

So **the primary quantity here is coherence, not signal**, and the floor is Phase 1m's registered
0.10 so the two phases are comparable. A cluster median with a tight interval proves nothing.

Two differences from Phase 1m, and they are the reason this is worth running rather than a repeat:

- **The axes are environmental rather than descriptive.** Phase 1m grouped on where an animal is;
  this groups on *what happened to it* — how warm its water is, how fast that water warmed, how deep
  it lives. The owner's phrasing is the hypothesis: a driver that hit some and not others.
- **One axis varies inside a survey.** A species' own occupied temperature differs between species in
  the same trawl, so that axis is not confounded with which survey contributed most pairs. The two
  survey-level axes are, and §2 states what that costs.

---

## 1. What was looked at before this was written

All published, all read off the notes rather than recomputed:

| what | value | where |
| --- | --- | --- |
| pooled pair-level latitude shift | median −0.011 °lat/decade, 2,240 pairs, 48% poleward | `marine-null` |
| unit-level heterogeneity | Q 235.7 against 27.6, 18 units, survives leave-one-out | Phase 3e + ADR 0016 |
| warming against movement, per unit | `+0.039 ± 0.179` °lat per °C | Phase 3e prediction 3 |
| warming × depth, linear | `+0.176 ± 0.131`, sign reversed against registration | Phase 3e prediction 4 |
| species-level thermal tracking | median index +0.06, 33% tracking, 27% into warmer water | `phase2a-thermal.md` |
| a single species' precision | median trend 1.69 standard errors from zero | Phase 1l |
| coherence on free grouping axes | 0.186, 0.087, 0.076 against a floor of 0.10 | Phase 1m |

**What was not looked at:** any cluster of any kind on the marine pairs; any cluster median; any
coherence on any axis here; any join of a pair's thermal position to its latitude trend. Nothing in
§§2–6 was written with a number from this phase in front of it.

---

## 2. Estimand and units, with the known problems first

**The unit is the species-survey pair** — `marine-null`'s own unit, deliberately, so that the
question is about the published null rather than about a new quantity.

**The response is the pair's latitude trend per decade**, from `metrics/range.shift_per_decade` on
the consistent footprint, exactly as `marine-null` computes it. Not re-derived.

**The estimand is the spread between cluster medians**, and beside it the **noise-corrected
coherence** — between-cluster variance over total variance in the pair trends, with the estimation
error removed the way Phase 1l removed it. The spread says whether the clusters differ; the
coherence says whether the clustering means anything. Both are reported for every axis.

### The three axes, fixed here

Each is a property of temperature or of place. **None is a property of the response**, which is the
circularity Phase 1m named and Phase 3i refused: grouping on how much something moved and then
measuring how much the groups moved would be coherent by construction.

1. **Thermal position of the pair** — the species' CPUE-weighted mean occupied bottom temperature
   over the segment, from `phase2a_thermal`, expressed as a percentile *within its own survey* so a
   Baltic species and a Gulf species are compared on their own water. Terciles. **This is the
   pair-level axis and the one prediction 3 is about.**
2. **The survey's warming rate** — its OISST footprint trend, from Phase 3e. Terciles across surveys.
3. **The survey's median haul depth** — from Phase 3e. Terciles across surveys.

Terciles rather than deciles: Phase 1m used ten groups on hundreds of species; three axes over
~2,240 pairs but only ~29 surveys means the survey-level axes have about ten surveys per group, and
ten groups would leave three. Three is the count that keeps the survey-level axes readable at all,
and it is fixed here rather than chosen against a result.

### Known problems, before any fit

- **The two survey-level axes have the effective sample size of a survey count, not a pair count.**
  Every pair inside one survey shares that survey's warming and depth, so a naive interval over
  2,240 pairs would be wrong by a large and unmeasured factor. Both are reported with a **bootstrap
  clustered on the survey**, and prediction 5 measures the gap against the naive one. This is Phase
  1l's lesson — its own interval resamples units as if independent, and that is recorded there as
  owed work — applied in advance rather than discovered again.
- **Thermal position is available for far fewer pairs.** `phase2a-thermal.md` reports bottom
  temperature on 55% of survey rows and usable ambient warming in five surveys of twenty, and it
  excluded NEUS-Fall outright for a calendar drift of 5.1 days per decade. So axis 1 runs on a subset
  of a subset, and its unit count is a graded prediction rather than an assumption.
- **A tercile of occupied temperature is not a thermal limit.** The literature's quantity is distance
  to a species' thermal maximum, which needs a physiological or a global-range estimate this project
  does not hold. A within-survey percentile is a much weaker proxy and it is what the lake supports.
- **Warm-water surveys hit a ceiling.** `phase2a-thermal.md` flagged GMEX and SEUS: a species at its
  thermal maximum has nowhere warmer to be sampled, which truncates its occupied temperature from
  above. That biases axis 1's top tercile in a direction the note states and does not correct.
- **Three axes is three tests.** No axis is added after this line, and §5 says what a single clearing
  axis out of three is worth.
- **Nothing here is causal.** A cluster that moved more is a cluster that moved more.

---

## 3. The design, fixed before any fit

- **Calibration rung.** Pooling every pair with no clustering must reproduce `marine-null`'s median
  of **−0.011** to three significant figures, by calling `phase1b.analyse` itself rather than a copy
  of it — Phase 1k's arm A, for Phase 1k's reason. If it misses, nothing above it is interpreted.
- **Per axis:** assign each pair to a tercile, report each tercile's median trend, its interval, and
  its pair and survey counts; then the spread between the extreme terciles and the coherence.
- **The null for the spread.** Cluster labels are shuffled **within survey** for axis 1 and **across
  surveys** for axes 2 and 3, 1,000 draws, seeded by `crc32` of the axis name — so the shuffle breaks
  the alignment between cluster and response while preserving the structure the axis is built on. An
  axis's spread counts only past the 95th percentile of its own null.
- **Coherence** is computed as Phase 1l computes its split: total variance minus the mean squared
  standard error, so a between-cluster share is not inflated by estimation noise. `split_difference`
  is called, not reimplemented.
- **ADR 0016 applies to every cluster median**, and with terciles of ~29 surveys the survey-level
  axes are squarely inside its floor. A tercile median that does not survive dropping one survey is
  reported as not surviving.
- **Seed** `SEED = 1`, as Phase 1k and 1l.

---

## 4. Predictions

1. **The calibration reproduces `marine-null`'s median to three significant figures.**
2. **At least one axis's tercile spread clears its own null.** The registered form of "the null is a
   mixture". Graded false, the marine null is not a mixture along any axis this lake can define, and
   that is a stronger statement than the null itself.
3. **The thermal-position axis is the most coherent of the three.** It varies within survey, so it
   alone is not confounded with which survey contributed most pairs. Registered as the substantive
   expectation.
4. **The best axis's coherence exceeds 0.10**, Phase 1m's registered floor, inherited so the two
   realms are comparable. Registered as the prediction most likely to fail, on Phase 1m's evidence.
5. **A survey-clustered interval is at least twice a naive pair-level one** on the two survey-level
   axes. The measured price of treating 2,240 correlated pairs as independent.

---

## 5. Stop conditions

- **The calibration misses.** Stop; nothing above it is interpreted.
- **Prediction 2 false.** Publish as a null about clustering: the marine null survives being cut
  three ways by thermal exposure, and `marine-null` gains that sentence rather than a hedge.
- **Prediction 4 false while 2 holds.** Then the clusters differ and the grouping still explains
  almost nothing — Phase 1m's verdict in a second realm, and it publishes as that rather than as a
  discovery. **One axis clearing a null out of three, with coherence under the floor, is not a
  finding and this note will not report it as one.**
- **Axis 1 fits fewer than 300 pairs or fewer than 8 surveys.** It publishes as a coverage statement
  and prediction 3 is graded false rather than dropped.
- No axis, tercile count, null construction or floor is revisited after any cluster median is seen.

---

## 6. What this cannot establish

- **Not causation**, in any cluster. Every axis is an environmental property correlated with a great
  many others — fishing pressure, stratification, productivity, and the shape of the shelf.
- **Not that the right clustering has been found.** Three environmental axes is three, and the
  taxonomic version of this question is #66's rank ingest, which is a different note.
- **Not a species-level claim.** Phase 1l's 1.69 standard errors bind here too: no individual pair's
  trend is readable, which is the whole reason the unit of *reporting* is the cluster.
- **Not the ocean.** `marine-null`'s own scope, unchanged: continental-shelf trawl surveys of the
  North Atlantic and North Pacific, 0% southern hemisphere, bottom-dwelling fish where trawls can go.
- **Not timing.** A species that shifted its season rather than its position is invisible to this
  estimand, exactly as `MARINE_NULL_BIAS` already records.
- **Not a licence to project.** No axis here is forecastable, and a cluster is not a mechanism.

---

# Results — run 2026-09-01

`make report-phase3j`. Two consecutive runs are identical, checked before anything here was written
down, because Phase 3f's null was irreproducible and measuring twice is the only thing that found it.

**Calibration — PASS.** Pooling every pair with no clustering gives **−0.0110**, reproducing
`marine-null`'s −0.011 to three significant figures, by calling `phase1b.analyse` itself.

| axis | scale | pairs | surveys | low | mid | high | spread | null bar | | coherence | |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| thermal position | within survey | 1,722 | 17 | −0.0050 | −0.0316 | −0.0008 | **+0.0042** | 0.0275 | inside | **0.000** | below |
| warming rate | across surveys | 2,240 | 23 | −0.0178 | −0.0318 | +0.0406 | **+0.0584** | 0.1035 | inside | 0.031 | below |
| haul depth | across surveys | 2,170 | 22 | −0.0713 | +0.0330 | +0.0221 | **+0.0934** | 0.1030 | inside | 0.035 | below |

## The answer

**The marine null is not a mixture along any axis this lake can define.** No axis's tercile spread
beats its own null, and no axis's coherence comes near the floor. Cut three ways by thermal exposure,
`marine-null` stays what it was.

That is a stronger statement than the null it tests. The owner's question was whether a warming that
hit some units and not others could hide inside a flat median, and the honest answer is: not along
where a species sits in its own survey's water, not along how fast that water warmed, and not along
how deep it lives.

## The predictions, graded

**1 — TRUE.** The calibration reproduces −0.011 exactly, so the response is `marine-null`'s own and
not a second copy of it.

**2 — FALSE.** No axis's spread beats its own null. Depth comes closest and is still inside:
**+0.0934 against a bar of 0.1030**, which is 91% of the way there and the reason this note says
"not detected" rather than "absent".

**3 — FALSE, and backwards.** The thermal-position axis was registered as the substantive
expectation, on the argument that it is the only axis varying *within* a survey and so the only one
free of "which survey contributed most pairs". It is the **least** coherent of the three at **0.000**
— between-tercile variance is essentially nil. Within one trawl, where a species sits in its own
survey's temperature range tells you nothing whatever about how its centroid moved.

**4 — FALSE.** The best axis is depth at **0.035**, against Phase 1m's floor of 0.10. So this is
Phase 1m's verdict in a second realm: on the axes obtainable here, a cluster is a precise measurement
of a mixture.

**5 — TRUE, on both survey-level axes and on the third as well.** Clustering the bootstrap on surveys
rather than on pairs widens the interval by **3.1×** (warming), **3.0×** (depth) and **2.4×**
(thermal), against a registered bar of two. Every pair inside one survey shares that survey's water,
gear and footprint, and the price of ignoring that is now measured rather than argued.

## The stop condition, and what it does

§5 registered: *prediction 2 false → publish as a null about clustering: the marine null survives
being cut three ways by thermal exposure, and `marine-null` gains that sentence rather than a hedge.*

Applied. `marine-null`'s caveat now says the null was tested for mixture along three environmental
axes and survived, and `seas-disagree`'s caveat — which pointed at this note as unrun — says it ran.

**No new ledger entry.** §5 also pre-committed that one axis clearing a null out of three with
coherence under the floor is not a finding; zero axes clearing is not a finding either, and a
fourteenth entry saying "we looked and there was nothing" belongs inside the claim it qualifies
rather than beside it.

## Two things worth more than the gradings

**Prediction 5 is the transferable result, and it is the second time this week.** Phase 1k's leg 2
turned out to have an interval 4.5× too tight for the same reason — units treated as independent when
they are not — and here the marine pairs come in at 3×. Two of the ledger's medians have now been
measured on this and both were wrong in the direction that flatters. `atlas-no-net-change` is the
third built the same way and is still unchecked.

**And the thermal axis's exact zero is the sharpest single number here.** It is the axis the
registration argued hardest for, on a design argument that still looks right: it varies within a
survey, so it cannot be confounded with which survey contributed most pairs. It returned nothing at
all. Whatever sorts a moving species from a staying one inside one trawl, it is not where that
species sits in the water the trawl sampled.

## What this does not establish

- **Not that no clustering works.** Three environmental axes is three, and the taxonomic version —
  family, order, migratory strategy — is #66's rank ingest and a different note. Phase 1m ruled out
  the free taxonomic proxies; this rules out the free environmental ones.
- **Not that warming does nothing.** `seas-disagree` already carries the null at unit level and this
  adds that it does not hide in a subset along these axes. A driver acting through productivity,
  fishing pressure, stratification or oxygen is untouched by any of it.
- **Not the ocean.** `marine-null`'s scope, unchanged: northern shelf trawl surveys, bottom-dwelling
  fish, where trawls can go.
- **Not a thermal limit.** A within-survey percentile is a weak proxy for distance to a species'
  thermal maximum, as §2 said before the run. The registration's own caveat stands: the literature's
  quantity needs a physiological or global-range estimate this project does not hold, and a null
  against a weak proxy is a weaker null than one against the real thing.
