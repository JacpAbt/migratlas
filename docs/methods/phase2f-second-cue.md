# Phase 2f — does when an animal moves have more than one cue?

**Status: pre-registered 2026-09-03, before any second driver has been fitted to a timing response,
and before the fetch it needs.** No precipitation or radiation value exists at a UK transect in this
lake; no green-up day has ever been joined to a passage date or a flight date; no held-out comparison
between a one-cue and a two-cue timing model exists anywhere in this repository. What *was* looked at
is in §1, and all of it is published.

#81. The second of the three studies the owner opened on 2026-09-03 with *is it just the temperature
really?* — this one on the leg where temperature already explains half to three quarters, to ask what
the rest is not.

---

## Why this note exists

The synthesis's claim 1 says *when animals move follows the temperature before it*, on two
instruments: radar autumn passage at −0.62 to −0.66 days per °C, and British butterflies' flight at
−4.70. Claim 4 says the rest — a quarter to a half of every timing change — is unexplained and named
nowhere. Both are honest and both were produced by the same design: one driver against a date, with a
year term. That design cannot find a second cue. It can only leave a residual.

Every timing response this project has fitted has had exactly one environmental column in it. The
lake holds three more that every phenology paper names: **precipitation** in the same months as the
temperature, at every radar station already and at every UK transect after one fetch; **downward solar
radiation**, the sunshine an ectotherm actually develops and flies under, one field away on the same
route; and the **green-up day** of the animal's own 1° cell, 41 years of it, dated and in the lake
since August and used only as a skill covariate. None has been asked whether it explains what
temperature leaves.

**The animal-specific outlook, again.** Species do not have to share a second cue. Phase 2d found the
thermal responses are the species' beyond their error (Q 206 against 95); if there is a second cue,
this note asks per species whether it is theirs too, and grades the count of species it moves against
the count chance would move.

**Which leg of the spine this bears on.** Claims 1 and 4 directly. A second cue that improves held-out
prediction in most species rewrites claim 1 to name it; a second cue that improves nothing beyond
chance names one more thing the unexplained half is not.

---

## 1. What was looked at before this was written

| what | value | where |
| --- | --- | --- |
| radar thermal response, year term | −0.624 ± 0.175 d/°C, 78 stations; share 51% | Phase 2c |
| butterfly thermal response, year term | −4.70 [−4.98, −4.23] d/°C, 75 species-generations; share 0.75 | Phase 2d |
| the radar's unexplained half | residual `b` −0.27 d/decade, and the 2012 step | Phases 2c, 1c |
| wind as a timing covariate | four looks, no signal, the last harmful | Phases 2a, 3f, 3h |
| skill from seven weather and index covariates, per station | 20 of 143 above chance | Phase 3a |
| precipitation at the radar stations | in the lake, months 3–11, 1995–2025 | `era5` |
| green-up day per 1° cell | 256,119 cell-years, 1982–2022 | `pku_gimms_ndvi` |

**Literature, from memory and flagged:** wet and dull springs delay British butterflies' emergence and
suppress flight; the scheme's own reports say so and the mechanism is development under lower
radiation. Not verified against a reference before this registration and not to be quoted in a finding
until it is.

**Not looked at:** any second driver against any timing response; any held-out comparison; any UK
precipitation or radiation value; any green-up value at a station or a transect.

---

## 2. Estimand and unit, with the known problems first

**Two records, two units.** The radar station in the claim band, autumn `q50_doy`, Phase 2c's 78 with
its panel called rather than copied. The butterfly species-generation, Phase 2d's 75 with its panel,
windows and floors called rather than copied.

**The drivers, per unit-year, on the unit's own pre-season window** (June–July for the radar; the
two-month window Phase 2d fixed per species-generation for the butterflies):

- `T`, the pre-season mean 2 m temperature — the published driver, unchanged.
- `P`, the pre-season total precipitation over the same months.
- `R`, the pre-season mean downward solar radiation over the same months — **butterflies only**; the
  radar's autumn passage has no plausible radiation mechanism and adding a driver without one is a
  fishing trip.
- `G`, the green-up day that year of the 1° cell containing the site or station.

**The models, per unit, all with the unit's intercepts and a linear year term, exactly as Phase 2c's
arm B and Phase 2d's arm B:**

| arm | columns | what it is for |
| --- | --- | --- |
| **0** | year | the climatology-and-trend floor |
| **T** | T, year | calibration: must reproduce the published response |
| **TP** | T, P, year | does rain add? |
| **TR** | T, R, year | does sunshine add? (butterflies) |
| **TG** | T, G, year | does the season's own phenology add? |
| **all** | every driver, year | how much is left? |

**Two quantities per unit per arm.** The added driver's coefficient with its interval — year-clustered
bootstrap for the butterflies as Phase 2d's, ordinary least squares for a station's single series —
and the **held-out error**: leave-one-year-out prediction of the response, the model refitted without
that year each time, summarised as the root mean square over every held-out row. The **improvement**
of an arm over arm T is one minus the ratio of their held-out errors.

