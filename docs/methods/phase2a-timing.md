# Phase 2a, second link — does warming explain the autumn advance?

**Status:** pre-registered 2026-07-30, before the temperature was fetched.

Phase 1a established that nocturnal autumn passage over the mid-latitude US advanced by
0.6–0.7 days per decade, and Phase 1c established it is not an artefact of the metric, the
screening or the mixture. What it has never established is **why**. That is this note.

## The test, which is attribution arithmetic rather than a regression coefficient

A regression of passage date on temperature across stations would be nearly meaningless: southern
stations are warmer *and* have different passage dates, so the coefficient would be a statement about
geography. Everything here is therefore **within station, year to year**.

Three quantities, and the test is whether the first two multiply to the third:

1. **Sensitivity `S`** — days of passage-date shift per °C of pre-season warmth, fitted within each
   station across years.
2. **Warming `W`** — °C per decade in that station's pre-season, from ERA5.
3. **Observed advance `A`** — days per decade, already measured in Phase 1a.

If the advance is thermally driven then **S × W ≈ A**. That product is the explained share, and it
is the honest halfway house to the DAMIP counterfactual `phase2a-design.md` reserves the causal claim
for: it says whether thermal forcing is *sufficient in magnitude*, not whether it is the cause.

Three ways it can come out, all of them informative:

- **S × W ≈ A.** The advance is consistent with thermal forcing in both sign and size.
- **S × W ≪ A.** Birds do respond to temperature, but nowhere near enough to produce the observed
  advance. Something else is doing most of the work, and the honest output is that this test has
  found the response function and *not* the explanation.
- **S ≈ 0.** No within-station thermal response at all, in which case the pre-season temperature is
  the wrong cue and the note says so.

## Definitions, fixed here

**Response.** Autumn q50 passage date, the same quantity Phase 1a and 1c use, at the same stations
and under the same coverage filters. Autumn only: spring has no trend to explain, and Phase 1c
showed what little signal it had was partly speed weighting.

**Pre-season window.** June and July mean 2 m air temperature. Chosen to sit *before* the August–
November passage window without touching it: a predictor overlapping the response would partly be
the response. Two months rather than one because a single month is noisier without being more
specific.

**Wind support.** The projection of the night wind onto the station's own mean autumn heading,
averaged over the passage window, from the NARR 925 hPa winds already in the lake. Entered as a
second predictor because a night's passage is largely wind support, so a year of favourable winds
could shift the date without any thermal signal — and if wind absorbs the apparent thermal effect,
that is worth knowing before attributing anything to warming.

**Model.** Per station: `passage_date ~ 1 + pre_season_temperature + wind_support + post_2012`.
The break term is the same dual-polarisation one every other phase carries. Coefficients are pooled
across stations afterwards, with the spread reported — a mean sensitivity with a wide spread means
stations disagree, which is a finding rather than noise, and the same shape Phase 1b and the thermal
link both produced.

**Where the claim lives.** 37–50°N, matching the surviving Phase 1a claim. Numbers for the other
bands are computed and shown, but the southern bands still carry the unexplained 2012 step and no
attribution is claimed there.

## Predictions

1. **`S` is negative** — a warmer June–July is followed by earlier autumn passage. A positive `S`
   would mean warmth *delays* autumn migration, which is also a coherent hypothesis (a longer
   breeding season, later departure) and would be reported as found rather than argued away.
2. **`W` is positive** — the pre-season warmed. If it did not, there is nothing to attribute to.
3. **`S × W` is smaller in magnitude than `A`.** Stated in advance because I expect the honest
   answer to be a partial explanation: autumn departure in nocturnal migrants is strongly
   photoperiod-cued, and a local June–July temperature is a crude stand-in for conditions across a
   whole flyway. Predicting a partial result in advance is what stops a partial result being
   presented as a success.

## Results, run 2026-07-30

Reproduce with `make phase2a-timing`. 143 stations with at least 15 usable autumns.

