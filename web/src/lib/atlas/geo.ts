/**
 * The atlas's geometry: two equal-area projections, a view that fits one to the sheet, and a
 * camera that moves between places. ADR 0021 decisions 3 and 4.
 *
 * Every map is equal-area so a reader can compare sizes -- Equal Earth for the world, a Lambert
 * azimuthal equal-area plate centred on each system -- and every move between places is made in one
 * projection, the plates' Lambert with its centre travelling the great circle, so the land turns as
 * a globe does and never changes shape on the way.
 */

export const RAD = Math.PI / 180;
const EARTH_KM = 6371;

/** A longitude-latitude box, in degrees. */
export interface Box {
  west: number;
  east: number;
  south: number;
  north: number;
}

/** A projection onto the unit sphere's plane: longitude and latitude in, plane coordinates out. */
export interface Projection {
  forward(lon: number, lat: number): [number, number];
}

/** Equal Earth (Šavrič, Patterson & Jenny 2018): equal-area, for the whole world. */
export function equalEarth(): Projection {
  const A1 = 1.340264;
  const A2 = -0.081106;
  const A3 = 0.000893;
  const A4 = 0.003796;
  const M = Math.sqrt(3) / 2;
  return {
    forward(lon, lat) {
      const th = Math.asin(M * Math.sin(lat * RAD));
      const t2 = th * th;
      const t6 = t2 * t2 * t2;
      const x = (lon * RAD * Math.cos(th)) / (M * (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2)));
      return [x, th * (A1 + A2 * t2 + t6 * (A3 + A4 * t2))];
    },
  };
}

/**
 * Lambert azimuthal equal-area about a centre, for a plate and for the camera.
 *
 * A point past the horizon folds onto the rim. Seen from far out the projection is a globe's near
 * side, and Lambert would otherwise smear the far side round its edge; the spot that hides the
 * world's change of projection never opens that far, so the rim is not seen either.
 */
export function lambert(lon0: number, lat0: number): Projection {
  const s0 = Math.sin(lat0 * RAD);
  const c0 = Math.cos(lat0 * RAD);
  return {
    forward(lon, lat) {
      const dl = (lon - lon0) * RAD;
      const sp = Math.sin(lat * RAD);
      const cp = Math.cos(lat * RAD);
      const cd = Math.cos(dl);
      const cosc = s0 * sp + c0 * cp * cd;
      const dx = cp * Math.sin(dl);
      const dy = c0 * sp - s0 * cp * cd;
      if (cosc < 0) {
        const r = Math.hypot(dx, dy) || 1;
        return [(dx / r) * Math.SQRT2, (dy / r) * Math.SQRT2];
      }
      const k = Math.sqrt(2 / Math.max(1e-9, 1 + cosc));
      return [k * dx, k * dy];
    },
  };
}

/** A rectangle on the sheet, in CSS pixels. */
export interface Sheet {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** A projection placed on the sheet: scaled, and translated so its origin lands at `tx`, `ty`. */
export class View {
  constructor(
    readonly proj: Projection,
    readonly scale: number,
    readonly tx: number,
    readonly ty: number,
    /** The box this view was fitted to, widened: a fine graticule is drawn inside it only. */
    readonly around: Box | null = null,
  ) {}

  /** The view that frames `box` inside `sheet`, centred. */
  static fit(proj: Projection, box: Box, sheet: Sheet): View {
    let x0 = Infinity;
    let x1 = -Infinity;
    let y0 = Infinity;
    let y1 = -Infinity;
    for (let i = 0; i <= 48; i++) {
      const lon = box.west + ((box.east - box.west) * i) / 48;
      const lat = box.south + ((box.north - box.south) * i) / 48;
      const edge: [number, number][] = [
        [lon, box.south],
        [lon, box.north],
        [box.west, lat],
        [box.east, lat],
      ];
      for (const [a, b] of edge) {
        const [x, y] = proj.forward(a, b);
        x0 = Math.min(x0, x);
        x1 = Math.max(x1, x);
        y0 = Math.min(y0, y);
        y1 = Math.max(y1, y);
      }
    }
    const s = Math.min(sheet.w / (x1 - x0), sheet.h / (y1 - y0));
    const padLon = (box.east - box.west) * 0.6;
    const padLat = (box.north - box.south) * 0.6;
    return new View(
      proj,
      s,
      sheet.x + sheet.w / 2 - (s * (x0 + x1)) / 2,
      sheet.y + sheet.h / 2 + (s * (y0 + y1)) / 2,
      { west: box.west - padLon, east: box.east + padLon, south: box.south - padLat, north: box.north + padLat },
    );
  }

