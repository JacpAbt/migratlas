# Phase 1o — is the level between one species and all of them a taxonomic one?

**Status: pre-registered 2026-09-01, before the rank lookup has been fetched.** No family or order
has been resolved for any taxon key in this lake, no taxonomic group has been formed, and no
group-level slope or coherence exists in this repository. What *was* measured first is the count of
distinct taxon keys per network, quoted in §1, because the design has to know whether the lookup is
a thousand calls or fifty thousand. Nothing else.

#66. Phase 1m's successor on the axis Phase 1m could not reach, and Phase 3j's on the axis Phase 3j
did not cover.

---

## Why this note exists

Two phases have now closed the cheap ways to find a level between one species and all of them.

**Phase 1m ruled out the free descriptive axes.** Grouping Swedish and North American birds by where
a species lives and by how widely it is spread raised the group signal from 1.69 to 5.70 — exactly the
square root of the group size, so arithmetic rather than insight — while the noise-corrected coherence
cleared its 0.10 floor in one network of three (0.186, 0.087, 0.076). Its stop condition fired and its
verdict was that the groups are *precise measurements of aggregates that are mostly arbitrary*.

**Phase 3j ruled out the free environmental axes**, in a different realm: cutting the marine pairs by
thermal position, warming rate and depth produced no spread beating its null and no coherence above
0.035.

Phase 1m's own closing item is what remains:

> **An ecological grouping needs an ingest.** Family, order, and migratory strategy are what the
> literature groups on, and the lake stores only `taxon_key` and `taxon_label`. A GBIF rank lookup is
> small, and it is now the *tested* prerequisite for the owner's proposal rather than a guess about
> one — this phase ruled out the free proxies rather than the idea.

So the owner's proposal — cluster species that do similar things, rather than reading one at a time or
massing them by taxon — has one untried axis left, and it is the one the literature actually uses.

## What is *not* in this note, and it is a third of the proposal

**Migratory strategy is not obtainable here.** GBIF's Backbone is a taxonomy, not a trait database:
it gives family, order and class and says nothing about whether a bird migrates. The trait databases
that would (EltonTraits and its relatives) are a new source, a new licence question and a new registry
entry, and none of that is in this note. So #66 is being answered two-thirds: **family and order, not
strategy.** Recorded here rather than discovered in the results, because a note claiming to test "the
ecological grouping" while testing only its taxonomic half would be overstating itself.

---

## 1. What was looked at before this was written

Everything Phase 1m and Phase 1l published, and one new measurement — the size of the lookup:

| network | distinct taxon keys |
| --- | --- |
| `bbs` | 679 |
| `sbs_fixed_routes` | 279 |
| `sbs_point_counts` | 270 |
| `ukbms_phenology` | 59 |

About a thousand keys once the two Swedish networks' overlap is removed, which is a few minutes of
cached lookups against an API this project already uses as its taxonomy spine. That is the whole of
the new information and it says nothing about any answer.

**What was not looked at:** any family, any order, any group, any group-level slope, any coherence.

---

## 2. Estimand and units, with the known problems first

**The unit is a group-network pair**, as Phase 1m's was: groups formed inside each network separately,
so a group is never defined by pooling two protocols.

**The estimand is Phase 1m's, unchanged, so the two are comparable rather than each judged on its
own terms.** Three quantities per axis per network:

1. **Group signal** — the median |group slope| over its own standard error. Species level is **1.69**.
2. **Coherence** — the noise-corrected intraclass correlation, `phase1m._icc`, called rather than
   reimplemented. **This is the primary**, for the reason Phase 1m established: averaging *n* species
   raises the signal by about √n whether or not they belong together.
3. **The paired disagreement at group level**, for the Swedish pair only, as Phase 1l and 1m computed
   it. Species level is 1.17; group level on the descriptive axes was 1.15.

**The floor is Phase 1m's registered 0.10**, inherited so that "family beats latitude" is a statement
about the axes and not about two differently-chosen bars.

### The two axes, fixed here

- **Family** — the substantive axis. What the literature groups on, and fine enough to separate the
  warblers from the waders.
- **Order** — the sensitivity, reported always and never promoted.

Both are properties of the animal and neither is a property of its trend, so the circularity Phase 1m
named and Phase 3i refused does not apply. Grouping on a taxonomy and measuring a slope introduces no
shared estimation error.

### Known problems, before any fit

- **Order is likely degenerate on these networks, and family may be too.** A temperate bird survey is
  mostly Passeriformes, so an order-level grouping probably puts a large majority of species in one
  group — and a grouping with one dominant group has a coherence near zero *by construction*, not
  because taxonomy is uninformative. The count of species in the largest group is therefore reported
  for every axis, and a dominant-group share above about two thirds makes that axis's coherence
  uninterpretable rather than low. **This is the most likely way this phase fails to answer its own
  question**, and it is written down before the fit.
