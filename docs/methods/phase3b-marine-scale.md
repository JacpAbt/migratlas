# Phase 3b — which seas are moving, and what separates the movers from the stayers?

**Status:** pre-registered 2026-08-19. Written before any trend has been fitted on the units this
note defines, before any driver has been paired with any response, and before any cross-unit
regression has been sketched against data. What *was* looked at first is in §1: the gear
structure of every survey, because Phase 3a's marine half died on gear changes and this design
exists to not die the same way.

## Why this note exists

`marine-null` said it in 2026-07: the pooled marine shift is ~zero *because* surveys disagree in
sign, and the disagreement is the interesting object. The owner's direction of 2026-08-18
promoted that heterogeneity from caveat to estimand. And Phase 3a's marine half added a hard
lesson the same day: a whole-record rule that excludes any gear-changed survey throws away most
of the record — 8 of 15 candidate units died on it — when the change is usually one refit with
decades of homogeneous record on either side.

## 1. What was looked at before this was written

Gear structure only — segments, counts, years. No trend, no driver, no response was computed.
Measured 2026-08-19 from the lake, per survey unit passing the footprint bar (29 in all):

- 19 units have ≥ 20 total years; only 13 of them are single-gear throughout — the whole-record
  rule's harvest.
- **17 units have a longest single-gear segment of ≥ 20 years** — the salvage this note is
  built on. NEUS-Fall alone recovers a 46-year homogeneous segment from a 57-year record that
  the whole-record rule discarded for two refits; SCS-SUMMER recovers 39 years, GSL-S 32,
  NEUS-Spring 27.
- Four units are genuinely unsalvageable at segment scale and are named now so nobody rescues
  them later: BITS-1 and BITS-4 alternate gears almost yearly (14 and 11 segments, longest 4
  years), WCTRI and Nor-BTS fragment likewise. They will be published as coverage, not fitted.

## 2. The unit: a survey's longest single-gear segment

One unit per survey: its **longest run of consecutive recorded years under one gear**, ties
broken toward the earlier segment, admitted when the segment has ≥ 20 years. Within a segment
there is no gear change by construction, so no break term, no dummy, and no level step wearing a
trend's clothes. The cost is stated plainly: a segment is shorter than its record, and years
outside it — including the most recent years of NEUS — go unused by this design.

## 3. Estimands

Per unit, over its segment only, all machinery already in the repository:

- **The movement**: the per-decade centroid-latitude trend, as `phase1b`/`metrics.range` compute
  it — per-species trends (≥ 15 years within the segment), summarised per unit by the median and
  its interval. No break term, because the segment needs none.
- **The warming**: the per-decade trend in the unit's own in-situ haul temperatures (surface;
  bottom where recorded) over the same segment years — the water the fish were in, not a
  reanalysis of it.
- **The setting**: the unit's median haul depth, fixed over the segment.

Across units, one registered regression: latitude trend on temperature trend, with a
temperature-trend × depth interaction, weighted by the inverse variance of each unit's latitude
trend. Two slopes and an intercept; nothing enters after this line.

**On climate velocity.** The TASKS sketch named gradient-based local climate velocity as the
driver. This registration deliberately uses the in-situ temperature *trend* instead: it is
already in the lake at the haul, it beats any gridded product on the shelf, and a
gradient-based velocity needs OISST fields this project has verified but not ingested.
Velocity is an extension this note does not license — if it comes, it comes with its own note.

## 4. Predictions

1. **The heterogeneity is real, not sampling noise.** A Cochran-style Q across the units'
   latitude trends exceeds its 95th percentile under the hypothesis of one common trend. If
   this fails, `marine-null`'s "different seas doing different things" was overread from
   noisy per-survey estimates, and that correction gets published against the finding itself.
2. **Warming water, moving fish.** The cross-unit slope of latitude trend on in-situ
   temperature trend is positive: units whose water warmed faster shifted poleward faster.
   The literature expects this; `marine-null` suggests it is not guaranteed here.
3. **Shallow forces horizontal.** The temperature × depth interaction is negative: the same
   warming moves fish further, in latitude, where the water is shallow — a deep basin offers a
   vertical escape this design cannot see directly, and says so.
4. **The salvage is worth its cost.** At least 15 units enter the fit (against Phase 3a's 7),
   and the four fragmented surveys are published as coverage rows beside them.

## 5. Stop conditions

- Fewer than 12 units with a qualifying segment *and* a temperature series → the whole phase
  publishes as a coverage statement and the cross-unit regression is not run.
- Prediction 1 failing does not stop the phase — it *is* a result, and among the most
  publishable this design could produce.
- No unit's segment definition is revisited after any trend is seen.

## 6. What this cannot establish

Causality (warming and shifting could share an unmeasured driver; the design is correlational
across ~17 units); species-level stories (the unit is the survey-segment, deliberately);
anything about vertical movement (depth centroids exist in the machinery but this registration
binds only the latitude estimand — a depth companion would be its own note); anything about the
four fragmented surveys, whose absence is a statement about their sampling, not their fish.

---

## Results — run 2026-08-19

**The stop condition fired, and the bottleneck moved.** The gear salvage did what §1 measured
it would: seventeen surveys hold a qualifying single-gear segment. But the registration's
driver requirement — twenty years of the survey's own in-situ surface temperature *inside the
segment* — cut those seventeen to **ten**: NS-IBTS-1, NEUS-Fall, NEUS-Spring, SCS-SUMMER, EBS,
GMEX-Summer, GMEX-Fall and the three SEUS seasons. The European units mostly measure fish
without recording the water (GSL, SWC-IBTS, NS-IBTS-3, SP-NORTH, EVHOE all fell here, not on
gear). Ten is below §5's floor of twelve, so **the regression was not run and this phase
publishes as a coverage statement**, exactly as registered.

- **Predictions 1–3 — UNGRADEABLE**, by the stop condition's own design: no regression ran,
  so no heterogeneity test, no warming slope, no depth interaction was ever computed. The
  per-unit estimands above were logged in passing and are not interpreted.
- **Prediction 4 — GRADED FALSE.** Ten units entered, against the predicted fifteen. The
  salvage beat Phase 3a's seven, but the prediction bound to the wrong bottleneck: gear was
  solved, temperature coverage was not.

**What this licenses next, and what it does not.** The path this note explicitly reserved —
gridded SST (OISST, verified no-auth, 1981–present) sampled over each survey's footprint as
the warming driver — would restore most of the temperature-poor units, at the cost this note
named: a reanalysis of the shelf instead of the water the fish were in. That trade now has a
measured price (seven units) and belongs to its own registration, written like this one,
before any pairing is looked at. Nothing in this run is carried over as a prior.
