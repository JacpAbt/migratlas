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
