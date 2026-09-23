# Phase 2c — is the thermal sensitivity a response, or a co-trend?

**Status: pre-registered 2026-08-31, before any refit.** No sensitivity has been fitted at any
timescale, in any arm below, at any spatial scale. No detrended series exists in this repository, no
first-differenced series exists, and the regional response has never been fitted at all. What *was*
looked at is in §1 and it is one line of code and a great many published numbers, so this note
cannot claim innocence about the problem — only about the answer.

---

## Why this note exists

`phase2a-timing.md` publishes a response function, and `anthropogenic-share` rests on it:

```
S = -0.659 ± 0.165 days per °C     W = +0.518 ± 0.047 °C per decade
S x W = -0.301 ± 0.090             observed A = -0.559 ± 0.249
```

— from which the ledger publishes that about half the autumn advance tracks pre-season temperature,
and `phase2a-attribution.md` that essentially all of that half is anthropogenic.

The note states, as confound 3, that this is safe because *"`S` is fitted on year-to-year variation
rather than on the long-term slope."*

**That sentence is false, and a correction dated today records it in that note.** The design matrix
in `phase2a_timing.py` is `[1, temperature, wind_support, post_2012]`. There is no year term and
neither series is detrended, so `S` is a within-station slope over thirty-one years in which both the
response and the predictor trend. Where two series share a trend, a regression of one on the other
absorbs that shared trend into the coefficient — and `S x W` then partly reproduces `A` by
construction rather than by evidence.

The observed ratio is 0.54 rather than 1.0, so interannual variance does dominate and the
circularity is partial. **How partial has never been measured**, and five published products rest on
the answer: `anthropogenic-share`, the ATTRICI comparison, `transfer-fails`' aerial leg,
`reports/response.py`'s dial, and every row of Forecast A.

---

## 1. What was looked at before this was written

**The design matrix**, quoted above, and the correction it forces. That is the whole of the new
information: it says the question is worth asking and says nothing about the answer.

**Everything already published**, which is a great deal and constrains the design rather than the
result: `S`, `W`, `A` and their intervals; the 54% explained share; `f = 0.98` and ATTRICI's 37.5%;
Phase 3a's autumn median skill of `+0.005` with 20 of 143 stations above chance; Phase 3h's floor
diagnostic, which puts a station's passage date at **34%** explainable and a flyway-band region's at
**65%**; and Phase 3h's arm B median skill of `+0.0649` at eleven regions.

That last pair is why arm D exists rather than being a good idea for later.

**What was not looked at:** any sensitivity refitted under any specification; any detrended,
differenced or regionally pooled series; any residual trend; any explained share other than the
published one. Nothing in §§2–6 was written with a number from this phase in front of it.

---

## 2. Estimand and unit, with the known problems first

**The estimand is an interval on the explained share**, not a corrected point estimate. That is the
substantive decision in this note and the reason it is worth registering rather than just fixing.

Write the within-station model with a time trend in it:

```
passage(t)      = a + b·t + s·temperature(t) + (wind, break) + e
temperature(t)  = c + w·t + u
```

Then the observed trend decomposes exactly:

```
A  =  b  +  s x w
```

- **`s` estimated with the trend in the model** (arm B) is the response to a year-to-year departure.
  `s x W` is then the thermally-attributable part of the advance *under the assumption that `b`
  carries everything non-thermal*, and `b` is what is left over.
- **`s` estimated without it** (arm A, as published) absorbs `b` in proportion to how much of each
  series is trend, and over-attributes.

**And the two cannot be separated on this record.** A response that acts on the secular timescale and
a non-thermal process that happens to trend the same way are the same column of the design matrix.
One realised series, one region, thirty-one years: this is not a limitation of the estimator, it is
unidentifiability, and no arm below repairs it. So the honest output is **an interval whose ends are
the two specifications**, published with the reason it cannot be narrowed. A single number in that
interval would be a choice presented as a measurement.

**Unit: the station-season**, the 78 stations at 37–50°N where `S` is published, autumn only. Arm D's
unit is the flyway-band region and is a *cross-check* rather than a rung — see §3.

### Known problems, before any fit

- **The 2012 step is inside every arm.** Phase 1c tested four explanations and all four failed. Every
  arm carries the same `post_2012` term the published fit carries, so the step is held constant
  across the ladder and none of these numbers resolves it. A coefficient conditioned on an
  unexplained step inherits the mystery, and that is unchanged from `phase2a-timing.md`.
- **A year term costs a degree of freedom where they are scarce.** Stations carry 15 to 31 usable
  autumns against four columns; adding a fifth is affordable and not free, and it will widen every
  interval. A wider interval on arm B is expected and is not evidence about `s`.
