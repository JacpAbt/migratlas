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