| band | n | S (d/°C) | W (°C/dec) | S × W | observed A |
| --- | --- | --- | --- | --- | --- |
| 24–32°N | 23 | −0.271 ± 0.69 | +0.397 ± 0.06 | −0.144 ± 0.24 | **+0.213 ± 0.94** |
| 32–37°N | 42 | −0.516 ± 0.29 | +0.461 ± 0.07 | −0.152 ± 0.16 | −0.637 ± 0.47 |
| 37–42°N | 43 | −0.792 ± 0.24 | +0.527 ± 0.06 | −0.359 ± 0.14 | −0.463 ± 0.31 |
| 42–50°N | 35 | −0.495 ± 0.21 | +0.506 ± 0.08 | −0.229 ± 0.10 | −0.677 ± 0.41 |
| **37–50°N** | **78** | **−0.659 ± 0.165** | **+0.518 ± 0.047** | **−0.301 ± 0.090** | **−0.559 ± 0.249** |

**All three predictions held.**

1. **`S` is negative and separable from zero.** A June–July that is 1 °C warmer is followed by autumn
   passage **0.66 ± 0.17 days earlier**. Every band is negative, and the sign was predicted.
2. **`W` is positive.** The pre-season warmed by **+0.52 ± 0.05 °C per decade** in the claim band,
   and by +0.40 to +0.53 everywhere. There is something to attribute to.
3. **`S × W` is smaller than `A`.** The response function predicts −0.30 ± 0.09 days per decade
   against an observed −0.56 ± 0.25 — **54% of the advance**.

**The wind did not do it, and it did not hide the temperature either.** The wind-support coefficient
is −0.243 ± 0.385 days per m s⁻¹, indistinguishable from zero, and the two predictors are essentially
uncorrelated within station: **+0.025 ± 0.048**. Confound 1 resolves cleanly — the thermal coefficient
is not absorbing the wind's work, and the split between them is identifiable rather than a coin toss.
That is a better outcome than the note anticipated.

### What "54%" does and does not license

**The intervals overlap.** Explained spans [−0.39, −0.21] and observed spans [−0.81, −0.31], which
share [−0.39, −0.31]. So the honest reading is *about half, and not statistically distinguishable
from more*: this rules out warming being a negligible part of the advance, and it does not rule out
warming accounting for most of it. A point estimate of 54% should not be quoted as though the
remaining 46% were established to exist.

What can be said firmly is the direction and the order of magnitude: the response is real, it is in
the right direction, and it is the right size to matter. Prediction 3 was written to expect a partial
explanation because autumn departure in nocturnal migrants is strongly photoperiod-cued and a local
June–July temperature is a crude stand-in for a whole flyway. That expectation is consistent with
what came out, which is the most that can be claimed from a consistency check.

### The southern band behaves differently, again

24–32°N is the one band where the arithmetic inverts: the response function predicts an advance
(−0.144) while the observed change is a **delay** (+0.213), on an interval of ±0.94 that contains
almost anything. This is the same band that carries the unexplained 2012 step through Phase 1a, 1c
Test B and Test D, and it misbehaves here too. No attribution is claimed for it, consistent with the
scope fixed in advance.

The best-matched band is 37–42°N: the strongest sensitivity (−0.792) and 78% of its observed advance
explained.

## Confounds

1. **Temperature and wind are correlated.** Warm years are not meteorologically independent of windy
   ones. Both go in the same model so neither is credited with the other's work, and the
   correlation between them is reported so a reader can see how identifiable the split is. Where
   they are collinear beyond separating, that is the answer — `phase2a-design.md` commits to
   reporting unidentifiability rather than picking a winner.
2. **A local temperature is not a flyway temperature.** These birds pass a station; they did not
   breed there. June–July at the radar is a proxy for the conditions upstream, and a poor one for
   the northernmost migrants whose breeding grounds are thousands of kilometres away. This bounds
   how much `S` can ever explain and is a reason to expect prediction 3 to hold.
3. **ERA5 is a reanalysis whose observing system changed.** Same caveat as `adr/0006` records for
   NARR. It bites less here than for a trend, because `S` is fitted on year-to-year *variation*
   rather than on the long-term slope, but `W` is a long-term slope and is exposed to it.
4. **The station panel changes.** Reporting stations rise from 104 in 1995 to 159 by 2017, so a
   pooled `S` computed over an unbalanced panel would weight late-joining stations differently.
   Sensitivities are fitted per station and only then pooled, which is the same discipline Phase 1a
   used for its trends.
