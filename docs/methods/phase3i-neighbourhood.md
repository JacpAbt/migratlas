# Phase 3i — is there a scale between a station and a region, and does it pay?

**Status:** pre-registered 2026-08-23. Written before any neighbourhood has been formed, before any
smoothed series has been computed, before any fit in any arm below has been run, and before the
split-half reliability of a smoothed series has been measured at any `k`. Nothing in §§2–6 was
written with a number from this phase in front of it. Results are appended below, with every
prediction graded whichever way it went.

`TASKS.md` #64. The successor Phase 3h asked for by name, on the ground Phase 3h itself established.

---

## Why this note exists

Phase 3h moved the aerial question from "uniformly useless" to "not uniformly useless" by changing
what was being predicted rather than how. It pooled 143 stations into eleven flyway-and-band regions
and the autumn median skill went from `+0.0055` to `+0.0649` — an order of magnitude, with no change
of driver, estimator, era split, null or filter.

It then said, in its own closing section, what was wrong with that:

> the per-station ceiling is 34% and the pooled one is 65%; nothing was tried in between.

And why it mattered:

> Eight of eleven regions still have no skill … A median of `+0.065` over eleven noisy units is not a
> model that works; it is a model that has stopped being uniformly useless.
>
> The skilful regions do not agree between seasons — not one overlaps. … Either autumn and spring are
> genuinely different phenomena with different predictable regions … or a count of three at a 5% bar
> is partly luck and the non-overlap is what luck looks like. Distinguishing them needs more units.

So this phase is the *cheapest* remaining move on the response axis, and it is the one Phase 3h's own
result argues for over raising the estimator: **more units, at a scale between one station and a
whole region.** #62's partial pooling, splines and gradient boosting stay queued behind it, on Phase
3h's instruction — do not raise the estimator until the response stops paying.

---

## 1. What was looked at before this was written

Everything here is a number this project already published, read off the notes rather than recomputed
for this one:

| what | value | where |
| --- | --- | --- |
| per-station median skill, autumn / spring | `+0.0055` / `−0.0308` | 3h arm A |
| per-region median skill, autumn / spring | `+0.0649` / `+0.0114` | 3h arm B |
| the gain from pooling, autumn / spring | `+0.0595` / `+0.0423` | 3h ladder |
| significant units, per station, autumn / spring | 21 of 143 / 12 of 140 | 3h arm A |
| significant units, per region, both seasons | 3 of 11 | 3h arm B |
| implied per-station explainable share, autumn / spring | 34% / 44% | 3h floor diagnostic |
| median split-half reliability of a regional series | 65% / 66% | 3h floor diagnostic |
| the skilful autumn regions | central 32-37N, central 42-50N, eastern 32-37N | 3h per-region table |
| the skilful spring regions | central 24-32N, western 32-37N, western 37-42N | 3h per-region table |

What has **not** been looked at, and is the reason this note can be registered honestly: no
neighbourhood of any size has been formed, no smoothed response or smoothed covariate series exists
in this repository, and the split-half reliability of a smoothed series has never been computed at
any `k`. The two numbers 34% and 65% are the endpoints of an interval whose interior is unmeasured.

One inherited caution, stated because it bounds what the interior can mean: 3h recorded that its
reliability estimator **over-reads by an unknown amount** — on a simulation with true reliability 0.75
it returned 0.79. So 65% is a ceiling estimate, not a ceiling.

---

## 2. Estimand and units, with their known problems first

**The unit is a station-season, as in Phase 3a and 3h arm A** — 143 in autumn, 140 in spring, the
same panel, the same qualifying rule, the same era split, the same dropped stations for the same
reasons. The count is deliberately identical to arm A's so that the family bar (`binomial_bar`, 12
and 11) and the significant counts are directly comparable to a number already published.

**What changes is the series each unit predicts.** For a station *s*, the response is the unweighted
mean of `q50_doy` over *s* and its `k − 1` nearest qualifying stations — the same `q50_doy` from the
same `passage_quantiles` call with the same filters Phase 3a used, unweighted for the reason 3h gave
(a weighting scheme is a free parameter, and this phase spends its novelty on the neighbourhood).

**`k = 5`, fixed here, before anything is computed, and not chosen from an outcome.** It is tied to a
decision this project already made: 3h required **four** qualifying stations before a region was
poolable at all, so a station plus its four nearest is the smallest neighbourhood that meets the
project's own existing floor. Two further values, `k = 3` and `k = 9`, are registered as
sensitivities in §3 — reported always, never promoted to primary.

