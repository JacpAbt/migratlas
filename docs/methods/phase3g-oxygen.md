# Phase 3g — does the water's oxygen sort the movers from the stayers, where its temperature did not?

**Status:** pre-registered 2026-08-19, **before any CMEMS request has been made**. Written before a
single oxygen value has been read, sampled, correlated or plotted. What *was* looked at first is in
§1: unit counts and median haul depths only, from the lake, because the design has to know its units
exist and has to fix the depth it reads oxygen at before reading any. The candidate was nominated in
[`covariate-survey-2026-08-addendum.md`](covariate-survey-2026-08-addendum.md) §5, where it was
deferred for want of a credential; the owner supplied one on 2026-08-19.

## Why this note exists

Phase 3e closed the marine question it opened and left a sharper one behind. Over eighteen units it
found the seas differ emphatically — Cochran's Q of 235.7 against a bar of 27.6 — and that warming
does **not** predict which of them move: the cross-unit slope of latitude trend on warming was
`+0.039 ± 0.179`, graded false against its own registered prediction. Its own closing sentence is
this note's mandate: *whatever sorts the movers from the stayers, it is not the thermometer alone.*

Dissolved oxygen is the leading non-thermal candidate in the literature and was, until today, the
one this project could not reach. The addendum established why: WOA23 publishes oxygen as an
all-time **climatology** — `cell_methods` reads `time: mean within years time: mean over years`, and
every decadal path returns 404 — so the free route cannot carry a trend at all. A time-varying field
needs the Copernicus Marine biogeochemical reanalysis and therefore an account.

**What the credential bought, verified without it.** Product
`GLOBAL_MULTIYEAR_BGC_001_029`, monthly dataset `cmems_mod_glo_bgc_my_0.25deg_P1M-m_202406`:
**1993-01 to 2026-05**, 0.25°, **75 depth levels from −0.5 m to −5,902 m**, carrying `o2` alongside
`nppv`, `chl`, `phyc`, four nutrients, `ph` and `spco2`. Licence clause 2.2 grants a royalty-free
perpetual right to "modify, adapt, develop, create and distribute Value Added Products or Derivative
Work … for any purpose" and to redistribute the product in original form — so unlike eBird, nothing
here poisons a derived tile. The client is a pure `py3-none-any` wheel.

## 1. What was looked at before this was written

**Counts and depths only, measured 2026-08-19 from the lake**, through Phase 3b's own pipeline — the
same consistent footprint, the same deterministic gear rule, the same longest single-gear segment —
so these are the same units Phase 3e fitted and not a different set.

