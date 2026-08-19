# Phase 3e — the marine question again, with water the surveys did not record

**Status:** pre-registered 2026-08-19. Written before any OISST value has been read, before any
footprint mean has been computed, and before any unit's trend has been paired with any other.
This is the successor registration Phase 3b's results section reserved: the same question, with
the warming driver taken from a gridded product because the in-situ requirement left ten units
against a floor of twelve.

## Why this note exists

Phase 3b died honestly: seventeen qualifying gear segments, but only ten whose surveys recorded
their own water for twenty years — the European fleets measure fish, not temperature. The
reserved extension was priced in advance: NOAA OISST (0.25°, 1981–present, public domain, one
verified 2.1 GB monthly-mean file) sampled over each survey's footprint, at the named cost that
a reanalysis of the shelf is not the water the fish were in. This note pays that cost with its
eyes open and adds the calibration that keeps it honest: where both waters exist, they must
agree, or the gridded route stops.

## 1. What was looked at before this was written

Segment-era overlap only, measured 2026-08-19: clipping each survey's longest single-gear
segment to the OISST era (1981+), **19 units retain ≥ 20 years** — against Phase 3b's ten.

One flaw in the measuring instrument, found by measuring twice: the per-year gear assignment
used polars' `mode().first()`, whose tie order is unstable, and the Baltic surveys' tied years
segmented differently across two runs. **The registered rule is deterministic**: a year's gear
is the one with the most hauls, ties broken lexicographically by gear name. The unit count is
re-measured under that rule when the runner first executes, before any response is touched, and
the floor below applies to that count. (Phase 3b's own outcome is unaffected — its ten fitted
units had no tied years — but its runner inherits the fix.)

## 2. The design: Phase 3b's, with one substitution

Everything Phase 3b registered stands unchanged except the warming driver:

- **Unit**: the survey's longest single-gear segment under the deterministic gear rule,
  clipped to 1981+, admitted at ≥ 20 clipped years.
- **The movement**: per-species latitude trends within the clipped segment (≥ 15 years),
  summarised by the median and its interval. Unchanged.
- **The warming**: the per-decade trend in the **OISST monthly means averaged over the unit's
  consistent footprint cells**, over the same clipped years. This replaces the in-situ trend
  for every unit, including the ten that have both — one driver definition for all units,
  because mixing definitions across units would make the cross-unit slope a comparison of
  instruments.
- **The setting**: median haul depth. Unchanged.
- **The regression**: WLS of latitude trend on OISST trend with a standardised-depth
  interaction, inverse-variance weights. Unchanged.

## 3. The calibration, before anything is interpreted

For the units that recorded their own water (Phase 3b's ten): the correlation across units
between the OISST footprint trend and the in-situ haul trend over the same years. If it is not
positive, the gridded product does not track the shelf water the fish were in, every result
below is uninterpreted, and that finding — OISST failing on the shelf — publishes on its own.

## 4. Predictions

1. **The calibration passes**: OISST and in-situ warming agree in direction across the ten
   dual-record units.
2. **The heterogeneity is real**: Cochran's Q across the units' latitude trends exceeds its
   chi-square bar — `marine-null`'s "different seas doing different things", now tested at a
   unit count that can carry it. If this fails, that correction publishes against the finding.
3. **Warming water, moving fish**: the cross-unit slope of latitude trend on OISST trend is
   positive, interval clear of zero.
4. **Shallow forces horizontal**: the warming × depth interaction is negative.
5. **The unit count holds**: at least 15 units enter under the deterministic gear rule.

## 5. Stop conditions

- Fewer than 12 units after the deterministic re-measure → coverage statement, no regression.
- Calibration failing → predictions 2–4 uninterpreted; the OISST-on-the-shelf failure is the
  published result.
- Prediction 2 failing does not stop anything — it is a result.
- No segment, footprint, or driver definition is revisited after any trend is seen.

## 6. What this cannot establish

Everything Phase 3b's §6 lists, plus one more: the water the fish were actually in. OISST is
the sea surface as satellites and ships estimate it at 0.25°; bottom trawls live at the bottom.
The calibration bounds this substitution where it can be bounded and the caveat carries it
where it cannot.
