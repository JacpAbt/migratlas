import type { Feature, Polygon } from "geojson";

/** Where the sun is, in coordinates the globe understands. */
export interface SolarPosition {
  declinationDeg: number;
  /** Longitude with the sun directly overhead. */
  subsolarLonDeg: number;
}

const DEG = 180 / Math.PI;
const RAD = Math.PI / 180;

/**
 * Solar declination and subsolar longitude via Spencer's Fourier series.
 *
 * Accurate to a few arcminutes, which is far better than a globe at this zoom can
 * show. Includes the equation of time — without it the terminator is visibly out of
 * place by up to a quarter hour of longitude near November.
 */
export function solarPosition(when: Date): SolarPosition {
  const start = Date.UTC(when.getUTCFullYear(), 0, 1);
  const dayOfYear = (when.getTime() - start) / 86_400_000;
  const utcHours =
    when.getUTCHours() + when.getUTCMinutes() / 60 + when.getUTCSeconds() / 3600;

  const g = (2 * Math.PI * (dayOfYear + (utcHours - 12) / 24)) / 365;

  const declination =
    0.006918 -
    0.399912 * Math.cos(g) +
    0.070257 * Math.sin(g) -
    0.006758 * Math.cos(2 * g) +
    0.000907 * Math.sin(2 * g) -
    0.002697 * Math.cos(3 * g) +
    0.00148 * Math.sin(3 * g);

  const eqTimeMinutes =
    229.18 *
    (0.000075 +
      0.001868 * Math.cos(g) -
      0.032077 * Math.sin(g) -
      0.014615 * Math.cos(2 * g) -
      0.040849 * Math.sin(2 * g));

  const subsolarLon = 15 * (12 - utcHours - eqTimeMinutes / 60);

  return {
    declinationDeg: declination * DEG,
    subsolarLonDeg: normaliseLon(subsolarLon),
  };
}

/**
 * The unlit hemisphere as a polygon, for shading the globe's night side.
 *
 * Nocturnal migration is gated by darkness, so this is not decoration — it is the
 * same photoperiod signal that Phase 2a uses as a driver.
 */
export function nightPolygon(when: Date, stepDeg = 2): Feature<Polygon> {
  const { declinationDeg, subsolarLonDeg } = solarPosition(when);

  // At an equinox tan(declination) approaches zero and the terminator degenerates to
  // a pair of meridians. Clamping keeps the polygon finite instead of producing
  // Infinity latitudes.
  const decl = Math.abs(declinationDeg) < 0.01 ? 0.01 * Math.sign(declinationDeg || 1) : declinationDeg;
  const tanDecl = Math.tan(decl * RAD);

  const ring: [number, number][] = [];
  for (let lon = -180; lon <= 180; lon += stepDeg) {
    const hourAngle = (lon - subsolarLonDeg) * RAD;
    const lat = Math.atan(-Math.cos(hourAngle) / tanDecl) * DEG;
    ring.push([lon, clampLat(lat)]);
  }

  // Close toward whichever pole is in darkness: the one opposite the sun's
  // declination.
  const darkPole = declinationDeg >= 0 ? -90 : 90;
  ring.push([180, darkPole], [-180, darkPole]);
  const first = ring[0];
  if (first) ring.push(first);

  return {
    type: "Feature",
    properties: {},
    geometry: { type: "Polygon", coordinates: [ring] },
  };
}

function normaliseLon(lon: number): number {
  return ((((lon + 180) % 360) + 360) % 360) - 180;
}

function clampLat(lat: number): number {
  return Math.max(-89.9, Math.min(89.9, lat));
}
