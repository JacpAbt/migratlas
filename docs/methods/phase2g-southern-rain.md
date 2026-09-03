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
