# Phase 1i — does a climate response measured in one hemisphere carry to another?

**Status:** pre-registered 2026-08-07, before any sensitivity has been computed in any realm. What
*was* measured first is in §1 and it is substantial: the southern temperature field was fetched and
the power of the southern leg was calculated before this note was written, because a design that
cannot detect the thing it is looking for should be abandoned before it is designed rather than
after it is run.

## Why this note exists

`coverage-bias` has published a promise since the day it landed: *no model trained on this should be
trusted elsewhere without being tested there first.* Every range-shift projection in the literature
assumes climate responses transfer between regions and realms. Almost nobody tests it, because
almost nobody has three responses measured under one audit. This project now does.

It is also the last item on `DATASETS.md`'s list that was ever described as the novelty claim.

## 1. What was measured before this was written

**The southern temperature field**, because the leg could not be designed without knowing whether it
was possible. `era5_south`: monthly 2 m temperature at the 496 cells of the SABAP common footprint,
1987–1991 and 2008–2012, 59,520 rows. Fetching a *covariate* is not fetching the answer — the
relationship between temperature and birds is untouched — but it is more than nothing and it is
declared here.

| | |
| --- | --- |
| annual mean temperature, 1987–1991 | 9.4 – 24.1 °C |
| warming, epoch 1 → epoch 2 | **+0.311 °C** (461 of 496 cells warmed) |
| sd of cell temperature across the footprint | 2.74 °C |
| planar spatial gradient | 3.675 °C / 1000 km |
| **R² of that planar fit** | **0.220** |

**And the power of the southern leg**, from the occupied-cell counts Phase 1e already publishes:

| | |
| --- | --- |
| occupied cells per species | median 168, quartiles 93–292 |
| CTI standard error per species (sd/√n) | median **0.211 °C** |
| signal separating full tracking from none | **0.311 °C** |
| species individually well powered (SE < half the signal) | **126 of 560 — 22%** |
| SE of the *mean* shift across 560 species | **0.0107 °C, 29× the signal** |

Two findings from that table govern everything below.

**The response must be measured in temperature, not in distance.** An R² of 0.220 means four fifths
of the spatial temperature variance is not a north–south gradient — it is the escarpment and the
Lesotho highlands. A tracking measure expressed as kilometres poleward would largely be measuring
the planar approximation, and in this region a bird can track its thermal niche by going uphill.

**The southern claim can be about the community and cannot be about a bird.** Individually the
median species' standard error is two thirds of the entire signal. Collectively the aggregate is
powered twenty-nine fold. So no per-species southern number is published from this note, at all.

What was **not** looked at: any relationship between temperature and any response, in any realm; any
sensitivity; any species' thermal envelope.

## 2. The estimand

For each realm, the **thermal tracking ratio** — the fraction of the local warming that the animals
followed.

```
tracking  =  observed shift in the animals' thermal position
             ------------------------------------------------
             shift the local warming would require to be fully tracked
```

One is perfect tracking. Zero is no response at all. Negative is movement against the warming. It is
dimensionless *physically* rather than statistically, which is the whole reason for choosing it.

**Rejected: standardising each realm by its own standard deviation.** That also yields shared units,
and they would be meaningless — a standard deviation is a property of how variable that particular
record happens to be, so two systems with identical biology and different measurement noise would
report different sensitivities. Shared units are not shared meaning.

Per realm:

- **Marine, north.** Observed latitudinal shift per species×region from Phase 1b, over the shift of
  the same survey's own measured isotherm. FISHGLOB carries sea temperature at the haul, so both
  numerator and denominator come from one instrument.
- **Terrestrial, south.** The community temperature index: the mean temperature of the cells a
  species occupies, in each epoch, against the footprint's own +0.311 °C. A species that tracked
  perfectly keeps its CTI while the region warms.
- **Aerial, north.** Passage date against the date the local temperature threshold moved. **This leg
  is conditional** — see §5.

## 3. The unit, and why a distribution rather than a number

Each realm yields *many* sensitivities, not one: 2,240 species×region pairs in the marine record,
560 species in the south, and one per radar station in the aerial one. That matters, because with
three pooled numbers "fit on two, predict the third" is arithmetic — the mean of two values against a
third, with no degrees of freedom and no error that means anything.

**So the transfer test predicts a distribution from two distributions**, and is scored on where the
third actually falls: its centre, its spread, and the share of the observed distribution the
prediction's interval covers.

## 4. Predictions, registered now

1. **The realms disagree.** The three tracking distributions do not share a common centre — a
   Kruskal–Wallis test across them rejects at p < 0.05. If they agree, transfer is supported and
   `coverage-bias`'s warning is weaker than it claims.
2. **Prediction error exceeds within-realm spread.** Fitting on two realms and predicting the third,
   the absolute error in the centre is larger than the standard error of the held-out realm's own
   mean. This is the quantitative form of "it does not transfer", and it is run three ways, holding
   each realm out in turn.
3. **The southern community tracks less than the northern ones.** Directional, and registered
   because it is the literature's expectation for a climatic debt rather than mine. If it fails, that
   is a result and not a bug.
