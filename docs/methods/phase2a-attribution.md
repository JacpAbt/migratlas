# Phase 2a, the causal step — how much of the advance is human?

**Status:** pre-registered 2026-07-30, before any model data was read. Availability was checked
first (15 models carry both experiments), because a counterfactual from one model is not a claim.

`phase2a-timing.md` established a response function: autumn passage is 0.66 ± 0.17 days earlier per
°C of June–July warmth, the pre-season warmed 0.52 ± 0.05 °C per decade, and the product accounts
for about half the observed advance. What it deliberately did not do is say the warming was
*caused* by anything. That is this note, and it is the step `phase2a-design.md` reserves the causal
claim for.

## The design: models supply a fraction, observations supply the magnitude

CMIP6 DAMIP runs the same models twice — `historical` with all forcings, and **`hist-nat` with only
solar and volcanic forcing, human influence removed**. The difference between them is the modelled
human contribution, and it is the only way to ask a counterfactual question of a single realised
climate.

The naive approach — take the modelled warming difference and multiply by the sensitivity — inherits
every model's bias in absolute trend. So instead:

1. **From the models, a ratio.** `f = (W_hist − W_nat) / W_hist`, the share of the modelled June–July
   warming attributable to human forcing, over the window both experiments cover.
2. **From observations, the magnitude.** `W_obs` from ERA5 at the radar stations, already measured
   at +0.518 ± 0.047 °C per decade.
3. **From the radar, the translation.** `S = −0.659 ± 0.165` days per °C, from
   `phase2a-timing.md`.

Then the **anthropogenic advance** is `S × f × W_obs`, to be read against the observed
`A = −0.559 ± 0.249` days per decade.

A ratio transfers across windows and survives a model running warm or cold in absolute terms, which
an absolute difference does not. That is the whole reason for the indirection, and it is this note's
version of the plan's "bias-adjusted".

## The window problem, and why it is not swept aside

**CMIP6 `historical` ends in 2014.** The observed advance is 1995–2025. So the modelled fraction is
computed over **1995–2014** and applied to an observed warming measured over 1995–2025. That is a
real mismatch, and the ratio construction is what makes it tolerable rather than fatal: `f` is a
statement about the *composition* of the forcing, which changes slowly, not about a rate.

It is still an assumption, and it is stated rather than hidden: **the anthropogenic share of
pre-season warming over 1995–2014 is taken as representative of 1995–2025.** Given that greenhouse
forcing grew over the later period while volcanic forcing was quiet, if anything this understates
the human share, so the direction of the error is known.

## The Pinatubo trap, named in advance

**1995 is a bad start year for a natural-forcing counterfactual.** Pinatubo erupted in 1991 and
cooled the early 1990s; a `hist-nat` run beginning in 1995 is recovering from that cooling, so it
can show a *positive* warming trend from volcanic recovery with no human forcing at all. That would
inflate `W_nat`, shrink `f`, and understate the human contribution.

So the window sensitivity is part of the test rather than an afterthought: `f` is computed over
1995–2014 and again over 1980–2014, and both are reported. If they disagree materially, the
Pinatubo recovery is doing the work and the later-starting number is the biased one.

## Ensemble handling, fixed here

- **Average members within a model first, then across models.** MIROC6 and CanESM5 each contribute
  50 `hist-nat` members while nine models contribute three or fewer; pooling members directly would
  make the answer a statement about two models.
- **A model is used only if it has both experiments.** All 15 do.
- **The spread across models is reported, not just the mean.** A tight ensemble and a scattered one
  licence different confidence, and collapsing to a single number hides which we have.
- **Sampled at the radar stations**, June–July, so the fraction is local to where the birds were
  counted rather than global. Models are 1–2° so this is regional rather than truly local, and is
  described that way.

## Predictions

1. **`W_hist` is positive** and broadly resembles the observed +0.52 °C/decade. This is a
   validation rather than a finding: if the ensemble cannot reproduce the observed pre-season
   warming, the counterfactual built on it is not trustworthy and that will be said.
2. **`W_nat` is near zero**, possibly slightly positive from Pinatubo recovery in the shorter window.
3. **`f` is large — above 0.8.** Human dominance of recent warming is among the best-established
   results in the field, so a small `f` here would be evidence of a bug in my extraction, not a
   discovery. Saying so in advance is what makes it a check.
4. **`S × f × W_obs` remains smaller in magnitude than `A`,** for the same reason
   `phase2a-timing.md` predicted: photoperiod is a large part of autumn departure and a local
   temperature is a crude flyway proxy. The causal step sharpens *what* the thermal part is due to;
   it does not enlarge the thermal part.

## What this can and cannot conclude

**Can:** that the pre-season warming the birds responded to is attributable in a stated proportion
to human forcing, and therefore that a stated share of the observed advance is consistent with an
anthropogenic cause.

**Cannot:** that the *whole* advance is anthropogenic, since only about half of it tracks temperature
at all. Nor that temperature is the mechanism rather than a correlate of one — the response function
is observational and a confounder common to both would survive this. Nor anything about the southern
bands, whose 2012 step is still unexplained and which are excluded here as they are everywhere else.

The claim this note is allowed to make is narrow and worth stating precisely: *of the portion of the
autumn advance that tracks pre-season temperature, this share is attributable to human forcing.*

## Results, run 2026-07-30

Reproduce with `make ingest-cmip6 && make phase2a-attribution`. All 15 models that carry both
experiments landed, 3 members each where 3 exist (GFDL-CM4 publishes 1 `historical` member), for
1,288,760 driver rows sampled at the 143 radar stations and read on the 78 inside the claim band.