  project(lon: number, lat: number): [number, number] {
    const [x, y] = this.proj.forward(lon, lat);
    return [this.tx + this.scale * x, this.ty - this.scale * y];
  }

  /** Sheet pixels per kilometre at a place, measured north to south. */
  pxPerKm(lon: number, lat: number): number {
    const [ax, ay] = this.project(lon, lat);
    const [bx, by] = this.project(lon, lat + 100 / (EARTH_KM * RAD));
    return Math.hypot(bx - ax, by - ay) / 100;
  }
}

/** Where the camera is: the Lambert centre, its scale, and where that centre sits on the sheet. */
export interface Camera {
  lon: number;
  lat: number;
  s: number;
  tx: number;
  ty: number;
}

export const viewOf = (c: Camera): View => new View(lambert(c.lon, c.lat), c.s, c.tx, c.ty);

export const ease = (f: number): number => (f < 0.5 ? 4 * f * f * f : 1 - (-2 * f + 2) ** 3 / 2);

/** Along the great circle between two places, so the camera crosses the globe the short way. */
export function slerp(a: { lon: number; lat: number }, b: { lon: number; lat: number }, f: number): [number, number] {
  const v = (lon: number, lat: number): [number, number, number] => [
    Math.cos(lat * RAD) * Math.cos(lon * RAD),
    Math.cos(lat * RAD) * Math.sin(lon * RAD),
    Math.sin(lat * RAD),
  ];
  const p = v(a.lon, a.lat);
  const q = v(b.lon, b.lat);
  const d = Math.acos(Math.max(-1, Math.min(1, p[0] * q[0] + p[1] * q[1] + p[2] * q[2])));
  if (d < 1e-6) return [a.lon, a.lat];
  const wa = Math.sin((1 - f) * d) / Math.sin(d);
  const wb = Math.sin(f * d) / Math.sin(d);
  const x = wa * p[0] + wb * q[0];
  const y = wa * p[1] + wb * q[1];
  const z = wa * p[2] + wb * q[2];
  return [Math.atan2(y, x) / RAD, Math.atan2(z, Math.hypot(x, y)) / RAD];
}

/** A camera between two: centre on the great circle, zoom in log scale, easing out by `dip`. */
export function between(a: Camera, b: Camera, f: number, dip = 0): Camera {
  const e = ease(f);
  const [lon, lat] = slerp(a, b, e);
  const s = Math.exp(Math.log(a.s) + (Math.log(b.s) - Math.log(a.s)) * e - dip * 4 * e * (1 - e));
  return { lon, lat, s, tx: a.tx + (b.tx - a.tx) * e, ty: a.ty + (b.ty - a.ty) * e };
}

/** How far a flight between two places has to ease out to hold both on the sheet. */
export function dipFor(a: Camera, b: Camera, sheet: Sheet): number {
  const [lon, lat] = slerp(a, b, 0.5);
  const mid = lambert(lon, lat);
  const [ax, ay] = mid.forward(a.lon, a.lat);
  const [bx, by] = mid.forward(b.lon, b.lat);
  const apex = (0.55 * Math.min(sheet.w, sheet.h * 1.6)) / (Math.hypot(ax - bx, ay - by) || 1e-6);
  return Math.max(0, (Math.log(a.s) + Math.log(b.s)) / 2 - Math.log(apex));
}

/** Move `km` from a place along `bearing` (radians clockwise from north). Small steps only. */
export function step(lon: number, lat: number, bearing: number, km: number): [number, number] {
  const dLat = (km * Math.cos(bearing)) / EARTH_KM / RAD;
  const dLon = (km * Math.sin(bearing)) / (EARTH_KM * Math.cos(lat * RAD)) / RAD;
  return [lon + dLon, lat + dLat];
}
