import { Popup, type ExpressionSpecification, type Map as MapLibreMap } from "maplibre-gl";

import { palette } from "../globe/flavor";

import { DART, dartIcon } from "./dart";
import {
  attributionFor,
  fetchLayer,
  meanPosition,
  type LayerMeta,
  type LoadedLayer,
} from "./types";

/**
 * A station feature. Weekly values arrive as scalar `w0`..`w51` properties, present only for
 * weeks that have data; `dw`/`sw` carry the week's movement bearing and ground speed, present
 * only where the VVP fit gave the night a velocity.
 */
interface SeriesProperties {
  station: string;
  peak: number | null;
  years: number;
  weeks_present: number;
  autumn_shift_days_per_decade?: number | null;
  trend_years?: number | null;
  [week: `w${number}`]: number | undefined;
  [bearing: `dw${number}`]: number | undefined;
  [speed: `sw${number}`]: number | undefined;
}

const WEEKS = 52;
const weekKey = (week: number): string => `w${week}`;
const bearingKey = (week: number): string => `dw${week}`;
const speedKey = (week: number): string => `sw${week}`;

const SOURCE_PREFIX = "series-";

/** The value at the clock's week. A plain property lookup, evaluated per feature per frame. */
const valueAt = (week: number): ExpressionSpecification => ["to-number", ["get", weekKey(week)]];

/**
 * A gap must read as "not measured", so the station is not drawn rather than drawn at zero.
 *
 * `has` on a scalar key, not a lookup into an array property: MapLibre hands arrays to the paint
 * path natively and to the query path as a JSON string, so an array-based filter drew 161
 * stations that queryRenderedFeatures reported as zero.
 */
const hasValueAt = (week: number): ExpressionSpecification => ["has", weekKey(week)];

function paint(
  maxValue: number,
  atWeek: number,
): {
  color: ExpressionSpecification;
  radius: ExpressionSpecification;
} {
  // Read here rather than at module load, so a surface change is a repaint rather than a reload.
  const ramp = palette().warm;
  // Peak passage is orders of magnitude above a quiet night, so a linear ramp would leave
  // most of the year as one flat colour.
  const logMax = Math.max(Math.log10(maxValue), 1);
  const week = (w: number): ExpressionSpecification => ["log10", ["max", valueAt(w), 1]];

  return {
    color: [
      "interpolate",
      ["linear"],
      week(atWeek),
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
      ["interpolate", ["linear"], week(atWeek), 0, 2, logMax, 7],
      6,
      ["interpolate", ["linear"], week(atWeek), 0, 5, logMax, 22],
    ] as ExpressionSpecification,
  };
}

/**
 * Add a station time series whose week is chosen by expression.
 *
 * Every station is one feature carrying all 52 weeks, so advancing the clock re-evaluates two
 * paint properties and a filter rather than fetching or rebuilding anything (ADR 0002). The
 * cost of a week change is independent of how many weeks exist.
 */
export async function addSeries(
  map: MapLibreMap,
  meta: LayerMeta,
  baseUrl: string,
  initialWeek: number,
): Promise<LoadedLayer> {
  const ramp = palette().warm;
  const [data, terms] = await fetchLayer<GeoJSON.FeatureCollection>(baseUrl, meta.name);

  const maxValue = data.features.reduce(
    (best, feature) => Math.max(best, Number((feature.properties as SeriesProperties)?.peak ?? 0)),
    1,
  );

  const id = `${SOURCE_PREFIX}${meta.name}`;
  map.addSource(id, { type: "geojson", data, attribution: attributionFor(meta, terms) });

  // A herd fits inside one tile quantum at globe zoom, where the GeoJSON tiler drops coincident
  // points outright -- measured: 481 cells render from z3.5 and vanish below z3.4, whatever the
  // filter says. So a compact layer hands over, the way the drawn coastline hands over to the
  // surveyed one: below the threshold a single locator says the study is here, above it the
  // cells say what it looks like.
  const span = extent(data);
  const compact = span < 2;
  const HANDOVER = 3.4;

  map.addLayer({
    id,
    type: "circle",
    source: id,
    ...(compact ? { minzoom: HANDOVER } : {}),
    paint: {
      "circle-color": ramp[2],
      "circle-radius": 3,
      "circle-opacity": 0.8,
      // Blurred, because a radar's measurement is an airspace tens of kilometres across, not
      // a point at the antenna. A hard disc would claim precision the instrument lacks.
      "circle-blur": 0.6,
    },
  });

  const locatorId = `${id}-locator`;
  if (compact) {
    map.addSource(locatorId, {
      type: "geojson",
      data: {
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            geometry: { type: "Point", coordinates: meanPosition(data) },
            properties: { title: meta.title },
          },
        ],
      },
    });
    map.addLayer({
      id: locatorId,
      type: "circle",
      source: locatorId,
      maxzoom: HANDOVER,
      paint: {
        "circle-color": ramp[2],
        "circle-radius": 4,
        "circle-opacity": 0.85,
        "circle-blur": 0.4,
      },
    });
  }

  // The dart: where the mass moved that week. Registered before the layer that wears it, and
  // `updateImage` on a surface change because removing an image a layer is using makes MapLibre
  // warn on every frame.
  const flowId = `${id}-flow`;
  if (!map.hasImage(DART)) {
    const icon = dartIcon(ramp[4]);
    map.addImage(DART, icon.data, { pixelRatio: icon.pixelRatio });
  }
  map.addLayer({
    id: flowId,
    type: "symbol",
    source: id,
    layout: {
      "icon-image": DART,
      // The bearing is geographic, so the dart turns with the globe rather than the screen.
      "icon-rotation-alignment": "map",
      "icon-allow-overlap": true,
      "icon-ignore-placement": true,
      "icon-size": ["interpolate", ["linear"], ["zoom"], 1, 0.55, 6, 1.0],
    },
    paint: { "icon-opacity": 0.85 },
  });

  let current = -1;
  const showWeek = (week: number): void => {
    if (week === current) return;
    current = week;
    const { color, radius } = paint(maxValue, week);
    map.setFilter(id, hasValueAt(week));
    map.setPaintProperty(id, "circle-color", color);
    map.setPaintProperty(id, "circle-radius", radius);
    // A week with passage but no velocity fit shows a station and no dart, which is the honest
    // rendering of "it flew, and the fit could not say where to".
    map.setFilter(flowId, ["all", hasValueAt(week), ["has", bearingKey(week)]]);
    map.setLayoutProperty(flowId, "icon-rotate", ["to-number", ["get", bearingKey(week)]]);
  };
  showWeek(initialWeek);

  attachPopup(map, id, meta, () => current);

  return {
    meta,
    terms,
    cells: data.features.length,
    center: meanPosition(data),
    // A camera that can actually see it: a compact layer is invisible below the hand-over, so
    // pointing at its centre from globe zoom would frame a locator and claim the layer is empty.
    ...(compact ? { zoom: 5.5 } : {}),
    showWeek,
    // Re-run the week it is already on. `showWeek` short-circuits when the week has not moved,
    // so the repaint has to forget which week that was -- otherwise a surface change is a no-op
    // on every layer that happens to be showing the right week already.
    repaint: () => {
      map.updateImage(DART, dartIcon(palette().warm[4]).data);
      const week = current;
      current = -1;
      showWeek(week);
    },
    setVisible: (visible) => {
      // The dart and the locator follow their stations: one checkbox, one measurement.
      for (const layerId of [id, flowId, locatorId]) {
        if (map.getLayer(layerId)) {
          map.setLayoutProperty(layerId, "visibility", visible ? "visible" : "none");
        }
      }
    },
  };
}