**Pooled.** For each added driver: the count of units whose coefficient is clear of zero, against the
binomial chance bar at a 5% false-positive rate (`phase3a.binomial_bar`, 8 at 75 units and 8 at 78);
the median coefficient with a units-bootstrap interval; the median improvement over arm T; and
Cochran's Q across the units' coefficients, weighted by their errors, as Phase 2d's P5.

### Known problems, before any fetch

- **Green-up is itself thermal.** A warm spring greens early. `T` and `G` are collinear in a way `T`
  and `P` are not, so `G`'s coefficient conditional on `T` measures the season's phenology beyond its
  temperature and can be small while green-up matters. The held-out improvement is the honest
  quantity for it; the coefficient alone is not.
- **Monthly totals are heat's and rain's shadows.** Degree-days and rain-days would be the mechanism's
  quantities; the monthly route is the one the lake supports and the same for every unit.
- **Leave-one-year-out with a year term extrapolates at the ends.** The first and last years are
  predicted from one side of the trend. Every arm pays the same price, so the comparison stands and
  the level does not.
- **Every site in Britain shares a spring**, so the effective sample for a butterfly unit is its years,
  and every interval is clustered on year. A held-out year is held out for every site at once for the
  same reason.
- **The radar's residual carries the 2012 step**, inside every arm through the `post_2012` term Phase
  2a's design carries; no arm here resolves it.
- **Adding a column to twenty rows costs variance.** Phase 3h's wind arm made the fit worse. A negative
  improvement is a result and is reported as one.
- **The UK fetch rewrites `era5_uk`.** The lake replaces the partitions a write touches, so
  precipitation and radiation land in one call with the temperature already there, re-read from the
  archive's cache. If that call fails, the butterfly arms are not run and the note says so.
- **Nothing causal**, in any arm.

---

## 3. The design, fixed before any fetch

- **The fetch.** ERA5 monthly means, `total_precipitation` and `surface_solar_radiation_downwards`,
  months 1–8, 1973–2021, over the UK box, at the same transects, landed under `era5_uk` in one call
  with `2m_temperature`; `era5.FIELDS` gains a radiation field with its unit conversion stated. The
  radar's precipitation is already in the lake.
- **Green-up join.** Each site or station takes the green-up day of the 1° cell containing it, from
  the `pku_gimms_ndvi` driver rows; a cell the metric refused (deserts, ice, evergreen) leaves the
  unit out of arm TG and arm all, and the count left out is reported.
- **Calibration.** Arm T reproduces Phase 2c's arm B median −0.624 on 78 stations and Phase 2d's
  −4.70 on 75 units, each to three significant figures, by calling those modules' panels.
- **Floors** as the parent phases': fifteen years per unit; a butterfly unit needs the same ten sites.
- **Seed** `SEED = 1`; 1,000 bootstrap draws; leave-one-year-out is deterministic.
- **Fixed before any number is seen:** the driver list, the windows, the arms, the held-out scheme,
  the chance bar, and that `R` is asked of the butterflies only.

---

## 4. Predictions

1. **Calibration.** Arm T reproduces −0.624 and −4.70 to three significant figures. *Check.*
2. **Rain moves more butterfly species than chance.** The count of species-generations whose `P`
   coefficient is clear of zero exceeds the binomial bar. *Discovery; registered as expected on the
   literature above.*
3. **Wetter pre-seasons delay flight.** The median `P` coefficient across units is positive and its
   units-bootstrap interval excludes zero. *Discovery.*
4. **Sunshine moves more butterfly species than chance**, and its median coefficient is negative —
   brighter, earlier. *Discovery.*
5. **The radar's unexplained half is not summer rain or spring green-up.** Neither `P` nor `G`
   moves more stations than the chance bar, and the median improvement of arm all over arm T is under
   5% for the radar. *Registered as the expectation*, on Phase 3a's and 3h's evidence that the
   station-level target is mostly noise.
6. **Temperature stays the dominant cue for the butterflies.** The median improvement of arm all
   over arm T is under **10%**. Graded false, claim 1 of the synthesis must name a second cue.
   *Discovery, and the one that changes the story.*
7. **The second cue is the species'.** Cochran's Q across the butterfly `P` coefficients clears its
   bar. *Discovery*, mirroring Phase 2d's prediction 5.

---

## 5. Stop conditions

- **Calibration misses** → nothing above it is interpreted.
- **The UK fetch fails** → the butterfly arms are not run; the radar arms publish alone.
- **Predictions 2, 4 and 5's butterfly half all fail** → no second cue moves more species than chance,
  claim 4 of the synthesis gains *and not rain, sunshine or green-up on these windows*, and no fourth
  driver is reached for in this note.
- **Prediction 6 fails** → claim 1 is rewritten in the synthesis to name the cue, in the same commit,
  with the improvement it earned.
- No window, driver, arm, floor or bar is revisited after any number is seen.

---

## 6. What this cannot establish

- **Not causation.** Three correlates of a date at the same place, and everything that trends with a
  British spring or an American summer survives every arm.
- **Not the mechanism's quantities.** Monthly means and totals, not degree-days, rain-days or hours of
  sun.
- **Not the migrants.** Seventy-two of seventy-five butterfly units are residents.
- **Not the radar's 2012 step**, which no arm here touches.
- **Not the other realms.** Two timing records, both northern.
