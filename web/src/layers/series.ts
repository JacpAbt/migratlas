import { Popup, type ExpressionSpecification, type Map as MapLibreMap } from "maplibre-gl";

import { WARM_RAMP } from "../globe/flavor";

import {
  attributionFor,
  fetchLayer,
  meanPosition,
  type LayerMeta,
  type LoadedLayer,
} from "./types";

/**
 * A station feature. Weekly values arrive as scalar `w0`..`w51` properties, present only for
 * weeks that have data.
 */
interface SeriesProperties {
  station: string;
  peak: number | null;
  years: number;
  weeks_present: number;
  autumn_shift_days_per_decade?: number | null;
  trend_years?: number | null;
  [week: `w${number}`]: number | undefined;
}

const WEEKS = 52;
const weekKey = (week: number): string => `w${week}`;

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
  // Peak passage is orders of magnitude above a quiet night, so a linear ramp would leave
  // most of the year as one flat colour.
  const logMax = Math.max(Math.log10(maxValue), 1);
  const week = (w: number): ExpressionSpecification => ["log10", ["max", valueAt(w), 1]];

  return {
    color: [
      "interpolate",
      ["linear"],
      week(atWeek),
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
  const [data, terms] = await fetchLayer<GeoJSON.FeatureCollection>(baseUrl, meta.name);

  const maxValue = data.features.reduce(
    (best, feature) => Math.max(best, Number((feature.properties as SeriesProperties)?.peak ?? 0)),
    1,
  );

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

  let current = -1;
  const showWeek = (week: number): void => {
    if (week === current) return;
    current = week;
    const { color, radius } = paint(maxValue, week);
    map.setFilter(id, hasValueAt(week));
    map.setPaintProperty(id, "circle-color", color);
    map.setPaintProperty(id, "circle-radius", radius);
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
