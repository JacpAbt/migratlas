/**
 * The plate: the world, drawn at the size it will be drawn at.
 *
 * A plate in a claim chapter is a *figure* -- where on Earth this claim is -- and not the map. ADR
 * 0013 puts the interactive map in "The world", so this is deliberately a still rather than a
 * limitation of one.
 *
 * **Everything is generated at the measured pixel size.** `notebook/ink.ts` says why at length and
 * the mock this was designed in was the counter-example, and is worth recording now that it is
 * deleted: it drew into a 1000-unit viewBox scaled down to whatever the plate happened to be, so a
 * 1.5px pen rendered at 0.6px on a laptop and 1.7px on a monitor, and the hachure gaps moved with
 * the window. Sizing the *labels* in rendered pixels fixed the labels and left the strokes wrong.
 * Here the projection takes the width and returns everything else.
 *
 * **The hand is rough.js, not a second wobble.** `globe/coastline.ts` jitters its geometry because
 * MapLibre draws WebGL and cannot be handed a rough.js path. An SVG plate can, and rough.js already
 * draws every stroke twice with controlled divergence -- which is what a pen does. Applying the
 * globe's jitter here as well would be two hands on one line.
 *
 * **The geometry is the basemap the globe uses**, fetched from the same URL rather than baked into a
 * second asset. One copy cannot drift from the other.
 */

import { HAND, mark, pen, seedOf } from "../notebook/ink";

/** A coastline ring, resampled, in degrees. */
export interface Ring {
  /** Projected area in square degrees, for deciding what gets a hachure fill. */
  area: number;
  points: [number, number][];
}

/**
 * Latitude range the plate covers.
 *
 * Not the full sphere: Mercator sends the poles to infinity, and the land below 58°S is Antarctica,
 * which no claim in this ledger is about and which would cost a third of the plate's height.
 */
export const TOP_LAT = 80;
export const BOTTOM_LAT = -58;

/** Points per ring after resampling. rough.js roughens every segment it is given, and a coast
    sampled at Natural Earth's fjord density costs a great deal and looks no more drawn. */
const SAMPLES = 56;

/** Rings smaller than this are dropped: at plate size they are one pixel of noise. */
const MIN_AREA = 1.5;

/** How many of the largest rings get a hachure fill rather than a stroke alone. */
const HACHURED = 8;

interface Geometry {
  type: string;
  coordinates: number[][][] | number[][][][];
}

function ringsOf(geometry: Geometry): number[][][] {
  if (geometry.type === "Polygon") return geometry.coordinates as number[][][];
  if (geometry.type === "MultiPolygon") return (geometry.coordinates as number[][][][]).flat();
  return [];
}

/** Shoelace, on the ring's own degrees. Only ever compared against other rings. */
function areaOf(points: [number, number][]): number {
  let total = 0;
  for (let index = 0; index < points.length; index += 1) {
    const [x1, y1] = points[index]!;
    const [x2, y2] = points[(index + 1) % points.length]!;
    total += x1 * y2 - x2 * y1;
  }
  return Math.abs(total) / 2;
}

/**
 * Resample a ring to `SAMPLES` points, evenly by arc length.
 *
 * By length rather than by index, because Natural Earth samples a fjord far more densely than a
 * desert coast: taking every nth vertex spends the whole budget on Norway.
 */
export function resample(ring: number[][], samples = SAMPLES): [number, number][] {
  const spans = [0];
  for (let index = 1; index < ring.length; index += 1) {
    const [ax, ay] = ring[index - 1] as [number, number];
    const [bx, by] = ring[index] as [number, number];
    spans.push(spans[index - 1]! + Math.hypot(bx - ax, by - ay));
  }
  const total = spans[spans.length - 1] || 1;

  const out: [number, number][] = [];
  for (let step = 0; step < samples; step += 1) {
    const target = (step / samples) * total;
    let index = 1;
    while (index < spans.length - 1 && spans[index]! < target) index += 1;
    const from = spans[index - 1]!;
    const to = spans[index]!;
    const along = to > from ? (target - from) / (to - from) : 0;
    const [ax, ay] = ring[index - 1] as [number, number];
    const [bx, by] = ring[index] as [number, number];
    out.push([ax + (bx - ax) * along, ay + (by - ay) * along]);
  }
  return out;
}

/** Every coastline ring in the basemap, resampled and sorted largest first. */
export function ringsFrom(land: { features: { geometry: Geometry }[] }): Ring[] {
  const rings: Ring[] = [];
  for (const feature of land.features) {
    for (const ring of ringsOf(feature.geometry)) {
      if (ring.length < 4) continue;
      const points = resample(ring);
      const area = areaOf(points);
      if (area < MIN_AREA) continue;
      rings.push({ area, points });
    }
  }
  return rings.sort((first, second) => second.area - first.area);
}

let cached: Promise<Ring[]> | undefined;

