# Phase 1f — can the atlas comparison be drawn per cell without drawing effort instead?

**Status:** pre-registered 2026-08-05. Written before any per-cell quantity has been computed from
both epochs, before any cell has been looked at individually, and before anything has been drawn.
What *was* already known when this was written is set out in §1 — the species-level results of
[Phase 1e](phase1e-atlas.md) are published, so this note cannot claim innocence about them, and
pretending otherwise would make the pre-registration worthless.

## Why this note exists

`atlas-no-net-change` is the only finding on the site whose claim has a camera position and no
layer. Selecting it flies the globe to southern Africa and draws nothing, which is worse than
drawing nothing at all: the reader is pointed at a place and shown an empty map, and the honest
reading of an empty map is "there is nothing here".

Phase 1e §10 named three destinations for its result — a `Finding`, the species pages, and a
recomputed `coverage-bias`. All three shipped. **A map layer was not among them.** §5 does derive
the per-cell quantity a map would need, and `models/occupancy.py::occupied_given_silence` implements
it, but no note ever registered what would be drawn with it, on which cells, or what would stop it
being drawn. That is what this note is for, and it is a separate question from Phase 1e because a
per-cell number can fail in a way a per-species number cannot: **it can draw where people went.**

## 1. What was already known when this was written

Everything in the results section of `phase1e-atlas.md`, which is published. Specifically: 512
reportable species, 496 shared cells, median Δψ −0.007, the corrected and naive answers agreeing to
0.002 at the median, detection correlating 0.84 across the gap, and the 2019-2023 sensitivity
passing at 14.4% sign disagreement among species that moved.

That is a lot to know in advance, and it constrains what this note is allowed to claim. It is why
prediction 1 below is *not* evidence of anything — it is a consistency check that would indicate a
bug if it failed, not a discovery if it holds. The predictions that carry weight here are 3 and 4,
which are about spatial structure and about effort, and nothing published so far speaks to either.

What was **not** looked at: any per-cell richness, any per-cell difference, the spatial distribution
of anything, and any map.

## 2. The estimand

For each cell *c* in the common footprint, the **expected number of the analysed species present**,
estimated separately in each epoch, and the difference between the two.

```
R_c^(e)  =  Σ_s  [ 1                                    if the species was recorded in c
                 [ Pr(occupied | k=0; ψ_s^e, p_s^e, n_c^e)   if it was not
```

with the second line exactly the expression registered in Phase 1e §5, and ψ_s^e, p_s^e the fits
that finding already published. **ΔR_c = R_c^(2) − R_c^(1)** is what would be drawn.

**Not species richness, and the layer may not use that word.** It is the expected count of *the
species this analysis could fit* — those with thirty or more occupied footprint cells at baseline —
which excludes every scarce and every newly-arrived species by construction. A cell's true richness
is higher than this number and moves for reasons this number cannot see.

**Why a count and not a mean Δψ per cell.** ψ is a property of a species over the footprint, not of
a cell, so there is no per-cell ψ to average; assigning a species' single Δψ to each of its cells
would draw the same value everywhere the species occurs and call it a spatial pattern. The count is
the honest per-cell quantity because each term in the sum is genuinely about that cell — it is the
species' own detection history *there*.

**Aggregated across species, and that is an ethics requirement rather than a presentation choice.**
The registry classifies both atlases `low` rather than `not_sensitive`, deliberately, because the
taxa include species that are sensitive at fine scale. A per-species per-cell surface would be a
27 km locator for every one of them. The sum over ~500 species is not, and the layer must never be
split by taxon, filtered to one species, or given a per-species tooltip.

## 3. The unit, and its known problems

A quarter-degree cell, ~27 × 27 km, the same grid Phase 1e fitted on and the coarser of the two
atlases' native units.

**The footprint is not a region.** Only cells with ≥20 full-protocol cards in *both* epochs enter,
which is 496 of them. The layer will therefore be a scatter of cells over South Africa, Lesotho and
Eswatini with holes in it, and the holes are not missing data to be interpolated — they are places
nobody atlassed twice. Any smoothing, contouring or nearest-neighbour fill would invent the one
thing this design refuses to guess.

**Both epoch fits are used, and the species set must be identical across them or the difference is
partly a change of species set.** Registered now: the sum runs over the species reportable in *both*
epochs under the primary window, which Phase 1e's `paired()` already identifies.

**A species whose sign flipped between windows stays in.** The flip rule in Phase 1e §4 governs
publishing a number *about that species*; dropping those species from a sum over 500 would select
the summands on an outcome, which is the worse error. Registered here so the choice is not made
after seeing the map.

## 4. Predictions, registered now

1. **The median ΔR_c across cells is within ±1.5 species of zero.** A consistency check, not a
   finding — the species-level median is already published as flat, so anything else means the
   per-cell aggregation is wrong. Failure here is a bug report.
2. **Corrected and naive surfaces agree closely: the median absolute difference in ΔR_c is under 1
   species.** Follows from Phase 1e's own result that 20+ cards leaves detection nothing to explain.
   If it fails, the map is drawing the model rather than the birds.
3. **There is real spatial structure: |ΔR_c| is not spatially independent.** Neighbouring cells
   should resemble each other more than distant ones (Moran's I on ΔR_c > 0, tested against a
   permutation null). If ΔR_c is spatial noise, a map of it is decoration and should not ship.
4. **The surface is not effort.** |ΔR_c| correlates with the change in card count per cell at
   |ρ| < 0.3 (Spearman). This is the prediction the layer lives or dies by.

## 5. Stop conditions

Each of these stops the layer. None of them stops the note, which gets its results either way.

- **Prediction 4 fails at |ρ| ≥ 0.3.** The surface is a map of where atlassing intensified and it is
  not published, in any form, with any caveat. A caveat does not stop a reader believing a map.
- **Prediction 3 fails.** Nothing is drawn; the finding keeps its empty view and gains a sentence
  saying the per-cell signal was tested for and was not there. An honest empty view beats a
  decorative full one.
- **Prediction 2 fails.** The corrected surface is withheld and the naive one is drawn instead, with
  the disagreement published — the reverse of the usual preference, because if the two disagree here
  it is the model that is unsupported, not the count.
- **Any cell's ΔR_c is driven by fewer than 5 species** whose individual contribution exceeds 0.5.
  Such a cell is a handful of coin flips and is dropped from the layer, with the count of dropped
  cells published. If more than 10% of cells drop, the whole layer does.

## 6. What this cannot establish

- **Not a trend.** Two epochs, nineteen unobserved years between them. No per-decade phrasing.
- **Not a cause.** No land-use, climate or protection covariate enters this. A cell that lost
  species and a cell that gained them are described, not explained.
- **Not southern Africa.** 496 cells in three countries, chosen by where volunteers atlassed twice.
- **Not richness.** See §2. It is a count over a fitted species set, and that set is biased towards
  species that were already widespread.
- **Not within-cell change.** 27 km is large enough to contain a species' entire local range, so a
  species that retreated within a cell is invisible here and a cell can look unchanged while
  everything inside it moved.

## 7. Where the result goes

- A gridded layer through `tiles/export.py::export_surface`, which cannot be called without a
  `PublicationClearance` minted from the registry's classification.
- A manifest entry, so the layer's terms and its description ship with it.
- The `atlas-no-net-change` view gains the layer, and its `because` stops apologising for an empty
  map.
- Results appended to this note with every prediction graded, whether or not anything is drawn.
