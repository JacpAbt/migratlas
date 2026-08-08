/** One entry of the build-layers manifest. */
export interface LayerMeta {
  name: string;
  title: string;
  description: string;
  realm: string;
  evidence_type: string;
  /** Which builder produced it, and so which renderer consumes it. */
  kind: "surface" | "series" | "tracks";
  /** Wire shape. A grid carries index arrays; geojson carries one feature per cell. */
  format: "grid" | "geojson";
  value_kind: string;
  /**
   * The sentence a feature popup prints beside its numbers. Authored in `reports`-side Python
   * like all frontend prose; absent on layers that have no popup.
   */
  popup_caveat?: string;
  /**
   * How the values map onto a ramp. Declared by the builder, never guessed here.
   *
   * `sequential` is a count and is painted on log10 against one ramp. `diverging` is a signed
   * change: the same treatment would map every negative cell onto the colour of the smallest
   * positive one and lose the sign, which for a change layer is the entire result.
   */
  scale: "sequential" | "diverging";
  attribution: string;
  licence: string;
  landing_page: string;
  caveats: string;
}

/** The sidecar the ethics gate writes beside every published layer. */
export interface LayerTerms {
  "dwc:dataGeneralizations": string;
  sensitivity: string;
}

export interface LoadedLayer {
  meta: LayerMeta;
  terms: LayerTerms;
  /** Features handed to MapLibre. For a grid, the cells that survived decoding. */
  cells: number;
  /** Mean position of the layer's features -- where to point a camera to see it. */
  center: [number, number];
  /**
   * The zoom that camera needs, when the default globe zoom cannot show the layer at all -- a
   * compact layer's cells sit below the tiler's hand-over and are legitimately absent above it.
   */
  zoom?: number;
  /**
   * Whether it is drawn on arrival, defaulting to true.
   *
   * The *declared initial* value, and deliberately never written to afterwards -- `setVisible` does
   * not update it. Two things read it and both need it to mean the same thing: the tools panel
   * initialises its checkboxes from it, and `Shell.svelte` builds explore mode's layer list from it.
   * Having `setVisible` write back here would make the second of those a function of the first, and
   * the view effect re-applies visibility whenever the view changes -- which is a loop.
   *
   * The invariant that matters is the one between the panel and the map, and it is a test rather
   * than a comment: `globe.spec.ts` asserts every layer's MapLibre visibility agrees with its
   * checkbox, on first load and after a toggle. It exists because this field was read as the truth
   * in one place and overridden in another, and nothing noticed for a release.
   */
  visible?: boolean;
  setVisible: (visible: boolean) => void;
  /** Called when the clock crosses into a new week. Only time-indexed layers implement it. */
  showWeek?: (week: number) => void;
  /**
   * Recolour for the surface now in force.
   *
   * Optional because not every layer has a colour of its own to change, and because a layer that
   * forgets to implement it should render in the wrong palette rather than fail to render.
   */
  repaint?: () => void;
}

export async function fetchLayer<T>(
  baseUrl: string,
  name: string,
  extension = "geojson",
): Promise<[T, LayerTerms]> {
  const [data, terms] = await Promise.all([
    fetch(`${baseUrl}layers/${name}.${extension}`).then((r) => {
      if (!r.ok) throw new Error(`${name}: ${r.status}`);
      return r.json() as Promise<T>;
    }),
    fetch(`${baseUrl}layers/${name}.meta.json`).then((r) => {
      if (!r.ok) throw new Error(`${name} terms: ${r.status}`);
      return r.json() as Promise<LayerTerms>;
    }),
  ]);
  return [data, terms];
}

export async function loadManifest(baseUrl: string): Promise<LayerMeta[]> {
  const response = await fetch(`${baseUrl}layers/manifest.json`);
  if (!response.ok) return [];
  return (await response.json()) as LayerMeta[];
}

/**
 * A gridded surface as published: parallel index arrays rather than one feature per cell.
 *
 * The exporter measured a compact GeoJSON point feature at ~101 bytes carrying ~20 bytes of
 * information, so the one-degree global surface is 2,909 KiB as features and 331 KiB as a grid.
 * Expanding it here costs one pass over the arrays.
 */
export interface GridPayload {
  format: "grid";
  cell_size_deg: number;
  value_kind: string;
  x: number[];
  y: number[];
  v: number[];
}

/** Rebuild cell centres from grid indices. Inverse of the exporter's encoding, exactly. */
export function gridToFeatures(grid: GridPayload): GeoJSON.FeatureCollection {
  const { x, y, v, cell_size_deg: size } = grid;
  // Three parallel arrays are only meaningful together; a truncated one would silently pair
  // the wrong value with the wrong cell.
  if (x.length !== v.length || y.length !== v.length) {
    throw new Error(`grid arrays disagree: x=${x.length} y=${y.length} v=${v.length}`);
  }

  const features: GeoJSON.Feature[] = [];
  for (let index = 0; index < v.length; index++) {
    const [xi, yi, value] = [x[index], y[index], v[index]];
    if (xi === undefined || yi === undefined || value === undefined) continue;
    features.push({
      type: "Feature",
      geometry: {
        type: "Point",
        coordinates: [(xi + 0.5) * size - 180, (yi + 0.5) * size - 90],
      },
      properties: { value },
    });
  }
  return { type: "FeatureCollection", features };
}

/**
 * Mean position of a collection's points.
 *
 * A mean rather than a bounding-box centre: a layer with one far-flung outlier would otherwise
 * frame mostly empty ocean. Nothing here needs a true centroid.
 */
export function meanPosition(collection: GeoJSON.FeatureCollection): [number, number] {
  let lon = 0;
  let lat = 0;
  let count = 0;
  for (const feature of collection.features) {
    if (feature.geometry.type !== "Point") continue;
    const [x, y] = feature.geometry.coordinates;
    if (x === undefined || y === undefined) continue;
    lon += x;
    lat += y;
    count++;
  }
  return count === 0 ? [0, 0] : [lon / count, lat / count];
}

/** Attribution MapLibre shows whenever the layer is visible, terms included. */
export function attributionFor(meta: LayerMeta, terms: LayerTerms): string {
  return (
    `<a href="${meta.landing_page}">${meta.title}</a> (${meta.licence}) — ` +
    terms["dwc:dataGeneralizations"]
  );
}
