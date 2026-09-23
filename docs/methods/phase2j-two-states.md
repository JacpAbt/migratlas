# Phase 2j — does an animal answer a hard winter by staying less, or by moving faster?

**Status: pre-registered 2026-09-13, before any state model has been fitted to any track in this
repository.** No step length has ever been computed here — Phase 1h refused to, for a stated reason
reproduced in §2 — no turning angle exists, and no track has ever been split into a moving state and
a still one. What *was* looked at is in §1, and all of it is published. A coverage audit ran before
this note: it counted animals, years, fix intervals and driver footprints, and fitted nothing.

#87, and the third of the three tests ADR 0019 registers. It is the only one that observes both
states directly. A migration is movement and stationary time; a displacement measures their product
and can move for either reason, so an animal that travels the same distance by stopping less and an
animal that travels it by moving faster are the same number to every fit this project has published.

---

**Which leg of the spine this bears on.** Claim 3, which says the animal decides its own response,
and ADR 0019's central conjecture, which says the states have different cues. It bears on no
published number directly: this is the terrestrial counterpart to Phase 2i's aerial duty cycle, and
its first job is to produce the split rather than to overturn anything.

---

## 1. What was looked at before this was written

- **Phase 1h** measured, per animal-year, the great-circle **displacement** between a winter position
  and a summer one, for the Yahatinda elk and the Svalbard reindeer. It chose displacement
  deliberately: *"a displacement needs one fix near each end"*, where a path length is contaminated
  by how often the collar fired. Its prediction 2 was that displacement must **not** track the fix
  rate, and it held at ρ = −0.047 and +0.092.
- **Phase 3a** fitted herd displacement against green-up and snow depth per herd-year, and its
  prediction 4 registered **no significant skill in either herd** — the Phase 1h null re-expressed.
- **`era5_land`** holds ERA5-Land monthly **snow depth in metres** at the two herd ranges,
  2001–2024, one site per herd, fetched because the elk and reindeer literature names snow as the
  covariate that matters most. It is the locomotion-cost variable.
- **The lake's tracks**: 5.9M fixes over seven Movebank sources and five species — Yahatinda elk,
  BC mountain caribou, Missouri bison, Bylot arctic fox (GPS and Argos), Svalbard reindeer and
  Hebblewhite's wolves.

**Not looked at, anywhere:** any step length, any turning angle, any state. The decomposition of a
displacement into *how long an animal spent moving* and *how fast it moved while moving* does not
exist in this repository, and Phase 1h's reason for avoiding it is this note's hardest problem.

---

## 2. Estimand and unit, with the known problems first

**The unit is an animal-year.** Per source, a two-state hidden Markov model is fitted to the
sequence of steps: **step length** with a gamma emission and **turning angle** with a von Mises
emission, two states, a 2×2 transition matrix, fitted by Baum–Welch over all animals of that source
at once. States are ordered by mean step length after fitting, so "encamped" and "travelling" are
labels assigned by size and never by hand.

**Three estimands, per animal-year.**

- **A — the travelling fraction.** The mean posterior probability of the travelling state. This is
  the terrestrial state split, and the counterpart of Phase 2i's duty cycle.
- **B — the travelling step length.** The posterior-weighted mean step length in the travelling
  state, in kilometres per step at the source's own interval: the speed while moving.
- **C — the answer to snow.** For the two herds with a driver, each of A and B regressed across
  years on the winter mean snow depth at that herd's range, per animal and pooled.

**"Stays less" is a rise in A; "moves faster" is a rise in B.** They are separable here and are the
same number in a displacement.

### Known problems, stated before any number is seen

- **A step length tracks the collar, and this is the deepest problem.** Phase 1h refused path
  lengths for exactly this reason. Three things are done about it and none of them is a fix: steps
  are kept only where the interval is within **±20%** of the source's own modal interval, so every
  step compared is a step over a comparable time; the model is fitted per source, so no interval is
  compared across sources; and **prediction 4 is the registered control** — an animal-year's
  travelling fraction must not correlate with that year's median fix interval beyond Phase 1h's own
  bar of |ρ| < 0.2. **If that fires, nothing else in this note is read.**
