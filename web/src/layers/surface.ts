import type { ExpressionSpecification, Map as MapLibreMap } from "maplibre-gl";

import { palette } from "../globe/flavor";

import {
  attributionFor,
  fetchLayer,
  gridToFeatures,
  meanPosition,
  type GridPayload,
  type LayerMeta,
  type LoadedLayer,
} from "./types";

const SOURCE_PREFIX = "surface-";

/**
 * What either painter returns. One shape rather than two, so `addSurface` sets the same six
 * properties whichever scale a layer declares -- a sequential layer simply has no stroke.
 */
interface CirclePaint {
  color: ExpressionSpecification;
  radius: ExpressionSpecification;
  opacity: ExpressionSpecification;
  strokeWidth: ExpressionSpecification | number;
  strokeColor: string;
}

/**
 * Colour by value on a perceptually-ordered ramp, sized by value too.
 *
 * Two encodings for one variable is usually a mistake, but on a globe a cell is only a few
 * pixels when zoomed out — size alone is invisible and colour alone is hard to read against
 * the basemap.
 */
function paint(maxValue: number): CirclePaint {
  const ramp = palette().cool;
  // Counts are heavily skewed: a handful of well-sampled cells dwarf the rest, so the ramp
  // is placed on log10 to keep the typical cell visible rather than uniformly dark.
  const logMax = Math.max(Math.log10(maxValue), 1);
  const stop = (fraction: number) => Math.pow(10, logMax * fraction);

  return {
    color: [
      "interpolate",
      ["linear"],
      ["log10", ["max", ["get", "value"], 1]],
      ...ramp.flatMap((colour, index) => [
        (logMax * index) / (ramp.length - 1),
        colour,
      ]),
    ] as ExpressionSpecification,
    radius: [
      "interpolate",
      ["linear"],
      ["zoom"],
      1,
      ["interpolate", ["linear"], ["get", "value"], 1, 1.2, stop(1), 3.5],
      6,
      ["interpolate", ["linear"], ["get", "value"], 1, 3, stop(1), 11],
    ] as ExpressionSpecification,
    // Fading the sparse end rather than colouring it pale. A 29,000-cell global grid drawn at
    // uniform opacity reads as a halftone screen over the ocean: the eye sees a texture instead
    // of a quantity, and a cell with one tracked individual claims as much attention as a
    // hotspot with hundreds.
    opacity: [
      "interpolate",
      ["linear"],
      ["log10", ["max", ["get", "value"], 1]],
      0,
      0.3,
      logMax * 0.5,
      0.7,
      logMax,
      0.9,
    ] as ExpressionSpecification,
    // A count has no direction to carry, so nothing is ringed.
    strokeWidth: 0,
    strokeColor: ramp[4],
  };
}

/**
 * Colour a signed change from a shared centre, with direction carried twice.
 *
 * Losses run warm and gains run cool, both outward from a near-invisible zero, so the ramp reads
 * away from the centre in either direction rather than dark-to-light across the range. The extent is
 * symmetric on the larger tail: scaling each side to its own maximum would make a −39 cell and a
 * +27 cell equally saturated and imply they are equal changes.
 *
 * Direction is also drawn, not only coloured. A loss gets a ring, a gain is solid. ADR 0007's rule
 * that meaning never rests on hue alone is not satisfied by a diverging ramp -- the two ends of one
 * are exactly the confusion a red-green reader cannot resolve, and this layer's whole content is
 * which way a cell went.
 */
