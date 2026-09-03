# Phase 2e — is where an animal moved the population's, rather than the sea's or the air's?

**Status: pre-registered 2026-09-03, before any abundance trend has been fitted.** No abundance index
exists per species-survey pair or per species-network in this repository, no range-extent series has
been computed, and no latitude shift has ever been set beside a change in numbers. What *was* looked
at is in §1, and all of it is published.

#80. The first of the three studies the owner opened on 2026-09-02 with the question *is it just the
temperature really?* — and the one that bears on the leg of the spine with no explanation at all.

---

## Why this note exists

The synthesis (`synthesis-2026-09.md`, claim 2) holds seven measured nulls under one sentence: **where
animals are does not follow warming.** Phase 3k added that most of what the trawl surveys report as
fish moving is where the ships went. What is left over is a spread of latitude shifts that neither
temperature, nor depth, nor oxygen, nor the sea, nor the species explains. A fact with that many
failed explanations is an unfinished result.

Every driver tried against *where* has been a property of the environment. None has been a property
of the **population**. A species whose numbers are rising occupies new cells and its centroid moves
toward them; one whose numbers are falling retreats toward wherever it persists, and the centroid moves
there. Neither needs a degree of warming. The abundance–occupancy relationship is among the most
replicated patterns in ecology, and this lake has never looked at it, although every count source in
it carries the numbers: catch per area swept in the trawls, individuals per route-run in the bird
schemes.

**The animal-specific outlook.** The unit is the species in its survey, as `marine-null`'s is. If the
population axis sorts the movers from the stayers where the environmental axes did not, the answer to
*why did this species move* is a fact about that species' numbers, which is a different kind of why
from a temperature — and one the fisheries and the count schemes can act on.

**Which leg of the spine this bears on.** Claim 2, *where does not follow warming*, gains either its
first positive explanation or one more named null; and claim 3's *where* half — the animal does not
organise where it moves — is tested on the one axis that is a property of the animal's numbers rather
than of its name.

---

## 1. What was looked at before this was written

| what | value | where |
| --- | --- | --- |
| pooled marine latitude shift | median −0.011 °lat/decade, 2,240 pairs, IQR spanning zero | `marine-null` |
| between-survey heterogeneity, drift in the design | residual Q 77.3 against 25.0; drift +0.82 ± 0.29 | Phase 3k |
| warming against shift | +0.04 ± 0.18, and −0.12 ± 0.12 with drift | Phases 3e, 3k |
| thermal axes as a mixture | no spread beats its null; coherence ≤ 0.035 | Phase 3j |
| species against survey, over chance | +0.12 against +0.14 | Phase 3k |
| bird network medians, withheld | +0.052, +0.097, +0.034 °lat/decade; IQRs spanning zero | Phase 1k |
| a single species' latitude trend | 1.69 standard errors from zero | Phase 1l |
| free grouping axes on birds | coherence 0.03–0.19 against a floor whose chance level is now known to vary | Phases 1m, 1o, #78 |

**Not looked at:** any abundance index, any abundance trend, any range-extent series, any join of
either to a latitude shift, in any realm.

---

## 2. Estimand and unit, with the known problems first

**The unit is the species in its survey**: the species-survey pair for the trawls, `marine-null`'s own
2,240; the species in its network for `bbs`, `sbs_point_counts` and `sbs_fixed_routes`, on Phase 1m's
1996–2024 window and its species table, called rather than copied.

**Three quantities per unit**, all on the consistent footprint the latitude trend was fitted on:

- **`L`, the latitude trend** per decade, with its standard error — the published one, unchanged.
- **`N`, the abundance trend**: the slope per decade of the natural log of the yearly index, where the
  index is the species' summed catch per unit effort across the year's sampling events divided by the
  number of events — hauls for a trawl, route-runs for a scheme — over years the species was caught,
  at least fifteen of them (twenty for the birds, matching their latitude trends).
- **`E`, the extent trend**: the slope per decade of the log of the number of consistent cells the
  species was caught in that year, over the same years.

### The five things asked

1. **Does extent follow abundance?** Spearman's correlation of `E` with `N` within each survey. The
   abundance–occupancy check: if numbers and occupied cells do not move together here, the index is
   not measuring numbers and nothing below is interpreted.
2. **Does the size of a shift follow the size of a change in numbers?** Pairs cut into terciles of
   `|N|` within survey; the top tercile's median `|L|` against the bottom's, against a null that
   shuffles the tercile labels within survey, 1,000 draws — Phase 3j's design with a population axis
   in place of a thermal one.
3. **Its control, registered with it.** The same spread on terciles of the latitude trend's own
   standard error. A rare species has a noisy `N` and a noisy `L`, and the magnitude of a noisy
   estimate is inflated, so `|N|` and `|L|` can rise together through rarity alone. The abundance
   spread counts only if it exceeds the precision spread.
4. **Does the direction follow?** Terciles of signed `N`: the top tercile's median `L` against the
   bottom's, same null. Growing species moving poleward more than declining ones is the leading-edge
   story the literature tells for northern shelves; it is registered as less likely than the
   magnitude result, because a contraction's direction depends on where the core is.
