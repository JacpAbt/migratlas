# Forecast A — what the fitted thermal response implies under scenario warming, and where it stops being sayable

**Status:** pre-registered 2026-08-19, **before any scenario store has been opened**. Written before
a single ScenarioMIP temperature has been read, sampled, differenced or projected. What *was* looked
at first is in §1: catalogue counts only, from the copy already in the raw archive, because a design
has to know which models can carry a projection before it specifies one. This is `TASKS.md` #13 and
`DATASETS.md` step 1, and it inherits both.

## Why this note exists, and what it refuses to be

`DATASETS.md` recorded this as the one forecast the project's own results support, and named its
headline in advance: *"the novelty mask is likely to be the headline."* This note is that step, and
it starts by settling the thing that could make it dishonest.

**#54 constrained a forecast to where hindcast skill exists, and hindcast skill barely exists.**
Phase 3a found autumn timing above chance at 20 of 143 stations and spring nowhere. Phase 3f pooled
the rows, added the wind, and stopped at its own calibration rung without improving on that. Read
strictly, that constraint licenses almost nothing.

**It does not bind this, and the reason is the same one the response dial rests on.** Hindcast skill
measures *interannual* predictability: given this year's drivers, can the model beat the climatology
for this year? A scenario projection asks something else — if the pre-season is persistently warmer
by ΔT, what does the fitted within-station response imply for the mean passage date? The first is a
forecast. The second is a response function read forwards, which is what
[`reports/response.py`](../../src/migratlas/reports/response.py) already publishes as a dial with its
envelope drawn and extrapolation refused. This note is that dial extended along one axis — someone
else's scenario temperature instead of a reader's slider — and it is bound by exactly the same two
limits: the fitted envelope, and the band.

**So the deliverable is a mask more than a map.** Under any warm scenario the late century leaves the
range S was fitted over, and outside that range a straight line is arithmetic rather than evidence.
The registered output is therefore *where the projection may be stated at all*, and the projected
values only where it may.

Every projection in this note also carries, beside it, whether that station has any interannual
skill at all. A reader who takes a scenario response for a year-ahead forecast has been misled by
presentation, and the presentation is this note's responsibility.

## 1. What was looked at before this was written

**Catalogue counts only, measured 2026-08-19** from the Pangeo CSV already cached in the raw archive.
No zarr store was opened; no temperature was read.

| | |
| --- | --- |
| catalogue rows | 514,818 |
| ScenarioMIP `Amon tas` stores | **1,392** |
| models with a paired `historical` run in this project's ensemble | 15 |
| of those, with **all four** SSPs | **13** |

Per scenario, across the fifteen: ssp126 at 14, ssp245 at 15, ssp370 at 13, ssp585 at 15. The two
incomplete models are **GFDL-CM4** (no ssp126, no ssp370) and **HadGEM3-GC31-LL** (no ssp370).

This reproduces `DATASETS.md`'s own measurement of 2026-07-30 exactly — 1,392 stores, 13 of 15 with
all four — which is three weeks of the catalogue not moving under a claim this note depends on.

**What was not looked at:** any scenario temperature, any anomaly, any projected shift, any mask
share. No store was opened.

## 2. Estimand and units, with their known problems first

- **Unit:** the station-scenario-window. Stations are the **78 in the claim band, 37–50°N**, because
  that is where `S` is published and `transfer-fails` measured a response fitted in one place
  transferring nowhere else untested (hold-one-out error 0.68 across realms).
- **Response function:** `S`, the within-station thermal sensitivity of autumn passage date,
  `−0.659 ± 0.165` days per °C over 78 stations, from `phase2a_timing.sensitivities()`. Read, not
  re-estimated. If this note re-fitted it, the projection and the ledger would be free to disagree.
- **Driver:** June–July mean 2 m air temperature over each station, from ScenarioMIP `Amon tas`,
  expressed as **each model's own anomaly against its own 1995–2014 baseline** and added to nothing —
  the anomaly *is* ΔT. A model running warm or cold cancels, which is the same trick that made `f` a
  ratio in the attribution.
- **Windows:** **2040–2059** and **2080–2099**. Two, not a smooth curve: the point is the contrast
  between a horizon inside the fitted range and one outside it.
- **Projected shift:** `S × ΔT`, in days, per station-scenario-window, with `S`'s interval carried
  through.

Known problems, stated before the design rather than after the numbers:

- **`S` carries only the thermal half of the observed advance.** `anthropogenic-share`'s own caveat:
  of the observed `−0.56 ± 0.25` days per decade, the part tracking pre-season temperature is
  `−0.30 ± 0.09`, and the rest does not track temperature at all and is unexplained. A projection
  built on `S` projects the explained half and is silent about the other. It must not be read as a
  projection of passage date.