function divergingPaint(extent: number): CirclePaint {
  const shades = palette();
  const loss = shades.warm[4];
  const gain = shades.cool[4];
  // Zero is the pale end of the warm ramp by day and its dim end by night, which is what "no
  // change" should look like on either surface: present, and not asking for attention.
  const nothing = shades.warm[0];
  const span = Math.max(extent, 1);

  return {
    color: [
      "interpolate",
      ["linear"],
      ["get", "value"],
      -span,
      loss,
      -span * 0.15,
      shades.warm[2],
      0,
      nothing,
      span * 0.15,
      shades.cool[2],
      span,
      gain,
    ] as ExpressionSpecification,
    // Magnitude, so a cell that barely moved stays small whichever way it went. Zoom-scaled the
    // same way the count layers are, because a quarter-degree cell is sub-pixel on a whole globe.
    radius: [
      "interpolate",
      ["linear"],
      ["zoom"],
      1,
      ["interpolate", ["linear"], ["abs", ["get", "value"]], 0, 1.2, span, 4],
      6,
      ["interpolate", ["linear"], ["abs", ["get", "value"]], 0, 3, span, 12],
    ] as ExpressionSpecification,
    opacity: [
      "interpolate",
      ["linear"],
      ["abs", ["get", "value"]],
      0,
      0.35,
      span * 0.5,
      0.75,
      span,
      0.9,
    ] as ExpressionSpecification,
    // Interpolate on the outside, `case` in each stop -- not the other way round. MapLibre allows
    // a `zoom` expression only as the input to a *top-level* step or interpolate, so a `case`
    // wrapping one is rejected at `addLayer`. It rejects it by logging: the layer never enters the
    // style, `addSurface` returns a `LoadedLayer` anyway, and the panel then offers a checkbox for
    // something that was never drawn.
    strokeWidth: [
      "interpolate",
      ["linear"],
      ["zoom"],
      1,
      ["case", ["<", ["get", "value"], 0], 0.6, 0],
      6,
      ["case", ["<", ["get", "value"], 0], 1.8, 0],
    ] as ExpressionSpecification,
    strokeColor: loss,
  };
}

/**
 * Add a gridded surface to the globe.
 *
 * Attribution and the generalisation statement are attached to the source, so MapLibre shows
 * them whenever the layer is visible. That is a requirement, not a nicety: a published layer
 * must never be separable from the terms it was published under.
 */
export async function addSurface(
  map: MapLibreMap,
  meta: LayerMeta,
  baseUrl: string,
): Promise<LoadedLayer> {
  const isGrid = meta.format === "grid";
  const [payload, terms] = await fetchLayer<GridPayload | GeoJSON.FeatureCollection>(
    baseUrl,
    meta.name,
    isGrid ? "grid.json" : "geojson",
  );
  const data = isGrid ? gridToFeatures(payload as GridPayload) : (payload as GeoJSON.FeatureCollection);

  const diverging = meta.scale === "diverging";
  // A count's ramp is placed on its maximum. A change's is placed on its largest tail in either
  // direction, so both sides share one scale and a loss of 39 does not read like a gain of 27.
  const values = data.features.map((feature) => Number(feature.properties?.value ?? 0));
  const extent = values.reduce(
    (best, value) => Math.max(best, diverging ? Math.abs(value) : value),
    1,
  );
  const painter = () => (diverging ? divergingPaint(extent) : paint(extent));

  const sourceId = `${SOURCE_PREFIX}${meta.name}`;
  map.addSource(sourceId, {
    type: "geojson",
    data,
    attribution: attributionFor(meta, terms),
  });

  const first = painter();
  map.addLayer({
    id: sourceId,
    type: "circle",
    source: sourceId,
    paint: {
      "circle-color": first.color,
      "circle-radius": first.radius,
      "circle-opacity": first.opacity,
      // Sharp for a change layer. The blur that keeps a count surface from reading as halftone
      // also smears a ring into its fill, and the ring is how direction survives without hue.
      "circle-blur": diverging ? 0 : 0.35,
      "circle-stroke-width": first.strokeWidth,
      "circle-stroke-color": first.strokeColor,
    },
  });

  return {
    meta,
    terms,
    cells: data.features.length,
    center: meanPosition(data),
    setVisible: (visible) => {
      if (map.getLayer(sourceId)) {
        map.setLayoutProperty(sourceId, "visibility", visible ? "visible" : "none");
      }
    },
    repaint: () => {
      if (!map.getLayer(sourceId)) return;
      const next = painter();
      map.setPaintProperty(sourceId, "circle-color", next.color);
      // The ring is drawn in the surface's own loss colour, so it has to follow day/night too.
      map.setPaintProperty(sourceId, "circle-stroke-color", next.strokeColor);
    },
  };
}