/** Greatest axis span of a collection's points, in degrees. */
function extent(collection: GeoJSON.FeatureCollection): number {
  let minLon = Infinity;
  let maxLon = -Infinity;
  let minLat = Infinity;
  let maxLat = -Infinity;
  for (const feature of collection.features) {
    if (feature.geometry.type !== "Point") continue;
    const [x, y] = feature.geometry.coordinates;
    if (x === undefined || y === undefined) continue;
    minLon = Math.min(minLon, x);
    maxLon = Math.max(maxLon, x);
    minLat = Math.min(minLat, y);
    maxLat = Math.max(maxLat, y);
  }
  if (minLon > maxLon) return 0;
  return Math.max(maxLon - minLon, maxLat - minLat);
}

function attachPopup(
  map: MapLibreMap,
  id: string,
  meta: LayerMeta,
  week: () => number,
): void {
  const popup = new Popup({ closeButton: true, maxWidth: "320px" });

  map.on("click", id, (event) => {
    const feature = event.features?.[0];
    if (!feature) return;
    const properties = feature.properties as unknown as SeriesProperties;
    popup.setLngLat(event.lngLat).setHTML(summary(properties, week(), meta)).addTo(map);
  });

  map.on("mouseenter", id, () => (map.getCanvas().style.cursor = "pointer"));
  map.on("mouseleave", id, () => (map.getCanvas().style.cursor = ""));
}

const MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(" ");

function weekLabel(week: number): string {
  const date = new Date(Date.UTC(2001, 0, 1 + week * 7));
  return `${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]}`;
}

function summary(properties: SeriesProperties, week: number, meta: LayerMeta): string {
  const at = (index: number): number | undefined =>
    properties[weekKey(index) as `w${number}`];
  const value = at(week);

  let peakWeek = 0;
  for (let index = 1; index < WEEKS; index++) {
    if ((at(index) ?? -1) > (at(peakWeek) ?? -1)) peakWeek = index;
  }
  const shift = properties.autumn_shift_days_per_decade;

  const rows = [
    [`Week of ${weekLabel(week)}`, value === null || value === undefined ? "no data" : fmt(value)],
    [`Busiest week (${weekLabel(peakWeek)})`, fmt(properties.peak ?? 0)],
    ["Years observed", String(properties.years)],
  ];
  const bearing = properties[bearingKey(week) as `dw${number}`];
  const speed = properties[speedKey(week) as `sw${number}`];
  if (bearing !== undefined && speed !== undefined) {
    rows.push(["Heading this week", `${bearing}° at ${speed} m/s`]);
  }
  // Null when the station failed the trend thresholds -- saying so beats an empty row -- and
  // absent entirely on a layer that publishes no trend, where the row would be an insinuation.
  if (shift !== undefined) {
    rows.push([
      "Autumn passage shift",
      shift === null
        ? "too short a record"
        : `${shift > 0 ? "+" : ""}${shift.toFixed(2)} days/decade over ${properties.trend_years} yr`,
    ]);
  }

  const caveat = meta.popup_caveat ? `<p class="caveat">${meta.popup_caveat}</p>` : "";
  return `
    <strong>${properties.station}</strong>
    <table>${rows.map(([k, v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join("")}</table>
    ${caveat}
  `;
}

function fmt(value: number): string {
  return value >= 1000 ? `${Math.round(value / 1000)}k` : String(Math.round(value));
}
