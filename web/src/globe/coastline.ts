/**
 * The coastline, drawn twice by hand at globe zoom and handed back to the survey above it.
 *
 * This is the piece of the drawn globe with a correctness cost, and the whole design is about
 * bounding it. A hatch that tiles wrongly is ugly; a graticule half a degree out is a reference line
 * nobody reads. A *coastline* in the wrong place is a wrong statement about where the land is, on a
 * page whose entire argument is about where animals were -- so the deviation is stated, bounded, and
 * withdrawn the moment anyone could measure against it.
 *
 * Three rules do that.
 *
 * **It is a second layer, not a replacement.** The true coastline stays in the style. The drawn pass
 * fades out and the true one fades in across the same two zoom levels, so the honest geometry is
 * what is on screen from zoom 2.6 up. Nothing is deleted, and a failure to build this leaves the
 * accurate coast at full strength -- which is why the ramp is applied here, on success, rather than
 * written into the style up front.
 *
 * **The excursion is smaller than the pixel it is drawn at.** `JITTER` is 0.55 degrees, and at the
 * zooms where this layer is visible one degree is about three pixels -- so the drawn shore sits
 * within about two pixels of the true one, which is what a pen does to a line anyway. By zoom 2.6
 * the same 0.55 degrees would be six pixels, and by then it is gone.
 *
 * **Small islands are not jittered at all.** A ring half a degree across displaced by half a degree
 * is not a sketch of an island, it is a different island. Anything under `MIN_EXTENT` is drawn from
 * its own true geometry, once.
 */

/** Largest excursion off the true shore, in degrees. Exported because it is the bound a test
    holds this to, and a bound nothing checks is a hope. */
export const JITTER = 0.55;

/** A ring narrower than this in both axes keeps its real outline, undrawn and unjittered. */
export const MIN_EXTENT = 6;

/** Where the drawn pass has fully given way to the surveyed one. */
export const HANDOVER: [number, number] = [1.8, 2.6];

/**
 * Offset along a closed ring, at position `t` (0 to 1).
 *
 * Whole cycles only, so the offset at the end of a ring is the offset at its start: a coastline is a
 * loop, and a jitter that does not close leaves every island cut open at the vertex the data happens
 * to begin on.
 */
function wander(t: number, seed: number, amplitude: number): number {
  const phase = (index: number) => (seed * (index + 1) * 2.399963) % (Math.PI * 2);
  return (
    amplitude *
    (0.62 * Math.sin(2 * Math.PI * t + phase(0)) +
      0.26 * Math.sin(4 * Math.PI * t + phase(1)) +
      0.12 * Math.sin(9 * Math.PI * t + phase(2)))
  );
}

function extent(ring: number[][]): [number, number] {
  const lons = ring.map(([lon]) => lon!);
  const lats = ring.map(([, lat]) => lat!);
  return [Math.max(...lons) - Math.min(...lons), Math.max(...lats) - Math.min(...lats)];
}

/** One pass of the pen over a ring. Two of these with different seeds is what a drawn line is. */
function pass(ring: number[][], seed: number, amplitude: number): [number, number][] {
  // Cumulative length rather than vertex index, because Natural Earth samples a fjord far more
  // densely than a desert coast: parameterising by index would put all the wobble in the fjords.
  const spans: number[] = [0];
  for (let index = 1; index < ring.length; index += 1) {
    const [ax, ay] = ring[index - 1] as [number, number];
    const [bx, by] = ring[index] as [number, number];
    spans.push(spans[index - 1]! + Math.hypot(bx - ax, by - ay));
  }
  const total = spans[spans.length - 1] || 1;

  return ring.map(([lon, lat], index) => {
    const t = spans[index]! / total;
    return [
      lon! + wander(t, seed, amplitude),
      // Clamped, so a shore near the pole cannot be pushed over it.
      Math.max(-89.9, Math.min(89.9, lat! + wander(t, seed + 31, amplitude))),
    ];
  });
}

/**
 * Every coastline in the source, as drawn strokes.
 *
 * Two passes per large ring, one per small one, all as LineStrings: the fill underneath is still the
 * true polygon, so this layer only ever draws the edge. A drawn stroke that sits a pixel or two off
 * the shape it outlines is what a sketch looks like, and here it is also what keeps the *filled*
 * land exactly where the survey put it.
 */
export function drawnCoast(land: GeoJSON.FeatureCollection): GeoJSON.FeatureCollection {
  const features: GeoJSON.Feature[] = [];
  let seed = 1;

  const rings = (geometry: GeoJSON.Geometry): number[][][] => {
    if (geometry.type === "Polygon") return geometry.coordinates;
    if (geometry.type === "MultiPolygon") return geometry.coordinates.flat();
    return [];
  };

  for (const feature of land.features) {
    for (const ring of rings(feature.geometry)) {
      if (ring.length < 4) continue;
      const [width, height] = extent(ring);
      const small = width < MIN_EXTENT && height < MIN_EXTENT;
      const passes = small ? 1 : 2;
      for (let index = 0; index < passes; index += 1) {
        features.push({
          type: "Feature",
          properties: {},
          geometry: {
            type: "LineString",
            // The second pass diverges a little less than the first, which is what going over a line
            // actually does: a hand corrects towards what it meant the first time.
            coordinates: pass(ring, seed + index * 97, small ? 0 : JITTER * (index ? 0.7 : 1)),
          },
        });
      }
      seed += 1;
    }
  }

  return { type: "FeatureCollection", features };
}

export const DRAWN_COAST = "coast-drawn";

/** Fades out exactly as the surveyed coastline fades in. */
export function drawnOpacity(): unknown[] {
  return ["interpolate", ["linear"], ["zoom"], 0, 0.9, HANDOVER[0], 0.9, HANDOVER[1], 0];
}

/** The other half of the same crossfade. */
export function trueOpacity(): unknown[] {
  return ["interpolate", ["linear"], ["zoom"], 0, 0, HANDOVER[0], 0, HANDOVER[1], 1];
}