/** The basemap's land, fetched once per session and shared with whoever asks next. */
export function loadLand(base: string): Promise<Ring[]> {
  cached ??= fetch(`${base}basemap/land.geojson`)
    .then((response) => {
      if (!response.ok) throw new Error(`land.geojson: ${response.status}`);
      return response.json() as Promise<{ features: { geometry: Geometry }[] }>;
    })
    .then(ringsFrom);
  return cached;
}

const mercator = (lat: number) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));

/**
 * Width over height the plate must have, at any size.
 *
 * **Mercator keeps its shapes only if both axes share one scale**, and this is the one number that
 * says so. Longitude spans 2π radians across the width; latitude spans `mercator(TOP) -
 * mercator(BOTTOM)` of the same units down the height. Give the projection a box of any other shape
 * and it is no longer Mercator -- it is Mercator times a constant in one axis, which is a
 * projection nobody chose and which has no name.
 *
 * This was learned the expensive way. `projection` used to take a width *and* a height and scale
 * each axis into whatever it was handed, and `.plate__sheet` was `flex: 1` -- so every plate took
 * the leftover height of its page column. Measured on the shipped book: 531x630 and 472x513 against
 * the 0.587 this ratio demands, a **vertical stretch of ×1.9 to ×2.1** on every plate in the
 * ledger, which is why North America looked tall and Greenland looked wrong. The height parameter
 * is gone rather than corrected: a stretched plate is now unspeakable rather than merely wrong.
 */
export const PLATE_RATIO = (2 * Math.PI) / (mercator(TOP_LAT) - mercator(BOTTOM_LAT));

/**
 * Web Mercator into a box of the one shape it can have. Returned as functions so nothing else needs
 * the algebra, and the height is returned rather than accepted.
 */
export function projection(width: number) {
  const height = width / PLATE_RATIO;
  const top = mercator(TOP_LAT);
  const bottom = mercator(BOTTOM_LAT);
  return {
    height,
    x: (lon: number) => ((lon + 180) / 360) * width,
    y: (lat: number) =>
      ((top - mercator(Math.max(BOTTOM_LAT, Math.min(TOP_LAT, lat)))) / (top - bottom)) * height,
  };
}

export interface PlateInk {
  ink: string;
  pencil: string;
  faint: string;
  accent: string;
}

/**
 * Draw the plate. Nothing is scaled afterwards, so a stroke width here is a stroke width on screen.
 *
 * `at` marks the claim's own place, from the camera `story.ts` already records for it -- reusing a
 * position that is guarded by a test rather than inventing an extent per claim.
 */
export function drawPlate(
  host: SVGSVGElement,
  rings: Ring[],
  width: number,
  colours: PlateInk,
  at: { center: [number, number]; label: string } | null,
): void {
  host.replaceChildren();
  if (width <= 0) return;
  const { height, x, y } = projection(width);
  const rc = pen(host);

  // Graticule first, beneath the land: a reference line belongs under the thing it refers to, which
  // is the order `globe/graticule.ts` already keeps.
  const grid = document.createElementNS("http://www.w3.org/2000/svg", "g");
  for (let lon = -150; lon < 180; lon += 30) {
    grid.append(
      rc.line(x(lon), 0, x(lon), height, {
        stroke: colours.faint,
        strokeWidth: 1,
        roughness: 1.5,
        seed: seedOf(`meridian-${lon}`),
      }),
    );
  }
  for (const lat of [60, 30, 0, -30]) {
    grid.append(
      rc.line(0, y(lat), width, y(lat), {
        stroke: colours.faint,
        strokeWidth: 1,
        roughness: 1.5,
        seed: seedOf(`parallel-${lat}`),
      }),
    );
  }
  mark(host, "graticule", grid as SVGGElement);

  const land = document.createElementNS("http://www.w3.org/2000/svg", "g");
  rings.forEach((ring, index) => {
    const path = ring.points
      .map((point, step) => `${step === 0 ? "M" : "L"}${x(point[0]).toFixed(1)} ${y(point[1]).toFixed(1)}`)
      .join("");
    land.append(
      rc.path(`${path}Z`, {
        ...HAND,
        stroke: colours.ink,
        strokeWidth: 1.3,
        seed: seedOf(`ring-${index}`),
        ...(index < HACHURED
          ? {
              fill: colours.pencil,
              fillStyle: "hachure",
              hachureAngle: -41,
              hachureGap: 7,
              fillWeight: 0.7,
            }
          : {}),
      }),
    );
  });
  mark(host, "land", land as SVGGElement);

  if (!at) return;
  const here = document.createElementNS("http://www.w3.org/2000/svg", "g");
  const [lon, lat] = at.center;
  here.append(
    rc.circle(x(lon), y(lat), Math.max(26, width * 0.05), {
      ...HAND,
      stroke: colours.accent,
      strokeWidth: 2,
      roughness: 2.2,
      seed: seedOf(at.label),
    }),
  );
  mark(host, "here", here as SVGGElement);
}
