/**
 * The graticule, ruled by hand.
 *
 * A paper globe has meridians and parallels on it, drawn under the coastlines, and their being
 * slightly out is part of what says a person drew it. Generated rather than fetched: 17 lines of
 * geometry cost nothing to compute and would cost a request to download.
 *
 * The wobble is bounded and the layer fades out by zoom 3.5, and those two things are the same
 * decision. A graticule is a coordinate claim -- a line that says "this is 30 degrees west" -- so a
 * drawn one is only honest while nobody can read a position off it. At globe zoom the amplitude here
 * is under a pixel of arc; by the zoom where half a degree would be a visible error, the line is
 * gone and the data layers are what is left. The coastlines will need the same treatment for the
 * same reason, and there it matters more, because a shoreline in the wrong place is a wrong claim
 * about where an animal was.
 */

import type { LayerSpecification, SourceSpecification } from "maplibre-gl";

import { palette } from "./flavor";

/** Degrees between lines, both ways. Twelve meridians and five parallels reads as a globe; a line
    every ten degrees reads as graph paper wrapped round a ball. */
const EVERY = 30;

/** Sampled this finely so the projection curves the line rather than chording it. */
const STEP = 2;

/** Largest excursion off true, in degrees. */
const WOBBLE = 0.55;

/** Two sines at whole-cycle frequencies, so a meridian closes on itself at the pole it returns to. */
function wander(t: number, seed: number): number {
  const phase = (index: number) => (seed * (index + 1) * 2.399963) % (Math.PI * 2);
  return (
    WOBBLE * 0.75 * Math.sin(2 * Math.PI * t + phase(0)) +
    WOBBLE * 0.25 * Math.sin(6 * Math.PI * t + phase(1))
  );
}

function lines(): GeoJSON.FeatureCollection {
  const features: GeoJSON.Feature[] = [];
  let seed = 1;

  const add = (coordinates: [number, number][]) => {
    features.push({
      type: "Feature",
      properties: {},
      geometry: { type: "LineString", coordinates },
    });
  };

  for (let lon = -180; lon < 180; lon += EVERY) {
    const points: [number, number][] = [];
    // Stopping at 88 rather than 90: every meridian meets every other one at the pole, and a dozen
    // wobbled lines converging on one point is a knot rather than a globe.
    for (let lat = -88; lat <= 88; lat += STEP) {
      const t = (lat + 88) / 176;
      points.push([lon + wander(t, seed), lat]);
    }
    add(points);
    seed += 1;
  }

  for (let lat = -60; lat <= 60; lat += EVERY) {
    const points: [number, number][] = [];
    for (let lon = -180; lon <= 180; lon += STEP) {
      const t = (lon + 180) / 360;
      // Clamped, so a wobbled parallel near the top of the range cannot cross the pole.
      points.push([lon, Math.max(-89, Math.min(89, lat + wander(t, seed)))]);
    }
    add(points);
    seed += 1;
  }

  return { type: "FeatureCollection", features };
}

export const GRATICULE = "graticule";

export function graticuleSource(): SourceSpecification {
  return { type: "geojson", data: lines() };
}

/**
 * Faint, and gone before it could mislead.
 *
 * Interpolated on zoom rather than switched, because a line that vanishes between one frame and the
 * next reads as a rendering fault. Drawn under the coastlines, which is where a ruled grid goes on
 * paper.
 */
export function graticuleLayer(): LayerSpecification {
  return {
    id: GRATICULE,
    type: "line",
    source: GRATICULE,
    paint: {
      "line-color": palette().coast,
      "line-width": 0.6,
      "line-opacity": ["interpolate", ["linear"], ["zoom"], 0, 0.34, 2, 0.34, 3.5, 0],
    },
  };
}
