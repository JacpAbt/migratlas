# Phase 1k — what four idle monitoring schemes say on their own, and what they say together

**Status:** pre-registered 2026-08-23. Written before any centroid, any flight-date trend, any
effort correction and any fit on `bbs`, `sbs_point_counts`, `sbs_fixed_routes` or `ukbms_phenology`.
No species has been counted, no minimum series length has been applied to any of them, and the
number of qualifying units in each network is unknown to this note. What *has* been read is the row
count, year count, span and column list of each — measured on 2026-08-23 and recorded in
[`holdings-audit-2026-08.md`](holdings-audit-2026-08.md) — and nothing else.

This note is also **Phase 1j's successor**, which 1j required by name: *the leg waits for a successor
registration that sets the floor on the unit, and that registration inherits this measurement rather
than pretending to be blind to it.* Inherited in §2 explicitly.

---

## Why this note exists

The holdings audit found that four sources carrying `count`, `effort`, `effort_unit`, `protocol`,
`site_id` and `year` — the exact shape the atlas and radar analyses got their answers from — have
never been asked anything. Three of them are certified `detectable` by this project's own coverage
assessment. Together they hold 9.1 million rows across spans of 30, 49, 50 and 59 years.

| source | rows | span | what it measures |
| --- | --- | --- | --- |
| `bbs` | 7,548,397 | 1966–2025 | designed route counts, North America |
| `sbs_point_counts` | 490,869 | 1975–2024 | summer point counts, Sweden |
| `sbs_fixed_routes` | 468,933 | 1996–2025 | fixed routes, Sweden |
| `ukbms_phenology` | 627,752 | 1973–2021 | mean flight date per site-species-year, UK |

The owner's brief was explicit and it shapes the design: **ask each one what it finds on its own, and
also ask what each does inside a group.** So this phase has two legs and a synthesis, and the
synthesis fits nothing new — it puts already-fitted distributions side by side, which is the only
honest way to compare them.

---

## 1. A problem with the grouping axis, stated before it is used

`Realm` is documented in `evidence/types.py` as the **physical medium of an observation or driver**,
and its stated purpose is routing: *a marine metric pulls sea surface temperature and chlorophyll
where an aerial one pulls reanalysis winds.* It is a fact about the instrument, not about the animal.

That has a consequence this phase cannot design around silently. `bbs` is `terrestrial` because a
route count happens on the ground. `darkecology_daily` is `aerial` because radar looks up. **Both
measure birds.** Grouping by `realm` would put a bird survey with an elk herd and separate it from a
radar measuring the same birds — and any cross-group difference would be an instrument difference
wearing a medium's clothes.

So:

- **The synthesis never groups by `realm`.** It groups by the taxonomic class read from `taxon_key`
  per row, which is a property of the animal.
- **No taxon name is written into an identifier anywhere in `reports/`.** That package is inside the
  taxon-agnostic AST guard, and `ingest/` and `models/` are the only exempt ones. The grouping is
  data-driven: classes are whatever the taxonomy returns for the keys present.
- **`realm` is still reported per unit**, because it is what routes the drivers, and a reader
  comparing two rows needs to see when the instrument differs.

Recommending a schema change is out of scope here and recorded as a candidate: the question *what is
happening to animals that move through water, air and land* needs a field for the animal's own medium,
and the registry has none. Adding one touches a required, load-bearing field and belongs in its own
change with its own tests.

---

## 2. Estimands and units, with their known problems first

Two legs, because the sources split into two kinds of series, and each leg's estimand is **one this
project already publishes** so that the new sources land on an existing axis rather than a new one.

### Leg 1 — distribution

**Estimand:** the trend in a species' abundance-weighted latitudinal centroid within one network,
in **°latitude per decade**. This is the quantity `marine-null` publishes, deliberately, so the
comparison to fish is by construction rather than by argument.

**Unit:** the species-network pair, as `marine-null`'s unit is the species-survey pair.

**Floor:** a unit qualifies with **20 years** of the species present in the network. Registered at 20
with a sensitivity at 15, and set on the *unit* rather than on a proxy for it — which is 1j's
correction, inherited.