- **First differences amplify measurement error, and the target is mostly error.** Phase 3h measured
  a station's passage date at 34% explainable. Differencing doubles the noise variance while removing
  the trend, so arm C is registered as the noisiest arm and as a sensitivity. If it comes back wide
  and null that is a statement about the filter, not about the animals.
- **Arm D changes two things at once.** It pools the response *and* uses the interannual
  specification, so the difference between arm D and arm B is not attributable to either. It is in
  the design because Phase 3h showed the per-station target is two-thirds noise, and a null at a
  station is uninformative about a null at a region — not because a two-step rung is good practice.
  Phase 3h's own instruction was one change per rung, and this note declares the violation rather
  than dressing it as a rung.
- **`W` is not refitted.** The warming trend is a secular quantity and no arm touches it; it is read
  from the published function, so the ledger and this note cannot disagree about it.
- **Every arm is observational.** A confounder common to temperature and passage date survives all
  four, exactly as `phase2a-attribution.md` says of itself.

---

## 3. The design, fixed before any fit

| arm | specification | unit | what it is for |
| --- | --- | --- | --- |
| **A** | `[1, temp, wind, post_2012]` — the published fit, unchanged | 78 stations | **calibration.** Must reproduce `-0.659` to three significant figures |
| **B** | `+ year` | 78 stations | the interannual response, and the note's primary |
| **C** | first differences of response and every covariate | 78 stations | a stricter high-pass, registered sensitivity |
| **D** | arm B's specification | 11 flyway-band regions | the same question where the target is 65% signal rather than 34% |

Everything else is inherited unchanged from `phase2a_timing.sensitivities()`: the response
(`q50_doy`, same filters), the pre-season window (June–July mean 2 m temperature), the wind-support
co-predictor, the break term, the per-station fit followed by a cross-station mean, and the band.

Arm D's regions are `phase1.FLYWAYS` crossed with `phase1.LATITUDE_BANDS`, restricted to the bands
inside 37–50°N, with the response and every covariate averaged unweighted across member stations —
Phase 3h's own construction, called rather than reimplemented, for the reason its arm A existed.

**The explained share is computed for arms A and B and reported as a pair.** Arm C and arm D report
their own `s` and their own share, and neither may replace the pair: C is a sensitivity and D is a
cross-check at a different unit.

**The residual `b` is reported with every arm**, because `A = b + s x W` is the whole argument and a
share published without its remainder invites the reader to invent one.

### Calibration, on a deterministic quantity

Arm A must return `S = -0.659` to three significant figures on 78 stations. A mean of per-station
slopes involves no seed, so unlike Phase 3f's calibration this one cannot be flipped by one
borderline unit — the lesson Phase 3f recorded and Phase 3h applied.

### Fixed before any number is seen

The four arms, the band, the window, the covariate list, the break term, the region construction, and
that the deliverable is an interval rather than a point. Nothing joins this list after this line.

---

## 3a. Amendments, written while implementing and before the registered run

Five things §3 under-specified. All five were settled before any arm was fitted — no sensitivity
existed at any timescale when these were written — and each would otherwise have been a silent
choice inside the code.

**A. Arm C differences consecutive years only.** §3 says "first differences of response and every
covariate" and does not say what to do about a gap. A difference across a missing year spans more
than a year and is not a first difference, so only steps of exactly one year are used. The break
dummy differences to a **spike at the transition year**, which is the correct differenced analogue
of a level shift, and it is kept rather than dropped.

**B. Arm C's floor is one fewer than the other arms'.** A unit with *n* observations has at most
*n − 1* usable differences, so applying `MIN_YEARS` to differences would exclude units the other
arms admit and turn the ladder into a comparison of panels. The floor is `MIN_YEARS − 1` usable
differences, which is the natural analogue.

**C. Arm D's regions are `response_floor`'s, and the band is applied first.** The assignment is
`region_of` and the four-station floor is `MIN_STATIONS`, both called rather than reimplemented, for
the reason Phase 1k's calibration arms call the published reports. The panel is restricted to the
claim band *before* regions are formed, so a region cannot be built partly out of stations no claim
covers. Regions under the floor are logged by name.

**D. `W` and `A` come from the raw series in every arm.** §2 says `W` is not refitted; this makes it
explicit for `A` as well. Both secular quantities are fitted once per unit on the undifferenced,
untrended series and reused across arms, so the arms differ in exactly one thing — how `s` is
estimated — and their shares are therefore comparable. A test pins it.

**E. The panel was extracted from `phase2a_timing.sensitivities()` as a pure refactor.** Arm A has to
reproduce the published `S`, and the surest way is for the published fit and arm A to consume one
panel rather than two copies of one. `panel()` now carries station longitude, which arm D needs and
which nothing in `phase2a_timing` reads. `sensitivities()` is otherwise untouched, and prediction 1
is the check that the refactor changed nothing.

