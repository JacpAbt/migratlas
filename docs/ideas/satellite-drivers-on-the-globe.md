# Idea — put the satellite drivers on the same clock as the animals

**Status:** idea, not a commitment. Nothing here is scheduled. Recorded 2026-07-29 so it is not
re-invented from scratch later.

## Why this and not animal-detection-from-space

The obvious reading of "use satellite data" is to find animals in the imagery. That works, but
only for large, aggregated, high-contrast animals against a uniform background: whales at the
surface and elephants in savannah at ~30 cm commercial resolution, seal and walrus haul-outs,
wildebeest on open plains, and best of all penguin colonies, which are counted from **guano
staining** in free Landsat and Sentinel-2 imagery. It fails for anything under about a metre of
visible extent, under canopy, underwater, nocturnal, or in flight — which is most animals and
nearly all migration. It cannot be the backbone for "where are the animals"; it is a
per-species, per-site census instrument.

Meanwhile satellites already carry this project's second question entirely. Winds, temperature,
sea-surface temperature, chlorophyll, sea ice, vegetation green-up and sea level are all
satellite or satellite-fed reanalysis products, and Phase 2a's attribution is built on them.
Satellites are how we answer *why it changed*, far more than *where they are*.

So the frontend opportunity is not detection. It is this: **the globe already has a clock, and
the drivers are on the same clock.** Right now the clock moves animals and the environment stays
still, which quietly implies the environment is a backdrop. It is the cause.

## The proposal

Drive an environmental layer from the existing week index, so dragging the time slider greens up
the continents, retreats the sea ice, and warms the sea surface *while* the passage layer
brightens. Migration timing and its driver become one visual statement instead of a regression
coefficient in a report.

Concretely, in rough order of value per unit of work:

1. **Vegetation green-up.** A weekly NDVI (or EVI) climatology. Spring green-up is the single
   most legible driver of northern-hemisphere migration timing, and seeing the green wave move
   north ahead of the passage peak is the whole Phase 2a story in one gesture.
2. **Sea ice edge.** A weekly ice-extent contour as a line layer. Small — a polyline, not a
   grid — visually striking, and directly relevant to Arctic-breeding migrants. Cheap enough
   that it may be worth doing first.
3. **Sea-surface temperature.** The marine counterpart, and the driver for the marine layers
   that currently sit on a static basemap.
4. **Wind at 850 hPa.** Arrows or a particle field. The most beautiful and the most expensive;
   also the one with the strongest direct mechanism for a single night's passage.

## How it fits what already exists

- **Same time index.** `web/src/state/time.ts` already publishes a 0–51 week index, and the
  radar layer already reads a per-week property. A driver layer joins the same subscription. No
  new animation machinery, and ADR 0002 still holds: change an expression, never rebuild a layer.
- **Same export shape.** A weekly global climatology at 1° is 360 × 180 × 52 values. Quantised
  to a byte per cell that is ~3.4 MB, or ~70 KB per week fetched on demand — the grid format in
  `tiles/export.py` already carries index arrays and a `cell_size_deg`, so this needs a value
  encoding decision and not a new format. A globe never resolves better than ~0.25°, so the
  temptation to ship native resolution should be refused.
- **Same gate.** ERA5 and Copernicus Marine are open with attribution, so the licence check
  added for eBird passes here — but it still has to be asked, per source, in the registry.
- **`features/annotate.py`** is the planned Phase 2a component that samples any raster onto any
  point set. The frontend layer and the attribution panel would read the same climatology, which
  is the point: the picture and the regression should not be able to disagree.

## What must be true first

- Phase 2a exists. Publishing a driver layer before the attribution analysis invites the viewer
  to draw the causal conclusion themselves, from a picture, with no stated uncertainty. That is
  the failure mode this project is built to avoid.
- The honest label is settled. A weekly *climatology* is not the weather of a particular year;
  animating one against a 30-year passage climatology is comparing two averages, and the caption
  has to say so. Per-year driver data is a much larger commitment.
- The performance budget absorbs it. Currently 26.3 MB heap and 221 KiB compressed for three
  layers, against a 150 MB ceiling — there is room, and the browser test will say so rather than
  anyone guessing.

## The narrower detection idea, kept separately

If animal-detection-from-space is ever wanted, the tractable open case is **penguin colonies**:
published, repeatedly counted from free imagery over ~15 years, and — crucially — colony
locations are already public, so the ethics gate has nothing to withhold. That lands as
`SURVEY_INDEX`, which is already one of the seven evidence types: a repeated count at a fixed
site, animated by year rather than by week. It would also be the first Antarctic data in the
lake and the first non-flying, non-marine-megafauna vertical.

The same idea for rhino or elephant would be the opposite: a satellite-derived location for a
poaching-target species is exactly what `redact.py` exists to refuse, and no aggregation short of
uselessness makes it safe. Do not start there.
