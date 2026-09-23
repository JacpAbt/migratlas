# Phase 2g — did the cells that got wetter gain birds? The southern atlas's rain

**Status: pre-registered 2026-09-03, before the fetch.** No precipitation value exists at any southern
African atlas cell in this lake; `era5_south` holds temperature only. No rainfall change has ever
been set beside a change in occupancy or in reporting rate, per cell or per species. What *was*
looked at is in §1, and all of it is published.

#82. The third of the three studies the owner opened on 2026-09-03 with *is it just the temperature
really?*, taken because the first two landed the same day — and the one on the leg where temperature
was never the right question to begin with.

---

## Why this note exists

Southern Africa is the one place this project measured outside the northern temperate zone, and it
is semi-arid. Its birds' occupancy did not change on net between the two atlases (`atlas-no-net-change`,
median Δψ −0.007 across 512 species), and the one driver ever tested against the per-cell change was
**surface water**, which explained none of it — with the caveat that the water record was attenuated
and the null meant *not detectable* rather than *absent* (Phase 1g). The transfer test then used the
southern leg as a thermal-tracking leg and found no tracking at all.

Nobody has asked the region's own question. In a semi-arid country, what a year does for its birds is
decided by **rain** before it is decided by heat: rain sets the grass, the seed, the insects and the
water, and a wet run of years fills the interior with species that a dry run empties out of it. Two
five-year atlas epochs thirty years apart differ in how wet they were, cell by cell, and that
difference is the obvious explanatory driver for a per-cell change in who was recorded. ERA5 carries
it, at the same 496 cells `era5_south` already samples, on the same route, in one fetch.

**The animal-specific outlook.** Rain does not move every bird alike. A per-cell answer says whether
the wetter squares gained species; a per-species answer says which species followed the rain and
which did not, which is the kind of why a conservation plan can use. Both are asked, and the second
is the one decision 2 of ADR 0018 requires.

**Which leg of the spine this bears on.** Claim 2, *where does not follow warming*, on its southern
leg: a rainfall response here would be the first positive explanation of a where-change anywhere in
this project, and it would not be temperature. Claim 6, the coverage limit, gains a driver in the
hemisphere that had almost none.

---

## 1. What was looked at before this was written

| what | value | where |
| --- | --- | --- |
| atlas occupancy change | median Δψ −0.007, deciles −0.075 to +0.048, 512 species on 496 cells | `atlas-no-net-change`, Phase 1e |
| per-cell change in detected taxa | drawn on the 496 cells; tracks effort at rho −0.199 | Phase 1f |
| surface water against the per-cell change | partial *r* −0.036; toroidal *p* 0.59, spectral *p* 0.79 | Phase 1g |
| the water placebo | naive *p* 0.031 in the driest quarter, spectral *p* 0.085 | Phase 1g |
| southern thermal tracking | −0.014, not separable from zero | Phase 1i |
| `era5_south` | 2 m temperature, monthly, the two epochs, 496 cells | registry |

**Not looked at:** any rainfall value at any atlas cell; any join of rainfall to occupancy, to
reporting rate or to the per-cell change; any per-species response to anything in this region.

---

## 2. Estimand and unit, with the known problems first

**Two units.** The footprint cell — Phase 1f's 496, with its change in detected taxa and its change
in cards — and the species, Phase 1e's baseline set with thirty or more epoch-1 cells detected.

**The driver, per cell: `ΔR`, the change in mean monthly rainfall** between the epochs, the epoch-2
mean over 2008–2012 minus the epoch-1 mean over 1987–1991, in millimetres per day, from ERA5 monthly
means sampled at the cell. Beside it `R₁`, the epoch-1 mean, for the placebo.

**The cell-level question is Phase 1g's, with rain in place of water.** The per-cell change in
detected taxa regressed on `ΔR` conditioning on the change in cards; the partial correlation; the
toroidal-shift null and the Moran spectral null; leave-one-quadrant-out; and a placebo subset. Every
one of those is called from `phase1g` with a `driver` argument added for the purpose, rather than
copied, so the two phases cannot condition on effort differently.

**The placebo, fixed here.** The wettest quarter of cells by `R₁`. Where rain is not what limits the
birds, a change in it should predict nothing; Phase 1g's placebo was the driest quarter by water
extent on the mirror-image argument.

**The species-level question is new.** For each baseline species, its per-cell **reporting rate** —
cards recording it over cards in the cell — in each epoch, and the change between them; regressed
across the footprint cells on `ΔR` conditioning on the change in cards, with an ordinary least
squares interval on the rainfall coefficient. Zeros are cells: a species never recorded in a cell in
an epoch has a reporting rate of nought there, as it does in Phase 1e's occupancy fits. Pooled: the
count of species whose coefficient is clear of zero against the binomial chance bar; the median
coefficient with a units-bootstrap interval; Cochran's Q across species.

### Known problems, before any fetch