### Leg 2 — timing

**Estimand:** the trend in mean flight date, in **days per decade**. This is the quantity
`autumn-advance` publishes, again deliberately.

**Unit:** the **site-species-generation**, which is the unit Phase 1j declared. 1j's own recorded
correction measured **10,941 units clearing fifteen years** inside 1995–2021, against 143 for the
aerial panel; that measurement is inherited here rather than re-derived, and the floor is set on the
unit at **15 years** to match it.

### Known problems, before any result

- **Three of the four sources are birds.** This deepens the tilt the project is arranged against, and
  `ukbms_phenology` is the only counterweight. Stated rather than mitigated: the fix is admitting
  non-bird sources, not declining to analyse the ones already in the lake.
- **Effort is measured but not identical.** A BBS route, a Swedish point count and a Swedish fixed
  route are three protocols with three denominators. The registered treatment is to model counts per
  unit effort within a network and **never to pool across networks**; the whole design of the
  synthesis is comparison, not pooling.
- **A centroid moves for reasons other than animals moving.** Survey coverage expands, observers
  improve, and a network's spatial footprint changes across decades. `marine-null`'s own caveat says
  the same about trawls. The registered mitigation is the one the atlas work used: restrict each
  unit to sites sampled in both the first and last fifth of its window, and report how many sites
  that discards.
- **An abundance-weighted centroid is not a range edge.** A species can shift its centroid with no
  range change and vice versa. This phase claims centroids and says nothing about edges.
- **Networks are not independent.** Sweden and North America share a climate system and a
  hemisphere. Agreement between them is weaker evidence than it looks, and §6 says so.
- **A flight date is not a migration date.** Most UKBMS taxa are resident, so an advance in flight
  period is a phenological response and not a migration timing shift. The comparison to radar
  passage is a comparison of *thermal tracking*, which is what `transfer-fails` was about, and not a
  claim that the two measure the same behaviour.

---

## 3. The design, fixed before any fit

### The ladder

| leg | arm | what it fits | what its result means |
| --- | --- | --- | --- |
| 1 | A | `fishglob`, this phase's estimator | calibration — must reproduce `marine-null` |
| 1 | B | `bbs` | the first question ever asked of it |
| 1 | C | `sbs_point_counts`, `sbs_fixed_routes` | two protocols, one country, same birds |
| 2 | D | the radar panel, this phase's estimator | calibration — must reproduce `autumn-advance` |
| 2 | E | `ukbms_phenology` | 1j's leg, on the unit 1j declared |
| — | S | nothing | the synthesis: already-fitted distributions, side by side |

**Arm S fits nothing and that is the point.** A model spanning four networks with different
protocols would have a pooled coefficient nobody could interpret, and the owner's "what does it do in
a group" is answered by comparing distributions rather than by averaging them. What S produces is a
table and a set of pairwise interval comparisons.

### The estimator, stated exactly

Ordinary least squares of the unit's annual series on year, per unit, with a **cluster bootstrap over
sites** for the interval — the same shape `displacement-flat` used for animals and `marine-null` for
species-survey pairs. No ridge, no pooling, no shrinkage: this is a descriptive phase and #62's
estimator rungs stay where they are.

The reported quantity per network is the **median of its units' slopes** and the **interquartile
range**, because `marine-null` established that a pooled median hides the variation worth planning
around, and the IQR is what shows it.

### The null

Per unit, 1,000 year-shuffle permutations seeded by `phase3h.unit_seed` — `crc32` of the unit's name,
so a unit's null is a property of that unit. A unit is significant when its observed slope's magnitude
exceeds its own 95th null percentile. The family bar is `phase3a.binomial_bar` at the network's unit
count.

### Calibration, on deterministic quantities

- Arm A must reproduce **`marine-null`'s median of −0.011 °latitude per decade** on the same rows, to
  three significant figures.
- Arm D must reproduce **`autumn-advance`'s −0.56 days per decade**, to two significant figures.

Medians and point estimates rather than counts, for the reason Phase 3h gave: a seeded count once
crossed a bar between two legitimate seeds and fired a stop condition over a coincidence.

