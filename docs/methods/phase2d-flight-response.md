# Phase 2d — does the butterflies' flight date follow the temperature, and is the response the species'?

**Status: pre-registered 2026-09-02, before any fetch.** No ERA5 value exists at any UK coordinate in
this lake. No flight-date series has ever been joined to a temperature. No per-species response has
been fitted on any insect record here. What *was* looked at is in §1: everything Phase 1j and Phase 1k
published about this source, the radar's own response function, and one literature figure quoted from
memory and flagged as such.

#75. The second of ADR 0018's two studies, and the first test of its decision 2: the animal is the unit
of a *why* question, because a species' response to a driver is a different and better-determined
quantity than a species' trend.

---

## Why this note exists

`flight-advance` publishes the largest timing signal in this lake — **−2.10 days per decade over
12,213 site-species-generation series**, 59 taxa, 3,144 sites, 1973–2021 — and no driver has ever been
fitted to it. Phase 1j registered the temperature sample it needed and its ingest gate fired on a
badly chosen proxy; Phase 1k fitted the trend and left the driver for a successor; the successor never
came, because each successor was chosen from the previous phase's residual rather than from the
whole. ADR 0018 records that as the failure mode this project had fallen into.

The spine registered there has three legs and this is the first: *when animals move follows
temperature*. Today it stands on radar alone — `phase2a-timing.md`'s −0.659 ± 0.165 days per °C over
78 stations, with Phase 2c's −0.624 ± 0.175 net of a time term — plus one calibration edge in Phase 3c
(spring sea-surface temperature to plankton bloom, +9.7 days per °C over 38 years). A leg on one
instrument in one realm is a leg on one point. This note asks the same question of a different animal
with a different instrument on a panel eighty times bigger, and asks it **per species first**.

Which is what ADR 0018 decision 2 changes about the design. Phase 1k measured a median flight-date
series at **1.05** standard errors from zero — one series is unreadable. But a series is a *trend*: one
slope on year at one site for one species. A *response* is a slope on temperature pooled across every
site the species occupies, and a species here occupies hundreds. The unit that cannot carry a trend can
carry a response, and whether the responses of different species differ from one another is the
owner's question — *most migrations are animal specific* — made falsifiable.

**Which leg of the spine this bears on.** The first, directly. It bears on the third only by analogy:
if species differ in their thermal response, the animal is the unit of *when*; Phase 3k has just found
that in the marine record the animal is not the unit of *where* beyond what the sea is.

---

## 1. What was looked at before this was written

All published, none of it about a response:

| what | value | where |
| --- | --- | --- |
| flight-date trend, network median | **−2.104** d/decade, 12,213 units, taxon-clustered CI −2.454 to −1.809 | `flight-advance`, Phase 1k |
| a single series' precision | median \|slope\| / se **1.05** | Phase 1k, 2026-09-01 registration |
| units, taxa, sites, span | 12,213 · 59 · 3,144 · 1973–2021 | Phase 1j ingest, Phase 1k |
| flight-curve shape trends | graded in Phase 1j's prediction 6, 2026-08-31 | Phase 1j |
| radar thermal response | −0.659 ± 0.165 d/°C; −0.624 ± 0.175 with a year term | `phase2a-timing.md`, Phase 2c |
| radar thermal share of the advance | 51–54% | Phase 2c |
| plankton bloom on spring SST | +9.7 d/°C, 38 years | Phase 3c calibration C2 |

**Literature, from memory and to be verified before any finding quotes it:** Roy & Sparks (2000, *Global
Change Biology* 6:407–416) reported that most British butterflies' first appearance and peak dates
advanced with warmer spring temperatures, of the order of two to ten days earlier per °C. The size is
the reason prediction 3 is registered as it is; the reference is flagged rather than trusted.

**What was not looked at:** any ERA5 value at any UK coordinate; any join of a flight date to a
temperature; any response coefficient; any per-species anything on this source.

---

## 2. Estimand and unit, with the known problems first

**The unit is a species-generation.** Thirteen species have their generations split by the scheme, and
Phase 1j's reasoning holds: a species-level date across two broods is an average of two peaks and a
trough. A generation flies in its own months and gets its own pre-season.

**The response is the mean flight date** as `phase1k.timing` reconstructs it — `period_start`'s day of
year plus `count` — per site, per year.

**The driver is the pre-season mean 2 m temperature at the site**, from ERA5 monthly means, over a
window fixed per unit by a rule stated here and not chosen against any fit:

