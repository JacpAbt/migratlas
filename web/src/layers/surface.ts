import type { ExpressionSpecification, Map as MapLibreMap } from "maplibre-gl";

import { COOL_RAMP } from "../globe/flavor";

import { attributionFor, fetchLayer, type LayerMeta, type LoadedLayer } from "./types";

const SOURCE_PREFIX = "surface-";

/**
 * Colour by value on a perceptually-ordered ramp, sized by value too.
 *
 * Two encodings for one variable is usually a mistake, but on a globe a cell is only a few
 * pixels when zoomed out — size alone is invisible and colour alone is hard to read against
 * the basemap.
 */
function paint(maxValue: number): {
  color: ExpressionSpecification;
  radius: ExpressionSpecification;
  opacity: ExpressionSpecification;
} {
  // Counts are heavily skewed: a handful of well-sampled cells dwarf the rest, so the ramp
  // is placed on log10 to keep the typical cell visible rather than uniformly dark.
  const logMax = Math.max(Math.log10(maxValue), 1);
  const stop = (fraction: number) => Math.pow(10, logMax * fraction);

  return {
    color: [
      "interpolate",
      ["linear"],
      ["log10", ["max", ["get", "value"], 1]],
      ...COOL_RAMP.flatMap((colour, index) => [
        (logMax * index) / (COOL_RAMP.length - 1),
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
  const [data, terms] = await fetchLayer<GeoJSON.FeatureCollection>(baseUrl, meta.name);

  const maxValue = data.features.reduce(
    (best, feature) => Math.max(best, Number(feature.properties?.value ?? 0)),
    1,
  );

  const sourceId = `${SOURCE_PREFIX}${meta.name}`;
  map.addSource(sourceId, {
    type: "geojson",
    data,
    attribution: attributionFor(meta, terms),
  });

  const { color, radius, opacity } = paint(maxValue);
  map.addLayer({
    id: sourceId,
    type: "circle",
    source: sourceId,
    paint: {
      "circle-color": color,
      "circle-radius": radius,
      "circle-opacity": opacity,
      "circle-blur": 0.35,
    },
  });

  return {
    meta,
    terms,
    setVisible: (visible) => {
      if (map.getLayer(sourceId)) {
        map.setLayoutProperty(sourceId, "visibility", visible ? "visible" : "none");
      }
    },
  };
}
