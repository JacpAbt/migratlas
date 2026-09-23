# Phase 2i — is the radar's residual in the front's speed, or in the departure?

**Status: pre-registered 2026-09-13, before any latitude gradient of passage date has been fitted in
this repository.** No front speed exists anywhere here; no passage date has ever been regressed on
latitude within a year; the ratio of a front's speed to the flight speed measured inside it has
never been formed. What *was* looked at is in §1, and all of it is published. A coverage audit ran
before this note and is in §2's floors: it counted stations, years and night lengths, and did not
fit the estimand.

#86, and the second of the three tests ADR 0019 registers. A passage date at a station is a
**transit** observation whose cause sits upstream in a **residence** phase: it is the departure date
plus the time spent getting there, and that time is itself flying and stopping over in alternation.
Every driver ever fitted to this record was a residence-side driver, so the unexplained half of the
advance has never had a transit-side candidate to reject.

---

**Which leg of the spine this bears on.** Claim 4 directly — the residual and the 2012 step — and
claim 1, whose first leg is a transit date sharing a heading with an emergence date and a bloom
date. If the residual and the step are transit-side, claim 1's legs are three different quantities
and the book cannot call them one thing. If they are departure-side, claim 1's radar leg is a
transition and claim 4's residual is still unexplained but is at least located.

---

## 1. What was looked at before this was written

- **Phase 2a** fits, per station, `passage_date ~ 1 + pre_season_temperature + wind_support +
  post_2012`, and publishes `S = −0.66 ± 0.17` d/°C (−0.62 ± 0.18 with a year term) over 78 stations
  in the 37–50°N claim band, 1995–2025, with temperature explaining 51–54% of the advance.
- **Phase 2c** reports the residual with every arm: under arm B it is **−0.272 d/decade**, about
  half the advance, and named nowhere on purpose.
- **Phase 1a** found a step at the dual-polarisation upgrade. **Phase 1c** measured it at
  **+1.41 ± 0.66 d** in autumn and established that it is **latitude-graded**: **+2.16 d at 24–32°N
  against +0.01 d at 42–50°N**, correlation with latitude −0.23 across 142 stations. It tested and
  rejected four mechanisms — window truncation, panel composition, curvature, and precipitation
  screening — the last with demonstrated power, because the same test detects the coupling in
  spring at +0.26.
- **Phase 1c** also measured airspeed as `|radar velocity − NARR 925 hPa wind|` over 901,083
  station-nights and found its trend **flat**, which is what the `composition-stable` finding
  rests on and what licenses treating this mixture as one thing across the record.
- **Phase 2f** added summer rain and spring green-up to the radar's timing and found neither moves
  more stations than chance; the full model predicts a held-out year 7.5% *worse* than temperature
  alone.

**Not looked at, anywhere:** the latitude gradient of passage date within a year. Phase 1c computed
the *step's* correlation with latitude across stations, which is a different quantity — a property
of one break, not a per-year series — and it did so to test a mechanism rather than to measure a
speed. The front's speed, the flight speed inside it, and the ratio of the two do not exist in this
repository.

---

## 2. Estimand and unit, with the known problems first

**The unit is a year.** Within each year, across a fixed panel of stations, fit

```
q50_doy ~ 1 + (latitude − L̄)
```

giving an intercept `a(Y)` — the median passage date at the panel's mean latitude — and a slope
`b(Y)` in **days per degree**. In autumn the birds move south, so `b` is negative and `|b|` is the
time the median-passage isochrone takes to cross one degree.

**Three estimands.**

- **A — the front's speed.** `111.19 / |b(Y)|` km per day, the speed of the median-passage
  isochrone.
- **B — the flight speed.** Traffic-weighted airspeed over the same stations and window, m/s,
  through `phase1c`'s own path so it is the published quantity and not a second copy of it.
- **C — the duty cycle.** `front_km_per_day / (flight_km_per_hour × night_hours)`, dimensionless,
  where `night_hours` is the traffic-weighted mean `integration_hours` of the night window. One
  means flying every available hour of every night; a tenth means the front advances as if the
  birds flew one hour in ten. **This is the residence share of transit and it is the number ADR
  0019 asks for.**

**What the decomposition can and cannot say, stated before it is run.** The band-average trend in
passage date is `da/dY` *by construction*, and the slope trend `db/dY` contributes zero at the mean
latitude. So this design does **not** partition the published −0.272 d/decade into two shares. What
it does is sharper and narrower: the residual's *band average* is a departure-side quantity, and
everything **latitude-graded** — including the 2012 step's +2.16 d against +0.01 d — is transit-side.
The test is therefore whether a latitude-graded trend and a latitude-graded step exist in `b(Y)`,
and whether their size matches what the published step gradient implies.

### Known problems, stated before any number is seen