- **The states are statistical.** "Encamped" and "travelling" are two gamma components with a
  Markov chain between them. They are named for their step lengths and correspond to behaviour only
  under an assumption this design cannot test. No animal is claimed to have been doing anything.
- **A fitted mixture is not a fact about an animal.** Fitting per source pools animals of different
  sexes, ages and years into one emission, which is a strong assumption and the reason prediction 7
  asks whether individuals differ at all.
- **Snow at a herd centroid is not snow under an animal.** One ERA5-Land cell per herd, monthly,
  against animals ranging over a degree or more.
- **Argos is not GPS.** `movebank_bylot_fox_argos` has a 24-hour median interval, a 20° latitude
  span and Doppler positioning whose error is kilometres. It is **excluded** and reported as
  excluded; only its GPS sibling enters.
- **Short records.** Only the elk (23 years) and the caribou (21) span two decades; the bison,
  fox, reindeer and wolves run 8 to 14 years. The driver half is therefore the two herds that have
  a driver, and every other source contributes the split and nothing else.
- **Nothing causal**, and no mechanism for any snow response.

**Floors.** A step is usable if its interval is within ±20% of the source's modal interval and both
its endpoints are finite. An animal-year needs **200** usable steps; a source needs **30** usable
animal-years; a herd-year needs **5** animals before it enters the snow fit. Winter is months 1–3,
Phase 3a's own window. `SEED = 1`, 1,000 bootstrap draws resampling animals, 200 EM iterations or a
relative log-likelihood change below 1e-6.

---

## 3. The design, fixed before any number is seen

1. **Load** each source's `TRACK` rows through `lake.reader.scan` with an explicit `source_id`,
   sorted by animal and time.
2. **Steps.** Great-circle distance and turning angle between consecutive fixes of one animal,
   keeping only intervals within ±20% of the source's modal interval; a run of kept steps is one
   sequence, and sequences shorter than 10 steps are dropped.
3. **Fit** the two-state model per source by Baum–Welch: gamma step lengths by weighted moments,
   von Mises angles by the weighted circular mean and the standard concentration approximation,
   transitions from the posterior pair probabilities. States ordered by mean step length.
4. **Decode** with forward–backward posteriors; per animal-year take A and B as §2 defines them.
5. **Snow.** `era5_land`'s winter mean per herd-year, joined to the herd's animal-years; A and B
   each regressed on it with animal-resampled intervals.
6. **The control.** Spearman correlation between an animal-year's travelling fraction and its
   median fix interval, per source, against Phase 1h's bar.
7. **Heterogeneity.** Cochran's Q across individuals' snow responses, against its chi-square bar.

---

## 4. Predictions

1. **Coverage.** At least four sources yield 30 usable animal-years, and both herds yield 10
   herd-years with snow. *Check.*
2. **The states separate.** The travelling state's mean step length is at least **three times** the
   encamped state's in every fitted source. *Check: a two-state model whose states do not separate
   has found nothing, and that source is not interpreted.*
3. **Most of the time is spent still.** The median travelling fraction is below **0.5** in every
   source. *Discovery, registered as expected: the terrestrial counterpart of Phase 2i's 0.26.*
4. **The split does not track the collar.** |ρ| between an animal-year's travelling fraction and its
   median fix interval is below **0.2** in every source. *Control, and the one Phase 1h's refusal
   makes load-bearing.*
5. **A deeper-snow winter raises the travelling fraction**, with an animal-resampled interval
   excluding zero, in at least one of the two herds. *Discovery, registered with its direction: snow
   buries forage, so an animal must spend more of its time searching.*
6. **It does not raise the travelling step length.** The answer is *staying less*, not *moving
   faster*, in whichever herd prediction 5 holds. *Discovery, and the one that makes the state split
   worth having: a displacement cannot tell these apart.*
7. **The response is the animal's.** Cochran's Q across individuals' snow responses clears its bar
   in at least one herd. *Discovery, mirroring claim 3.*

---

## 5. Stop conditions

- **Prediction 1 fails** → the coverage table is published and nothing else is interpreted.
- **Prediction 2 fails for a source** → that source is dropped and reported as unseparated.
- **Prediction 4 fires in a source** → that source's split is **not interpreted**, and if it fires
  in both herds the note reports that this instrument measures the collar and makes no state claim
  at all. Phase 1h's refusal would then stand vindicated and the successor is a state-space model
  that estimates position error rather than an HMM that assumes it away.