- **Family is nested inside order**, so the two axes are not independent and a disagreement between
  them is a statement about granularity rather than two pieces of evidence.
- **Families are unequal.** Some hold one species. A group needs **five member species** to enter, the
  floor Phase 1m's stop condition used, and the count of species discarded by it is reported.
- **A thousand rank lookups is a thousand chances to mis-resolve.** The Backbone is asked about a key
  this project already resolved, so no name matching is involved and the failure mode is a key with no
  family rather than a wrong one. Keys that return no family are reported and excluded.
- **Three of the four networks are birds** and the fourth carries 59 taxa. The tilt Phase 1k recorded
  is unchanged and this phase makes it no better.
- **Nothing causal.** A family is not a mechanism.

---

## 3. The design, fixed before any fetch

- **The lookup.** For each distinct `taxon_key`, GBIF's Backbone classification, cached to disk on
  first fetch the way the per-source taxon-key caches already are. **Not a new registered source**:
  the Backbone is already this project's taxonomy spine and already the resolver every ingest calls,
  and this reads higher ranks from the same API for keys it already assigned. If that reading turns out
  to need a licence or an account it does not currently have, the phase stops and says so.
- **Then Phase 1m's machinery**, unchanged: `phase1m` for the group-level fit, `_icc` for coherence,
  `phase1l.split_difference` for the paired decomposition.
- **ADR 0016** on every group-level slope, since a family panel may fall below its floor of 30.
- **Seed** `SEED = 1`, as Phase 1k, 1l, 1m and 1n.

---

## 4. Predictions

1. **At least 90% of taxon keys resolve to a family.** A lower rate means the lookup is the finding.
2. **Family clears the 0.10 coherence floor in at least two networks of three.** Registered as the
   substantive expectation, and it is the thing the owner's proposal predicts: species in one family
   do similar things. Phase 1m's descriptive axes managed one of three.
3. **Family beats both of Phase 1m's descriptive axes** on coherence, in every network where both are
   computable. If taxonomy is not better than where-it-lives, the proposal's remaining axis is no
   better than the ones already ruled out.
4. **Order is less coherent than family**, or uninterpretable under §2's dominant-group rule. Coarser
   groups mix more.
5. **The paired disagreement does not improve at group level**: the Swedish ratio stays at or above
   1.15. Registered because Phase 1m already showed the protocol difference is systematic and Phase 1n
   has since shown it is a constant offset — an offset cannot be averaged away by any grouping, and a
   ratio that fell here would contradict two published results rather than add to them.

---

## 5. Stop conditions

- **Fewer than 90% of keys resolve.** Publish as a lookup statement; grade nothing else.
- **The dominant group holds more than two thirds of an axis's species.** That axis's coherence is
  reported as uninterpretable, not as low, and it grades no prediction.
- **Prediction 2 false** — family clears the floor in one network or none. Then the taxonomic axis
  joins latitude, range extent and the three environmental axes on the list of groupings that do not
  find the level, and **#66 is answered negatively**: the owner's proposal is right that one species is
  too noisy and wrong that a grouping this lake can build fixes it. That is a publishable answer and
  the note says it plainly rather than reaching for strategy as a rescue.
- **Prediction 5 false.** Then either Phase 1n's offset or Phase 1m's systematic finding is wrong, and
  the disagreement is the result — nothing else in this phase is interpreted until it is understood.
- No axis, floor, member minimum or seed is revisited after any number is seen.

---

## 6. What this cannot establish

- **Not the ecological grouping.** Two thirds of it: family and order, not migratory strategy. See
  above.
- **Not that no grouping works.** Five axes will have been tried after this one and all of them are
  axes this lake can build without a new source. A trait database is the untried direction and it is
  not this note.
- **Nothing causal, and nothing about why any species moved.**
- **Not that a coherent family means the members share a driver.** Families share ancestry, and
  ancestry correlates with body size, habitat and diet — a coherent family names a bundle, not a cause.
- **Not anything about the marine or aerial realms.** Three bird count networks and one butterfly
  scheme, all terrestrial by instrument.
- **Not a licence to publish Phase 1k's withheld medians.** Phase 1l's stop condition binds until its
  own successor lifts it, and Phase 1n has just re-confirmed the ratio above 1.

---

# Results — run 2026-09-01

`make report-phase1o`. **The lookup holds completely: 953 of 953 keys resolved to a family.** No key
came back without one, so nothing is excluded and the lookup is not the finding.