### Registered sensitivities

The floor (20 years against 15 for leg 1), and the effort treatment (modelled against raw counts).
Both reported always, neither promotable to primary.

### Seed

`SEED = 1` for every null in this phase.

---

## 3a. Amendments, written while implementing and before the registered run

Two, and the second is the reason this convention exists.

**The footprint rule is `consistent_footprint`, not the first-and-last-fifth rule §2 registered.**
§2 said each unit would be restricted to sites sampled in the first and last fifth of its window.
The implementation uses the rule `marine-null` uses instead — cells sampled in at least 80% of the
network's years. The reason is arm A: the calibration reproduces `marine-null` by calling
`phase1b.analyse` itself, so if the new networks used a different footprint rule the legs would not
be comparable to the arm certifying them. A weaker rule on the new sources and a stronger one on the
calibration would have been the worst of the options.

**Leg 2's estimand had to be reconstructed, and the first implementation fitted the wrong quantity.**
§2 says the estimand is the trend in mean flight date. The lake does not store a flight date as a day
number: `ingest/ukbms.py` lands `period_start` as the first day of flight and `count` as the days from
there to the count-weighted mean, and its own comment says so. The first implementation fitted `count`
directly, which is **how far into a flight period its mean falls** — a shape, not a date — and would
have graded prediction 6 and 7 on a quantity neither mentions. The estimand is now
`period_start.dt.ordinal_day() + count`, which is the mean's day of year.

Recorded rather than quietly corrected, because the registration is what caught it: the prediction
named a date, and the column did not hold one.

**And a measurement in the holdings audit was wrong.** That note said all four idle sources carry a
measured effort column. Measured today: `bbs` is 0.00% null, `sbs_point_counts` 0.51%,
`sbs_fixed_routes` 0.11% — and **`ukbms_phenology` is 100% null.** It has the column and none of the
values, which `ingest/ukbms.py` sets deliberately: a flight-date series has no catch to denominate.
The audit is corrected in place. Nothing in this phase depended on it — leg 2 fits dates and never
touches effort — but the claim was published and it was wrong.

---

## 4. Predictions

1. **Arm A reproduces `marine-null`'s median to three significant figures.**
2. **`bbs`'s median species trend is positive — poleward — and its bootstrap interval excludes zero.**
3. **In every one of the three bird networks, the interquartile range of species trends spans zero.**
   The sign disagreement `marine-null` found is not a marine peculiarity.
4. **`bbs` and both Swedish networks agree in the sign of their medians.**
5. **The two Swedish networks agree within each other's intervals.** Same birds, same country, two
   protocols. If they disagree, that bounds every cross-network comparison this project makes,
   including `transfer-fails`.
6. **`ukbms_phenology`'s median flight-date trend is earlier and clears its null.** Registered as
   near-certain and acted on by a stop condition, not by interpretation — an advance in butterfly
   flight periods is among the most replicated results in phenology, so its absence would impeach
   this pipeline long before it impeached the biology.
7. **`ukbms`'s advance per decade exceeds the radar's −0.56 in magnitude.** Shorter-lived, more
   tightly thermally coupled. A smaller advance would be the more interesting outcome.
8. **No two of the four networks' medians agree within their intervals.** `marine-null`'s claim that
   a single global number would erase every difference worth planning around, tested outside the
   marine realm.

---

## 5. Stop conditions

- **Either calibration misses its target.** Stop. An estimator that cannot reproduce this project's
  own published numbers is not the estimator that produced them, and nothing downstream is readable.
- **Fewer than 30 units clear the floor in a bird network.** That network is published as a coverage
  statement and no trend is claimed from it. Set on the unit, per 1j's correction.
- **Prediction 6 is false.** Stop leg 2 and report it as a finding about the pipeline rather than
  about insects. Then the flight-date path is debugged before anything else in this phase is read.
- **The effort treatment changes a network's median sign.** Report both treatments and claim neither.
  A result that depends on which denominator was chosen is a result about the denominator.

---

## 6. What this cannot establish

