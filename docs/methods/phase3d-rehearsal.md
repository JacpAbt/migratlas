# Phase 3d — would the standing prediction have worked? The dress rehearsal

**Status:** pre-registered 2026-08-19. Written before any SEAS5 field has been fetched, before
any forecast has been paired with any observation, and before any rolling-origin fit has run.
The owner's direction, same day: rather than predicting the future and waiting a year per
grade, predict the recent past blind — the months the lake already holds — using only what
would have been knowable at the time, and grade immediately.

## Why this note exists

#57 proposes a standing annual prediction: our fitted response models driven by someone else's
seasonal forecast, graded in public when the year's data lands. Phase 3a tested the response
half — era-split hindcasts with *observed* drivers — and found autumn skill at 20 of 143
stations with nothing at the median. But the real product never gets observed drivers: it gets
a forecast issued months ahead, with the forecast's own error stacked on top. That full
pipeline has never been tested, and standing it up untested would be theater. ECMWF archives
every SEAS5 forecast it issued, so the rehearsal can stand at the first of June in each recent
year, predict that autumn with the forecast actually issued then, and collect eight grades
today instead of one next year. **If the rehearsal fails its chance bar, #57 does not go
live**, and the year of theater is saved.

## 1. What was looked at before this was written

Nothing new. The radar record and its coverage come from Phase 3a's note (143 autumn stations,
1995–2025); SEAS5's archive structure (real-time from 2017, hindcasts 1993–2016, monthly means,
lead months 1–6, issue on the 6th at 12 UTC) comes from the covariate survey's verified
catalogue facts. No SEAS5 value has been seen.

## 2. The design: rolling origin, issue-time information only

For each **target year Y in 2017–2024** (the real-time SEAS5 era, so every forecast is one the
world actually received):

- **Fit** the response model on years `< Y` only — the same registered class as Phase 3a
  (ridge, leave-one-year-out lambda inside the training years, training-only standardisation,
  training climatology as baseline) — with the **weather-only columns**: `temp_season`,
  `temp_pre`, `precip_season`. The modes are excluded, deliberately: the target season's mode
  means are not knowable at issue time, and Phase 3a's prediction 5 already measured what the
  models carry. This difference from 3a is a handicap the real product would share.
- **Predict** autumn Y's median passage day per station using SEAS5's **June issue** of year Y:
  lead months 1–6 cover June–November, supplying the June–July pre-season and the
  August–November season from one issue date. Fields: 2 m temperature and total precipitation,
  monthly means, sampled at the stations like every gridded driver in the lake.
- **Grade** against the observed `q50_doy`, per station-year, Murphy score against the
  training climatology.

**All 143 autumn stations, no selection.** The 20 stations Phase 3a found significant were
selected on the same recent years this rehearsal grades, so grading them alone would be
selection dressed as validation. The map-level verdict is the count of stations whose pooled
eight-year skill exceeds the 95th percentile of a per-station null built by re-pairing each
target year with the seven wrong years' forecasts (all 8!/… permutations are unnecessary;
1,000 random re-pairings, seed 20260819).

## 3. The driver calibration, so a null has an address

Before any pipeline verdict is read: per station, the correlation between SEAS5's June-issued
season temperature and the observed season temperature over the eight years. If the map-median
correlation is not positive past its own re-pairing null, the rehearsal's conclusion is about
**the forecast**, not about migration — SEAS5 carries no June-to-autumn temperature signal over
this band at these leads — and the note says exactly that.

## 4. Predictions

1. **The full pipeline does not beat chance at map level** — registered as the expected
   outcome, because observed-driver skill was already marginal and forecast drivers only
   degrade it. Grading this false (the pipeline beating chance) would be the good kind of
   wrong, and would be #57's launch licence.
2. **Full-pipeline skill is lower than Phase 3a's observed-driver skill at the median
   station** — the price of forecasting the drivers, measured.
3. **The driver calibration passes**: SEAS5's June issue carries positive temperature signal
   for the band's autumn at the map median. The survey's literature says seasonal temperature
   forecasts have modest but real skill over North America at these leads; if this fails,
   predictions 1–2 are uninterpreted per §3.

## 5. Stop conditions

- Driver calibration failing → the pipeline verdict publishes as a statement about SEAS5 over
  this band, predictions 1–2 uninterpreted, and #57 waits for a driver that works.
- Whatever the grades, **#57 goes live only if prediction 1 is graded false** — the rehearsal
  is the licence, not a formality.
- No target year, station set, issue month, or lead window changes after any grade is seen.

## 6. What this cannot establish

Anything about spring (unlicensed by 3a and untested here); anything about long-horizon change
(#13's question, different machinery); station-level guarantees (eight years per station is a
coarse instrument, and the map-level count is the only registered verdict); anything about
other forecast systems — one issue month of one system is what this note binds.

---

## Results — run 2026-08-19

136 stations graded, eight June issues each, seed as registered.

- **Prediction 3 — GRADED TRUE.** The driver calibration passes: SEAS5's June-issued season
  temperature correlates with the observed one at a map-median of +0.344. The forecast is not
  the weak link, which makes the verdict below interpretable.
- **Prediction 1 — GRADED TRUE, as registered.** The full pipeline does not beat chance: 6 of
  136 stations significant against a chance bar of 11, median skill −0.014. Knowing in June
  what SEAS5 knew, the standing prediction would have been indistinguishable from guessing the
  climatology, eight autumns running.
- **Prediction 2 — GRADED TRUE, with its comparison named.** Phase 3a's observed-driver autumn
  median was +0.005; the full pipeline's is −0.014. The designs differ (one era split with
  modes there, rolling origins without modes here), so the comparison is between recorded
  medians, not a shared test set — but the direction is the registered one: forecasting the
  drivers costs what little skill observation offered.
- **The licence: REFUSED.** Per §5, #57 does not go live. The rehearsal cost one afternoon and
  one CDS licence click; the alternative was a year per grade of a prediction this note now
  shows would have graded as noise.

What survives is worth stating plainly: the two-stage architecture works as machinery — the
archive supplied real issued forecasts, the driver signal is present, the pipeline runs end to
end and grades honestly. What is missing is a response that translates seasonal temperature
into passage timing strongly enough to survive the forecast's own error. If a future response
model earns more observed-driver skill than Phase 3a's, this rehearsal re-runs unchanged and
the licence question reopens on evidence.