- **Predictions 5 and 6 both hold** → the synthesis gains **the terrestrial state answer**: a hard
  winter is answered by staying less rather than by moving faster, beside Phase 2i's aerial duty
  cycle, and ADR 0019's conjecture has its first direct observation of both states.
- **Prediction 5 fails** → snow does not move the time budget either, which extends Phase 3a's
  herd-displacement null from the product to both of its factors — a stronger null than the one
  published, and it is published as such.
- **Prediction 3 alone** changes no claim; it is the split, and it is published whatever the rest
  does.
- No source, floor, window or bar is revisited after any number is seen.

---

## 6. What this cannot establish

- **Not causation**, and no mechanism.
- **Not behaviour.** Two gamma components are not two activities; §2's second known problem stands.
- **Not a law about species.** Five species, two with a driver, all northern.
- **Not the migrants of the other realms.** No bird, no fish, no insect appears here.
- **Not an escape from the collar.** The interval filter and prediction 4's control reduce the
  fix-rate confound; a state-space model that estimates location error would address it, and this
  is not one.
- **Not snow under the animal.** One monthly cell per herd.

---

# Results — run 2026-09-13

`make report-phase2j`, run as a pair twice: once as registered and once after the two corrections
below. Both pairs were identical line for line.

## Two corrections, both found in the first pair's own output

**Correction 1 — the code's control gate was stricter than the registration.** §5 drops *a source*
whose split tracks the collar and reads the rest; the module refused to read anything if the control
fired anywhere. The note is the authority and the gate now matches it.

**Correction 2 — the heterogeneity statistic was degenerate, and provably so.** The first run gave
Cochran's Q as **1892.0** for the elk over 44 animals and **1560.0** for the reindeer over 40. Those
are 44 × 43 and 40 × 39 exactly: the code used one pooled spread as every animal's standard error,
which makes `Q = n(n − 1)` identically. A statistic that is a function of the sample size carries no
information, so it was **quarantined and not scored in either direction**, and each animal's error is
now its own, from its own regression residuals. The corrected Q varies as a real statistic should —
33.4, 331.5, 373.9 and 5082.2 against bars of 54.6 and 59.3 — and prediction 7 is graded on it.

## The sources

| source | animals | animal-years | interval | separation | travelling fraction | travelling step | fix-rate ρ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Yahatinda elk | 128 | 264 | 2.0 h | 6.25× | 0.751 | 0.400 km | −0.012 |
| BC mountain caribou | 69 | 146 | 7.0 h | 5.29× | 0.694 | 0.818 km | +0.118 |
| Missouri bison | 33 | 82 | 1.0 h | 11.62× | 0.737 | 0.187 km | **−0.442** |
| Bylot arctic fox (GPS) | — | 23 | — | — | — | — | dropped, under 30 |
| Svalbard reindeer | 48 | 222 | 2.0 h | 6.71× | 0.644 | 0.215 km | +0.000 |
| Hebblewhite wolves | 39 | 48 | 2.0 h | 56.31× | 0.523 | 1.869 km | **+0.269** |

**The control fired in two of five**, so the bison and the wolves are dropped as §5 says and the
elk, caribou and reindeer stand. It did not fire in either herd with a driver.

## The answer, and the failure that frames it

**The registered split did not appear.** Prediction 3 said the median travelling fraction would sit
below 0.5 in every source. It sits at **0.52 to 0.75 in all five** — the long-step state is the
*majority* state everywhere. At a one-to-seven-hour fix interval an ungulate is almost never
motionless between fixes, so what a two-state gamma mixture separates here is **ordinary movement
from unusually short steps**, not transit from residence. The labels this note registered —
"encamped" and "travelling" — are **not supported by the result**, and every number below is a
statement about a short-step state and a long-step state rather than about an animal standing still.
**ADR 0019's direct observation of both states is not achieved at these intervals**, and that is the
most important thing in the run.

**Within the split that does exist, the two herds answer snow in opposite directions.**