---

## 4. Predictions

1. **Arm A reproduces the published `S`** to three significant figures on 78 stations. Calibration,
   not a hypothesis.
2. **Arm B's `s` is negative and its 95% interval excludes zero.** A real interannual thermal
   response exists.
3. **`|s_B| < |S_A|`.** Removing an absorbed co-trend shrinks the coefficient. Registered as the
   expected direction, so a *larger* arm B would be the surprise and would need explaining rather
   than celebrating.
4. **Arm C agrees with arm B in sign, and its interval is wider.** The two high-pass filters should
   not disagree about direction; differencing should cost precision.
5. **Arm D's interval is narrower than arm B's**, and arm D's point estimate lies inside arm B's
   interval. Registered because Phase 3h's floor diagnostic predicts exactly this and it is the
   cheapest available check on that diagnostic.
6. **The thermal share under arm B is below 50%** — that is, `|s_B x W| < |A| / 2`, so under the
   interannual specification most of the observed advance is *not* thermally attributable.
   Registered as the substantive claim and as the one most consequential if false.

---

## 5. Stop conditions

- **Arm A off its calibration.** The harness does not reproduce the fit it claims to extend.
  Nothing above arm A is interpreted; the table is printed in full, as Phase 3f's was.
- **Arm B's interval covers zero *and* arm D's covers zero.** Then no interannual thermal response
  is identified at either scale, and the published attribution rests entirely on a co-trend.
  `anthropogenic-share` is withdrawn to a `direction="limit"` finding in the same commit, and
  `reports/response.py`'s dial and Forecast A's fitted envelope are rescoped with it. **This outcome
  is live and the note is worthless if it is not willing to pay it.**
- **Arm B clear of zero.** `anthropogenic-share` republishes as an interval on the explained share,
  carrying both ends and the identification problem, rather than as `-0.30 of the -0.56`.
- **Arm C's sign disagrees with arm B's.** The two filters disagree, no single share is published,
  and the disagreement is the result.
- **Arm D fails to fit at all** — fewer than four regions inside the band clearing the year floor.
  Arm D publishes as a coverage statement and predictions 5 is graded false, not dropped.
- No arm, window, band, covariate or unit is revisited after any refitted sensitivity is seen. A
  wrong prediction here is recorded as a correction, never edited away.

---

## 6. What this cannot establish

- **Which timescale the animals respond on.** The two specifications bracket it and the data cannot
  choose between them. That is the finding, not a preamble to a better number.
- **That the residual `b` is anything.** It is what a linear time term absorbs: a non-thermal driver,
  a slow instrument drift, the unexplained 2012 step's tail, or a thermal response on a timescale
  arm B removes. Naming it would be inventing it.
- **Causation, in any arm.** Every one is a regression of a date on a temperature at the same place.
- **Anything outside 37–50°N autumn aerial.** Not spring, which has no published `S` and no skill.
  Not the southern bands, where the 2012 step lives. Not the seas, the herds or the atlases.
- **Whether the response is linear.** Every arm is linear by construction, and Phase 3f's spline arm
  sits unread behind a fired calibration.
- **Anything about the *forecast* question.** Interannual skill was measured by Phase 3a and refused
  by Phase 3d. A response function read forwards is a different object, as `forecast-a.md` argues at
  length, and nothing here reopens either.

---

# Results — run 2026-08-31

`make report-phase2c`. Two consecutive runs are identical, checked before anything here was written
down, because Phase 3f's null was irreproducible and measuring twice is the only thing that found it.

| arm | units | S d/°C | W | S × W | observed | residual `b` | share |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **A** as published | 78 | **−0.659 ± 0.165** | +0.518 | −0.301 ± 0.090 | −0.559 | −0.258 | **0.54** |
| **B** + year term | 78 | **−0.624 ± 0.175** | +0.518 | −0.287 ± 0.094 | −0.559 | −0.272 | **0.51** |
| **C** first differences | 77 | −0.514 ± 0.238 | +0.514 | −0.205 ± 0.142 | −0.557 | −0.353 | 0.37 |
| **D** regions | 6 | −0.562 ± 0.291 | +0.467 | −0.266 ± 0.142 | −0.133 | +0.134 | *not read* |

**Calibration — PASS.** Arm A returns **−0.6585** against the published −0.659, on 78 stations.

## The answer, stated before the grading

**The circularity is real and it is small.** Adding a time term moves the sensitivity from −0.659 to
−0.624 — a shift of **0.20 of arm B's own interval** — and the attributed share from 54% to 51%. The
stop condition that would have withdrawn `anthropogenic-share` outright did not fire, and the
published number survives a check it had never been given.

