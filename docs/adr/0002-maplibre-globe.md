# ADR 0002 — MapLibre GL JS v5 globe, and no deck.gl in globe mode

**Status:** accepted · 2026-07-28

## Context

The product is a globe you spin, holding potentially large point and raster layers, and it must stay
light on memory. Three candidates: CesiumJS, deck.gl's `GlobeView`, and MapLibre GL JS v5's globe
projection.

Evidence gathered rather than assumed:

- **CesiumJS** is the most capable true-3D globe, but a 2026 ISPRS benchmark measured ~21,357 ms total
  blocking time on large point data, against near-zero for MapLibre. It is built for terrain and
  precise 3D cartography, which this project does not need.
- **deck.gl `GlobeView`** is still flagged experimental: no basemap provider, no pitch or bearing, no
  high-precision rendering above zoom 12, and `TileLayer`/`MVTLayer` support described as
  experimental. Whether `MapboxOverlay` works correctly under MapLibre's globe projection is not
  documented; the tracking issue is closed with no confirmation either way.
- **MapLibre GL JS v5** shipped globe projection in January 2025 and renders heatmap, symbol,
  fill-extrusion and custom layers directly on the globe, reusing Mercator vector tiles via
  client-side reprojection.

## Decision

MapLibre GL JS v5 globe projection, with all animal data pre-baked into tiles and drawn with native
MapLibre layers. No deck.gl while in globe projection.

If trip-style animation is wanted later, it goes in the zoomed-in Mercator mode, where `MapboxOverlay`
interleaving is documented and supported.

## Consequences

Good: one GL context, one memory budget, and the lightest of the three options. Data volume is a
tiling problem rather than a browser problem, which is where it belongs. Time animation is a `filter`
expression on a time index, not a layer rebuild.

Bad: no true 3D terrain, and no pitch on the globe. Flight-altitude data, which the radar profiles do
have, cannot be shown as literal 3D height on the globe and will need a different encoding.

Revisit if: deck.gl's globe support becomes stable and documented, or a layer genuinely needs 3D.