| network | axis | groups | species | dropped | largest group | signal | **coherence** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `bbs` | family | 30 | 459 | 61 | 11% | 2.84 | **0.094** |
| `bbs` | order | 16 | 515 | 5 | 53% | 1.83 | 0.059 |
| `sbs_point_counts` | family | 14 | 127 | 62 | 17% | 3.46 | **0.346** |
| `sbs_point_counts` | order | 7 | 167 | 22 | 51% | 2.39 | 0.235 |
| `sbs_fixed_routes` | family | 16 | 141 | 56 | 15% | 1.29 | **0.192** |
| `sbs_fixed_routes` | order | 8 | 179 | 18 | 51% | 0.86 | 0.051 |

Species level: signal **1.69**, paired ratio **1.17**. Phase 1m's descriptive axes: 0.186, 0.087,
0.076 on latitude and 0.189, 0.027, 0.095 on range extent, clearing the floor in one network of three.

## The answer, and the reason not to celebrate it yet

**Family is the first axis in five to clear the coherence floor in more than one network** — 0.346 and
0.192 against Phase 1m's 0.10 — and in both Swedish networks it roughly doubles the best descriptive
axis. On its face the owner's proposal is right and the level between one species and all of them is a
taxonomic one.

**And the pattern across the three networks is exactly what small-sample optimism looks like.**

| network | species | family coherence |
| --- | --- | --- |
| `sbs_point_counts` | 127 | 0.346 |
| `sbs_fixed_routes` | 141 | 0.192 |
| `bbs` | **459** | **0.094** |

The coherence falls monotonically as the panel grows, and **the one network that fails the floor is by
far the largest**. A noise-corrected intraclass correlation subtracts a mean squared standard error
from a total variance, and with few species the between-group term is itself poorly estimated and
biased upward. Three points cannot separate "family works better in Sweden" from "the estimate is
optimistic where the panel is thin", and this note does not pretend to.

So the honest statement is narrower than prediction 2's pass: **family is the best grouping axis this
project has tried, it is the first to clear the floor twice, and its ordering across networks is
consistent with the estimate being inflated in small panels.** What would settle it is a fourth count
network of a size between 141 and 459, which the lake does not hold.

## The predictions, graded

**1 — TRUE.** 100% of keys resolved.

**2 — TRUE.** Family clears the 0.10 floor in two networks of three, against Phase 1m's one.

**3 — FALSE, by 0.001.** Family had to beat both descriptive axes in every network where both are
computable. In `bbs` it is 0.094 against range extent's 0.095. In the two Swedish networks it wins
comfortably — 0.346 against 0.186 and 0.189, and 0.192 against 0.087 and 0.027 — but the registered
wording was "every network" and `bbs` is a network. Graded false on what it said, with the margin
stated so nobody has to wonder: one part in a thousand, in the network whose coherence is least
trustworthy for the reason above.

**4 — TRUE, in all three.** Order is less coherent than family everywhere (0.059 against 0.094, 0.235
against 0.346, 0.051 against 0.192), which is what coarser groups should do.

And §2's registered worry did **not** bite: the largest order holds 51–53% of each panel, under the
two-thirds threshold that would have made those rows uninterpretable. A temperate bird survey is
mostly passerines and that turned out to leave enough between-group variance to read. Recorded because
the note predicted this would be the most likely way the phase failed to answer itself, and it was
not.

**5 — TRUE, and emphatically in the direction registered.** The paired disagreement with families as
the unit is **1.348**, above the 1.15 floor and above both the species-level 1.17 and Phase 1m's
group-level 1.15. Grouping makes the protocol disagreement *worse*, which is exactly what Phase 1n's
constant offset predicts: an offset survives averaging untouched while the between-group scatter it is
compared against shrinks, so the ratio rises. Two published results agree with each other here rather
than one contradicting the other.

## What this settles about #66

**Two thirds of it, and the honest verdict is "the best axis yet, on a pattern that needs a fourth
network".** Family is not ruled out the way latitude, range extent, thermal position, warming rate and
depth were ruled out — it is the only axis of six to clear the floor more than once. But it is also
the only one whose per-network ordering tracks panel size that cleanly, and one of the three networks
fails.

**Migratory strategy remains untried**, and it is the third of #66 this note declared out of scope
before it ran. That is now the untested direction, and it needs a trait database — a new source, a new
licence question and a new registry entry.

## What this does not establish

- **Not that families share a driver.** Families share ancestry, and ancestry correlates with body
  size, habitat and diet. A coherent family names a bundle, not a cause.
- **Not that Phase 1k's medians can be published.** Prediction 5 went the wrong way for that: the
  protocol disagreement is worse at family level, so Phase 1l's stop condition binds harder rather
  than less.
- **Not migratory strategy**, and so not the owner's proposal in full.
- **Nothing about the marine or aerial realms.** Three terrestrial count networks.
- **Not a mechanism, a cause, or a licence to project.**