- **Nothing causal, and no attribution.** These are slopes against year. Why anything moved is Phase
  2's question and this phase supplies no driver.
- **Not that `realm` answers the medium question.** §1 records that it cannot, and this phase works
  around it rather than fixing it. A cross-medium synthesis worth the name needs a schema field that
  does not exist yet.
- **Not that agreement between networks means agreement in the world.** Sweden and North America
  share a hemisphere and a climate system. Two networks agreeing is consistent with one common
  driver and with two coincidences, and this design cannot separate them.
- **Not whether a centroid shift is a range shift.** Different quantities, and only the first is
  claimed.
- **Not that the butterfly and radar series measure the same behaviour.** One is a resident insect's
  flight period and the other is nocturnal aerial passage. They share a *thermal tracking* question,
  which is `transfer-fails`' subject, and nothing else.
- **Not anything about the bird tilt.** Three of four sources here are birds. This phase makes the
  tilt more visible, not smaller, and the remedy is admission rather than analysis.

---

## Results — run 2026-08-23

**Both calibration arms pass, which is what makes the rest of this readable.**

| arm | quantity | target | measured | verdict |
| --- | --- | --- | --- | --- |
| A | `marine-null` median | `-0.011` °lat/dec | **`-0.0110`** | PASS |
| D | `autumn-advance` slope | `-0.56` d/dec | **`-0.559`** | PASS |

Both by calling the published report itself, so what passed is the pipeline that produced the
findings and not a second copy of it.

### Leg 1 — distribution

| network | units | median °lat/dec | 95% CI | IQR | beat own null | bar | cells kept / dropped |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `bbs` | 520 | **`+0.0517`** | `[+0.0341, +0.0754]` | `[-0.0827, +0.2104]` | 345 | 34 | 762 / 696 |
| `sbs_point_counts` | 189 | **`+0.0968`** | `[+0.0701, +0.1433]` | `[-0.0284, +0.3350]` | 118 | 15 | 33 / 42 |
| `sbs_fixed_routes` | 197 | `+0.0335` | `[-0.0036, +0.0855]` | `[-0.1308, +0.2104]` | 74 | 15 | 84 / 17 |

Every network clears the 30-unit floor, so all three are trends rather than coverage statements. The
consistency rule is expensive: `bbs` loses 696 of 1,458 cells and `sbs_point_counts` 42 of 75.

### Leg 2 — timing

| network | units | median d/dec | 95% CI | IQR | beat own null | bar |
| --- | --- | --- | --- | --- | --- | --- |
| `ukbms_phenology` | 12,213 | **`-2.104`** | `[-2.180, -2.038]` | `[-4.586, +0.519]` | 2,476 | 651 |

12,213 units against Phase 1j's measured 10,941, because 1j counted inside its registered 1995–2021
window and this fits the whole 1973–2021 span.

### Grading

**Prediction 1 — TRUE.** Arm A reproduced `-0.0110` against a target of `-0.011`.

**Prediction 2 — TRUE.** `bbs`'s median is `+0.0517` and its interval excludes zero. The first
question ever asked of this source has an answer: the abundance-weighted centroids of North American
breeding birds have moved poleward, at about half a degree of latitude per century.

**Prediction 3 — TRUE, and it is the result worth keeping.** All three bird networks have an
interquartile range spanning zero: `bbs` `[-0.083, +0.210]`, `sbs_point_counts` `[-0.028, +0.335]`,
`sbs_fixed_routes` `[-0.131, +0.210]`. **`marine-null`'s finding that surveys disagree even about the
direction of movement is not a marine peculiarity.** It reproduces in three independent terrestrial
count networks, on another continent, in a different taxonomic class, under a different protocol. The
claim that a single global number would erase every difference worth planning around now has evidence
outside the realm it was made in.

345 of 520 `bbs` units beat their own year-shuffle null against a chance bar of 34. Two thirds of
species carry a real trend and they do not share a direction.

**Prediction 4 — TRUE.** All three medians are positive.