**Neighbours are geographic and deterministic.** Great-circle distance between `station_latitude` and
`station_longitude` as `phase1` already reads them, nearest first, ties broken by station id
ascending. Computed once per season over that season's qualifying panel, so a station's neighbourhood
is a property of the panel and not of the order a list was built in.

Known problems, before any result:

- **The neighbourhoods overlap, so the units are less independent than 3h's eleven were.** Two
  adjacent stations share up to `k − 1` members. The per-unit null handles this the way 3h's did — it
  shuffles years, so all spatial structure is preserved under the null — but it does nothing for the
  independence of the 143 counts from each other. **The primary quantity is therefore the median and
  the count is secondary**, which is the rule #62 imposed and 3h followed.
- **Smoothing the response should raise skill mechanically, and that is the hypothesis rather than a
  confound.** A station's series carries measurement noise that no driver can predict; averaging over
  a neighbourhood removes some of it. The floor diagnostic says how much room that leaves (34% at one
  station). So a gain is not a surprise and is not, by itself, interesting — **what the phase is for
  is where in the 34-to-65 interval the gain lands, and at what cost in unit count and coarseness.**
- **The real confound is the drivers, not the response**, and it is the same one 3h wrote arm A to
  catch: if a *covariate's* spatial mean is smoother, and therefore easier to fit, than the
  response's, then the gain is an artefact of smoothing the inputs. Arm C exists for exactly this and
  a stop condition in §5 turns on it.
- **A neighbourhood answer is still coarser than a station answer.** Skill on a five-station mean does
  not imply skill at any of the five. It is less coarse than a region of a dozen or more, which is the
  entire point, but the site would have to say what it is.
- **Missing years differ between member stations**, so a neighbourhood-year is the mean of whichever
  members reported and the response's own measurement error varies with the count. Not corrected —
  correcting it needs a weighting scheme — but the per-unit member count is printed, as 3h printed
  its per-region station count.

---

## 3. The design, fixed before any fit

### The ladder, one step at a time

| arm | response | covariates | what its difference from the arm below means |
| --- | --- | --- | --- |
| A | per station | per station, Phase 3a's seven | nothing — the calibration rung, and it must reproduce 3h arm A |
| B | **neighbourhood, `k = 5`** | **neighbourhood, `k = 5`** | the target change, scale-matched exactly as 3h matched its regional arm |
| C | per station | neighbourhood, `k = 5` | the driver-side control: any gain here is smoother *inputs*, not a cleaner response |

No estimator arm, and no basis arm. Phase 3f spent five rungs on estimator complexity and produced a
difference nobody could attribute; 3h refused to repeat it while also changing the response, and this
note refuses for the same reason. The only thing moving is the spatial scale of the series.

No wind arm either. 3h's arm C added wind support and the favourable share at the regional scale and
the median *fell* (`+0.0649` to `+0.0132` in autumn). Whatever that means, it is a driver question at
a settled scale, and mixing it into a scale question would make both unreadable.

### The estimator, stated exactly

`models.skill.hindcast(x, y, seed=...)` **verbatim** — the same function Phase 3a, 3f and 3h called.
Ridge, leave-one-year-out lambda selected inside the training years only, training-only
standardisation, era split at 70/30 with a five-test-year floor, Murphy score
`1 − MSE_model / MSE_climatology` on the test era. Nothing about the estimator changes.

The climatology in that denominator is the **smoothed** series' own training-era mean wherever the
response is smoothed. Stated because it is the thing that keeps arm B honest: a smoothed series is
compared against its own climatology, not against the station's, so a reduction in variance does not
by itself produce a score.

### The null, and the significance rule

Per unit, 1,000 year-shuffle permutations, seeded by `phase3h.unit_seed` — `crc32` of the unit's
name, so a unit's null is a property of that unit and not of its position in a list. That is Phase
3f's correction 1, inherited rather than rediscovered. A unit is significant when its observed skill
exceeds its own 95th null percentile; the family bar is `phase3a.binomial_bar`, 12 at 143 units and
11 at 140.

### Calibration, on a deterministic quantity

Arm A must reproduce **3h arm A's medians** — autumn `+0.0055`, spring `−0.0308` — to three
significant figures. Medians and not counts, for the reason 3h gave: a seeded count crossed a bar
between two legitimate seeds once already and fired a stop condition over a coincidence. A median of
an observed skill distribution does not depend on the seed.

### The reliability measurement, which is the interpretive anchor