| window | models | `W_hist` °C/dec | `W_nat` °C/dec | `f` |
| --- | --- | --- | --- | --- |
| **1995–2014** | 15 | **+0.586 ± 0.090** | **+0.010 ± 0.090** | **0.98** |
| 1980–2014 | 15 | +0.517 ± 0.077 | +0.060 ± 0.038 | 0.88 |

The ± is the **spread across models**, not the uncertainty of any one trend — it says how much the
modelling centres disagree, which is what a single-model answer would hide.

**All four predictions held.**

1. **`W_hist` reproduces the observed warming.** +0.586 modelled against +0.518 observed, a ratio of
   1.13. The ensemble is warm by 13%, which is close enough to license using it for a ratio.
2. **`W_nat` is near zero:** +0.010 ± 0.090 °C/decade, indistinguishable from zero.
3. **`f` is above 0.8:** 0.98. This was written down in advance as a check on the extraction rather
   than a discovery, and that is how it should be read.
4. **The human share is smaller in magnitude than the observed advance:** 0.296 against 0.559 days
   per decade.

### The attribution

| term | value | source |
| --- | --- | --- |
| `S` | −0.659 days per °C | radar, 78 stations |
| `W_obs` | +0.518 °C per decade | ERA5 at those stations |
| `S × W` | −0.301 days per decade | per station, then averaged (`phase2a-timing.md`) |
| `f` | 0.98 | 15 CMIP6 models, `historical` against `hist-nat` |
| **`f × S × W`** | **−0.296 days per decade** | **the human share** |
| observed `A` | −0.559 days per decade | radar |

**53% of the observed autumn advance is attributable to human forcing** — or more precisely, *the
part of the advance that tracks pre-season temperature is essentially all anthropogenic, and that
part is about half of the whole.* Under the other window it is 48%, so the window choice moves the
answer by five points, which is far less than the ±0.25 day interval on `A` already allows.

Every caveat `phase2a-timing.md` carries transfers intact: the intervals on explained and observed
overlap, so "about half" is not distinguishable from more. What this note adds is that the half which
*is* thermal is not natural variability.

### The window prediction was backwards, and the data say so

The note above predicted that a window starting in 1995 would be the contaminated one, because a
`hist-nat` run beginning four years after Pinatubo is still recovering from volcanic cooling. **That
reasoning is wrong, and in the direction that matters.** A window starting in 1980 sits *before* both
El Chichón (1982) and Pinatubo (1991), so both cooling episodes fall in its first half and tilt a
fitted line upwards; by 1995 most of Pinatubo's cooling had already decayed. The measurement agrees:
`W_nat` is +0.060 °C/decade over 1980–2014 against +0.010 over 1995–2014, so it is the **longer**
window that carries the volcanic recovery.

The two fractions differ by 0.10, which is exactly at the pre-registered threshold and counts as
agreement, so the rule never fired and the primary window is the first one listed. Both are reported
regardless. Getting the mechanism backwards cost nothing here because the test was specified as
"compute both and compare" rather than "assume which is biased" — which is the argument for writing
the comparison into the method rather than the reasoning.

### Nine of fifteen counterfactuals *cool*

Over 1995–2014, nine models give `f > 1`, up to 1.49. That is not a bug: without greenhouse gases,
volcanic and aerosol forcing alone produce a *negative* trend, so human forcing accounts for more
than all of the modelled warming. The per-model spread is 0.49 to 1.49, wide enough that no single
model should be quoted — which is why the headline ratio is taken on the ensemble means, where the
denominator cannot vanish, and why models whose own warming is below 0.05 °C/decade are excluded from
the per-model spread and counted.

### Synthetic null, added after the fact

Not pre-registered, and said so plainly. One `hist-nat` member per model is relabelled `historical`
and the rest keep their label, so there is no forced difference and the same machinery should find
nothing.

- forced difference `W_hist − W_nat`: **+0.576** °C/decade
- null difference: **−0.018** °C/decade
- the null is **3%** of the forced difference — **pass**, against a 20% ceiling

**The first version of this control was malformed.** It compared the null's *fraction* against zero
and reported +8.67, which read as the method being broken. It was not: under the null the denominator
is a near-zero warming by construction, so the ratio explodes for a reason that says nothing about
the method — the same pathology `MIN_RATIO_WARMING` exists to keep out of the per-model spread. The
numerator carries the information, so the control is now read as a difference. Recorded here because
a control that can be misread this easily is worth a warning next to it.

### Two failures worth recording

**Nine of fifteen models were silently dropped on the first run.** `xarray` refuses to decode a
non-standard calendar without `cftime`, and `cftime` was not a declared dependency. The ingest logs
an unreadable store and carries on, which is right — one bad member must not cost the other
eighty-seven — but that tolerance meant a third of the ensemble vanished along a line drawn by which
modelling centre chose which calendar, and the only symptom was a six-model ensemble that looked
entirely reasonable. It was caught because the row count came back byte-identical to the previous
run. Two fixes: `cftime` is now declared, and `phase2a_attribution.shortfall` compares the models in
the lake against the models the catalogue offers and prints a refusal banner where the claim is made.

**HadGEM3-GC31-LL was dropped even with `cftime`.** Its calendar is 360-day, where every month has
thirty days, so the slice bound `2014-12-31` raises rather than clamping. The slice now uses
year-only bounds, which every CMIP6 calendar accepts, and `tests/test_attribution.py` opens a real
360-day zarr store to hold that.

### What this licenses

The claim is narrow and worth stating precisely: **of the portion of the autumn advance that tracks
pre-season temperature, essentially all is attributable to human forcing.** Not that the whole
advance is — about half of it does not track temperature at all and remains unexplained. Not that
temperature is the mechanism rather than a correlate of one, since the response function is
observational and a confounder common to both would survive this. And nothing about the southern
bands, whose 2012 step is still unexplained and which are excluded here as everywhere else.
