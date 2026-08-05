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