- **An isochrone is not a cohort, and this is the deepest problem.** The gradient compares different
  stations in the same year, not one group of birds tracked down a flyway. A station at 32°N and one
  at 48°N may see different species in different proportions, and a systematic latitudinal change in
  the mixture would produce a gradient with no bird having travelled. `composition-stable` says the
  mixture did not drift *in time*; it says nothing about its drift *in space*. **Estimand A is
  therefore the speed of a statistical front and is only an animal's speed under an assumption this
  design cannot test.**
- **Latitude-only distance understates the path.** These migrants move south-south-west, so one
  degree of latitude is less than the distance flown. Estimand A is a **lower bound** on the front's
  ground distance per day, and therefore estimand C is a **lower bound** on the duty cycle.
- **The instrument confound cannot be controlled by upgrade date.** `phase1_robustness` records that
  the per-station dual-polarisation dates are not in the lake, which is why a common 2012 break is
  used. A rollout whose order happened to correlate with latitude would produce a latitude-graded
  step with no bird changing anything. The spring control in prediction 6 is the only discriminator
  available and its weakness is named there.
- **Panel composition changes.** The network runs 104 stations in 1995 and 159 by 2017, and a
  gradient fitted on a changing panel is partly a gradient in which stations exist. Fixed by
  restricting to stations present in **every** year, as Phase 1c fixed its own panel.
- **The taxon is unattributed.** This is the aerial mixture, and no species-level statement is
  available from it — which is why claim 3's animal-specific result has no radar instance.
- **Nothing causal.** A correlate of a date at a place, as always.

**Floors and panels, from the coverage audit and the parent phases.** Primary band **30–50°N**, the
fixed panel of **77** stations present in all 31 years; the registered secondary is Phase 2a's own
claim band **37–50°N**, fixed panel of **50** stations, for comparability with the published `S`.
24–30°N is excluded because no published claim covers it. Nights are `window_kind == "night"`,
`quantity == "reflectivity_traffic"`, coverage at or above Phase 1's floor, the autumn window as
`AUTUMN`, and `q50_doy` through `passage_quantiles` as Phase 2a computes it. `SEED = 1`, 1,000
bootstrap draws, years resampled whole.

---

## 3. The design, fixed before any number is seen

1. **Panel.** `phase2a_timing.panel()` for the station-year passage dates and latitudes; restrict to
   the band and to stations present in every year.
2. **Per year**, least squares of `q50_doy` on centred latitude → `a(Y)`, `b(Y)`, each with a
   standard error. A year with fewer than 20 panel stations is dropped and reported.
3. **Front speed** `111.19 / |b(Y)|` km/day; **flight speed** from `phase1c._airspeed_nights` and
   `_per_station_year` restricted to the same stations and window; **duty cycle** as §2 defines it.
4. **Trends.** `a(Y)` and `b(Y)` each regressed on year with a break at `FLEET_MIDPOINT_YEAR`, the
   same specification Phase 1c uses, giving a per-decade trend and a 2012 step for each.
5. **The step's consistency check.** The fitted step in `b` implies a step in passage date at any
   latitude, as `Δb × (L − L̄)`. Evaluated at 28°N and at 46°N, this must reproduce the published
   +2.16 d and +0.01 d to within their stated errors, or the transit reading is not consistent with
   the measurement it claims to explain.
6. **The spring control.** The same `b(Y)` fitted in `SPRING`. Birds move north in spring, so a
   transit-side step must reverse the sign of its latitude gradient; an instrument artefact cannot
   know which way the birds are flying.
7. **Intervals** by year-resampling bootstrap; **robustness** by leave-one-station-out on the panel
   and by refitting on the 37–50°N arm.

---

## 4. Predictions

1. **Coverage and calibration.** Both panels are complete for 31 years, and the airspeed level
   reproduces Phase 1c's published traffic-weighted mean. *Check.*
2. **The front is far slower than the birds.** The duty cycle is below 0.25 — the front advances as
   if the birds flew under a quarter of the available darkness. *Discovery, registered as expected
   on the stopover literature: a nocturnal migrant spends most of its migration on the ground.*
3. **The front's speed changed.** `b(Y)` has a per-decade trend whose bootstrap interval excludes
   zero. *Registered as the expectation*, because it is the only reading that reconciles two
   measured facts — Phase 1c's flat airspeed and Phase 1c's latitude-graded step — and it makes the
   duty cycle, not the flight speed, the thing that moved.
4. **The 2012 step is in the slope.** The break in `b(Y)` at 2012 has an interval excluding zero.
   *Discovery, and the direct statement of the step's latitude grading.*
5. **The step's size is consistent.** The step in `b` evaluated at 28°N and 46°N reproduces +2.16 d
   and +0.01 d within their errors. *Check on the transit reading itself; failing it means the
   gradient in `b` is not the gradient Phase 1c measured.*
