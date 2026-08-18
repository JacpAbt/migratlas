/**
 * A seasonal surface: one value per cell per half-month, walked by the clock.
 *
 * The green wave is its first tenant. The encoding is the compact grid's sibling -- index arrays
 * plus one 24-value array per cell -- expanded here into features whose `hm0`..`hm23` properties
 * the paint expression reads, so a half-month change is an expression swap and never a fetch
 * (ADR 0002). Null bins omit their key: "no vegetated ground that half-month" must not read as
 * greenness zero.
 */

import { Popup, type ExpressionSpecification, type Map as MapLibreMap } from "maplibre-gl";

import { palette } from "../globe/flavor";

import { attributionFor, fetchLayer, meanPosition, type LayerMeta, type LoadedLayer } from "./types";

const SOURCE_PREFIX = "seasonal-";

/** The wire shape `tiles/greenwave.py` writes. */
interface SeasonalGrid {
  format: "seasonal-grid";
  cell_size_deg: number;
  bins: number;
  value_kind: string;
  x: number[];
  y: number[];
  hm: (number | null)[][];
}

/** The half-month bin the clock's week falls in, read off the week's midpoint day. */
const binOf = (week: number): number => {
  const at = new Date(Date.UTC(2001, 0, 1 + week * 7 + 3));
  return at.getUTCMonth() * 2 + (at.getUTCDate() > 15 ? 1 : 0);
};

const binKey = (bin: number): string => `hm${bin}`;

function paint(atBin: number): ExpressionSpecification {
  const ramp = palette().growth;
  // NDVI arrives as hundredths, 0-100. Vegetation worth calling green starts around 0.2, and a
  // linear ramp from zero would spend half its colours below anything a reader would call plant.
  const value: ExpressionSpecification = ["to-number", ["get", binKey(atBin)]];
  return [
    "interpolate",
    ["linear"],
    value,
    ...ramp.flatMap((colour, index) => [10 + (index * 70) / (ramp.length - 1), colour]),
  ] as ExpressionSpecification;
}

export async function addSeasonal(
  map: MapLibreMap,
  meta: LayerMeta,
  baseUrl: string,
  initialWeek: number,
  deferTo: string[] = [],
): Promise<LoadedLayer> {
  const [grid, terms] = await fetchLayer<SeasonalGrid>(baseUrl, meta.name, "json");
  if (grid.x.length !== grid.y.length || grid.x.length !== grid.hm.length) {
    throw new Error(`${meta.name}: grid arrays disagree`);
  }

  const size = grid.cell_size_deg;
  const features: GeoJSON.Feature[] = [];
  for (let index = 0; index < grid.x.length; index++) {
    const [xi, yi, bins] = [grid.x[index], grid.y[index], grid.hm[index]];
    if (xi === undefined || yi === undefined || bins === undefined) continue;
    const properties: Record<string, number> = {};
    for (const [bin, value] of bins.entries()) {
      if (value !== null) properties[binKey(bin)] = value;
    }
    features.push({
      type: "Feature",
      geometry: {
        type: "Point",
        coordinates: [(xi + 0.5) * size - 180, (yi + 0.5) * size - 90],
      },
      properties,
    });
  }
  const data: GeoJSON.FeatureCollection = { type: "FeatureCollection", features };

  const id = `${SOURCE_PREFIX}${meta.name}`;
  map.addSource(id, { type: "geojson", data, attribution: attributionFor(meta, terms) });
  map.addLayer({
    id,
    type: "circle",
    source: id,
    paint: {
      "circle-color": paint(binOf(initialWeek)),
      // Soft and under-stated: the wave is context for the animals, not a subject shouting
      // over them, and at one degree a hard disc would claim precision the average lacks.
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 1, 2.5, 4, 9, 7, 26],
      "circle-opacity": 0.35,
      "circle-blur": 0.9,
    },
  });

  let current = -1;
  const showWeek = (week: number): void => {
    const bin = binOf(week);
    if (bin === current) return;
    current = bin;
    map.setFilter(id, ["has", binKey(bin)]);
    map.setPaintProperty(id, "circle-color", paint(bin));
  };
  showWeek(initialWeek);

  const popup = new Popup({ closeButton: true, maxWidth: "320px" });
  map.on("click", id, (event) => {
    const feature = event.features?.[0];
    if (!feature) return;
    // The wave is context, drawn under everything, so it answers a click only when nothing
    // above it does -- two popups opened by one click was how this rule announced itself.
    // Sibling ids are `<kind>-<manifest name>` with per-module kinds, so the match is on the
    // name anywhere in the id, not on a prefix this module would have to keep in sync.
    const covered = map
      .queryRenderedFeatures(event.point)
      .some((f) => f.layer.id !== id && deferTo.some((name) => f.layer.id.includes(name)));
    if (covered) return;
    const value = (feature.properties as Record<string, number>)[binKey(current)];
    const caveat = meta.popup_caveat ? `<p class="caveat">${meta.popup_caveat}</p>` : "";
    popup
      .setLngLat(event.lngLat)
      .setHTML(
        `<strong>${meta.title}</strong>
         <table><tr><th>NDVI this half-month</th><td>${((value ?? 0) / 100).toFixed(2)}</td></tr></table>
         ${caveat}`,
      )
      .addTo(map);
  });

  return {
    meta,
    terms,
    cells: features.length,
    center: meanPosition(data),
    showWeek,
    setVisible: (visible) => {
      if (map.getLayer(id)) {
        map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
      }
    },
    repaint: () => {
      map.setPaintProperty(id, "circle-color", paint(current));
    },
  };
}
