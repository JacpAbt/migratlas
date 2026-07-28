import type { ExpressionSpecification, Map as MapLibreMap } from "maplibre-gl";

/** One entry of the build-layers manifest. */
export interface LayerMeta {
  name: string;
  title: string;
  description: string;
  realm: string;
  evidence_type: string;
  value_kind: string;
  attribution: string;
  licence: string;
  landing_page: string;
  caveats: string;
}

/** The generalisation statement written beside each layer by the ethics gate. */
interface LayerTerms {
  "dwc:dataGeneralizations": string;
  sensitivity: string;
  cells: number;
}

export interface LoadedLayer {
  meta: LayerMeta;
  terms: LayerTerms;
  maxValue: number;
}

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
      0,
      "#2b3a5c",
      logMax * 0.35,
      "#3f7fa6",
      logMax * 0.65,
      "#6fd3c7",
      logMax,
      "#f6f5b4",
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
  const [data, terms] = await Promise.all([
    fetch(`${baseUrl}layers/${meta.name}.geojson`).then((r) => {
      if (!r.ok) throw new Error(`${meta.name}: ${r.status}`);
      return r.json() as Promise<GeoJSON.FeatureCollection>;
    }),
    fetch(`${baseUrl}layers/${meta.name}.meta.json`).then((r) => {
      if (!r.ok) throw new Error(`${meta.name} terms: ${r.status}`);
      return r.json() as Promise<LayerTerms>;
    }),
  ]);

  const maxValue = data.features.reduce(
    (best, feature) => Math.max(best, Number(feature.properties?.value ?? 0)),
    1,
  );

  const sourceId = `${SOURCE_PREFIX}${meta.name}`;
  map.addSource(sourceId, {
    type: "geojson",
    data,
    attribution:
      `<a href="${meta.landing_page}">${meta.title}</a> (${meta.licence}) — ` +
      terms["dwc:dataGeneralizations"],
  });

  const { color, radius } = paint(maxValue);
  map.addLayer({
    id: sourceId,
    type: "circle",
    source: sourceId,
    paint: {
      "circle-color": color,
      "circle-radius": radius,
      "circle-opacity": 0.85,
      "circle-blur": 0.35,
    },
  });

  return { meta, terms, maxValue };
}

export function setSurfaceVisible(map: MapLibreMap, name: string, visible: boolean): void {
  const id = `${SOURCE_PREFIX}${name}`;
  if (map.getLayer(id)) {
    map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
  }
}

export async function loadManifest(baseUrl: string): Promise<LayerMeta[]> {
  const response = await fetch(`${baseUrl}layers/manifest.json`);
  if (!response.ok) return [];
  return (await response.json()) as LayerMeta[];
}
