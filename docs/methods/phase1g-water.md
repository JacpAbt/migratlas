# Phase 1g — did the cells that lost water lose birds?

**Status:** pre-registered 2026-08-05, **before the download**. No JRC tile has been fetched, no
water value has been joined to an atlas cell, and no correlation of any kind has been computed. What
was already known is in §1, and it is a lot: this note is written on top of a published per-cell
change surface, so it cannot claim to be innocent of the response variable.

## Why this note exists

`atlas-no-net-change` describes and does not explain, and says so. [Phase 1f](phase1f-atlas-surface.md)
found real spatial structure in the per-cell change — Moran's I +0.227, p 0.001 — and the arid west
was the only quarter that gained. Something is organising that map and nothing in this project has
tried to say what.

`DATASETS.md` step 3 named the first attempt in advance: **surface-water change, as attribution
only.** The reasons it is first are that southern Africa is arid, that JRC Global Surface Water runs
1984–2021 and so straddles both atlas epochs almost exactly, and that its `change` layer says
directly which water was lost. It also carries a hard limit the same document states: **no future
surface water exists, so this factor can never enter a forecast.** It is explanatory or it is
nothing.

## 0. Step zero, and the stop condition attached to it

Before any analysis: **confirm the licence and register the source.** `DATASETS.md` recorded JRC GSW
as "confirmed open, no account" on 2026-07-30 from a HEAD request, which is availability and not
terms. The registry is the only door, `redistribution_allowed` is read from it, and this note does
not assume what that entry will say.

**Stop condition.** If the licence does not permit redistribution of a derived product, the factor
may still be used for analysis — the eBird precedent — but no water layer is drawn and the finding
carries the restriction. If it does not permit analysis either, this note ends here and is published
as a dead end.

## 1. What was already known when this was written

The whole of Phase 1f, which is published: 496 cells, the per-cell change in recorded analysed taxa,
its spatial structure, its near-zero correlation with effort (ρ −0.199, and negative), and the
east–west contrast — median −6.84 east of 28°E against +1.70 west of 22°E under the corrected
surface.

**That last figure is why this note is dangerous and why the nulls below are the whole design.** A
water effect is exactly what an arid west gaining and a mesic east losing would look like, which
means the shape of the answer was visible before the question was asked. Anyone can find a story that
fits one contrast. What has *not* been looked at: any water datum, at any resolution, anywhere.

## 2. The estimand

Per quarter-degree cell *c* in the Phase 1f footprint:

**ΔR_c**, the published change in recorded analysed taxa, regressed on **ΔW_c**, the change in
permanent surface water area within the cell between the two atlas epochs, conditioned on **ΔE_c**,
the change in atlas cards.

The response is the **uncorrected** count — the one that is drawn — and not the detection-corrected
surface. Phase 1f §5 sent the uncorrected one to the map because the two disagreed; using the
corrected one here would build a model on a surface this project has already declined to publish.
The corrected surface is a registered robustness check, not the primary.

**The unit is the cell and not the species.** Surface water is a property of a place. Assigning a
cell's water change to each of its species and fitting per species would multiply 496 observations
into 254,000 and call the extra ones evidence.

## 3. Predictions, registered now

Stated as directions and standardised effects, **not as absolute counts.** Phase 1f's two failed
predictions both failed because a per-unit threshold was applied to a sum over 512 units; the lesson
is recorded there and applied here.

1. **Cells that lost permanent water lost more analysed taxa**, conditioned on the change in cards:
   the coefficient on ΔW_c is positive, i.e. losing water goes with losing taxa.
2. **It survives a spatially-restricted null** at p < 0.05. See §4 — this is the prediction that
   distinguishes a result from an inevitability.
3. **It is not one region.** Leave-one-out over four quadrants of the footprint keeps the sign in all
   four.
4. **The placebo is null.** In cells with essentially no water at baseline there is no water to lose,
   so a fitted effect there is the model reading something else. The coefficient in that subset is
   not distinguishable from zero.

## 4. The null, which is the methodological point