**Prediction 5 — FALSE, and this is the uncomfortable one.** The two Swedish networks do not agree
within each other's intervals: `sbs_point_counts` at `+0.0968` sits outside `sbs_fixed_routes`' CI of
`[-0.0036, +0.0855]`, and `sbs_fixed_routes` at `+0.0335` sits outside `sbs_point_counts`' CI of
`[+0.0701, +0.1433]`. Neither point estimate falls inside the other's interval, and the two differ by
a factor of nearly three.

Their intervals do *overlap*, on `[+0.0701, +0.0855]`, and the registered wording was the strict
reading — "agree within each other's intervals" — so it grades false on the reading it was written
with, with the weaker agreement recorded rather than substituted.

**Same country, same birds, two protocols, and the answer moves by three times.** That bounds every
cross-network comparison this project makes, `transfer-fails` included: one leg disagreeing with
another is no longer evidence that realms differ, because two protocols on one country's birds
disagree by as much. This was registered as the prediction that would hurt, and it did.

**Prediction 6 — TRUE.** `ukbms_phenology`'s median is `-2.104` days per decade, its interval excludes
zero, and 2,476 of 12,213 units beat their own null against a chance bar of 651. The stop condition
does not fire and the timing leg stands.

**Prediction 7 — TRUE.** `-2.104` against the radar's `-0.56` is 3.8 times the magnitude. Registered
as the expected direction for a shorter-lived, more tightly thermally coupled group, and it came back
that way — on 12,213 units against the radar panel's 143.

**Prediction 8 — FALSE, and the prediction was badly posed.** `bbs`'s median `+0.0517` falls inside
`sbs_fixed_routes`' interval `[-0.0036, +0.0855]`, so at least one pair of the four agrees. Worse, the
prediction spoke of "the four networks' medians" when `ukbms_phenology`'s estimand is **days** and the
other three are **degrees of latitude** — a four-way median comparison was never well defined, and
writing it that way was an error in the registration rather than in the result. Recorded rather than
edited away.

### Arm S — the synthesis, and what it cannot do

The synthesis was registered to group by the taxonomic class read from `taxon_key`, on the argument
that `realm` describes the instrument's medium rather than the animal's. That axis turns out to be
**collinear with the network**: every source in this holding measures a single class. `bbs`,
`sbs_point_counts` and `sbs_fixed_routes` are birds, `ukbms_phenology` is insects, `fishglob` is fish.
No network measures two classes.

So the class comparison and the network comparison are the same table, and **this project cannot
currently separate a taxonomic-class effect from a network effect at all.** That is a stronger version
of §1's problem than §1 anticipated: §1 said `realm` describes the instrument, and the answer is that
the alternative axis identifies nothing either, because the holding confounds them by construction.
The question this phase was asked — what is happening to animals that move through water, air and
land — needs either a source measuring more than one class, or two sources measuring one class with
different instruments. The second exists in exactly one case, and it is what makes prediction 5 so
damaging.

### What this establishes, stated no more strongly than it holds

- **Three idle sources are idle no longer, and two carry a signal.** `bbs` and `sbs_point_counts` have
  medians whose intervals exclude zero; `sbs_fixed_routes` does not.
- **A poleward median with a sign-spanning spread, in three networks.** The direction agrees with the
  literature and with the marine work's framing. The dispersion is the finding.
- **The largest timing signal this project has measured, on the largest panel it has:** 12,213 units,
  `-2.104` days per decade.
- **And a bound on the project's own comparative method**, from prediction 5, which is worth more than
  any of the three point estimates.

### What the successor has to fix

1. **Prediction 5 needs explaining before any cross-network claim is published.** Two candidates, both
   testable on data already in the lake: the Swedish networks cover different footprints (33 cells
   against 84), or point counts and fixed routes weight detectability differently. The first is
   checkable by restricting both to their shared cells.
2. **`sbs_fixed_routes` is the shortest network at 30 years** and the only one whose interval includes
   zero. Whether that is length or protocol is not separable here.
3. **A class effect needs a source that breaks the collinearity.** Nothing in the current holding does.
4. **The registered 15-year floor sensitivity was not run.** Recorded as owed rather than quietly
   dropped.

---

## Correction, 2026-08-31: `reports/` is not inside the AST guard

