# Phase 2a, first link — does a fish keep its temperature or keep its place?

**Status:** pre-registered 2026-07-30, before any trend was fitted. Coverage was measured first,
because it decides which surveys can be in the test at all, and that is a decision that must not be
made after seeing an answer.

`phase2a-design.md` names this as the first testable link of the trophic pathway and the one needing
no new source: FISHGLOB carries a temperature measured *at the haul*, by the same instrument that
caught the fish, over decades. The question is what an animal does when its water warms.

Two things it can do, and they are distinguishable:

- **Track.** Move — polewards, deeper, or both — so that the temperature it occupies stays what it
  always was. Its position changes and its thermal niche does not.
- **Stay.** Remain where it is and experience warmer water. Its position does not change and its
  occupied temperature rises with the ambient.

Phase 1b already found that the latitude centroids largely **did not move**: pooled median
−0.011 °latitude per decade, 48% poleward, inside the permutation null. So if the water warmed, most
species must have been staying rather than tracking — unless depth was the escape route, which
Phase 1b reported but declined to claim.

## The measurement

Bottom temperature, not surface. These are demersal trawl surveys, so the bottom is the water the
fish are in; sea-surface temperature over a fish at 200 m is a different water mass. Surface is
carried through as a secondary check only, and where a survey has one and not the other that is
recorded rather than substituted.

Three quantities per survey, all on the **consistently sampled footprint** from Phase 1b, so a
survey that added or dropped stations cannot manufacture a thermal trend:

1. **Occupied temperature**, per species per year: the CPUE-weighted mean bottom temperature across
   the cells that species was caught in. Weighted the same way the distribution centroids are, so
   the two are the same kind of number.
2. **Available temperature**, per survey per year: the *unweighted* mean bottom temperature across
   the same footprint. This is the thermal environment the survey sampled, regardless of fish.
3. **Latitude and depth centroids**, per species per year, already computed by `metrics/range.py`.

## The tracking index, and why it needs the ambient term

An occupied-temperature trend alone says nothing. If a species' occupied temperature held constant
while the ocean did not warm, it did nothing at all. The informative quantity is occupied against
available:

```
tracking = 1 - (trend in occupied temperature / trend in available temperature)
```

- **≈ 1** — the ambient warmed and the occupied temperature did not. Full thermal tracking: the
  animal moved enough to hold its niche.
- **≈ 0** — the occupied temperature rose exactly as fast as the ambient. No tracking: it stayed put
  and warmed.
- **< 0** — occupied temperature rose *faster* than ambient, meaning it moved into warmer water.

Reported only where the available-temperature trend is distinguishable from zero, because the index
is a ratio and a near-zero denominator makes it meaningless rather than large. Surveys whose ambient
did not warm are reported as "no thermal forcing to respond to", which is an answer.

## Predictions

Fixed here, before fitting:

1. **Ambient bottom temperature has risen in most of these surveys.** If it has not, the whole test
   is uninformative and that will be said rather than worked around.
2. **The tracking index is near 0 for most species**, because Phase 1b established the latitude
   centroids did not move. Staying, not tracking.
3. **Depth is the discriminator.** Species whose depth centroid deepened should show a higher
   tracking index than those whose did not. If tracking is happening at all in a network whose
   latitudes are static, depth is the only route left.

Prediction 3 is the one worth the work. Prediction 2 is close to a restatement of Phase 1b and would
be weak evidence on its own.

## The identifiability trap, stated before it can be fallen into

**Depth and temperature are not independent measurements.** Deeper water is colder, so "the species
went deeper" and "the species held its temperature" are two descriptions of one event, not two
findings that corroborate each other. Presenting them as mutual support would be circular.

What the DAG says, and what this test is therefore allowed to conclude: depth is a *route* by which
thermal tracking happens, not a separate driver of it. So the defensible output is a single statement
— whether a species tracked its temperature, and by which axis — and never two statements counted
twice.

## Confounds, each measured rather than assumed away

1. **Sampling-date drift.** A survey whose mean day-of-year moved later samples warmer water for
   that reason alone. The trend in mean day-of-year is computed per survey and reported alongside
   every thermal trend. A survey with a material date drift is flagged and its thermal trend is not
   claimed.
2. **Haul drift inside the footprint.** The consistency rule works on 1° cells, and a 1° cell can
   span a shelf break, so hauls could migrate to deeper or shallower ground while the cell stays
   "consistently sampled". This is the same limitation Phase 1b recorded for its depth centroid and
   it is not solved here.
3. **Temperature missingness is not random.** Coverage runs from 99.8% (SEUS) to 0% (all Canadian
   surveys, GSL, Nor-BTS, most of the Irish and French series). A haul with a recorded temperature
   may differ systematically from one without. So a minimum share is required per survey-year, and
   the share is reported.
4. **Warm-water surveys can hit a ceiling.** In the Gulf of Mexico a species at its thermal maximum
   has nowhere warmer to be sampled, which truncates the occupied-temperature distribution from
   above and biases the trend downward — looking like tracking. Flagged for the GMEX and SEUS series
   specifically.