**An ordinary p-value here would be meaningless and it would look fine.** ΔR is spatially
autocorrelated at Moran's I +0.227. Surface water change is strongly spatially autocorrelated —
rivers and catchments are contiguous by construction. Two spatially structured surfaces correlate far
more often than independent sampling implies, and the usual test assumes independent sampling. This is
the single commonest way a landscape-factor result is wrong.

So significance is assessed against a null that **preserves the spatial structure of the factor and
destroys only its alignment with the response**: toroidal shifts of the water surface over the
footprint, plus Moran spectral randomisation as a second null with different failure modes. Both are
reported. An i.i.d. permutation is computed as well and published *beside* them, explicitly labelled
as the wrong test, because the gap between the naive p-value and the spatial one is worth showing —
the same instinct that publishes the corrected number beside the uncorrected one.

## 5. Stop conditions

- **Prediction 2 fails.** The effect is published as a null and the factor is dropped, exactly as
  ENRAM was. `DATASETS.md` step 3 pre-commits to this and it is not renegotiated here.
- **The effect vanishes when conditioned on ΔE_c.** It was effort. Nothing is published but the fact.
- **The placebo fires.** If cells with no baseline water show the same effect, the model is fitting
  something the water layer merely correlates with; the analysis is withdrawn rather than caveated.
- **Leave-one-out flips the sign.** One region is carrying it; reported as a regional observation and
  never as a footprint-wide effect.
- **Fewer than 100 cells carry any measurable baseline water.** The comparison has no contrast and
  the factor is untestable on this footprint.

## 6. What this cannot establish

- **Not cause.** Water loss and bird loss can both follow from a third thing — a drying trend, a
  land-use change, a catchment developed for irrigation. This is an association between two maps.
- **Not a forecast, ever.** No future surface water exists. Stated in `DATASETS.md` and repeated here
  because a fitted coefficient is the exact thing someone would later be tempted to project.
- **Not richness.** The response counts the taxa the occupancy comparison could fit, and those are
  the already-widespread ones — the birds least likely to be the first to leave a drying pan.
- **Not the mechanism.** Even a real effect does not say whether the birds needed the water, needed
  what lived in it, or needed the vegetation it supported.
- **27 km cells and two epochs.** A cell can lose a pan and gain a reservoir and read as unchanged.

## 7. Where the result goes

- A seventh `Finding` if the effect survives, or a published null if it does not. Both are results.
- A registry entry for the JRC source, generated into `PROVENANCE.md` like every other.
- A response curve per factor, drawable, if and only if §5 lets one be drawn.
- Results appended here with every prediction graded, whichever way it goes.

---

# Step zero — run 2026-08-05, before the download

## The licence permits it, so the stop condition does not fire

JRC Global Surface Water is published under the Copernicus Programme, **"free of charge, without
restriction of use"**, requiring attribution as *Source: EC JRC/Google* and citation of Pekel et al.,
*Nature* **540**, 418–422 (2016), doi:10.1038/nature20584. No licence *name* is given — there is no
"CC BY 4.0" on the page — and no restriction on redistribution or commercial use beyond attribution.

So a derived layer may be drawn as well as analysed, and the registry entry will carry
`redistribution.allowed: true` with `attribution_required: true`. §0's stop condition is resolved.

## Correction to §2, found before a byte was fetched

§2 said the `change` layer "says directly which water was lost between the two epochs". **It does
not, and this is the reason step zero exists.** The layer compares *JRC's* two epochs, and they are
not the atlas's:

| | first period | second period |
| --- | --- | --- |
| JRC occurrence-change intensity | 1984–1999 | 2000–2015 |
| SABAP, as Phase 1e registered it | 1987–1991 | 2008–2012 |

Each JRC period *contains* the matching atlas window and is roughly three times longer. Taking the
shelf product would mean regressing an atlas change measured over two five-year windows on a water
change measured over two fifteen-year ones — overlapping, not aligned, and blurred at both ends. The
mismatch would be invisible in the output and would attenuate any real effect toward zero, which is
the worst direction for it to fail in, because attenuation looks like an honest null.