6. **The spring gradient does not carry the same step with the same sign.** *Control.* Its known
   weakness: Phase 1c's spring step is −0.68 ± 0.76 d and covers zero, and its latitude correlation
   is −0.08, so spring may have no step to grade. A spring step **matching autumn's in sign and
   size** is the informative failure and points at a latitude-correlated instrument artefact; a
   spring step indistinguishable from zero is uninformative and will be reported as such rather
   than as support.
7. **The front-speed trend survives its robustness arms.** The sign of `db/dY` holds under
   leave-one-station-out and on the 37–50°N panel. *Check.*

---

## 5. Stop conditions

- **Prediction 1 fails** → nothing above it is interpreted.
- **Prediction 3 fails and prediction 4 fails** → the front's speed did not change and the step is
  not in it. The residual and the step are then **departure-side or instrumental**, claim 4 gains
  *not the front's speed* as a named null, and claim 1's radar leg is recorded as a transition
  rather than a transit — which settles the book's first chapter the other way.
- **Prediction 3 or 4 holds and prediction 5 fails** → a gradient exists but is not the one Phase 1c
  measured; nothing is claimed about the step and the discrepancy is the result.
- **Predictions 3, 4 and 5 hold and 6 does not fire** → **claim 4's residual gains its first
  transit-side component**, claim 1's radar leg is named a transit date distinct from claim 1's
  other two legs, and `earlier-passage`'s caveat gains one computed sentence carrying the duty
  cycle. The book's first chapter splits.
- **Prediction 6 fires** (spring step matches autumn's in sign and size) → the latitude grading is
  attributed to neither transit nor departure, and the note reports an instrument confound that four
  earlier mechanisms did not reach.
- **Prediction 2 alone** changes no claim; it is the state-split number ADR 0019 asked for and it
  is published whatever the rest does.
- No band, panel, floor, window or bar is revisited after any number is seen.

---

## 6. What this cannot establish

- **Not causation**, and not a mechanism for any change in the duty cycle: weather on the flyway,
  habitat at stopover sites, and the mixture's composition all survive every fit here.
- **Not an animal's speed.** The front is statistical; §2's first known problem is the reason.
- **Not the stopover duration of any individual.** The duty cycle is an aggregate ratio, and the
  record that would give durations per individual — automated telemetry — is not in this lake and
  did not meet the access bar in ADR 0019.
- **Not spring.** Spring enters only as a control on the step, and this note makes no spring claim.
- **Not the other realms**, and not the southern hemisphere.
- **Not a species.** The radar's taxon scope is unattributed.

---

# Results — run 2026-09-13

`make report-phase2i`, run as a pair. The two runs were identical line for line.

**Calibration — PASS, exactly.** The traffic-weighted autumn airspeed is **8.651 m/s** against Phase
1c's published **8.65 m/s**, through Phase 1c's own path.

## The panels

| band | stations in every year | years | mean latitude |
| --- | --- | --- | --- |
| 30–50°N (primary) | **46** | 31 | 39.09 |
| 37–50°N (claim band) | **33** | 31 | 41.31 |

The coverage audit counted 77 and 50 stations with traffic in every year; the passage panel is
smaller because `phase2a_timing.panel()` also requires a passage quantile above the night floor and
an inner join to temperature and wind. **The panel is 46 of 145 stations and they are survivors** —
every number below is on that panel, and the discrepancy in §"What does not reconcile" is the reason
to say so twice.

## The front, the flight and the night

| band | front | flight | night | duty cycle |
| --- | --- | --- | --- | --- |
| 30–50°N | **101 km/day** | 32.1 km/h | 12.1 h | **0.260** |
| 37–50°N | 94 km/day | 33.6 km/h | 12.0 h | 0.233 |

**The median-passage isochrone crosses the band at about 100 km a day while the birds inside it fly
at about 32 km an hour.** A night of sustained flight would carry them close to 390 km. They advance
a quarter of that. This is the state-split number ADR 0019 asked of the aerial record, and it is
published whatever the rest of this note says: **three quarters of the autumn passage period is not
spent moving the front forward**, and that is a lower bound, because a south-south-west heading
covers more ground than a degree of latitude counts.

## The gradients

| band | slope trend, d/°/decade | 2012 step in slope | intercept trend, d/decade | 2012 step in intercept |
| --- | --- | --- | --- | --- |
| 30–50°N | +0.0726 [−0.0561, +0.1972] | −0.2168 [−0.4163, +0.0312] | **−1.432 [−2.616, −0.219]** | **+1.879** |
| 37–50°N | −0.0485 [−0.2822, +0.2256] | −0.0207 [−0.4178, +0.4129] | −1.179 [−2.450, +0.340] | +1.240 |

## The answer

**The front's speed did not change, and the 2012 step is not in it.** Both intervals cover zero in
both bands, and the slope's trend does not even hold its sign between them (+0.0726 against
−0.0485). The registered expectation — that the duty cycle moved while the flight speed did not —
**failed**.

