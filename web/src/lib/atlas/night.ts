/**
 * The night sky over North America: what the weather radars saw, as pen strokes.
 *
 * A stroke is one night's flight of what a radar saw above it (ADR 0021 decision 5): it starts
 * somewhere in the air the radar sampled -- within `FOOTPRINT_KM` of it -- and runs on at the
 * radar's measured heading and ground speed for `NIGHT_HOURS`, which takes `LIFE` seconds on the
 * sheet. More traffic, more strokes. The strokes dry on their own sheet; while the map moves, a dried
 * trail would be left behind in the old frame, so each stroke draws its own tail instead.
 */

import { step, type View } from "./geo";
import { stationAt, WEEKS, type Radar, type Words } from "./data";
import type { Palette } from "./ink";

/** The air a radar profile describes: 100 m bins within 50 km of the station (`docs/PLAN.md`). */
export const FOOTPRINT_KM = 50;
/** One night's flight: an assumption, and the caption says so (`reports/atlas.py`). */
export const NIGHT_HOURS = 8;
const LIFE = 1.8;
/** Strokes a second from a radar at the year's busy level. */
const RATE = 16;
const MOST = 6000;

interface Stroke {
  lon: number;
  lat: number;
  plon: number;
  plat: number;
  age: number;
  life: number;
  bearing: number;
  rate: number;
  heavy: boolean;
}

export class NightSky {
  private strokes: Stroke[] = [];
  private owed: Float32Array;
  private peak = 0;

  constructor(private readonly radar: Radar) {
    this.owed = new Float32Array(radar.stations.length);
    for (let k = 0; k < WEEKS; k++) {
      let sum = 0;
      for (const s of radar.stations) sum += stationAt(s, k, radar.ref)?.a ?? 0;
      this.peak = Math.max(this.peak, sum / radar.stations.length);
    }
  }

  reset(): void {
    this.strokes.length = 0;
  }

  /** Strokes in flight: what the last frame drew. */
  get count(): number {
    return this.strokes.length;
  }

  /** Move every stroke `dt` seconds on and draw the step each took; `comet` draws whole tails. */
  frame(ctx: CanvasRenderingContext2D, dt: number, week: number, view: View, pal: Palette, comet: boolean): void {
    const { stations, ref } = this.radar;
    stations.forEach((s, i) => {
      const at = stationAt(s, week, ref);
      if (!at) return;
      this.owed[i] = Math.min(3, (this.owed[i] ?? 0) + at.a * RATE * dt);
      while ((this.owed[i] ?? 0) >= 1 && this.strokes.length < MOST) {
        this.owed[i] = (this.owed[i] ?? 0) - 1;
        // Somewhere in the air this radar sampled, evenly over the disc.
        const [lon, lat] = step(s.lon, s.lat, Math.random() * Math.PI * 2, FOOTPRINT_KM * Math.sqrt(Math.random()));
        const life = LIFE * (0.8 + Math.random() * 0.4);
        this.strokes.push({
          lon,
          lat,
          plon: lon,
          plat: lat,
          age: 0,
          life,
          bearing: at.bearing + (Math.random() - 0.5) * 0.14,
          // km per sheet-second, so the whole night's flight takes `life` seconds.
          rate: (at.kmh * (0.9 + Math.random() * 0.2) * NIGHT_HOURS) / life,
          heavy: at.a > 0.7,
        });
      }
    });

    // Thinner strokes when the view is far out, so the world view is not a smudge.
    const weight = Math.min(1.6, Math.max(0.5, view.pxPerKm(-96, 38) * 4.5));
    const light = new Path2D();
    const heavy = new Path2D();
    let kept = 0;
    for (const q of this.strokes) {
      q.age += dt;
      if (q.age > q.life) continue; // the night is over: as far as the measurement carries
      q.plon = q.lon;
      q.plat = q.lat;
      [q.lon, q.lat] = step(q.lon, q.lat, q.bearing, q.rate * dt);
      const [tlon, tlat] = comet ? step(q.lon, q.lat, q.bearing, -q.rate * Math.min(q.age, 0.25)) : [q.plon, q.plat];
      const [x0, y0] = view.project(tlon, tlat);
      const [x1, y1] = view.project(q.lon, q.lat);
      const path = q.heavy ? heavy : light;
      path.moveTo(x0, y0);
      path.lineTo(x1, y1);
      this.strokes[kept++] = q;
    }
    this.strokes.length = kept;
    ctx.lineCap = "round";
    ctx.strokeStyle = pal.ink;
    ctx.lineWidth = 1.25 * weight;
    ctx.stroke(light);
    ctx.lineWidth = 2 * weight;
    ctx.stroke(heavy);
  }

  /** What the radars say this week, read from them rather than from the calendar. */
  readout(week: number, words: Words["readout"]["air"]): string {
    let east = 0;
    let north = 0;
    let total = 0;
    for (const s of this.radar.stations) {
      const at = stationAt(s, week, this.radar.ref);
      if (!at) continue;
      total += at.a;
      east += at.a * Math.sin(at.bearing);
      north += at.a * Math.cos(at.bearing);
    }
    const share = total / this.radar.stations.length / (this.peak || 1);
    if (share < 0.25) return words.little;
    const amount = share > 0.7 ? words.great : words.fair;
    if (Math.hypot(east, north) / Math.max(total, 1e-9) < 0.3) return `${amount}, ${words.every_way}`;
    const octant = Math.round((((Math.atan2(east, north) * 180) / Math.PI + 360) % 360) / 45) % 8;
    return `${amount}, ${words.heading} ${words.compass[octant] ?? ""}`;
  }
}