§1 says, of writing no taxon name into an identifier: *"That package is inside the taxon-agnostic
AST guard, and `ingest/` and `models/` are the only exempt ones."* Both halves are false, checked
against `tests/test_taxon_agnostic.py` rather than remembered.

`GUARDED_PACKAGES` is `catalog`, `drivers`, `evidence`, `features`, `lake`, `metrics`, `taxonomy`
and `tiles`, plus `redact.py` and `config.py`. **`reports/` is not in it**, and neither are `cli.py`,
`ingest/` or `models/` — so the exempt set is much larger than two packages, and this phase's own
package was never being checked.

**And it cannot simply be added.** `reports/phase1_ebird.py` exists and `cli.py` imports it by name,
so the guard would fail on the identifier `phase1_ebird` the moment `reports/` entered the tuple.
Whether that file should be renamed and the package admitted is a real question and it is not this
note's to answer; it is recorded so the next person finds the measurement rather than the belief.

**What this does and does not change.** §1's *decision* stands on its own merits: grouping by the
taxonomic class read from `taxon_key` rather than by hand-written taxon names is right because the
grouping should be data-driven, and the synthesis found the axis collinear with the network anyway.
What was wrong is the reason given for it — a mechanism was cited where the truth is a convention
this package keeps voluntarily. A convention is worth less than a guard, and the difference is
exactly the kind of thing this project writes down.

---

# Registration — how precise is one flight-date series, and how wide is the median's interval?

**Pre-registered 2026-09-01, before either quantity has been computed.** Neither the per-unit
standard errors nor any species-clustered interval exists for leg 2 in this repository. What *is*
known is everything this note already publishes, and it is the reason for asking.

## Why

Leg 2's median is published as `flight-advance`: **−2.10 days per decade across 12,213 units, 95% CI
−2.180 to −2.038**. Two things about that interval were never checked, and Phase 1l checked both for
leg 1.

**The interval resamples units as if they were independent.** `_median_interval`'s own docstring
records the choice and the amendment behind it. But 12,213 site-species-generation units rest on 59
taxa and 3,144 sites: one species appears at hundreds of sites and responds to a single national
spring, so the units share far more than a resample over them admits. An interval 0.14 days wide on
a signal of 2.10 is the kind of precision that should be checked rather than enjoyed.

**And nobody measured what one series is worth.** Phase 1l's decisive number is that a median species
trend sits **1.69 standard errors from zero**, short of the two a single estimate needs — which is
why Phase 1k's three latitude medians are withheld to this day. The identical quantity for leg 2 has
never been computed, even though `shift_per_decade` returns a standard error per unit and leg 2
throws it away.

## The two quantities

1. **Per-unit precision.** The median of `|per_decade| / stderr` across the qualifying units, which
   is Phase 1l's `slope_vs_stderr` applied to leg 2's panel. Above 2 and a single site-species
   series is individually readable; below it, this network measures one series no better than the
   Swedish programmes measure one species.
2. **A species-clustered interval on the median.** The same percentile bootstrap, resampling **taxa**
   with all their series attached rather than resampling series. Taxa rather than sites because a
   species is the coarser dependence: it shares one national weather sequence across every site it
   occupies, where a site holds many species responding to different cues. The site-clustered
   interval is computed and reported beside it, and the **wider of the two is the one that counts** —
   a conservative choice, fixed here so it cannot be chosen after seeing which is wider.

## Predictions

1. **The median `|slope|/stderr` is below 2.** Derived from a number this note already published
   rather than from a hunch: 2,476 of 12,213 units beat their own year-shuffle null, so about a
   fifth clear roughly two standard errors and the median unit is well short of it. Registered as
   the expected and uncomfortable outcome.
2. **The species-clustered interval is at least three times wider than the published one.** 12,213
   units over 59 taxa is an effective sample size far closer to the taxa than to the units.
3. **The median itself does not move.** Clustering changes an interval, not a point estimate, so any
   movement beyond rounding is a bug rather than a result.

## Stop conditions

- **Prediction 1 false and the interval still excludes zero.** The claim stands unchanged and gains
  the per-unit figure as reassurance rather than as a caveat.
