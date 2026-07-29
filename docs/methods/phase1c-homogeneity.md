# Phase 1c — is the radar record homogeneous enough to carry the trend?

**Status:** pre-registered 2026-07-29. Written before any of the three tests below was run, and
before the new columns were looked at, for the same reason Phase 1a and 1b were: the tests are only
worth anything if the predictions were fixed in advance.

Phase 1a reported an autumn advance of 0.6–0.7 d/decade at 37–50°N that survived four break
specifications, a mid-winter placebo and a permutation null. Three things about the *instrument*
were never tested, and each of them could produce that number with no change in animal behaviour.
All three are testable from the daily product, which ships columns the ingest was dropping.

The claim under test is not "did animals shift". It is **"does the measurement mean the same thing
in 2025 as it did in 1995"**. If it does not, the Phase 1a number is an artefact and has to be
withdrawn or re-scoped. That outcome is on the table, and this note exists so it cannot be argued
away afterwards.

## Test A — is the trend an artefact of speed weighting?

**The problem.** Passage-date quantiles are cumulative sums of `traffic`, which integrates

```
RTR = reflectivity x speed x bin_height
```

so every measurement is weighted by how fast the scatterers were moving. `reflectivity_hours`
integrates

```
VIR = reflectivity x bin_height
```

and has no speed term. Both are published per station-night and both are now ingested.

This matters because flight speed is not a constant. It varies with wind support, and wind support
has its own trends and its own seasonal cycle. A season in which the later nights carry more tailwind
than they used to will push mass in the cumulative `traffic` curve towards those later nights, moving
the median passage date *later* — or the reverse — with the same birds flying on the same dates.

**Prediction if the Phase 1a result is biological.** The autumn quantile trends at 37–50°N recomputed
on `reflectivity_hours` agree with the `traffic` version in sign, and within roughly the reported
uncertainty (±0.3 d/decade), and stay outside the permutation null.

**Prediction if it is a speed artefact.** The trend shrinks towards zero, loses significance, or
flips sign when the speed weighting is removed.

**What is reported either way.** Both numbers, side by side, for every quantile and both seasons —
not just the surviving one. If they disagree, the honest headline is the speed-free version, because
the biological question ("when did the animals pass") is a question about mass aloft, not about
momentum across a transect. Horton et al. used a traffic rate, so `traffic` stays the replication
metric; `reflectivity_hours` becomes the headline metric only if the two diverge, and the divergence
is then the finding.

**Pre-committed:** no re-selection of stations, years, quantiles or break specification between the
two runs. Same pipeline, one column swapped.

## Test B — is the 2012 step precipitation screening?

**The problem.** Phase 1a found a step at the dual-polarisation upgrade whose size is graded by
latitude: +2.16 d at 24–32°N against +0.01 d at 42–50°N. Window truncation (0.0% clipping), panel
composition (0.01 d) and curvature (<0.1 d) were each tested and each failed to explain it. It is
currently unexplained inside a headline result, which is the least comfortable place for it to be.

The remaining instrument-side candidate is the screening. MistNet decides which volumes are
precipitation, and the amount of work it has to do varies enormously with climate: convective
rainfall is far heavier in the south-east than in the north-east. If the screening's behaviour
changed at the upgrade, the effect would be largest where there is most rain to screen — which is a
latitude gradient that could masquerade as the one observed.

**The measurements, both now ingested.** `fraction_rain` gives the share of sampled volumes
classified as precipitation per station-night. The unfiltered/filtered ratio of either quantity gives
how much the screening actually removed.

**Prediction if the step is screening.** Per station, the size of the fitted break coefficient
correlates positively with that station's mean `fraction_rain` (and/or with the change in the
unfiltered/filtered ratio across the break), and the latitude gradient in the break largely
disappears once rain fraction is conditioned on. The screening series itself shows a step at the same
date.

**Prediction if it is not.** No such correlation, and `fraction_rain` and the removal ratio are
smooth across the upgrade dates.

**Prior, stated so the result is not over-read.** This test is expected to come back negative.
MistNet was built to work on the *pre*-dual-polarisation archive and operates on single-polarisation
moments, so the upgrade should not change what it sees. A negative therefore rules out a mechanism
rather than explaining the step, and the step stays unexplained — which is already a better position
than not having asked, but it is not a result to dress up.

## Test C — did the composition of the biomass change?

**The problem.** The measurement is aerial biomass, not birds. Phase 1a bounded the *annual*
contribution of resident insect biomass with the July share (3.5% observed against 8.8% for a flat
year), which shows migration dominates the yearly cycle. It does not bound the mixture night by
night, it says nothing about *migratory* insects, and it does not exclude bats at all.