**So ΔW is built from the Yearly History layer over the atlas windows themselves**, which is what §2
should have said. Yearly History classifies each cell-year as no water, seasonal or permanent, back
to Landsat 5 in March 1984, so 1987–1991 and 2008–2012 are both fully inside it. Registered now,
before any tile is read.

## A limitation this creates, registered rather than discovered later

Yearly History as documented in the FAQ ends in **October 2015**. Phase 1e's registered alternative
epoch-2 window is **2019–2023**. So the water factor can be fitted against the primary window only,
and the sensitivity that licensed every species-level number in Phase 1e **cannot be repeated here**.
Any result from this note is conditional on one choice of epoch 2 in a way the atlas comparison is
not, and must say so.

## An unresolved discrepancy, recorded rather than assumed away

The two JRC pages disagree about the temporal span. The download page describes the primary dataset
as 1984–2024 and says seasonality, monthly and yearly assets cover 2022–2024 only with earlier years
requiring a merge against version 1.4; the FAQ describes yearly history as March 1984 to October
2015. `DATASETS.md` recorded 1984–2021 on 30 July. Three sources, three answers, so the version is
not established from documentation.

**Stop condition.** The epoch definition is read off the downloaded asset's own metadata at ingest
and recorded in the registry entry. If the years covered cannot be established from the data itself,
nothing is fitted — a factor whose own time span is uncertain cannot be aligned with an atlas window,
and guessing which version arrived would put the mismatch corrected above straight back in.

## Step zero, part two: the corrected plan was not executable either

The correction above said ΔW would be built from Yearly History over the atlas windows. **It cannot
be. The per-year classifications are not downloadable for any year the atlas epochs need.**

Enumerated from the bucket rather than inferred from a page, across all seven download roots:

| downloadable per-year classifications | 2015, 2016, 2017, 2018, 2019, 2020, 2021 |
| --- | --- |
| the atlas epochs need | 1987–1991 and 2008–2012 |
| **overlap** | **none** |

Per-year water before 2015 exists only as an Earth Engine image collection. That needs a Google
account and a cloud project, which is an account this project does not have and credentials it will
not handle for a factor. The tiled products — `occurrence`, `change`, `seasonality`, `recurrence`,
`transitions`, `extent` — are all whole-period summaries.

### What is used instead, and the honest cost

`change`, the occurrence change intensity, comparing 1984–1999 with 2000–2015. The atlas windows sit
*inside* those periods — 1987–1991 within the first, 2008–2012 within the second — so the ordering is
right and the two are correctly assigned. The instrument is coarser than the question, not aimed
somewhere else.

**What that costs is stated now, before any number exists: this instrument attenuates.** Averaging
water over fifteen years when the atlas sampled five blurs both ends, and blurring pulls a real
coefficient toward zero. It cannot manufacture an effect; it can only hide one.

### Stop condition 1 is amended, and this is a correction rather than an edit

As registered, a null dropped the factor and was published as a null. That is no longer the right
reading. **A null now means "not detectable with the only instrument available", not "no
association"** — and the finding must use those words. An attenuating instrument judged by a
null-drops-it rule can only fail in the uninformative direction, and reporting that failure as
evidence of absence would be the exact error this project exists not to make.

An effect that *survives* an attenuating instrument is, if anything, stronger evidence than the
registered design would have produced. The asymmetry is real and it is why the amendment weakens only
the negative branch.

Amended before the download, with nothing computed, because it is forced by an availability fact and
not by a result. The original text stands above it.

### The placebo gets a better definition than it was given

§3 prediction 4 wanted cells with "essentially no water at baseline". `occurrence` gives something
stricter and cleaner: cells with no water detected in the *entire* 1984–2021 record. A cell that
never held water certainly held none at baseline, so the placebo subset is unambiguous and does not
depend on an epoch this data cannot resolve.

### What is being fetched

Five 10° tiles, the footprint being 17.9–32.9°E and 22.1–34.6°S: `10E_30S`, `20E_20S`, `20E_30S`,
`30E_20S`, `30E_30S`. Two layers, `change` and `occurrence`, v1.4 2021. **185 MB in ten files.**