- **Prediction 1 true and the interval still excludes zero.** `flight-advance` stands as a **network
  median** and its caveat says explicitly that no individual series is readable — the same shape
  Phase 1l imposed on the latitude medians, without the withholding, because a median over 12,213
  series is a different object from a median over 189.
- **The wider interval covers zero.** Then the advance is not distinguishable from no change once
  dependence is admitted, and `flight-advance` is rescoped to `direction="limit"` in the same commit
  — the finding becoming a statement about what this panel can resolve rather than about
  butterflies. **This outcome is live and this registration is worthless if it is not willing to pay
  it.**
- Neither clustering, nor the choice of the wider interval, nor the floor of 2 is revisited after any
  number is seen.

## What this cannot establish

- **Not whether the advance is real.** It measures the precision of a summary, not the biology.
- **Not the right dependence structure.** Site and species dependence are both present and a two-way
  cluster bootstrap is not attempted; taking the wider of two one-way clusterings is a bound, not a
  model.
- **Nothing about the other networks.** Leg 1's medians are withheld on Phase 1l's stop condition and
  nothing here lifts that.

## Results — run 2026-09-01

| quantity | value |
| --- | --- |
| units | 12,213 over **59 taxa** and 3,144 sites |
| median | **−2.104** days per decade, unmoved |
| interval, series resampled (published until today) | −2.181 to −2.038, width **0.143** |
| interval, **sites** resampled | −2.243 to −1.996, width 0.247 |
| interval, **taxa** resampled | **−2.454 to −1.809**, width **0.645** |
| widening against the published interval | **4.51×** |
| median \|slope\| / its own standard error | **1.05** |

### The predictions, graded

**1 — TRUE, and worse than registered.** The median series sits **1.05** standard errors from zero,
against the two a single estimate needs. Phase 1l's Swedish species trends sit at 1.69, so **a single
flight-date series is less individually readable than a single species' latitude trend** — the
network whose panel is eighty times larger measures its own unit rather less precisely, which is not
what the panel size suggests.

**2 — TRUE.** The taxon-clustered interval is **4.51×** the published one, above the registered floor
of three. The site-clustered interval is 1.7×, so taxa are indeed the coarser dependence, as §
registered in advance and as the "one national spring" argument implies.

**3 — TRUE.** The median is −2.104 either way. Clustering changed the interval and not the estimate,
which is what it should do and is the check that this is a dependence correction rather than a bug.

### The stop condition, and what it does

Registered: *prediction 1 true and the interval still excludes zero* → the finding stands as a
**network median** and its caveat says explicitly that no individual series is readable.

The widest interval is **−2.454 to −1.809** and excludes zero comfortably. So `flight-advance` stands,
with three changes:

- the published interval is now the **taxon-clustered** one, and the claim names the clustering;
- the caveat states that the median series is 1.05 standard errors from zero, so this is a statement
  about a network and never about a site or a species;
- a supporting line carries the 4.51× and the reason, because a reader who saw the old interval
  should be able to see that it moved and why.

**The advance survives and the precision claim did not.** An interval of 0.143 days on a signal of
2.104 was asserting a resolution this panel does not have, and the error was in the direction that
flatters: too narrow, on the finding with the largest units count in the project.

### What this says about the rest of the ledger

Every other median-over-units in this ledger is built by the same `_median_interval`, which resamples
units. Three of them are exposed on the same argument and none has been checked:

| claim | unit | the dependence nobody has admitted |
| --- | --- | --- |
| `marine-null` | species × survey | every pair inside a survey shares one survey's water and gear |
| `atlas-no-net-change` | species | every species shares one atlas's observer pool and one footprint |
| `seas-disagree` | survey segment | the surveys are weighted by their own intervals, which are themselves unit-resampled |

Phase 3j already registers the survey-clustered version for the marine pairs, so that one is in hand.
The other two are not, and this note is the measurement that says how much it can matter: **4.5× on
the one case where it has been looked at.** Recorded here rather than acted on, because widening three
more published intervals is its own change with its own registration.
