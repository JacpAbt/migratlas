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

---

# Results — run 2026-09-02

`make report-phase2d`. Two consecutive runs are identical on every line, checked before anything
here was written down. The fetch landed the same afternoon: one 1.5 MiB file from the Copernicus
queue, 3,144 sites, 1,232,448 monthly rows, landed as `era5_uk`.

**Calibration — PASS.** `phase1k.timing()` returns **−2.1043** against the published −2.104.

**Coverage — landed.** 3,144 of 3,144 transects matched an ERA5 cell, every one within 30 km, the
furthest at 16.1 km.

## The units

**75 species-generations clear the floors**; 10 are published as coverage, all ten under the
fifteen-year floor. No unit's median flight fell too early for a pre-season, so the window rule
never returned nothing. Windows ran from February–March (the Peacock's post-winter flight) to
June–July (the second generations and the late fliers).

| quantity | value |
| --- | --- |
| median `S`, arm B (year term) | **−4.70** days per °C, units-bootstrap **[−4.98, −4.23]** |
| median `S`, arm A (no year term) | −4.80 |
| units whose year-clustered interval excludes zero | **60 of 75**, every one of them negative (counted from the printed intervals) |
| median `W` | **+0.337** °C per decade [+0.310, +0.352] |
| Cochran's Q across the 75 responses | **206.1** against a bar of 95.1 (74 degrees of freedom) |
| thermal share `median(S × W) / median(A)` | **0.75**, with median `A` −2.05 days per decade |
| migrants against residents, median `S` | −1.77 (3 units) against −4.83 (72 units) |

The strongest clear response is *Leptidea sinapis* at −7.72 [−11.75, −4.25]; the weakest is the
second generation of *Lycaena phlaeas* at +1.17 [−1.53, +2.61], the one unit whose point estimate is
positive, and it is not clear of zero.

## The answer

**The butterflies' flight date follows the warmth of the months before it, at seven times the radar's
response, and the response is the species'.**

A spring one degree warmer brings the median species' flight forward by **4.7 days**, against 0.66
days of autumn passage per degree over the radar. Adding the year term moves the median from −4.80
to −4.70 — a tenth of a day — so the co-trend Phase 2c measured as small on the radar is small here
too, on a different animal and a different instrument. Sixty of the seventy-five units clear zero on
an interval clustered on year, and all sixty are negative.

**Three quarters of the advance is the size the response predicts.** The pre-season warmed by
0.34 °C per decade across the units, `S × W` puts the median predicted advance near −1.6 days per
decade, and the median observed advance is −2.05: a share of **0.75**, against the radar's 51–54%.
The remaining quarter is the residual `b`, and naming it would be inventing it, as Phase 2c said of
the radar's half.

**And the responses differ between species beyond their own error.** Cochran's Q is 206.1 against
95.1: the 75 responses are not one number with noise. That is prediction 5, the substantive one, and
it is the first test ADR 0018 decision 2 has had — the animal is the unit of *when*. Where Phase 3k
found the marine where-shifts no more the species' than the sea's, the butterflies' when-shifts are
emphatically the species'.

**UNREGISTERED, seen in the table and not predicted anywhere:** for the nine multivoltine species
with both generations in the panel, the **first generation responds more strongly than the second in
all nine** — *Lasiommata megera* −6.86 against −2.79, *Celastrina argiolus* −6.16 against −1.76,
*Lycaena phlaeas* −5.44 against +1.17, *Pieris rapae* −5.08 against −2.53, *Pieris napi* −4.86
against −2.53, *Pieris brassicae* −4.52 against −2.91, *Polyommatus bellargus* −5.18 against −2.25,
*Aricia agestis* −4.57 against −2.12, *Cupido minimus* −4.12 against −2.88, *Polyommatus icarus*
−4.57 against −3.28. And for the two univoltines whose adults overwinter, the order **reverses**: the
Brimstone's post-winter flight responds at −3.42 and its summer emergence at −5.12, the Peacock's at
−1.96 and −4.18. A fresh generation emerging responds to the warmth that developed it; an
overwintered adult reappearing responds less; a second generation, developing through a summer that
is warm anyway, responds less than a first developing through a spring that varies. That is a
mechanism-shaped pattern and it was not registered, so it is a diagnostic: eleven of eleven pairs in
the direction development-not-reappearance predicts, and a successor's prediction rather than a
result.

**The migrants respond less**, at −1.77 against −4.83, on three units: *Vanessa cardui* at −4.16 is
clear of zero, *Vanessa atalanta* at −1.24 and *Colias croceus* at −1.77 are not. Registered weakly
and graded as registered; three units are three units.

**Five remnant units are noise and are left in.** For five of the split species the scheme carries
site-years where it separated no brood, and those rows form a plain `pollard-walk` unit of 17 to 19
years and 11 to 35 sites beside the species' generations — intervals tens of days wide, and no site
series long enough for an `A`. They clear the registered floors, enter the median with a weight in Q
near nothing, and are named here rather than removed, because removing them after seeing them is the
move §5 forbids. A floor on the number of site series with fifteen years would have excluded them;
it was not registered.

## The predictions, graded

**1 — TRUE** (check). 3,144 of 3,144 within 30 km.

**2 — TRUE** (check). −2.1043.

**3 — TRUE** (discovery on the number). −4.70 [−4.98, −4.23], below −0.66 by a factor of seven.

**4 — TRUE** (check). +0.337 [+0.310, +0.352].

**5 — TRUE** (the discovery). Q 206.1 against 95.1.

**6 — TRUE** (discovery). 0.75 against 0.54.

**7 — TRUE** (check on direction). |−4.70| < |−4.80|, by a tenth.

**8 — TRUE** (secondary, weak). −1.77 against −4.83 on three units.

**Eight of eight, and that is the tail the prediction ledger says to be suspicious of.** Four were
checks on the route and the arithmetic (1, 2, 4, 7). Two were registered in the direction the
literature has reported for twenty-five years (3, 6). One rests on three units (8). The prediction
that carried the phase's weight is 5, and its pass is the result; had it failed, the note would be
saying that the species respond alike and decision 2 had lost its first test.

## Stop conditions

None fired. The registered consequence of prediction 3 holding is that `flight-advance` gains the
response: its claim, its caveat and its environmental bias domain — which said *no driver enters
this* — now carry the median response, its interval, the share and the heterogeneity, computed at
build from this module rather than typed. **No new ledger entry.** ADR 0018 decision 5 makes the book
arc the place where *why it changed* grows, and a claim without a chapter fails the build.

## What this does to ADR 0018

**The first leg now stands on two instruments in two realms.** Radar autumn passage at −0.62 to
−0.66 days per °C with a thermal share of 51–54%; butterfly flight at −4.70 with a share of 0.75.
Timing follows the temperature before it, and does so more tightly in an ectotherm whose development
is thermal than in a nocturnal migrant whose departure is partly photoperiod's.

**Decision 2 passed its first test.** The responses are the species' — Q 206 against 95 — which is
what *most migrations are animal specific* predicts for *when*. Phase 3k found the opposite for
*where* in the marine record. The spine's sentence sharpens rather than breaks: **when is the
animal's and follows temperature; where is not organised by the animal beyond what the sea is, and
does not follow warming.** The synthesis, #76, is unblocked.

## What the successor has to fix

1. **Register the generation gradient** — a fresh generation responds, an overwintered adult
   reappearing responds less — and test it on degree-days rather than monthly means, which is the
   mechanism's own quantity.
2. **A floor on site series with fifteen years**, so that every unit carries an `A` and the remnant
   units above do not enter. Not applied here; it was not registered.
3. **The report should print the count of units clear of zero.** The 60 above was counted from the
   printed intervals; a count is a computed quantity and belongs in the output.
4. **#47.** This is the second responsive system the transfer test needed. Re-running Phase 1i with
   a butterfly leg is its own registration and inherits Phase 1j's window and conversion rules.

## What this does not establish

- **Not causation.** A response function: nitrogen, land use and recorder behaviour that trend with
  British springs survive every arm.
- **Not degree-days**, and so not the mechanism, only its monthly shadow.
- **Not migration.** Seventy-two of the seventy-five units are residents; this is when they emerge.
- **Not the other realms, and not the south.** One island, one scheme.
- **Not the third leg.** Species differing in *when* says nothing about *where*.
- **Not a licence to project.** A response read forwards is Forecast A's question.