**The bracket this phase publishes is 51% to 54% of the observed advance**, and the ledger now
carries it: `anthropogenic-share` reads `−0.30 days per decade of the −0.56 observed, 50%–53% of it`,
the two ends being the two specifications multiplied by the ensemble's own `f`.

That the bracket is narrower than the interval on either end of it is the useful part. "About half"
was not resting on the missing time term.

## The predictions, graded

**1 — TRUE.** Arm A reproduces the published `S` to three significant figures (−0.6585), so the
panel extraction in amendment E changed nothing and the ladder is readable.

**2 — TRUE.** Arm B is −0.624 ± 0.175 and its interval excludes zero. There is an interannual
thermal response, measured net of a linear time trend.

**3 — TRUE, and barely.** |−0.624| < |−0.659|, by 0.035 on an interval of ±0.175. The registered
direction is right and the magnitude is small enough that the two specifications are not
distinguishable from each other — which is a different statement from either being right.

**4 — TRUE, on both clauses.** Arm C agrees in sign (−0.514) and its interval is wider (±0.238
against ±0.175), as differencing should make it.

**5 — FALSE, and the registration is at fault rather than the result.** Arm D's interval is *wider*
than arm B's (±0.291 against ±0.175), not narrower. Its point estimate −0.562 does sit inside arm
B's interval, so the second clause held and the conjunction failed on the first. See the correction
below: §3's table said eleven regions and the claim band cannot contain more than six.

**6 — FALSE, by one point.** The thermal share under arm B is **51%**, not below 50%. Recorded as
false because that is what the registration says; the margin is stated so nobody has to wonder
whether it was close, and it was one point. The substantive reading is unchanged either way — about
half of the advance tracks pre-season temperature and about half does not, and the half that does
not remains unexplained.

## Correction: §3's table said eleven regions, and six is the most that can exist

§3 describes arm D's unit as "11 flyway-band regions", carried over from Phase 3h. Phase 3h pooled
across **all four** latitude bands. This phase is restricted to 37–50°N, which contains **two** of
them, so with three flyways the claim band admits at most six regions — and six is what fitted.

The consequence is that arm D was under-powered for its own prediction before it ran, and the
registration did not notice because it copied a unit count across a change of scope. The prediction
stands as graded false rather than being reinterpreted, and what the arm still says usefully is
below.

## Arm D's share is not read, and its `observed` is why

Arm D's sensitivity, −0.562 ± 0.291, is comparable to the others and is the one thing worth taking
from it: at regional scale the interannual thermal response is the same size as at station scale,
which is what should happen if both are estimating one quantity.

Its **share is not read**, because its denominator is a different quantity. The regional series'
observed trend is **−0.133 days per decade against the station-mean −0.559**, so the ratio 2.01 is
S × W at one aggregation divided by an advance at another. Amendment D fixed that `W` and `A` come
from the raw series in every arm, and they do — but the *unit* changed, and a secular trend is not
invariant to aggregation when the panel is unbalanced.

**That is a caution for Phase 3h and it is recorded here rather than as an aside.** A region-year is
the mean of whichever member stations reported, and Phase 3h noted that this makes the response's
measurement error vary across years. It does more than that: it moves the series' own trend, here to
a quarter of the station-mean value. Phase 3h's skill result is unaffected — skill is scored against
each series' own climatology, so a smaller trend is not a smaller score — but any *trend* read off a
regional series is not the trend read off its stations, and nothing in this project had said so.

## Arm C is below the bracket, and there are two reasons it could be

The three specifications fall in order: 54%, 51%, 37%. Removing more low-frequency covariation gives
a smaller thermal share every time, which is the pattern a shared trend produces.

**It is also the pattern measurement error produces, and this design cannot separate them.** Noise
in a predictor attenuates a slope towards zero, differencing amplifies predictor noise, and Phase 3h
measured this response as only 34% explainable at a station. So arm C's −0.514 is consistent with a
cleaner interannual estimate *and* with an attenuated one, and it is reported as the registered
sensitivity it is rather than as the low end of a bound.

**The bracket therefore is not a bound over all specifications**, and §2's language should be read
strictly: it is the range spanned by the two specifications §3 registered, published because those
two are the ones the identification argument is about. A high-pass stricter than a linear time term
gives a smaller share, and how much of that is bias is unmeasured.

## What did not change

- The stop condition that would have withdrawn `anthropogenic-share` did not fire, and neither did
  the one that would have rescoped `response.py`'s dial or Forecast A's envelope.
- `W`, `A`, the wind null and the temperature/wind split are untouched, as the correction to
  `phase2a-timing.md` said they would be — none of them turns on the timescale.
- The residual is still about half the advance and still unexplained. Under arm B it is −0.272 days
  per decade, and naming it would be inventing it.