> The pre-season of a unit is the two calendar months ending the month **before** the unit's
> climatological median flight month, where that month is the calendar month of the unit's median
> flight date over every site and year it has.

A unit flying in mid-June gets April–May; one flying in mid-April gets February–March; an August
generation gets June–July. The rule mirrors `phase2a-timing.md`'s June–July-before-autumn choice: a
predictor that overlaps the response is partly the response, and a flight period's temperature affects
whether the animal is *seen*, which is a different quantity from when it emerged. It uses the
climatological *mean* timing of a unit and nothing about its year-to-year variation or trend, which is
the line that keeps it non-circular.

**The estimand, per unit, is the within-site interannual thermal response `S`**: days of flight-date
shift per °C of pre-season warmth, fitted with a site intercept and a linear year term —

```
flight_day[site, year] = a[site] + S · temperature[site, year] + b · year + e
```

Phase 2c's lesson, applied in advance rather than discovered: without the year term `S` absorbs the
shared trend of two series that both trend, and the radar's circularity turned out small only because
somebody checked. The no-year fit is arm A, a reported sensitivity; arm B with the year term is the
primary. The two are published as a pair, as Phase 2c published its bracket.

**The secular pieces, per unit.** `W` is the trend per decade of the unit's cross-site mean pre-season
temperature over the years the unit has data. `A` is the unit's median per-series flight-date trend,
through `range_metrics.shift_per_decade` on the same series at Phase 1k's fifteen-year floor. The
thermal share is `S × W / A`, and the pooled share is the ratio of medians — the median over units of
`S × W` over the median over units of `A` — because a ratio taken per unit is unstable wherever `A` is
near zero, and pooling the ratios would weight those units most.

**Pooled across units.** The median `S` with a percentile bootstrap over units, and beside it the
question decision 2 is for: **Cochran's Q over the unit responses**, each weighted by its own
year-clustered standard error, against a chi-square bar with `units − 1` degrees of freedom. If Q clears,
the species' responses differ beyond their own estimation error and the response is a property of the
species. ADR 0016 applies to the median if fewer than 30 units qualify.

### Known problems, before any fetch

- **The interval on `S` must be clustered on year.** Every site in Britain sees roughly the same
  spring, so the effective sample for a national response is the number of years, not the number of
  site-years. Phase 1k measured the price of ignoring that at 4.5× on this very source. So every
  interval on `S` is a percentile bootstrap resampling **years** with all their site rows, 1,000 draws,
  with the naive interval printed beside it and never used for a grade.
- **"Mean flight date" is emergence for a resident and arrival for a migrant.** Phase 1j's problem,
  unchanged. The three migrants it registered — *Vanessa cardui*, *Vanessa atalanta*, *Colias
  croceus* — are the secondary in prediction 8 and are excluded from nothing.
- **A monthly reanalysis at a quarter degree is not the temperature a caterpillar experienced.**
  Degree-days from daily data would be the mechanism's own quantity; monthly means are the quantity
  the lake's driver route supports and the quantity the radar response was fitted on, and using the
  same thing on both legs is what makes the two legs comparable. Named as a ceiling on `S`, not
  corrected.
- **Coastal sites may match a sea cell.** ERA5's 2 m temperature over water is not the transect's.
  Nothing here can tell which sites those are; a site's match distance is recorded and no site is
  dropped for it.
- **The window rule is coarse.** Two calendar months is a blunt pre-season for a species whose
  development spans a whole spring. A finer rule would be tuned, and a tuned window is what §5 forbids.
- **Site fixed effects absorb the spatial gradient**, so `S` is identified from interannual variation
  and from a site's own departures, not from north-against-south. That is the design; a cross-site
  regression would be a statement about geography, as `phase2a-timing.md` said of stations.
- **Recorder turnover and site entry and exit** are not modelled, as Phase 1j recorded.
- **Nothing here is causal.** A date regressed on a temperature at the same place is a response
  function, and every alternative driver that co-varies with spring warmth survives the fit.

---

## 3. The design, fixed before any fetch

**The fetch.** ERA5 monthly means, `2m_temperature`, months **1–8**, years **1973–2021**, over the box
north 61.0, west −11.0, south 49.0, east 2.5, sampled at every UKBMS site the lake holds, through
`drivers/era5.ingest` and `features/annotate.nearest_cells` unchanged. Landed under its own source id,
`era5_uk`, for the reason `era5_south` was: the lake replaces the partitions a write touches, and a
second box under `era5` deleted five years of the North American record twice.