5. **Is the change in numbers the species' or the sea's?** For taxa caught in five or more surveys,
   `N`'s coherence grouped by species against grouped by survey, each with its permutation chance
   level, exactly as Phase 3k's unregistered diagnostic computed it for `L` — registered here.

Coherence of the tercile groupings is reported beside every spread. Three groups over hundreds to
thousands of units have a chance level near `2 / n`, which is negligible, so Phase 1m's 0.10 floor is
readable here in a way #78 says it was not for 171 groups.

### Known problems, before any fit

- **`N` and `L` come from the same rows.** A decomposition, not an instrument; nothing here is causal.
- **Catch numbers, not biomass; a mean over events, not a design-weighted index.** A survey's index
  built properly weights strata; this one weights hauls. It is the quantity the lake supports and it is
  the same for every unit, which is what the comparison needs.
- **Zero years break a logarithm.** Years the species was not caught are absent from its index and its
  extent, and a species caught in fewer than fifteen years has no trend. That selects for the common,
  as `marine-null`'s own floor does.
- **Rarity inflates both magnitudes.** Stated above and controlled by the precision axis.
- **Effort for the birds is one route-run**, so the bird index is a mean count per run; the Swedish
  point counts carry hours and are divided by them. Observer turnover moves counts and is not modelled.
- **Survey dependence.** Marine pairs inside one survey share its gear and water; every interval is a
  survey-clustered bootstrap with the naive one beside it, and the nulls shuffle within survey.
- **The bird legs have no published median to calibrate against.** Phase 1k's are withheld. The
  species tables are `phase1m._species_table`, called, and that is the whole of the calibration there.
- **Nothing causal, and nothing about why numbers changed.** Fishing, habitat, food and climate all
  move numbers; this note says whether the numbers moved the centroid, not what moved the numbers.

---

## 3. The design, fixed before any fit

- **Calibration.** Pooling every marine pair reproduces `marine-null`'s −0.011 to three significant
  figures, by calling `phase1b.analyse` itself.
- **Marine panel** from `phase1b.survey_unit(phase1b.load())` through `range_metrics.to_cells` and
  `consistent_footprint`; events are distinct `site_id` per year; `N` and `E` at a fifteen-year floor.
- **Bird panels** from `phase1m._species_table(source, (1996, 2024))` for `L`, and
  `phase1k.load_counts` on the same window for the index; events are distinct `(site_id,
  period_start)` per year; `N` and `E` at a twenty-year floor.
- **Terciles, spreads and nulls** through `phase3j._assign`, `_spread` and `_null_spread`, unchanged;
  coherence through `phase1m._icc`; the species-against-survey question through `phase3k.coherence`
  and `phase3k.chance_level`, unchanged.
- **Seed** `SEED = 1`; 1,000 draws.
- **Fixed before any number is seen:** the index definition, the floors, the tercile count, the window,
  the null construction, the control, and that the deliverable is one row per unit before any median.

---

## 4. Predictions

1. **Calibration reproduces −0.011.** *Check.*
2. **Extent follows abundance.** Spearman's `E` on `N` is positive and beats its within-survey
   shuffle null in the marine record and in every bird network. *Check* — the abundance–occupancy
   relationship; a failure is a failure of the index.
3. **The size of the shift follows the size of the change in numbers, in the marine record.** The
   top `|N|` tercile's median `|L|` exceeds the bottom's, the spread beats its null, **and exceeds the
   precision-axis spread.** *Discovery, and the substantive one.*
4. **The same in at least two of the three bird networks.** *Discovery.*
5. **The direction follows: growing species shift poleward more than declining ones, in the marine
   record.** Signed `N` terciles; spread positive and beats its null. *Discovery, registered as less
   likely than 3.*
6. **The population axis is more coherent than any thermal axis was.** The `|N|` tercile grouping's
   corrected coherence exceeds **0.035**, Phase 3j's best. *Discovery.*
7. **Changes in numbers are the species' more than the sea's.** For taxa in five or more surveys,
   `N`'s coherence by species exceeds its coherence by survey **once each is measured over its own
   chance level.** *Discovery.* The chance-corrected form, because Phase 3k showed the raw one is not
   one scale.

---

## 5. Stop conditions

- **Calibration misses** → nothing is interpreted.
- **Prediction 2 fails in a leg** → that leg's index does not measure numbers, and predictions 3 to 7
  are not interpreted for it.
- **Predictions 3 and 5 both fail in the marine record** → *where* is not the population's either, on
  this axis. Claim 2 of the synthesis gains that named null, `marine-null`'s caveat gains one sentence,
  and no eighth explanation is reached for in this note.
- **Prediction 3 passes on the spread and fails the precision control** → the result is rarity and is
  published as that, not as abundance.
- No floor, window, tercile count, null or control is revisited after any number is seen.

---

## 6. What this cannot establish

- **Not causation.** A centroid that moves when numbers move has told us the two co-move.
- **Not why numbers changed.** Fishing pressure, habitat, prey and climate are all upstream of `N` and
  none is in this design; RAM Legacy is a nominated candidate and not in the lake.
- **Not the rare species**, which the fifteen-year floor on the index removes by construction.
- **Not the ocean or the continents:** northern shelf trawls, one North American and two Swedish
  bird schemes.
- **Not timing.** Every quantity here is a place or a number, and the spine's *when* is untouched.