- **Two five-year means thirty years apart are mostly weather.** Their difference is interannual
  variability — an El Niño run against a La Niña run — far more than a trend. So this asks whether
  wetter-than-before squares gained birds, which is a real question about rain and birds, and not a
  question about climate change. The note says which.
- **A reanalysis over southern Africa is weakly constrained.** Fewer stations feed ERA5 there than
  over North America or Britain; rainfall is the field reanalyses estimate worst. Bounded by nothing
  here, and stated.
- **Reporting rate is not occupancy.** It moves with effort, which is why the change in cards is
  conditioned on, and with detectability, which is not. Phase 1e's detection correction changed the
  answer by 0.002 on this footprint, so the naive rate is the quantity Phase 1f already ships; the
  corrected `Δψ` is one number per species, not per cell, and cannot be regressed on a cell's rain.
- **Spatial autocorrelation in both rain and birds.** The two nulls exist for exactly this and are
  inherited whole.
- **Zeros dominate rare species' cells.** A species recorded in thirty cells has 466 zeros in each
  epoch; its coefficient is fitted mostly on where it was not. Registered as a reason the per-species
  count may sit near the chance bar, not as a reason to drop the zeros.
- **The fetch rewrites `era5_south`.** Temperature and precipitation land in one call, for the lake's
  partition rule; the temperature is re-read from the archive's cache.
- **Nothing causal.** Wetter squares differ in more than rain.

---

## 3. The design, fixed before any fetch

- **The fetch.** ERA5 monthly means, `2m_temperature` and `total_precipitation`, all twelve months
  of 1987–1991 and 2008–2012, over the SABAP box, at the 496 footprint cells, landed as `era5_south`
  in one call.
- **The frame.** `phase1f.surface()`'s cells joined to the rainfall change on the cell's own site id,
  every cell present or the frame is refused, as Phase 1g refuses a partial join.
- **Calibration.** `phase1g.fit` on Phase 1g's own water design, through the refactored code path,
  reproduces the published partial *r* of −0.036 to two decimals.
- **The species table** from `phase1e.detections` for both epochs on the footprint, at Phase 1e's
  thirty-cell baseline floor.
- **Seed** `phase1g.SEED` for the spatial nulls, as inherited; `SEED = 1` for the species bootstrap;
  999 spatial draws as Phase 1g's, 1,000 bootstrap draws.
- **Fixed before any number is seen:** the epochs, the driver definition, the placebo rule, the effort
  control, the floors, and that the species table publishes one row per species before any median.

---

## 4. Predictions

1. **The fetch lands** rainfall at all 496 cells for all 120 months. *Check.*
2. **Calibration.** The water partial *r* reproduces to two decimals through the refactored path.
   *Check.*
3. **Wetter cells gained taxa.** The rainfall coefficient is positive and the spectral null gives
   *p* < 0.05. *Discovery, registered as the region's expectation.*
4. **It survives losing any quadrant**: the coefficient keeps its sign with each quadrant removed.
   *Check on 3.*
5. **The placebo is quiet.** In the wettest quarter the rainfall coefficient is inside its spectral
   null (*p* ≥ 0.05). *Control.*
6. **More species follow the rain than chance.** The count of species whose rainfall coefficient is
   clear of zero exceeds the binomial bar. *Discovery, the animal-specific one.*
7. **They follow it differently.** Cochran's Q across species clears its bar. *Discovery.*

---

## 5. Stop conditions

- **Prediction 1 fails** → coverage statement; nothing below is computed.
- **Prediction 2 fails** → the refactor changed Phase 1g's answer; nothing is read until it is found.
- **Prediction 3 fails** → the southern leg has its third named null after water and heat, and claim
  2 of the synthesis gains *and not rainfall between the epochs*; the per-species half still runs,
  because a species-level response can exist under a null cell-level one, and predictions 6 and 7
  are graded on it.
- **Prediction 3 holds and 5 fails** → the association is not rain-limited and is reported as such.
- No epoch, placebo rule, floor or control is revisited after any number is seen.

---

## 6. What this cannot establish

- **Not climate change.** Two wet-or-dry runs of years, not a trend.
- **Not causation.** Rain co-varies with land use, grazing, fire and the people who atlassed.
- **Not detection.** The naive reporting rate is what the cell-level product already ships; the
  corrected occupancy cannot be regressed per cell.
- **Not the north, nor the sea.** One region, two epochs, one driver.
- **Not the migrants.** Most of these species are residents of the interior; the note says nothing
  about journeys.

---

# Results — run 2026-09-03