4. **Held-out marine predicts worst.** The marine record already disagrees with itself in direction
   — that is `marine-null` — so a prediction made from aerial and terrestrial should fit it least
   well. A design that predicted the noisiest realm best would be suspect.

## 5. Stop conditions

- **The aerial conversion dominates.** Turning a date shift into a fraction-of-warming needs the
  local seasonal temperature slope in °C per day. If the tracking ratio moves by more than 0.2
  across reasonable choices of that slope, the aerial leg is withdrawn and this becomes a two-realm
  test between marine-north and terrestrial-south — both spatial, no conversion, still crossing the
  equator and the realm. **The two-realm version is the fallback, not a failure.**
- **Any realm's tracking distribution has a median outside −1 to 2.** That is not a sensitivity, it
  is a broken denominator, and it stops that leg.
- **Fewer than three realms survive.** With two, the test is a comparison rather than a prediction,
  and §3's language changes accordingly: no "fit and predict", just the two distributions and their
  distance.
- **The southern CTI shift is inseparable from the footprint rule.** If cells that entered the
  footprint are warmer or cooler than those that did not, the CTI moves for a reason that is about
  atlassing. Checked before the ratio is computed, and it stops the southern leg.

## 6. What this cannot establish

- **Three realms is three points.** Even with distributions behind each, the transfer is being
  tested across three cases, and three cases cannot separate "realm" from "hemisphere" from
  "instrument" from "the particular decade each record covers".
- **Not causal, in any realm.** These are associations between a temperature field and an animal
  record, in three places where a great many other things also differ.
- **Not a licence to project.** A tracking ratio that transferred would say the *responses* are
  similar, not that a model fitted in one place may be run in another.
- **The southern leg is two snapshots** with nineteen unobserved years between them, and no wind, no
  counterfactual and no land-use covariate anywhere near it.
- **Nothing about individual animals**, in the south by construction — see §1.

## 7. Where the result goes

- A `Finding` either way, realm `all`, because a transfer that holds and a transfer that fails are
  equally publishable and the promise in `coverage-bias` is discharged by either.
- The three distributions drawn together, since the shape is the argument.
- Results appended here with every prediction graded, and the two-realm fallback recorded as taken
  or not taken.

---

## Amendment, 2026-08-07: which surveys the marine leg may use

Made during execution, after computing the temperature gradients and before dividing anything by
them. §5 registered a stop condition on the tracking *distribution's* median and said nothing about
whether an individual survey is admissible, which turned out to be the question that mattered.

**Both rules use the temperature field and the survey's geometry only.** No fish enter either, which
is what keeps this an amendment rather than a result chosen to suit itself — the same position the
Phase 1g placebo took when its subset had to be defined.

**First, the denominator is the full spatial gradient, not the latitudinal one.** Dividing by
`dT/dlat` alone assumes isotherms travel due north, and on a continental shelf the thermal gradient
is frequently cross-shelf. It is also numerically vicious: BITS-1 has a latitudinal gradient of
0.037 °C per degree and returned an isotherm velocity of −44 °latitude per decade. Climate velocity
is properly the warming rate over the magnitude of the spatial gradient, and that is what is used.

**Rule one: the gradient must be predominantly latitudinal.** The numerator is a latitudinal
displacement — Phase 1b measures no other kind — so the test only applies where poleward and cooler
coincide. Surveys where latitude carries less than half the gradient are out: `SP-PORC`, whose
gradient is 96% longitudinal, `BITS-4` and `NS-IBTS-1`. Across the 18 candidate surveys the
latitudinal share has median 0.88, so this excludes the tail rather than the bulk.

**Rule two: the isotherm must not cross the survey within a decade.** `BITS-1` again — 8.6 °latitude
per decade against a survey 3 ° tall. A survey its own isotherms leave inside the study period cannot
observe tracking inside it, whatever the fish do. Expressed against each survey's own extent rather
than a constant, so there is no threshold to have chosen.

14 of 18 surveys survive both, and 12 of those carry species that clear Phase 1b's own floors.

## Marine result — 2026-08-07

**1,426 species×survey pairs over 12 surveys.**

| | |
| --- | --- |
| median tracking | **−0.025** |
| quartiles | −0.368 to +0.587 |
| deciles | −1.942 to +2.625 |
| tracking at all (> 0) | **47.4%** |
| between 0 and 1 | 29.0% |

**This is `marine-null` restated in tracking units.** The median is indistinguishable from zero and
the share moving with their isotherm at all is 47.4%, which is a coin flip. Prediction 4 said the
marine realm should be predicted worst precisely because it disagrees with itself, and this is that
disagreement measured on a common scale rather than asserted.

The deciles are the honest caveat: a substantial minority of pairs sit outside −1 to 2, moving
several times faster than their isotherm or hard against it. A ratio inherits the noise of both its
parts, and a species whose own shift is poorly determined will produce a wild one. Every summary of
this distribution is therefore a median, never a mean.
