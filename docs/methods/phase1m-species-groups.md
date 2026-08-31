# Phase 1m — is there a level between one species and all of them?

**Status:** pre-registered 2026-08-23, written before any group has been formed, any group-level slope
fitted, or any coherence measured. What is known is Phase 1l's decomposition, run earlier today: the
median species slope is **1.69** standard errors from zero, only **23.5%** of the paired
between-programme disagreement is estimation error, and the noise-corrected method-to-species scatter
ratio is **1.17**.

Owner's proposal, and the reasoning behind it is Phase 3h's: *if the species trend is pretty low it
means that maybe we can make clusters of species that do similar migrations, instead of single species
or considering all birds as a single unit.*

---

## Why this note exists

Two levels have now been tried on the bird networks and both failed for opposite reasons. **One
species** is too noisy — a median trend 1.69 standard errors from zero is not individually
distinguishable from no trend. **A whole network** is a mixture: Phase 1k's medians summarise species
that do not share a direction, and Phase 1l showed that comparing two such mixtures was what produced
its own misleading 3× gap.

Phase 3h faced the identical problem on the spatial axis and solved it by pooling: 143 radar stations
became eleven flyway-band regions and the median skill rose an order of magnitude, `+0.0055` to
`+0.0649`, with nothing else changed. This asks whether the species axis has the same middle.

---

## 1. The trap, and how the grouping avoids it

**Grouping species by how they moved and then measuring how the groups moved would be circular.** The
groups would be coherent and their trends significant by construction. Phase 3h refused to redraw its
region boundaries for this reason, and Phase 3i's registration refused to search for a best cluster
size. So the grouping variable must not be the outcome.

**The primary grouping is the species' own mean latitude, and it is not circular for a stated
reason.** `shift_per_decade` centres the year before fitting, so the design matrix is orthogonal in
its two columns and the intercept and slope estimates are uncorrelated. Grouping on the intercept —
where a species lives — and measuring the slope introduces no shared estimation error. That a
northern species might *genuinely* have a different trend from a southern one is the hypothesis, not
a confound.

**Groups are deciles**, ten of them, fixed here. The count is chosen against Phase 3h's own
experience rather than tuned: eleven units was enough to carry a median and too few to carry a count,
and ten of about seventeen species each gives roughly a fourfold noise reduction within a group while
leaving enough groups to measure spread between them.

**Registered sensitivity:** the same analysis grouping by the number of grid cells a species occupies
— its range extent — reported always and never promoted. It is a second, independent axis, so if the
two disagree that is itself the finding.

---

## 2. Estimand and units

**The unit is a group-network pair.** Ten groups per network, formed inside each network separately so
that a group is never defined by pooling two protocols.

**The estimand is the group's trend**, the unweighted mean of its member species' slopes in
°latitude per decade, with the standard error propagated from the members' own.

**Three quantities are reported and each answers a different question:**

1. **Group-level signal**: the median |slope| over its own standard error. At species level this is
   `1.69`. Above 2 and a group's trend is individually distinguishable from no trend, which is the
   whole point of grouping.
2. **Coherence — an intraclass correlation**: between-group variance over total variance in the
   species slopes, with the estimation-error term removed as Phase 1l removed it. **This is the check
   that the grouping is not decoration.** Near zero means the species inside a group behave no more
   alike than species in different groups, and the group mean is another mixture wearing a better
   name.
3. **The paired disagreement at group level**: Phase 1l's method-to-species ratio, recomputed with
   groups as the unit. Species level gave `1.17`.

### Known problems, before any result

- **A decile of latitude is not an ecological group.** Family, migratory strategy and body size are
  what the literature would use and none is in the lake — `taxon_key` and `taxon_label` are all the
  schema stores, so an ecological grouping needs a GBIF rank lookup and a new ingest. Latitude is a
  proxy chosen because it is free and non-circular, not because it is right.
- **Averaging cannot fix a systematic protocol difference.** If two programmes differ in the same
  direction for every species, group means differ by the same amount and quantity 3 will not improve.
  That outcome would be more serious than the one it replaces, and it is the reason quantity 3 is
  registered rather than assumed.
- **Ten groups is a small family.** The binomial chance bar at ten units and a 5% rate is 2, so a
  count of significant groups can barely be read. The median is primary, as in Phase 3h.
- **Groups are formed per network, so the two networks' deciles hold different species.** For the
  paired test only species present in both are used, and their group is taken from the network being
  measured — so a species can sit in decile 4 of one and decile 5 of the other. That is a property of
  the data, and it is reported rather than forced.

---

## 3. Predictions

1. **The group-level median |slope|/standard error exceeds 2**, against `1.69` at species level.
2. **The noise-corrected intraclass correlation exceeds 0.10.** Latitude explains at least a tenth of
   the species-level variation in trend. Registered as the falsifiable form of "the grouping is worth
   making".
3. **The group-level method-to-species ratio is below `1.17`.** Averaging reduces the share of a
   comparison that is instrument.
4. **Grouping by latitude gives a higher intraclass correlation than grouping by range extent.**
   Where a species lives matters more than how widely it is spread.

---

## 4. Stop conditions

- **Fewer than eight groups carry five member species in both networks.** Publish as a coverage
  statement and claim nothing.
- **Prediction 2 graded false — the intraclass correlation is at or below 0.10.** Then the grouping is
  decoration: report it as such, do not interpret quantities 1 or 3, and do not propose a successor
  that groups on latitude again.

