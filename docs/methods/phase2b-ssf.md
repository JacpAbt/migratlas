# Phase 2b — what does a step cost, and what is it buying?

**Status:** pre-registered 2026-08-19. Written before any step has been built, any covariate
sampled along any track, or any selection coefficient fitted. What *was* looked at first is in
§1: gap-structure counts only, because a step-selection design needs to know its steps exist
before it can define them. This note answers the README's own oldest open question ("what
drives an individual animal's decisions?") at the smallest honest scale the lake supports.

## Why this note exists

The lake holds six million cleared track fixes whose findings so far are all *negative
space* — what collars cannot measure (Phase 1d), what displacement did not do (Phase 1h), what
years could not be asked (Phase 3a). Step selection is the analysis the tracks exist for: it
conditions each observed step on where the animal *could* have gone in the same interval, so
the sampling-rate confound that killed timing questions never enters — both the used and the
available steps live inside the same fix pair. The covariates have been waiting since the
survey: terrain verified, snow ingested, forty-one years of NDVI reduced.

## 1. What was looked at before this was written

Gap structure only, measured 2026-08-19 — no position, no covariate, no pairing:

| source | pairs at 1–3 h | verdict |
| --- | --- | --- |
| `movebank_yahatinda_elk` | 688,634 | in |
| `movebank_svalbard_reindeer` | 1,194,855 | in |
| `movebank_bylot_fox_gps` | 9,455 (of 1.72 M pairs, nearly all sub-hourly) | **out** |

The fox is excluded with its reason stated: its collars burst-sample at sub-hourly cadence, so
its natural step is a different object at a different scale, and forcing it into this design
would measure the resampling. A fox note can follow with its own scale.

## 2. The step, and the choice set

- **A step** is two consecutive GPS fixes of one animal between 1 and 3 hours apart, target
  2 hours. Pairs outside the window are not steps; nothing is interpolated.
- **The choice set**: each used step is matched with **10 available steps** from the same
  start point, lengths drawn from the herd's own empirical step-length distribution, turn
  angles uniform. Simpler than fitting parametric movement kernels, and the simplification is
  a stated limitation, not a hidden one.
- **Strata**: one used + its ten available steps form one stratum of a conditional logistic
  model — the standard SSF likelihood, fit per herd per season by numpy/scipy.
- **Seasons**: winter (December–March) and summer (June–September), fit separately. Spring
  (April–May) is fit only for prediction 4's contrast.

## 3. The covariates, fixed here

Sampled at each step's endpoint, standardised within herd-season:

- **Elevation and slope** from Copernicus GLO-30 (the fetch this note licenses; tiles for the
  two ranges, no auth).
- **Snow depth** from the ERA5-Land boxes already on disk — the endpoint's month, 9 km. The
  cadence mismatch (monthly snow against 2-hour steps) is stated: snow enters as a slow field,
  not a weather event.
- **NDVI** from the PKU archives already on disk — the endpoint's half-month and 1/12° cell,
  each step's year's own value, not the climatology.
- **Step length and its log**, as movement control terms, per SSF convention.

Nothing joins this list after this line.

## 4. Predictions

1. **Slope is avoided**: β_slope < 0 with its cluster-bootstrap interval clear of zero, in
   both herds, both seasons. The most confident prediction in this note; if it fails, the
   pipeline is suspect before the animals are.
2. **Winter snow is avoided**: β_snow < 0 in winter in both herds — deeper snow costs more per
   metre, and both herds live where that cost is real.
3. **Summer greenness is selected**: β_NDVI > 0 in summer in both herds.
4. **These residents do not surf**: the spring NDVI coefficient does **not** exceed the summer
   one in either herd. Green-wave surfing is a migrant's strategy; Phase 1h showed these herds
   do not migrate further than their collars can deny, and this prediction registers the
   expectation that they do not track the wave's front either. Graded false, it would be this
   design's most interesting result.

## 5. Stop conditions

- A herd-season with fewer than 5 animals or fewer than 5,000 used steps is not fit.
- A coefficient whose cluster-bootstrap interval (animals resampled, 500 draws) fails to
  stabilise is published as unstable, not interpreted.
- Any published utilization or selection surface passes the ethics gate exactly as the
  presence layers do: 0.01° floors, k ≥ 3 animals, the elk's `moderate` clearance — the gate
  is upstream of anything this analysis draws.
- No covariate, season window, or step definition changes after any coefficient is seen.

## 6. What this cannot establish

Causation in the behavioural sense — selection for a covariate is not preference, it is
correlated use given availability. Anything about migration — these are resident herds, chosen
by who collared them. Anything at scales the step erases: sub-hourly decisions (the fox's
world) and lifetime range shifts (Phase 1h's world) both live outside a two-hour window. And
nothing about other populations: two herds, two mountains' worth of scope, no more.
