/**
 * What the atlas draws from: the published layers, the world's outline, each plate's map and the
 * words, fetched and put into the shapes the drawing wants. Nothing here decides how a thing looks.
 */

import type { Box } from "./geo";
import type { Line } from "./ink";

export const WEEKS = 52;

interface Feature {
  geometry: { type: string; coordinates: unknown } | null;
  properties: Record<string, unknown> | null;
}
interface Collection {
  features: Feature[];
}

async function json<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url}: ${response.status}`);
  return (await response.json()) as T;
}

/** Every ring or line of a collection's features, polygons and lines flattened alike. */
export function lines(collection: Collection): Line[] {
  const out: Line[] = [];
  for (const feature of collection.features) {
    const geometry = feature.geometry;
    if (!geometry) continue;
    const c = geometry.coordinates as never;
    const parts: Line[] =
      geometry.type === "Polygon"
        ? (c as Line[])
        : geometry.type === "MultiPolygon"
          ? (c as Line[][]).flat()
          : geometry.type === "LineString"
            ? [c as Line]
            : geometry.type === "MultiLineString"
              ? (c as Line[])
              : [];
    out.push(...parts);
  }
  return out;
}

// --- The world's outline, and a plate's map -----------------------------------------------------

export interface WorldMap {
  land: Line[];
  borders: Line[];
}

export async function loadWorld(base: string): Promise<WorldMap> {
  const [land, borders] = await Promise.all([
    json<Collection>(`${base}basemap/land.geojson`),
    json<Collection>(`${base}basemap/borders.geojson`),
  ]);
  return { land: lines(land), borders: lines(borders) };
}

export interface PlateMap {
  box: Box;
  land: Line[];
  rivers: Line[];
  creeks: Line[];
  lakes: Line[];
  /** A labelled river's longest stretch, which carries its name. */
  named: { name: string; line: Line }[];
}

export async function loadPlateMap(base: string, path: string): Promise<PlateMap> {
  const document = await json<Collection & { box: [number, number, number, number] }>(`${base}${path}`);
  const [west, east, south, north] = document.box;
  const by = (role: string, test: (p: Record<string, unknown>) => boolean = () => true): Collection => ({
    features: document.features.filter((f) => f.properties?.["role"] === role && test(f.properties)),
  });
  const longest = new Map<string, Line>();
  for (const feature of by("river", (p) => p["major"] === true).features) {
    const name = String(feature.properties?.["name"] ?? "");
    const line = feature.geometry?.coordinates as Line;
    if (name && (!longest.has(name) || line.length > (longest.get(name)?.length ?? 0))) longest.set(name, line);
  }
  return {
    box: { west, east, south, north },
    land: lines(by("land")),
    rivers: lines(by("river", (p) => p["name"] === undefined || p["major"] === true)),
    creeks: lines(by("river", (p) => p["name"] !== undefined && p["major"] !== true)),
    lakes: lines(by("lake")),
    named: [...longest].map(([name, line]) => ({ name, line })),
  };
}

// --- The radars ----------------------------------------------------------------------------------

/** One radar: where it is, and per week its traffic and the eastward and northward flow, km/h. */
export interface Station {
  lon: number;
  lat: number;
  w: Float32Array;
  u: Float32Array;
  v: Float32Array;
}

export interface Radar {
  stations: Station[];
  /** The 95th percentile of weekly traffic: a station at it draws at full strength. */
  ref: number;
}

/**
 * `w<k>` is a week's median nightly traffic, `dw<k>` the bearing the mass moved toward (degrees
 * clockwise from north) and `sw<k>` its ground speed in m/s; a missing week omits its keys
 * (`tiles/station_series.py`), so "no data" stays NaN rather than becoming no passage.
 */
export async function loadRadar(base: string): Promise<Radar> {
  const collection = await json<Collection>(`${base}layers/aerial-passage.geojson`);
  const stations: Station[] = [];
  for (const feature of collection.features) {
    const p = feature.properties ?? {};
    const [lon, lat] = feature.geometry?.coordinates as [number, number];
    const w = new Float32Array(WEEKS).fill(Number.NaN);
    const u = new Float32Array(WEEKS).fill(Number.NaN);
    const v = new Float32Array(WEEKS).fill(Number.NaN);
    for (let k = 0; k < WEEKS; k++) {
      const traffic = p[`w${k}`];
      const bearing = p[`dw${k}`];
      const speed = p[`sw${k}`];
      if (typeof traffic === "number") w[k] = traffic;
      if (typeof bearing === "number" && typeof speed === "number") {
        u[k] = speed * 3.6 * Math.sin((bearing * Math.PI) / 180);
        v[k] = speed * 3.6 * Math.cos((bearing * Math.PI) / 180);
      }
    }
    stations.push({ lon, lat, w, u, v });
  }
  const values = stations.flatMap((s) => [...s.w].filter((x) => !Number.isNaN(x))).sort((a, b) => a - b);
  return { stations, ref: values[Math.floor(values.length * 0.95)] ?? 1 };
}

/** A station at fractional week `t`: strength 0..1.5, bearing in radians, ground speed in km/h. */
export function stationAt(s: Station, t: number, ref: number): { a: number; bearing: number; kmh: number } | null {
  const k0 = Math.floor(t) % WEEKS;
  const k1 = (k0 + 1) % WEEKS;
  const f = t - Math.floor(t);
  const pick = (a: number, b: number): number =>
    Number.isNaN(a) ? (Number.isNaN(b) ? Number.NaN : b * f) : Number.isNaN(b) ? a * (1 - f) : a + (b - a) * f;
  const mix = (a: number, b: number): number => (Number.isNaN(a) ? b : Number.isNaN(b) ? a : a + (b - a) * f);
  const w = pick(s.w[k0] ?? Number.NaN, s.w[k1] ?? Number.NaN);
  const u = mix(s.u[k0] ?? Number.NaN, s.u[k1] ?? Number.NaN);
  const v = mix(s.v[k0] ?? Number.NaN, s.v[k1] ?? Number.NaN);
  if (Number.isNaN(w) || Number.isNaN(u) || Number.isNaN(v)) return null;
  return { a: Math.min(1.5, Math.sqrt(Math.max(0, w) / ref)), bearing: Math.atan2(u, v), kmh: Math.hypot(u, v) };
}

// --- The foxes, the herds, the ice ---------------------------------------------------------------

/** Each journey's daily median positions, in order. The tracks carry no dates. */
export async function loadJourneys(base: string): Promise<Line[]> {
  return lines(await json<Collection>(`${base}layers/bylot-journeys.geojson`));
}

/** One 0.01-degree cell of a herd, and its collared animals in each typical week. */
export interface HerdCell {
  lon: number;
  lat: number;
  w: Float32Array;
  seed: number;
}

export async function loadHerd(base: string, layer: string): Promise<HerdCell[]> {
  const collection = await json<Collection>(`${base}layers/${layer}.geojson`);
  return collection.features.map((feature, index) => {
    const w = new Float32Array(WEEKS);
    for (let k = 0; k < WEEKS; k++) {
      const value = feature.properties?.[`w${k}`];
      w[k] = typeof value === "number" ? value : 0;
    }
    const [lon, lat] = feature.geometry?.coordinates as [number, number];
    return { lon, lat, w, seed: index * 31 + 7 };
  });
}

/** The ice's median edge by hemisphere and month (1-12). */
export type IceEdges = Record<string, Record<number, Line[]>>;

export async function loadIce(base: string): Promise<IceEdges> {
  const collection = await json<Collection>(`${base}layers/sea-ice-edge.geojson`);
  const edges: IceEdges = {};
  for (const feature of collection.features) {
    const hemisphere = String(feature.properties?.["hemisphere"]);
    const month = Number(feature.properties?.["month"]);
    (edges[hemisphere] ??= {})[month] = lines({ features: [feature] });
  }
  return edges;
}

// --- The words -----------------------------------------------------------------------------------

/** Somewhere the camera can go: a system's plate, or the plate of a still map of one region. */
export interface Place {
  name: string;
  frame: [number, number, number, number];
  centre: [number, number];
  map: string;
  /** Whose map the plate is drawn on. */
  credit: string;
}

export interface PlateWords extends Place {
  layer: string;
  button: string;
  title: string;
  callout: string;
  under: string;
  lead: string;
  caption: string;
  clock: "year" | "journey";
}

/** A map with no time in it: its words, where its cells are, and its plate if it is one region's. */
export interface StillWords {
  name: string;
  button: string;
  title: string;
  lead: string;
  caption: string;
  /** What a dot counts, beside the key's sample dots. Empty where the key is categories. */
  unit: string;
  key: { value: string; means: string }[];
  data: string;
  /** The terms its data was published under. */
  credit: string;
  plate: Place | null;
}

/** `web/public/atlas.json`, written by `reports/atlas.py`. */
export interface Words {
  world: { title: string; lead: string; caption: string; still: string; readout: string };
  plates: PlateWords[];
  stills: StillWords[];
  readout: {
    air: {
      little: string;
      fair: string;
      great: string;
      heading: string;
      every_way: string;
      compass: string[];
    };
    journey: { day: string; each: string; of: string; going: string };
    herd: { in: string; cells: string; reached: string };
  };
  controls: Record<
    "show" | "world" | "pause" | "play" | "slow" | "normal" | "fast" | "clock" | "journey" | "stills",
    string
  >;
}

export const loadWords = (base: string): Promise<Words> => json<Words>(`${base}atlas.json`);

/** A place's frame as a box. */
export const frameOf = (place: Place): Box => {
  const [west, east, south, north] = place.frame;
  return { west, east, south, north };
};

// --- The still maps ------------------------------------------------------------------------------

/** A still map's cells: one value each for the map's whole period, at the cell's centre. */
export interface Cells {
  /** Degrees on a side. */
  size: number;
  lon: Float32Array;
  lat: Float32Array;
  v: Float32Array;
  /** For an assessment, what each value names: `v` indexes this. */
  categories: string[] | null;
  /** The map's own statement, for the one still map the layer manifest does not describe. */
  note: string | null;
}

interface Grid {
  cell_size_deg: number;
  x: number[];
  y: number[];
  v: number[];
}

/**
 * Cell centres back from grid indices, as `tiles/` encoded them. Three parallel arrays mean
 * something only together, so a length that disagrees is refused rather than drawn: a truncated one
 * would pair values with the wrong cells and look like a map.
 */
export function decode(grid: Grid): Pick<Cells, "size" | "lon" | "lat" | "v"> {
  const { x, y, v, cell_size_deg: size } = grid;
  if (x.length !== v.length || y.length !== v.length) {
    throw new Error(`grid arrays disagree: x=${x.length} y=${y.length} v=${v.length}`);
  }
  const lon = new Float32Array(v.length);
  const lat = new Float32Array(v.length);
  for (let i = 0; i < v.length; i++) {
    lon[i] = (x[i]! + 0.5) * size - 180;
    lat[i] = (y[i]! + 0.5) * size - 90;
  }
  return { size, lon, lat, v: Float32Array.from(v) };
}

/** A still map's cells, fetched when it is switched on and not before. */
export async function loadCells(base: string, still: StillWords): Promise<Cells> {
  // The assessment ships as a report with its grid inside; a layer ships as the grid alone.
  const document = await json<Grid & { grid?: Grid & { categories: string[] }; caveat?: string }>(
    `${base}${still.data}`,
  );
  return {
    ...decode(document.grid ?? document),
    categories: document.grid?.categories ?? null,
    note: document.caveat ?? null,
  };
}

// --- Everything at once, once ----------------------------------------------------------------------

/** What a stage is made from, before any of it moves. */
export interface Cast {
  words: Words;
  world: WorldMap;
  radar: Radar;
  journeys: Line[];
  herds: { svalbard: HerdCell[]; "ya-ha-tinda": HerdCell[] };
  ice: IceEdges;
  /** Each published layer's own statement, by layer name, for the caption slip. */
  notes: Record<string, string>;
}

const casts = new Map<string, Promise<Cast>>();

/**
 * Everything the atlas opens with, fetched once for the session and shared by whoever asks first.
 *
 * The atlas mounts with its spread, and a turn is what mounts it, so data fetched on mount arrived
 * under a page already turning: on a slow connection both halves of the spread were paper for as
 * long as 400 KB took. `Reader` asks for this when the chapter is near, and the atlas asks again
 * and is handed the same promise. Raw data and not stages, because each stage owns its moving
 * parts. A failed fetch is forgotten, so the next ask tries again rather than failing forever.
 */
export function castOf(base: string): Promise<Cast> {
  let pending = casts.get(base);
  if (!pending) {
    pending = Promise.all([
      loadWords(base),
      loadWorld(base),
      loadRadar(base),
      loadJourneys(base),
      loadHerd(base, "svalbard-herd"),
      loadHerd(base, "yahatinda-herd"),
      loadIce(base),
      json<{ name: string; description: string }[]>(`${base}layers/manifest.json`),
    ]).then(([words, world, radar, journeys, svalbard, yaHaTinda, ice, manifest]) => ({
      words,
      world,
      radar,
      journeys,
      herds: { svalbard, "ya-ha-tinda": yaHaTinda },
      ice,
      notes: Object.fromEntries(manifest.map((layer) => [layer.name, layer.description])),
    }));
    pending.catch(() => casts.delete(base));
    casts.set(base, pending);
  }
  return pending;
}