| window | units clearing 20 segment years |
| --- | --- |
| 1982+ (Phase 3e's OISST window) | **19** — reproduces Phase 3e's own count exactly |
| 1993+ (this reanalysis begins) | **17** |
| 1993+ **and** a recorded median haul depth | **16** |

Three facts from that table shape the design.

**Eleven years of record cost two units, and one of them is the one Phase 3e was proudest of.**
NEUS-Fall — the 46-year unbroken single-gear run that Phase 3b's cruder rule had discarded and 3e
recovered — ends in 2008 and holds only 16 years inside the BGC era. NEUS-Spring goes with it. The
salvage that made Phase 3e possible does not survive this window, and the note records that rather
than quietly reporting a smaller *n*.

**One unit has no depth at all.** GSL-S records not a single haul depth across its segment (0% of
rows), which is the survey whose NaN median silently poisoned Phase 3e's solver until that run added
a guard. It goes to coverage by that existing rule, not by a new one.

**Median haul depths run 8 m to 258 m** — SEUS at 8, GSL-N at 258 — every one of them inside the
reanalysis's 75 levels with room to spare. So the depth question below is answerable rather than
aspirational.

**What was not looked at:** no oxygen value, at any depth, in any unit; no primary production; no
correlation, scatter, trend or fit involving any CMEMS variable. No CMEMS request has been issued.

## 2. Estimand and units, with their known problems first

- **Unit:** the survey's longest single-gear segment, clipped to 1993+, over its own consistent
  footprint. Unchanged from Phase 3b and 3e, deliberately: a unit definition revised for a new
  driver would make this a different experiment wearing 3e's numbers.
- **Response:** the unit's cross-taxa median latitude trend per decade, exactly as 3b and 3e
  computed it.
- **Driver:** annual mean `o2` over the unit's footprint cells, at **the reanalysis depth level
  nearest that unit's median haul depth**, in mmol m⁻³, trended per decade.
- **Secondary driver:** `nppv`, net primary production, at the surface, same footprint, same
  trend — food supply rather than habitability. Reported beside oxygen, never instead of it.

Known problems, stated before the design rather than after the result:

- **A reanalysis is a model constrained by observations, not a measurement — and a biogeochemical
  reanalysis is constrained far more thinly than a physical one.** There is no Argo-scale oxygen
  network; the model's `o2` is largely dynamics and parameterised biology. A trend in it therefore
  partly reflects its own assimilated observing system. This is the same caveat `narr` carries and
  it needs saying louder here, and it is why §6 refuses the word *measured* for anything below.
- **Bottom oxygen at 0.25° over a shelf is a coarse instrument.** The grid cell is tens of
  kilometres; the depth level nearest 38 m in the Baltic is not the water a trawl fished. The
  footprint mean is what is defensible, and it is not the water the fish were in — the distinction
  Phase 3e's own §6 drew for OISST, inherited here and worse.
- **Deoxygenation and warming are not independent.** Solubility ties them, which is exactly why §3
  makes that tie a *calibration* rather than pretending the two drivers are separable. Conditioning
  on warming does not isolate oxygen and this note does not claim it does.
- **Sixteen units is sixteen points.** Phase 3e's cross-unit regression carried the same limit and
  said so.
- **Every unit is northern.** `coverage-bias` already publishes this asymmetry as a finding; nothing
  here reaches the southern hemisphere.

**Excluded, and why:** the other seven BGC variables. Nutrients, pH and pCO₂ are all plausible and
all would turn this into a fishing expedition through eight drivers over sixteen units, which is the
design `literature-2026-08-coupling.md` refused for the coupling graph and refuses here. If oxygen
detects, one successor variable may be registered — after, and on its own note.

## 3. The design, fixed before any fetch

### The two calibrations, and they gate everything

Phase 3c established the pattern and Phase 3e used it: a link known from outside this project, which
must be detected or nothing below it is interpreted. Two, because one of them tests the *product*
and the other tests the *sampling*.

- **C1 — deoxygenation is happening.** The median unit's oxygen trend over 1993+ is **negative**.
  Global ocean oxygen loss over recent decades is among the better-established facts in ocean
  biogeochemistry; a product that shows sixteen northern shelf units gaining oxygen across thirty
  years is not reporting the ocean the literature describes, whatever else it is doing.
- **C2 — the oxygen behaves like oxygen.** Across units, the warming trend and the oxygen trend
  correlate **negatively**. Solubility requires it: warmer water holds less dissolved gas, and on a
  shelf that term dominates. C2 uses warming this project already holds, so it tests the sampling
  — depth choice, footprint, annual aggregation — against physics rather than against expectation.

**If either calibration fails, predictions 3 and 4 are not interpreted** and the phase publishes as
a calibration result: which of the two failed, and what that says about reading a BGC reanalysis at
shelf depths. That would be a useful published answer and it is the more likely one.

### The registered fit

Cross-unit weighted least squares, Phase 3e's `regression` machinery reused unchanged:

```
latitude_trend ~ 1 + oxygen_trend + warming_trend
```

Both drivers standardised across units so the two coefficients are comparable. Weights, the
heterogeneity test and the interval convention are Phase 3b's, unmodified.

Warming enters as a **conditioning term rather than a competitor**: Phase 3e already measured it at
`+0.039 ± 0.179` and this design is not re-litigating that. What prediction 4 asks is whether oxygen
carries anything the thermometer did not.

### Fixed before any value is read

- The depth level is chosen **once**, as the level nearest the unit's median haul depth, from the
  depths counted in §1. It is not revisited after any oxygen value is seen.
- The footprint is the unit's existing consistent footprint. Not re-derived.
- Annual means from monthly fields, all twelve months, no seasonal window — a seasonal window chosen
  after seeing trends is the commonest way this kind of analysis is quietly tuned.
- One fetch, one run.

## 4. Predictions

1. **C1 passes:** the median unit's oxygen trend is negative.
2. **C2 passes:** warming trend and oxygen trend correlate negatively across units.
3. **The hypothesis — deoxygenation predicts poleward movement.** The oxygen coefficient is
   negative (more oxygen loss, more poleward shift) with an interval clear of zero.
4. **Oxygen carries what the thermometer did not.** In the two-driver fit, oxygen's interval
   excludes zero while warming's includes it, as Phase 3e found it does alone.
5. **At least 15 units enter**, against the 16 counted in §1 — one unit of margin for a driver
   failure, and below 12 the phase publishes as coverage per Phase 3b's floor.
6. **Primary production does not out-predict oxygen.** `nppv`'s coefficient, fitted the same way, is
   no larger in magnitude than oxygen's. Graded false, the food-supply reading deserves its own
   registration and this one says so rather than absorbing it.

## 5. Stop conditions

- **Either calibration failing** → predictions 3, 4 and 6 uninterpreted; the phase publishes the
  calibration result and the coverage statement.
- **Fewer than 12 units entering** → coverage statement, no regression. Phase 3b's floor, unchanged.
- **A unit without a median haul depth** goes to coverage by Phase 3e's existing guard, never to a
  substituted depth.
- No segment, footprint, depth level, month set or driver definition is revisited after any oxygen
  value has been seen. If the fetch reveals the product is unusable as sampled, that is a published
  coverage statement and a successor registration, not an adjustment here.
- The `nppv` secondary is fitted once, reported once, and does not become the headline if oxygen
  fails.

## 6. What this cannot establish

- **Causation, in any form.** Sixteen units, one cross-sectional regression, two collinear drivers.
  A negative oxygen coefficient would say that the seas losing more oxygen are also the seas whose
  fish moved further poleward — which is worth knowing and is not a mechanism.
- **That oxygen is the sorter.** Deoxygenation covaries with warming, stratification and
  productivity. Conditioning on warming removes one of those three.
- **Anything a fish experienced.** The driver is a footprint-and-depth mean from a model. Phase 3e
  drew this line for a satellite reading the surface; it is further from the animal here, not closer.
- **That the reanalysis is right.** Nothing in this design validates CMEMS oxygen against
  observations, because this project holds none. C2 tests it against physics, which is weaker, and
  the word *measured* is not available for any number below.
- **Anything outside sixteen northern shelf surveys**, and nothing at all about the individuals,
  the timing, or the other realms.