**The step is in the intercept, where a departure change or an instrument lives.** The intercept's
2012 step is **+1.879 d** on the primary band, consistent with Phase 1c's published mean autumn step
of **+1.41 ± 0.66 d**; the slope's step covers zero. A step that sits in the level and not in the
gradient is latitude-flat, which is what a departure-side change or a fleet-wide instrument change
looks like and is not what an accumulating travel time looks like.

**So claim 4's residual gains a named null, and claim 1's radar leg gains a name.** The residual and
the step are **not the front's speed**. The radar's passage date is a **transition** — a departure
timing observation seen downstream — rather than a transit quantity, which means claim 1's three
legs are three transition dates and not a mixture of transit, emergence and bloom. **The book's
first chapter does not split.**

## The predictions, graded

**1 — TRUE** (check). Both panels complete for 31 years; airspeed 8.651 against 8.65.

**2 — FALSE**, by 0.010. The duty cycle is **0.260** on the primary band against a registered bar of
0.25, and 0.233 on the claim band. The substance and the threshold disagree and the threshold is
what was registered: the front does advance as if the birds flew only a quarter of the darkness, and
it is *not* below the number this note wrote down beforehand. Recorded as a miss, not as a pass with
an excuse.

**3 — FALSE.** +0.0726 d/°/decade, [−0.0561, +0.1972].

**4 — FALSE.** −0.2168 d/°, [−0.4163, +0.0312].

**5 — FALSE, and informatively.** The slope's step implies **+2.40 d at 28°N against a published
+2.16** — close — and **−1.50 d at 46°N against a published +0.01** — not close at all. A straight
line through the southern point overshoots the northern one, which says **the step's latitude
pattern is not linear**: it is concentrated in the south and flat above the middle latitudes, and
this design assumed a gradient. The failure is the design's, and it is the most useful thing in the
run.

**6 — not fired, and uninformative as registered** — with a warning. The spring slope's 2012 step is
**−0.2125 [−0.5131, +0.0920]**, which covers zero, so the control cannot be called. But its point
estimate is the same sign and within 0.005 of autumn's **−0.2168**. That near-identity is the
pattern prediction 6 was written to catch — a latitude-correlated artefact common to both seasons,
which no bird can produce — and this run has neither the precision to call it nor the right to
ignore it. **Any future transit reading of the autumn step has to clear this first.**

**7 — FALSE.** The slope's trend reverses sign between the two bands. Both cover zero, so it is the
sign of nothing, and it is graded false rather than waved through.

Two of seven. The five failures include the registered expectation, and the note is more useful for
it than it would have been had the expectation held.

## What does not reconcile, stated rather than buried

**The intercept's trend is about twice the published advance.** This panel gives **−1.432 d/decade**
[−2.616, −0.219] at 39.09°N, where Phase 2a publishes an observed advance of **0.6–0.7 days per
decade**. This note did not register a calibration against the passage trend — only against the
airspeed — and it should have. Three candidates, none tested here: the panel is 46 survivors of 145
rather than Phase 2a's 78; the primary band reaches to 30°N where the step is largest, and the
intercept sits at 39.09°N rather than in the claim band; and a +1.879 d step in the middle of a
declining series steepens the line fitted through it. **The nulls above are nulls on this panel**,
and a successor that cannot reproduce Phase 2a's advance on it should not be trusted with its
gradient either. This is the first thing to fix.

## What the successor has to fix

1. **Reconcile the intercept trend with Phase 2a's published advance**, or explain the panel
   difference that makes it irreducible. Nothing else here is safe until that is settled.
2. **Fit the step per latitude bin rather than as a linear gradient.** Prediction 5 failed because
   the pattern is not a line, and Phase 1c's own numbers (+2.16 at 24–32°N, +0.01 at 42–50°N) are
   bins, not a slope.
3. **The spring coincidence.** Two seasons whose slope steps agree to 0.005 and both cover zero
   need either a longer record or a per-station estimator before either can be read.
4. **A path length rather than a latitude.** The front's speed is a lower bound because these
   migrants head south-south-west. The radar's own `direction_deg` gives a heading, and projecting
   the gradient onto it is a better distance.

## What this does not establish

- **Not causation**, and no mechanism for the duty cycle.
- **Not an animal's speed.** The front is statistical, and §2's first known problem stands.
- **Not that the residual is departure timing.** It says the residual is *not the front's speed*.
  Latitude-flat covers departure timing and a fleet-wide instrument change alike, and this design
  cannot separate those two.
- **Not a stopover duration.** The duty cycle is an aggregate ratio.
- **Not spring**, which entered only as a control.
- **Not a species.** The radar's taxon scope is unattributed.