---

## 5. What this cannot establish

- **Nothing causal.** Groups of latitude are not a mechanism, and no driver enters this.
- **Not that the right grouping has been found.** A negative here rules out latitude deciles, not the
  owner's idea — an ecological grouping is the version worth testing and it needs an ingest first.
- **Not that a good intraclass correlation makes Phase 1k's network medians publishable.** That is
  Phase 1l's stop condition and only its own successor can lift it.
- **Not anything about the other networks.** Sweden is the only pair, so quantity 3 exists nowhere
  else, and `bbs` can answer 1 and 2 only.

---

## Results — run 2026-08-23

Window 1996–2024. Ten groups per network per axis, formed inside each network.

| axis | network | groups | species each | group signal | ICC corrected | ICC raw |
| --- | --- | --- | --- | --- | --- | --- |
| where it lives | `sbs_point_counts` | 10 | 18 | **5.70** | **0.186** | 0.160 |
| where it lives | `sbs_fixed_routes` | 10 | 20 | 1.94 | 0.087 | 0.063 |
| where it lives | `bbs` | 10 | 55 | **6.23** | 0.076 | 0.062 |
| how widely spread | `sbs_point_counts` | 10 | 18 | **5.42** | **0.189** | 0.162 |
| how widely spread | `sbs_fixed_routes` | 10 | 20 | 1.14 | 0.027 | 0.020 |
| how widely spread | `bbs` | 10 | 55 | **7.51** | 0.095 | 0.077 |

Species level, for comparison: signal `1.69`, method-to-species ratio `1.17`.

**Paired at group level, where it lives:** ratio `1.15` across 10 groups, against `1.17` at species
level.

### Grading

**Prediction 1 — TRUE in two networks of three.** The group signal is `5.70` and `6.23` on the
primary axis against `1.69` at species level, a 3.4- and 3.7-fold improvement. That is what averaging
about seventeen and fifty-five independent estimates should give — the square root of the group size
is 4.1 and 7.4 — so the mechanism is exactly the one the proposal predicted. `sbs_fixed_routes` misses
at `1.94`, and it is the shortest network in the lake at 29 usable years.

**Prediction 2 — FALSE.** The corrected intraclass correlation clears its registered floor of `0.10`
in **one network of three** on the primary axis: `0.186` for point counts, `0.087` and `0.076` for
the other two. Where a species lives explains between eight and nineteen percent of the variation in
how it moved.

**Prediction 3 — TRUE on the letter and empty in substance.** `1.15` against `1.17`. The registered
prediction was that averaging reduces the instrument share of a comparison, and it technically did, by
two hundredths. Recorded as true because that is what it says, and read below as the opposite of
encouraging.

**Prediction 4 — FALSE.** Latitude does not beat range extent: it wins in `sbs_fixed_routes`
(`0.087` against `0.027`) and loses in both others (`0.186` against `0.189`, `0.076` against `0.095`).
Neither axis is better, and both are weak.

### The stop condition fires, and what it means

§4 registered that a false prediction 2 means **the grouping is decoration** — report it as such, do
not read quantities 1 and 3 as validation, and do not propose a successor that groups on latitude
again. That is what happens.

**The two results together are the finding, and they are not in conflict.** Averaging seventeen
species raises the signal by roughly the square root of seventeen *whether or not those species belong
together*. So a group signal of 5.70 beside an ICC of 0.08 does not mean the grouping worked; it means
**the groups are precise measurements of aggregates that are mostly arbitrary.** That is the failure
§1 of this note named in advance — "another mixture wearing a better name" — and naming it in advance
is the only reason the improvement in quantity 1 is not being reported as a success.

So the proposal is right about the problem and this attempt is wrong about the solution:

- **The noise diagnosis holds.** One species is too noisy to read and grouping fixes that arithmetic
  completely. There is a usable level between one species and all of them.
- **Latitude and range extent do not find it.** They are the two axes obtainable from this lake
  without an ingest, and they explain a tenth of the variation. What makes two species move alike is
  not mainly where they live or how widely they are spread.

### And the protocol disagreement is worse than Phase 1l could tell

`1.17` to `1.15` is the important null here. Phase 1m was registered with the warning that averaging
cannot fix a systematic protocol difference — if two programmes differ in the same direction for
every species, their group means differ by the same amount. Grouping seventeen species at a time
changed the ratio by two hundredths, so **the disagreement does not average out.** It is not
species-specific noise in the protocols; the two programmes differ systematically.

That is the more serious of the two possibilities, and it means Phase 1l's stop condition on Phase
1k's distribution medians stands on firmer ground than when it fired.

### What the successor has to fix

1. **An ecological grouping needs an ingest.** Family, order, and migratory strategy are what the
   literature groups on, and the lake stores only `taxon_key` and `taxon_label`. A GBIF rank lookup is
   small, and it is now the *tested* prerequisite for the owner's proposal rather than a guess about
   one — this phase ruled out the free proxies rather than the idea.
2. **The systematic half of the protocol difference needs its direction measured.** If the two
   programmes differ by a roughly constant offset, that is a calibration and correctable. If the
   difference varies with something, that something is the explanation. Neither has been looked at.
3. **`sbs_fixed_routes` fails every measure here** and is the shortest network. Whether that is length
   or protocol is still not separable, and it was the successor's job in Phase 1l too.
4. **Footprint remains confounded** — 33 consistently sampled cells against 84 — for the third phase
   running. It should be restricted before any of the above.