The sharper risk is not the level but the drift: if the bird-to-insect ratio changed over thirty
years, then a trend in passage dates can be a trend in *what is being measured*. The Dark Ecology
descriptor states that the consequences of warming for insect migration phenology are undescribed,
so there is no published expectation to lean on.

**The method, adapted from a published one.** Airspeed separates the groups: birds fly 8–15 m s⁻¹,
insects 0–5 m s⁻¹. [Shi et al. 2025](https://academic.oup.com/condor/article/127/3/duaf020/8051150)
(*Ornithological Applications*) use airspeed jointly with velocity variability to estimate mixture
proportions. Their velocity-variability term is the per-height-bin VVP fit residual, which lives in
the vertical profiles and not in the daily product, so only the airspeed half is available cheaply.

The daily product publishes reflectivity-weighted `u`, `v` and **ground** speed. Airspeed is

```
airspeed = | (u, v) - (u_wind, v_wind) |
```

with the wind field sampled at the station and night from ERA5 at 850 hPa, which is the level
nearest the bulk of the profile (100 m bins to 3000 m above the radar). That gives one
reflectivity-weighted mean airspeed per station-night for 1995–2025.

**What a mean can and cannot do.** A single reflectivity-weighted mean over a mixture is not a
mixture proportion, and will not be reported as one. It is an index that moves monotonically with
the bird share under the two groups' known speed ranges. It is used for exactly two things:

1. **A level check.** Nights whose mean airspeed sits in the insect range are flagged, and the
   phenology is recomputed excluding them. If the 37–50°N autumn trend is unchanged, insects are not
   carrying it.
2. **A drift check.** Mean airspeed is regressed on year, per station and pooled, restricted to the
   migration windows the phenology uses. **A significant trend in mean airspeed is the failure
   condition for Phase 1a's interpretation**, because it means the mixture moved.

**Prediction if the Phase 1a result is biological.** No trend in within-window mean airspeed beyond
the null, and excluding insect-range nights leaves the passage-date trends within uncertainty.

**Confound to handle before believing a null.** Airspeed is a difference between two quantities with
their own histories: measured scatterer velocity, and a reanalysis wind. ERA5 is not homogeneous
either — its observing system changed over 1995–2025. So a trend in airspeed must be checked against
a trend in the ERA5 wind alone at the same points, and a trend present in both is attributed to the
reanalysis, not to the animals. Reporting airspeed drift without that check would be the same class
of error as reporting a passage-date trend without the dual-pol break term.

**Deferred, deliberately.** The full mixture model needs the profiles (220 GiB across seven Zenodo
records). It is worth a station-and-season subset only if the cheap tier shows drift, and it would
then be a validation of this test rather than a replacement for it.

### Test C's prediction, sharpened by Test A′ and fixed before the wind data landed

Test A′ (below, run 2026-07-29) measured what Test A only had to be insensitive to: mean ground
speed **did** drift, and very differently by season. Spring night ground speed rose
**+0.572 ± 0.118 m s⁻¹ per decade** on a 13.42 m s⁻¹ base — about 13% over the record — while autumn
rose only +0.102 ± 0.079 on 11.36. Day speeds rose alongside night in spring (+0.453 ± 0.141) and
the night-minus-day gap stayed flat in both seasons.

Ground speed is airspeed plus wind, so exactly one of two things produced the spring rise, and
airspeed separates them:

1. **Wind.** Spring winds over the network strengthened, or the mix of nights birds chose shifted
   towards stronger tailwinds. Then **airspeed is flat while wind speed rises**, and the ground
   speed trend says nothing about what is flying.
2. **The animals.** Either the same taxa flew faster, or the mixture moved towards faster fliers.
   Then **airspeed rises with the ground speed**, and a composition change is live — which is the
   failure condition for Phase 1a's interpretation.

The day-speed rise already favours the first, because daytime aerial biomass is insect-dominated
and insects have no reason to have gained 0.45 m s⁻¹ of self-powered speed in thirty years. But
"favours" is not "shows", and the wind term is measurable.

**So, pre-registered:** spring airspeed trend indistinguishable from zero while NARR wind speed at
the same stations and nights rises; autumn airspeed flat, matching its flat ground speed. Any other
combination needs explaining, and the one that would force a re-scoping of Phase 1a is a rising
autumn airspeed.

**The control this test cannot skip.** Airspeed is a difference between the radar's velocity and a
reanalysis wind, and reanalyses are not homogeneous either — NARR's assimilated observing system
changed over 1995–2025. So the wind trend at the same points is computed and reported alongside,
and a trend appearing in both is attributed to the reanalysis rather than to the animals. Reporting
airspeed drift without that check would be the same class of error as reporting a passage-date
trend without the dual-polarisation break term.

## Results — Tests A and B, run 2026-07-29

Reproduce with `make phase1c-report`. Test C is not here; it waits on the driver panel.

### Test A: the trend is not a speed artefact

Paired per station, 849 station-season-quantile slopes under each quantity — the same stations
under the same coverage filter, so the two runs differ in exactly one column.

| Autumn q50 | `traffic` | `reflectivity_hours` | paired difference |
| --- | --- | --- | --- |
| 24–32°N (n=23) | +0.21 | +0.36 | +0.15 ± 0.29 |
| 32–37°N (n=42) | −0.64 | −0.76 | −0.13 ± 0.33 |
| 37–42°N (n=43) | −0.46 | −0.60 | −0.13 ± 0.20 |
| 42–50°N (n=35) | −0.68 | −0.71 | −0.03 ± 0.17 |
| **37–50°N pooled** | **−0.56** | **−0.65** | **−0.09 ± 0.14**, r=0.86 |

**The prediction held.** Dropping the speed weighting leaves the autumn advance at 37–50°N
intact — if anything marginally stronger, and the paired difference is indistinguishable from
zero. The Phase 1a headline does not depend on `traffic`'s speed term, which was the outcome
worth checking and not the one guaranteed in advance.

Spring is worth a sentence because it moves the other way: the paired difference at 37–50°N is
+0.23 ± 0.17, and at 42–50°N the sign flips between metrics (`traffic` −0.13, hours +0.15). Both
intervals cover zero, so this is not a spring trend appearing or disappearing — it is consistent
with Phase 1a's finding that spring has no detectable trend, and it adds that what little
negative signal spring showed in `traffic` was partly the speed weighting. Reported because it
was in the pre-registered table, not because it is a result.

### Test B: the screening did change, and it does not explain the step

Two separate findings, and conflating them would be the easy mistake.

**The screening series steps at 2012, which was not predicted.** On a fixed panel of 142 of 145
stations with at least five years each side of the break, mean `rain_fraction` falls in both
season windows: 0.1747 → 0.1450 in spring and 0.1364 → 0.1126 in autumn, over 17 pre-break years
against 14 after. Per station the step is −0.0237 ± 0.0053 in spring and −0.0184 ± 0.0051 in
autumn, both comfortably non-zero. The note above predicted this would be flat, on the reasoning
that MistNet operates on single-polarisation moments and so should be blind to the upgrade.
**That prior was wrong.** The likeliest remaining mechanisms are that the upgrade changed which
elevation sweeps are available — the descriptor requires a sweep within 1° of each of five
requested angles — or that the 2012–2016 US drought is simply real meteorology. Distinguishing
them needs an independent precipitation record, which is the ERA5 dependency, so it is left open
here rather than guessed.

**It still does not explain the autumn step.** Rain is measured inside each season's own window,
so each phenology step is compared against the screening it actually saw:

| correlation with phenology step | spring (n=140) | autumn (n=142) |
| --- | --- | --- |
| station's screening step | **+0.26** | **−0.07** |
| station's mean rain fraction | +0.06 | −0.19 |
| station latitude | −0.08 | −0.23 |

Mean autumn phenology step is +1.41 ± 0.66 d, consistent with Phase 1a. The latitude gradient is
present (−0.23, the sign that matches +2.16 d at 24–32°N against +0.01 at 42–50°N) and rain
explains none of it — a station whose screening changed most is not a station whose autumn
passage dates jumped most. **The mechanism is ruled out for autumn, and the step remains
unexplained.**

The spring column is what makes that a real null rather than an insensitive test. Spring's
phenology step correlates with its screening step at +0.26 across 140 stations, so this design
*can* detect the coupling when it is there. Two consequences, and only the first bears on the
Phase 1a claim: the autumn null is a null with demonstrated power, and spring's own step — which
is −0.68 ± 0.76 d and covers zero, so not a Phase 1a claim — is partly screening-coupled and
should not later be promoted to a result without accounting for that.

So the tally on the autumn 2012 step is four mechanisms tested and four rejected: window
truncation, panel composition, curvature, and precipitation screening.

### The incidental finding worth recording

The screening severity of this dataset is not stationary: it steps by about 17% relative at 2012
and partially recovers afterwards. Anyone using the filtered-versus-unfiltered contrast as a
sensitivity test across that boundary — as Phase 1a does — is comparing two differently-screened
eras. It did not affect the phenology result, but it is a property of a widely-used public
dataset that its descriptor does not mention, and it is the kind of thing that would quietly
corrupt an analysis of biomass *levels* rather than of timing.

## What this note commits to

- All three tests are reported whether they support Phase 1a or destroy it.
- No station, year, quantile or specification is re-chosen after seeing a result.
- If Test A or Test C fails, the Phase 1a headline is re-scoped in `phase1-phenology.md` and the
  change is recorded there rather than quietly corrected.
- Test B is expected to be negative and a negative will be reported as "mechanism ruled out", not as
  "step explained".