| herd | years | fraction per metre of snow | step km per metre of snow |
| --- | --- | --- | --- |
| Yahatinda elk | 16 | −0.0978 [−0.2034, +0.0184] | **−0.1319 [−0.2163, −0.0288]** |
| Svalbard reindeer | 11 | **+0.2425 [+0.1302, +0.3448]** | **+0.0790 [+0.0475, +0.1090]** |

**The reindeer answer a snowier winter in both states at once**: more of their time in the long-step
state *and* longer steps when they take them. **The elk answer it in one state and the other way**:
shorter steps, with no detectable change in the time budget. Neither is "stays less rather than
moves faster" — the reindeer do both and the elk do neither.

**A displacement cannot tell these apart**, and that is the design's one clear success. Phase 1h
measured the displacement in these two herds and Phase 3a found it answered nothing; here each herd
has a response, in different components and with opposite signs, which a product of the two would
have averaged toward the null Phase 3a published.

## The predictions, graded

**1 — TRUE** (check). Five sources of six fitted; both herds cleared ten shared years (16 and 11).

**2 — TRUE** (check). 5.29× to 56.31×, all above three. The wolves' 56× is noted as suspicious: an
extreme separation is what one state capturing a handful of very long steps looks like, and the
wolves are dropped by prediction 4 in any case.

**3 — FALSE**, in all five sources and not marginally. See above; this failure is the run's result.

**4 — FALSE**, with its registered consequence applied. |ρ| clears 0.2 in the bison (−0.442) and the
wolves (+0.269), which are dropped; it is quiet in the elk, caribou and reindeer. Phase 1h's refusal
of path lengths is **half vindicated**: the collar does reach the split in two of five records, and
the two it reaches are the two with the shortest and the most irregular sampling.

**5 — TRUE**, in the reindeer: +0.2425 [+0.1302, +0.3448] per metre of snow.

**6 — FALSE.** The reindeer's travelling step rose too, +0.0790 [+0.0475, +0.1090].

**7 — TRUE**, on the corrected statistic. Q clears its bar for the elk's fraction (5082.2 / 59.3),
the elk's step (373.9 / 59.3) and the reindeer's step (331.5 / 54.6), and does not for the
reindeer's fraction (33.4 / 54.6) — so the animals within a herd differ in three of the four fits.

Four of seven, with two corrections. The three failures are the informative ones.

## The stop conditions, and what they do

- Prediction 1 held → the sources were interpreted.
- Prediction 2 held → no source was dropped for failing to separate.
- **Prediction 4 fired in two sources** → the bison and the wolves are not interpreted. It did not
  fire in both herds, so the snow fits stand.
- **Predictions 5 and 6 did not both hold** → the registered "terrestrial state answer" does not
  reach the synthesis. The reindeer answer in both components and the elk in one, and neither is
  the sentence §5 pre-committed.
- Prediction 5 did not fail → Phase 3a's herd-displacement null is **not** extended to both factors;
  the opposite happened, and each herd has a response the displacement did not show.
- **Prediction 3's failure blocks the state reading entirely.** Nothing here is published as a
  residence-versus-transit split, and the synthesis gains the failure rather than the split.
- No source, floor, window or bar was revisited after any number was seen.

## What the successor has to fix

1. **A shorter interval, or a different state variable.** The Bylot fox fires every four minutes and
   was dropped for having too few animal-years, not too few fixes; at that resolution a motionless
   state exists. The question is worth asking where the instrument can see it.
2. **Persistence, not step length.** If an ungulate is always moving, the residence state is a
   *bounded* movement rather than a still one, and the quantity that separates them is net
   displacement over a window against path length over the same window — a straightness ratio.
   That is a different model and it is the one this record can probably support.
3. **The elk and reindeer disagreement needs a mechanism.** Snow impedes locomotion and buries
   forage, and the two herds may sit on opposite sides of which one binds. No trait table here can
   say.
4. **The wolves' 56× separation** wants looking at before that source is used for anything.

## What this does not establish

- **Not residence and transit.** Prediction 3 failed; the states are short-step and long-step.
- **Not causation**, and no mechanism for either herd's snow response.
- **Not behaviour.** Two gamma components are not two activities.
- **Not a law about species.** Three readable sources, two with a driver, all northern.
- **Not an escape from the collar** in the two sources where the control fired.
- **Not snow under the animal.** One monthly ERA5-Land cell per herd.