**Floors, per unit.** At least **15 distinct years** and at least **10 sites** with both a flight date
and a pre-season temperature. Below either, the unit is reported as coverage and enters no pooled
quantity.

**Calibration rung.** `phase1k.timing()` must return its published median, **−2.104**, to three
significant figures, so the series this phase reconstructs are the series `flight-advance` publishes.
If it misses, nothing above it is read.

**Arms.** A: `[1 per site, temperature]`. B: `[1 per site, temperature, year]`, the primary. Both by
within-site demeaning and ordinary least squares on the demeaned columns. `W` and `A` come from the raw
series and are shared by both arms, as Phase 2c's amendment D fixed.

**Seed** `SEED = 1`, as every phase since 1k. Bootstraps keyed by `crc32` of the quantity's name.

**Fixed before any number is seen.** The window rule, the floors, the arms, the clustering unit, the
migrant list, the pooled-share construction, and that the deliverable is a per-species table with a
pooled median beneath it rather than a pooled median alone.

---

## 4. Predictions

Marked check or discovery, as Phase 3k marked its own.

1. **The ingest lands.** At least **99%** of the lake's UKBMS sites match an ERA5 cell within 30 km,
   and the monthly series is complete for 1973–2021 at every matched site. *Check on the route.*
2. **Calibration.** `phase1k.timing()` reproduces −2.104 to three significant figures. *Check.*
3. **The pooled response is negative and clear of zero**, and its magnitude exceeds the radar's:
   median `S` under arm B is below **−0.66** days per °C with a units-bootstrap interval excluding zero.
   *Discovery on the number, expected on the sign* — an ectotherm's development is thermal in a way
   a nocturnal migrant's departure is not, and the literature figure in §1 is five to fifteen times the
   radar's.
4. **The pre-season warmed.** Median `W` across units is positive and clear of zero. *Check.*
5. **The responses are the species'.** Cochran's Q over the unit responses, weighted by their
   year-clustered standard errors, clears its chi-square bar. *Discovery, and the substantive one:*
   graded false, the species respond alike and the animal is not the unit of *when* on this record.
6. **The thermal share exceeds the radar's.** The pooled share `median(S × W) / median(A)` is above
   **0.54**, the upper end of Phase 2c's bracket. *Discovery.* Graded false, the butterflies' advance
   is less thermal than the radar's, which would be the surprise.
7. **Arm B is smaller in magnitude than arm A**, as the radar's was. *Check on direction.* A larger
   arm B needs explaining rather than celebrating.
8. **The migrants respond less.** The median |`S`| over the three registered migrants is below the
   median over residents. *Secondary, weak*, for Phase 1j's reason: *V. atalanta* has become partly
   resident over this very window.

---

## 5. Stop conditions

- **Prediction 1 fails.** The ingest is reported as a coverage statement; the registry records what
  was found; nothing below is computed.
- **Prediction 2 fails.** The harness does not reconstruct the series it claims to extend. Stop.
- **Prediction 3 fails on the sign or on zero.** Then the butterflies' flight date does not follow
  pre-season temperature on this design, `flight-advance` gains that sentence, and the spine's first
  leg stands on radar alone. Pre-committed here so it cannot later be narrated as a window problem.
- **Prediction 5 fails.** Then the response is not species-specific on this record. It publishes as
  that, and ADR 0018 decision 2 has lost its first test — the note says so plainly rather than
  reaching for a finer taxonomy.
- **Fewer than 20 units clear the floors.** The pooled quantities publish as a coverage statement and
  predictions 3 to 7 are graded on whatever units exist, with the count stated.
- No window rule, floor, arm, clustering unit or seed is revisited after any number is seen.

---

## 6. What this cannot establish

- **Not causation.** A response function, not a mechanism. Nitrogen, land use, recorder behaviour and
  anything else that trends with British springs survives every arm.
- **Not degree-days.** Monthly means are the instrument the lake supports; the mechanism's own
  quantity is not in it.
- **Not a migration result for most of the panel.** Most of these species do not migrate, so this is
  when they *emerge*. The leg it supports is about timing following temperature, which does not need
  them to travel; the book's sentence must not say they did.
- **Not the other realms, and not the south.** One island, one scheme, one instrument.
- **Not a licence to project.** A response read forwards is Forecast A's question and needs its mask.
- **Not the third leg of the spine.** Whether species differ in *when* says nothing about whether the
  animal organises *where*, which Phase 3k has just answered in the negative for the marine record.
