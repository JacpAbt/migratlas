import { Popup, type ExpressionSpecification, type Map as MapLibreMap } from "maplibre-gl";

import { WARM_RAMP } from "../globe/flavor";

import {
  attributionFor,
  fetchLayer,
  meanPosition,
  type LayerMeta,
  type LoadedLayer,
} from "./types";

interface SeriesProperties {
  station: string;
  /** 52 weekly values; null where the instrument has no data for that week of year. */
  weeks: (number | null)[];
  peak: number | null;
  years: number;
  autumn_shift_days_per_decade?: number | null;
  trend_years?: number | null;
}

const SOURCE_PREFIX = "series-";

/**
 * The value at the clock's week, as a MapLibre expression.
 *
 * `to-number` rather than the raw lookup because a gap is published as JSON null, which is not
 * a number MapLibre can interpolate. Stations at a gap are filtered out entirely instead, so
 * the coercion to 0 never reaches a paint property.
 */
const valueAt = (week: number): ExpressionSpecification => [
  "to-number",
  ["at", week, ["get", "weeks"]],
];

/** A gap must read as "not measured", so the station is not drawn rather than drawn at zero. */
const hasValueAt = (week: number): ExpressionSpecification => [
  "!=",
  ["to-string", ["at", week, ["get", "weeks"]]],
  "",
];

function paint(maxValue: number): {
  color: ExpressionSpecification;
  radius: ExpressionSpecification;
} {
  // Peak passage is orders of magnitude above a quiet night, so a linear ramp would leave
  // most of the year as one flat colour.
  const logMax = Math.max(Math.log10(maxValue), 1);
  const week = (w: number): ExpressionSpecification => ["log10", ["max", valueAt(w), 1]];

  return {
    color: [
      "interpolate",
      ["linear"],
      week(0),
      ...WARM_RAMP.flatMap((colour, index) => [
        (logMax * index) / (WARM_RAMP.length - 1),
        colour,
      ]),
    ] as ExpressionSpecification,
    radius: [
      "interpolate",
      ["linear"],
      ["zoom"],
      1,
      ["interpolate", ["linear"], week(0), 0, 2, logMax, 7],
      6,
      ["interpolate", ["linear"], week(0), 0, 5, logMax, 22],
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
  const [data, terms] = await fetchLayer<GeoJSON.FeatureCollection>(baseUrl, meta.name);

  const maxValue = data.features.reduce((best, feature) => {
    const weeks = (feature.properties as SeriesProperties | null)?.weeks ?? [];
    return Math.max(best, ...weeks.map((value) => value ?? 0));
  }, 1);

  const id = `${SOURCE_PREFIX}${meta.name}`;
  map.addSource(id, { type: "geojson", data, attribution: attributionFor(meta, terms) });
  map.addLayer({
    id,
    type: "circle",
    source: id,
    paint: {
      "circle-color": WARM_RAMP[2],
      "circle-radius": 3,
      "circle-opacity": 0.8,
      // Blurred, because a radar's measurement is an airspace tens of kilometres across, not
      // a point at the antenna. A hard disc would claim precision the instrument lacks.
      "circle-blur": 0.6,
    },
  });

  const template = paint(maxValue);
  let current = -1;
  const showWeek = (week: number): void => {
    if (week === current) return;
    current = week;
    map.setFilter(id, hasValueAt(week));
    map.setPaintProperty(id, "circle-color", substitute(template.color, week));
    map.setPaintProperty(id, "circle-radius", substitute(template.radius, week));
  };
  showWeek(initialWeek);

  attachPopup(map, id, meta, () => current);

  return {
    meta,
    terms,
    cells: data.features.length,
    center: meanPosition(data),
    showWeek,
    setVisible: (visible) => {
      if (map.getLayer(id)) {
        map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
      }
    },
  };
}

/**
 * Rewrite a template expression's week index.
 *
 * The alternative is rebuilding the expression per week, which means re-deriving the colour
 * stops from the data every time the clock ticks. The template is built once and only the
 * index moves.
 */
function substitute(expression: ExpressionSpecification, week: number): ExpressionSpecification {
  const walk = (node: unknown): unknown => {
    if (!Array.isArray(node)) return node;
    if (node[0] === "at" && typeof node[1] === "number") return ["at", week, node[2]];
    return node.map(walk);
  };
  return walk(expression) as ExpressionSpecification;
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
    // GeoJSON arrays survive a MapLibre round-trip as JSON strings.
    const weeks: (number | null)[] =
      typeof properties.weeks === "string" ? JSON.parse(properties.weeks) : properties.weeks;
    popup.setLngLat(event.lngLat).setHTML(summary(properties, weeks, week(), meta)).addTo(map);
  });

  map.on("mouseenter", id, () => (map.getCanvas().style.cursor = "pointer"));
  map.on("mouseleave", id, () => (map.getCanvas().style.cursor = ""));
}

const MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(" ");

function weekLabel(week: number): string {
  const date = new Date(Date.UTC(2001, 0, 1 + week * 7));
  return `${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]}`;
}

function summary(
  properties: SeriesProperties,
  weeks: (number | null)[],
  week: number,
  meta: LayerMeta,
): string {
  const value = weeks[week];
  const peakWeek = weeks.reduce<number>(
    (best, candidate, index) => ((candidate ?? -1) > (weeks[best] ?? -1) ? index : best),
    0,
  );
  const shift = properties.autumn_shift_days_per_decade;

  const rows = [
    [`Week of ${weekLabel(week)}`, value === null || value === undefined ? "no data" : fmt(value)],
    [`Busiest week (${weekLabel(peakWeek)})`, fmt(properties.peak ?? 0)],
    ["Years observed", String(properties.years)],
  ];
  // Absent when the station failed the trend thresholds; saying so beats an empty row.
  rows.push([
    "Autumn passage shift",
    shift === null || shift === undefined
      ? "too short a record"
      : `${shift > 0 ? "+" : ""}${shift.toFixed(2)} days/decade over ${properties.trend_years} yr`,
  ]);

  return `
    <strong>${properties.station}</strong>
    <table>${rows.map(([k, v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join("")}</table>
    <p class="caveat">${meta.value_kind.replace(/_/g, " ")} — aerial biomass, not birds.
    A single station's shift is noisy; the pooled estimate is in the Phase 1 report.</p>
  `;
}

function fmt(value: number): string {
  return value >= 1000 ? `${Math.round(value / 1000)}k` : String(Math.round(value));
}