## Results, run 2026-07-30

Reproduce with `make phase2a-thermal`. 2,831,609 survey rows, 1,561,534 carrying a bottom
temperature (55%).

### Prediction 1 held, but only five surveys can answer anything

Of twenty survey units reaching the footprint threshold, **five have an ambient warming trend
separable from zero** and a stable calendar. Where it is separable, the water did warm:

| survey | ambient °C/decade | years | note |
| --- | --- | --- | --- |
| NEUS-Fall | **+0.715 ± 0.198** | 51 | **excluded — calendar drifted −5.1 d/decade** |
| GMEX-Fall | +0.507 ± 0.173 | 39 | warm ceiling |
| SEUS-fall | +0.483 ± 0.440 | 31 | |
| GMEX-Summer | +0.303 ± 0.259 | 41 | warm ceiling |
| SCS-SUMMER | +0.216 ± 0.159 | 49 | |
| NEUS-Spring | +0.162 ± 0.147 | 47 | |

Fifteen surveys drop out, most for having too few years with a thermometer at all, and four
because their ambient trend cannot be told from zero — including both flat SEUS series.

**The most painful exclusion is the most informative survey.** NEUS-Fall has the strongest warming
in the set by a wide margin, and its mean sampling date moved 5.1 days per decade earlier. Warming
water and a shifting calendar produce the same signature in an occupied-temperature trend, and 51
years of the best-covered survey cannot separate them. It is dropped rather than caveated, and that
is the single largest cost of confound 1.

### A correction to how the ambient threshold was implemented

The pre-registration said the index would be "reported only where the available-temperature trend is
distinguishable from zero". The first implementation made that a **magnitude floor** of 0.05 °C per
decade, which is not a test of distinguishability at all, and SP-NORTH walked straight through it:
an ambient trend of +0.069 ± 0.181 °C/decade — comfortably indistinguishable from no warming —
produced a mean tracking index of **+1.23 ± 0.70**, the ratio exploding on a denominator that was
noise.

Replaced with the criterion actually promised: the ambient trend must exceed 1.96 of its own
standard error. That is not a threshold moved after seeing a result, it is a bad proxy replaced by
the thing the note committed to, and SP-NORTH, EBS and both flat SEUS series fall out on it.

### Prediction 2 held: they stay and warm

Across the **673 species-survey pairs** from calendar-stable surveys:

- **median index +0.06, mean +0.08 ± 0.11** — indistinguishable from zero.
- 33% tracking (index > 0.5), 41% staying, **27% moving into warmer water** (index < −0.5).

So the typical North American shelf fish did not hold its thermal niche. Its water warmed and it
warmed with it.

And the pooled number hides the finding again, exactly as `phase2a-design.md` said it would: a
median of +0.06 sits between a third of species that clearly track and a quarter that move
*towards* warmer water. Per survey the spread is enormous — NEUS-Spring +0.13 ± 0.35, SCS-SUMMER
+0.11 ± 0.46 — which is the "mean near zero with large τ" case, not an absence of response.

GMEX-Fall is worth singling out: **−0.23 ± 0.11**, moving into warmer water, and it carries the
warm-ceiling flag that biases *towards* apparent tracking. A negative index in spite of a bias in
the other direction is the strongest single reading here.

### Prediction 3 failed: depth is not the route

This was the prediction worth the work, and it does not hold.

| | mean | correlation with tracking index |
| --- | --- | --- |
| depth shift | **+2.015 ± 0.922 m/decade** | **+0.12** |
| latitude shift | **−0.044 ± 0.016 °/decade** | **+0.23** |

- Species did deepen on average, and did move slightly **equatorward**, both separably from zero.
- Splitting on it directly: species that deepened score +0.13 ± 0.13, those that shoaled −0.01 ±
  0.20. The difference of +0.14 is smaller than the intervals around it. **Depth does not
  discriminate.**
- Latitude correlates with the index roughly twice as strongly as depth does, and in the coherent
  direction: more poleward means holding temperature better.

That last point is not a contradiction of Phase 1b, it is what Phase 1b's null looks like from the
inside. The pooled latitude shift being ~0 never meant species did not move — it meant they moved in
both directions, and this says the ones that moved poleward are the ones that kept their water.

**Both correlations are weak** (+0.23 and +0.12 explain little variance), so the honest summary is
that neither axis explains much of who tracked and who did not, and depth explains less than
latitude. What was predicted was that depth would be the answer in a network with static latitudes.
It is not.

## Scope, which is narrower than the source

**This will be a US result.** Temperature coverage decides it: the usable surveys are NEUS (57 and
53 years), SCS (51 and 42), GMEX (42 twice), EBS (38), SEUS (31 × 3), GOA and AI — all North
American, most of them NOAA. Every European survey with a long record has bottom-temperature
coverage between 0% and 22%, and every Canadian survey has none.

That compounds the bias already published in `geographic-coverage.md` rather than relieving it, and
the finding must be reported as North American shelf seas, not as "fish".