`make report-phase2g`, run in two pairs. The first pair agreed on every coefficient and every verdict
and moved two spectral p-values in the second decimal — 0.278 against 0.287, 0.007 against 0.004 —
which is the instability Phase 1g recorded against itself in August (TASKS #37) and left unresolved:
a seeded surrogate applied to cells whose order the surface did not fix. The frame is sorted by cell
now, and the second pair is identical line for line. The fetch landed the same day: 119,040 rows,
two fields, 496 cells, all 120 months at every cell.

**Coverage — landed.** **Calibration — PASS**: Phase 1g's water partial *r* through the refactored
path is −0.036 against its published −0.036.

## The cells

| quantity | value |
| --- | --- |
| rainfall change coefficient | **−8.98** taxa per mm/day |
| partial *r*, conditioning on the change in cards | **−0.088** |
| toroidal null | *p* 0.596, 76 cells usable per draw |
| spectral null | *p* **0.299** |
| naive *p*, kept and labelled as the wrong test | 0.111 |
| leave-one-quadrant-out | −2.13, −15.32, −13.44, −2.86 — same sign |
| placebo, wettest quarter by epoch-1 rain, 124 cells | coefficient **−28.7**, spectral *p* **0.007** |

## The species

| quantity | value |
| --- | --- |
| species with a rainfall coefficient | 560 |
| clear of zero, on cell-independent intervals | **194** against a chance bar of 37 |
| median coefficient | −0.0009 [−0.0028, +0.0011] per mm/day |
| Cochran's Q across species | **2,825.8** against 615.1 |

## The answer

**The cells that got wetter did not gain birds, and the species did not agree about the rain.**

At the cell level the region's own driver is the third named null on its where-change, after water
and heat: the coefficient is negative, a third of a standard deviation of nothing, and neither spatial
null comes near its bar. Wetter squares did not record more taxa. The placebo did not stay quiet
either, and in the direction nobody registered: in the wettest quarter of the footprint, the squares
that got wetter still recorded **fewer** taxa, at a spectral *p* of 0.007. Where rain is not what
limits birds, more of it in the second epoch went with fewer species written down. Whether that is
the birds or the atlassing — wet weather keeps observers in as surely as it keeps butterflies down —
is not separable here, and it is recorded as an unregistered-direction result in a control subset,
not as a finding.

**And underneath the null, a third of the species follow the rain.** 194 of 560 have a reporting-rate
response to the rainfall change that clears zero, against a chance bar of 37; the median across
species is indistinguishable from nought; and the species differ beyond any error at Q 2,826 against
615. Some species were recorded more where it got wetter and as many were recorded less, and the
cell total — the sum over species — cancels to nothing. That is the animal-specific outlook doing
work: the aggregate says rain does nothing, and the aggregate is wrong about every species in it.

**One bound on the 194, stated rather than left.** Each species' interval treats 496 cells as
independent. They are not — the spatial nulls exist because they are not — so the count clear of
zero is inflated by an amount this design did not measure, and the chance bar of 37 assumes the same
independence. A spatially honest per-species test, the spectral surrogate run per species, was not
registered and is the successor's. The heterogeneity is not exposed the same way: species differing
by a factor of four and a half in Q is not a spatial artefact.

## The predictions, graded

**1 — TRUE** (check). 496 of 496 cells, 120 of 120 months.

**2 — TRUE** (check). −0.036.

**3 — FALSE.** −8.98 taxa per mm/day, spectral *p* 0.299. Wetter cells did not gain taxa.

**4 — TRUE**, and of a null: the sign survives losing any quadrant, and the sign is of nothing.

**5 — FALSE.** The placebo is not quiet: −28.7, *p* 0.007, the opposite direction to the expectation
it was written to guard.

**6 — TRUE** (the animal-specific one). 194 against 37, on intervals that assume independence.

**7 — TRUE.** Q 2,825.8 against 615.1.

Five of seven. The two that failed are the two about the *cells*; the two discoveries about the
*species* held.

## The stop conditions, and what they do

- Predictions 1 and 2 held → everything was interpreted.
- **Prediction 3 failed → the registered consequence applies.** The southern leg has its third named
  null after water and heat; claim 2 of the synthesis gains *and not rainfall between the epochs*;
  the per-species half ran, and predictions 6 and 7 were graded on it.
- Prediction 3 failed and 5 failed → no *rain-limited* reading is available, and none is offered.
- `atlas-no-net-change`'s caveat gains one sentence, computed from this module at build: the
  cell-level null and the species-level count, with the count's independence assumption named in
  the note it points at.

## What the successor has to fix

1. **A per-species spatial null.** The spectral surrogate run once per species would give the 194 an
   honest bar; the eigenvectors are one decomposition and the surrogates are matrix products, so it
   is minutes and not hours.
2. **Which species follow the rain which way.** 194 responses with a sign each is a table this note
   does not publish, and the animal-specific outlook says it is the result. It needs a trait — diet,
   water dependence, migrant or resident — to become a why, and the lake holds no trait table.
3. **The wettest-quarter reversal** needs the effort record read differently: cards per month rather
   than per epoch, to see whether wet months were atlassed less.

## What this does not establish

- **Not climate change.** Two runs of years, thirty years apart.
- **Not causation.** Rain co-varies with grazing, fire, land use and the people who atlassed.
- **Not the 194 as a count.** It is an upper bound on cell-independent intervals.
- **Not the north, nor the sea.** One region, two epochs, one driver.