The split-half reliability of the `k = 5` smoothed series, computed **the same way 3h computed it for
a station and for a region**, so the three numbers sit on one axis. Deterministic, no fit involved,
and reported whatever the arms do — it is what makes "where in the interval" a question with an
answer rather than a figure of speech.

### The reporting split, carried over unchanged

Two medians per arm, as registered in 3f and used in 3h: **projectable drivers only**, and **all
explanatory drivers**. Skill that exists only with a driver nobody can project licenses a mechanism
claim and not a forecast.

### Registered sensitivities

`k = 3` and `k = 9`, arm B only, both seasons. Reported in the results table always. Neither can be
promoted to primary and neither grades a prediction — they exist so that a reader can see whether the
answer is a property of the scale or of the number 5.

### Seed

`SEED = 3` for every null in this phase, fixed here. `unit_seed` mixes it with the unit's name.

---

## 4. Predictions

Numbered, falsifiable, and graded in the results section whichever way they go.

1. **Arm B's autumn median lies strictly between `+0.0055` and `+0.0649`.** The interval's interior is
   the whole hypothesis. Above the top would mean a neighbourhood beats a region, which nothing
   predicts; below the bottom would mean smoothing five stations buys nothing a single station has.
2. **Arm B's significant count in autumn exceeds arm A's 21 of 143.** Same panel, same bar, cleaner
   response.
3. **The `k = 5` split-half reliability lies strictly between 34% and 65% in autumn.** This is the
   prediction the phase exists to make; if reliability at five stations is already at the regional
   ceiling, the interval was not an interval and the scale axis is shorter than 3h implied.
4. **Spring's arm B median stays below autumn's.** The project's own established asymmetry, tested
   again rather than assumed.
5. **Arm C's gain over arm A is less than half of arm B's gain over arm A**, in autumn. If the drivers'
   spatial mean is doing most of the work, the response was not the thing that was wrong and 3h's
   attribution needs re-reading.
6. **A majority of autumn's significant units fall inside the three regions 3h found skilful in
   autumn** — central 32-37N, central 42-50N, eastern 32-37N. A coherence check between two scales
   that should be describing the same ground. Nobody registered this at the regional scale and it is
   registered here so that agreement counts as evidence rather than as a remark.

---

## 5. Stop conditions

- **Arm A fails to reproduce 3h arm A's medians to three significant figures.** Stop. The panel, the
  filters or `hindcast` has moved, and nothing downstream of that is interpretable.
- **Fewer than 100 stations qualify in either season.** Stop and report the panel. The comparison to
  arm A's 143 and 140 is the reason the unit is a station at all.
- **Prediction 5 grades false** — arm C's gain is at least half of arm B's. Then arm B is not read as
  a response result: report all three arms, state that the scale gain is substantially a driver
  artefact, and stop. Interpreting arm B in that case would be the mistake 3h wrote its own arm A to
  prevent.
- **The reliability at `k = 5` exceeds 65%.** Stop before interpreting the arms. It would mean the
  smoothed series is measured *more* reliably than a whole region's, which contradicts the diagnostic
  this phase is built on, and the diagnostic would have to be understood before the skill numbers
  mean anything.

None of these is a failure of the phase. Three of the four are the phase discovering that its own
premise was wrong, which is the outcome a registration exists to make publishable.

---

## 6. What this cannot establish

- **Nothing causal.** Seven weather and index columns fitted to a date is not a mechanism, at any
  spatial scale.
- **No forecast licence.** That needs projectable drivers, hindcast skill *and* the novelty mask.
  This can supply the second, for some units, at a scale the site would have to name out loud.
- **Not whether the reliability ceiling is real.** 3h's estimator over-reads by an unknown amount, so
  every number on the 34-to-65 axis is a ceiling estimate. This phase inherits that and cannot fix it.
- **Not whether autumn and spring have genuinely different predictable ground.** More units make the
  question *askable* — 143 against 11 — but two seasons whose skilful units barely overlap at 143
  units would still admit both readings, because the units are not independent. Ruling out luck needs
  another network, which is refused elsewhere for its own reasons.
- **Not the best scale.** `k = 5` is the smallest neighbourhood meeting this project's existing floor,
  not an optimum. Searching `k` for the best score is exactly the tuning 3h refused when it declined
  to redraw its region boundaries, and the two sensitivities are reported precisely so that nobody
  needs to.
- **Nothing about any realm but the aerial one.** The marine and terrestrial halves are excluded here
  by the same registered rules that excluded them from 3a, 3f and 3h.