- **Interannual skill is absent at 123 of 143 stations.** Reported per station beside every
  projection, per the framing above.
- **The envelope is narrow and the scenarios are not.** `S` was fitted over within-station pre-season
  departures whose 5th-to-95th band is `−1.86` to `+1.74 °C`. Any ΔT beyond that is outside the
  fitted range by construction.
- **Every driver held constant is a claim about the future.** Wind, land use, light, and the
  unexplained half are all held at zero change, and §3 requires that stated in the output rather
  than in a footnote.
- **Model spread is not uncertainty about the world.** Thirteen models disagreeing is a statement
  about models.

**Excluded, and why:** spring, which has no published `S` and no skill; every realm but aerial, per
`transfer-fails`; the 24–37°N band, where Phase 1c's unexplained 2012 step lives and where a fitted
response would inherit it; and degree-day or extreme-day forms of the driver, which would need daily
CMIP6 rather than `Amon` and are a different and much larger commitment.

## 3. The design, fixed before any store is opened

### Selection

A model enters only with **both** a `historical` run (for its own baseline) and the scenario in
question. Members are capped at three per model per experiment and averaged within model before
anything crosses models, exactly as `drivers/cmip6.py` already does — otherwise CanESM5's fifty
members would make the answer a statement about CanESM5.

### The mask, which is the deliverable

A station-scenario-window is **sayable** only if the multi-model median ΔT lies inside the fitted
envelope, `[−1.86, +1.74] °C`, the 5th-to-95th band of the within-station departures `S` was fitted
over — the same bound `reports/response.py` publishes, for the same reason: a limit one observation
can move is not a limit.

Reported beside it as a registered sensitivity, never instead of it: the same mask at the
**absolute** observed range, `[−3.57, +3.97] °C`. Two masks, because the choice between them is a
judgement and hiding it inside one number would be the interesting part going missing.

### The fit

There is none. This is arithmetic on a published coefficient: `S × ΔT`, with `S`'s interval carried
through and the model spread reported separately. Nothing here estimates anything, which is why this
note has no null and no permutation test — and why it can be run at all on a response whose test era
Phase 3f has spent.

### Fixed before any number is seen

- The envelope bounds, the two windows, the band, the member cap and the baseline period.
- The mask is applied before any projected value is reported, not after inspecting it.
- One fetch, one run.

## 4. Predictions

1. **The mask grows with warming.** The sayable share falls monotonically from ssp126 to ssp585
   within each window, and from 2040–2059 to 2080–2099 within each scenario.
2. **The late century under ssp585 is almost entirely unsayable** — fewer than 10% of the 78
   stations inside the envelope.
3. **The near horizon under the coldest scenario is mostly sayable** — more than half the stations
   inside the envelope for ssp126, 2040–2059.
4. **No sayable projection exceeds two days of advance.** It cannot: `S` times the envelope's upper
   bound is `0.659 × 1.74 ≈ 1.15` days. Registered as a prediction anyway, because a number larger
   than that appearing would mean the mask was not applied.
5. **Which model you pick matters as much as the response fit.** At 2040–2059 the inter-model range
   of ΔT, multiplied by `S`, is at least as wide as `S`'s own interval at the median ΔT.

## 5. Stop conditions

- **Fewer than 13 models delivering a usable scenario series** → publish as a coverage statement,
  no projection.
- **Nothing sayable anywhere, in any scenario or window** → that is the result, published as the
  mask alone. It would be a stronger outcome than a map.
- **Any station whose model baseline is missing** goes to coverage, never to a substituted baseline.
- No envelope, window, band, member cap or masking rule is revisited after any projected value has
  been seen. If the mask turns out to leave an uninterestingly small map, that is the finding.
- The unexplained half of the advance is not modelled, extrapolated or apportioned. It is named.

## 6. What this cannot establish

- **Anything about a particular future year.** This is a response function read forwards under a
  scenario, and Phase 3d refused this project a year-ahead prediction on measured grounds. The two
  are different objects and the output says so on every row.
- **Passage date.** Only the thermally-driven component of it. The other half of `−0.56` remains
  unexplained and unprojected, and a reader adding the two would be inventing the second.
- **Anything outside 37–50°N aerial.** Not the southern band, not the herds, not the seas, not
  spring.
- **That the response stays linear, or stays at all.** `S` is a coefficient fitted over thirty years
  of departures within a ±2 °C band. Whether a bird's response to +1.7 °C resembles its response to
  +0.5 °C is exactly what the envelope declines to assert, and Phase 3f's spline arm — which might
  have spoken to it — is unread behind a fired calibration.
- **That the mask is conservative enough.** It is drawn from the observed departure band, which is a
  statement about what was sampled and not about where the biology holds.
