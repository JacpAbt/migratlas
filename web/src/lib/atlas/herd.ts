/**
 * A herd as a range that moves: where its collared animals were recorded each typical week, inked
 * and hatched; the weeks before it trailing in dashed outline; and a pen flick from where the herd
 * was last week to each place it newly reached this week.
 *
 * The layer is presence per 0.01-degree cell per typical week, with no animal followed from one week
 * to the next (`tiles/presence.py`), so a flick joins a cell to the nearest cell held the week before:
 * the shift between two weekly maps, not anyone's path (ADR 0021 decision 5). Everything here is
 * computed in the browser from the layer already cleared, and a range is coarser than its cells, so
 * nothing new about an animal is published (decision 9). From far out, a herd is one blot.
 */

import { WEEKS, type HerdCell } from "./data";
import type { View } from "./geo";
import { rng, type Line, type Palette } from "./ink";

const CELL = 0.01;
/** Weeks of outline left behind: the typical weeks change gradually, so these carry the movement. */
const TRAIL = 5;
/** Cells: a newly reached place farther than this from last week's is a new place, not a shift. */
const REACH = 25;

/** One flick: from a cell held last week to one reached this week. */
type Shift = readonly [number, number, number, number, number, number];

export class Herd {
  readonly centre: [number, number];
  private readonly peak: number;
  private readonly ranges: Line[][] = [];
  readonly shifts: Shift[][] = [];

  constructor(readonly cells: readonly HerdCell[]) {
    const lons = cells.map((c) => c.lon);
    const lats = cells.map((c) => c.lat);
    const lon0 = Math.min(...lons);
    const lat0 = Math.min(...lats);
    this.centre = [(lon0 + Math.max(...lons)) / 2, (lat0 + Math.max(...lats)) / 2];
    this.peak = Math.max(...Array.from({ length: WEEKS }, (_, k) => cells.reduce((s, c) => s + (c.w[k] ?? 0), 0)));

    const nx = Math.round((Math.max(...lons) - lon0) / CELL) + 1;
    const ny = Math.round((Math.max(...lats) - lat0) / CELL) + 1;
    const ix = (c: HerdCell): number => Math.round((c.lon - lon0) / CELL);
    const iy = (c: HerdCell): number => Math.round((c.lat - lat0) / CELL);

    for (let k = 0; k < WEEKS; k++) {
      // Presence blurred over a couple of cells and outlined where it thins out: a range, not cells.
      const grid = new Float32Array(nx * ny);
      for (const c of cells) if ((c.w[k] ?? 0) > 0) grid[iy(c) * nx + ix(c)] = 1;
      this.ranges.push(
        contour(blur(grid, nx, ny, 1.4), nx, ny, 0.12).map((ring) =>
          smooth(ring).map(([i, j]) => [lon0 + i * CELL, lat0 + j * CELL] as const),
        ),
      );
    }
    for (let k = 0; k < WEEKS; k++) {
      const next = (k + 1) % WEEKS;
      const bins = new Map<string, HerdCell[]>();
      for (const c of cells) {
        if ((c.w[k] ?? 0) <= 0) continue;
        const key = `${Math.floor(ix(c) / 8)},${Math.floor(iy(c) / 8)}`;
        (bins.get(key) ?? bins.set(key, []).get(key)!).push(c);
      }
      const shifts: Shift[] = [];
      for (const c of cells) {
        if ((c.w[next] ?? 0) <= 0) continue;
        let best: HerdCell | null = null;
        let distance = Infinity;
        const bx = Math.floor(ix(c) / 8);
        const by = Math.floor(iy(c) / 8);
        for (let dx = -4; dx <= 4; dx++) {
          for (let dy = -4; dy <= 4; dy++) {
            for (const p of bins.get(`${bx + dx},${by + dy}`) ?? []) {
              const d = Math.hypot(ix(p) - ix(c), iy(p) - iy(c));
              if (d < distance) {
                distance = d;
                best = p;
              }
            }
          }
        }
        // A cell held last week too is no shift.
        if (best && distance >= 2 && distance <= REACH) {
          shifts.push([best.lon, best.lat, c.lon, c.lat, Math.ceil(c.w[next] ?? 1), c.seed]);
        }
      }
      this.shifts.push(shifts);
    }
  }

  /** Cells held in a week, and how many were newly reached since the week before. */
  counts(week: number): { cells: number; reached: number } {
    const k = Math.floor(week) % WEEKS;
    return {
      cells: this.cells.filter((c) => (c.w[k] ?? 0) > 0).length,
      reached: this.shifts[(k - 1 + WEEKS) % WEEKS]?.length ?? 0,
    };
  }

  /** From afar: one blot, as big as the herd is that week. */
  blot(ctx: CanvasRenderingContext2D, week: number, view: View, pal: Palette): void {
    const k0 = Math.floor(week) % WEEKS;
    const k1 = (k0 + 1) % WEEKS;
    const f = week - Math.floor(week);
    const total = this.cells.reduce((s, c) => s + (c.w[k0] ?? 0) * (1 - f) + (c.w[k1] ?? 0) * f, 0);
    const [x, y] = view.project(this.centre[0], this.centre[1]);
    ctx.save();
    ctx.fillStyle = pal.ink;
    ctx.globalAlpha = 0.75;
    ctx.beginPath();
    ctx.arc(x, y, 1.5 + 3.5 * Math.sqrt(total / (this.peak || 1)), 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  /** Close enough to see cells: the range, the weeks behind it, and this week's shifts. */
  range(ctx: CanvasRenderingContext2D, week: number, view: View, pal: Palette): void {
    const k0 = Math.floor(week) % WEEKS;
    const k1 = (k0 + 1) % WEEKS;
    const f = week - Math.floor(week);
    const path = (rings: readonly Line[] | undefined): Path2D => {
      const p = new Path2D();
      for (const ring of rings ?? []) {
        ring.forEach(([lon, lat], i) => {
          const [x, y] = view.project(lon, lat);
          if (i) p.lineTo(x, y);
          else p.moveTo(x, y);
        });
      }
      return p;
    };
    ctx.save();
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.strokeStyle = pal.ink;
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 3]);
    for (let g = TRAIL; g >= 1; g--) {
      ctx.globalAlpha = 0.6 * (1 - (g - 1 + f) / TRAIL);
      ctx.stroke(path(this.ranges[(k0 - g + 1 + WEEKS) % WEEKS]));
    }
    ctx.setLineDash([]);
    for (const [k, alpha] of [
      [k0, 1 - f],
      [k1, f],
    ] as const) {
      if (alpha < 0.02) continue;
      const outline = path(this.ranges[k]);
      ctx.save();
      ctx.clip(outline, "evenodd");
      ctx.globalAlpha = alpha * 0.5;
      ctx.lineWidth = 0.8;
      const hatch = new Path2D();
      const { width: W, height: H } = ctx.canvas;
      // The other diagonal from the land's hatching, so a range reads apart from the ground.
      for (let c = -H; c < W + H; c += 4) {
        hatch.moveTo(c, 0);
        hatch.lineTo(c - H, H);
      }
      ctx.stroke(hatch);
      ctx.restore();
      ctx.globalAlpha = alpha * 0.9;
      ctx.lineWidth = 1.4;
      ctx.stroke(outline);
    }

    // Each shift as a pen flick that grows across the week, coming in and going out with it so the
    // change of week is not a blink.
    const e = f < 0.5 ? 2 * f * f : 1 - (-2 * f + 2) ** 2 / 2;
    const fade = Math.min(1, f / 0.15, (1 - f) / 0.2);
    const flicks = new Path2D();
    for (const [lon0, lat0, lon1, lat1, n, seed] of this.shifts[k0] ?? []) {
      const g = rng(seed + k0);
      for (let i = 0; i < Math.min(n, 3); i++) {
        const jx = (g() - 0.5) * CELL * 0.8;
        const jy = (g() - 0.5) * CELL * 0.8;
        const upto = Math.min(1, e * (1.05 + g() * 0.15));
        const [ax, ay] = view.project(lon0 + jx, lat0 + jy);
        const [bx, by] = view.project(lon1 + jx, lat1 + jy);
        flick(flicks, ax, ay, bx, by, 2.6 + g() * 1.2, (g() - 0.5) * 0.25, upto);
      }
    }
    ctx.globalAlpha = 0.85 * fade;
    ctx.fillStyle = pal.ink;
    ctx.fill(flicks);
    ctx.restore();
  }
}

/**
 * A pen flick from a to b, drawn up to `upto` of its length: filled, its width running from `w`
 * where the nib lands to a fine point, along a slight bow -- a nib pressed and lifted, not a line.
 */
function flick(
  path: Path2D,
  ax: number,
  ay: number,
  bx: number,
  by: number,
  w: number,
  bow: number,
  upto: number,
): void {
  const dx = bx - ax;
  const dy = by - ay;
  const len = Math.hypot(dx, dy) || 1;
  const cx = (ax + bx) / 2 - (dy / len) * bow * len;
  const cy = (ay + by) / 2 + (dx / len) * bow * len;
  const left: [number, number][] = [];
  const right: [number, number][] = [];
  for (let i = 0; i <= 10; i++) {
    const s = (i / 10) * upto;
    const x = (1 - s) ** 2 * ax + 2 * (1 - s) * s * cx + s * s * bx;
    const y = (1 - s) ** 2 * ay + 2 * (1 - s) * s * cy + s * s * by;
    const tx = 2 * (1 - s) * (cx - ax) + 2 * s * (bx - cx);
    const ty = 2 * (1 - s) * (cy - ay) + 2 * s * (by - cy);
    const tl = Math.hypot(tx, ty) || 1;
    const half = (w / 2) * (1 - 0.9 * s) * (s < 0.08 ? 0.6 + 5 * s : 1); // lands, swells, runs out
    left.push([x - (ty / tl) * half, y + (tx / tl) * half]);
    right.push([x + (ty / tl) * half, y - (tx / tl) * half]);
  }
  const [first, ...rest] = left;
  if (!first) return;
  path.moveTo(first[0], first[1]);
  for (const [x, y] of rest) path.lineTo(x, y);
  for (const [x, y] of right.reverse()) path.lineTo(x, y);
  path.closePath();
}

/** Marching squares: closed rings round values above `t`, on a grid padded with zeros. */
function contour(grid: Float32Array, nx: number, ny: number, t: number): [number, number][][] {
  type Point = [number, number];
  const segments: [Point, Point][] = [];
  const value = (i: number, j: number): number => (i < 0 || j < 0 || i >= nx || j >= ny ? 0 : (grid[j * nx + i] ?? 0));
  const cross = (a: number, b: number): number => (t - a) / (b - a || 1e-9);
  const TABLE: Record<number, string> = {
    1: "ws", 2: "se", 3: "we", 4: "en", 5: "wnes", 6: "sn", 7: "wn",
    8: "nw", 9: "ns", 10: "swne", 11: "ne", 12: "ew", 13: "es", 14: "sw",
  };
  for (let j = -1; j < ny; j++) {
    for (let i = -1; i < nx; i++) {
      const a = value(i, j);
      const b = value(i + 1, j);
      const c = value(i + 1, j + 1);
      const d = value(i, j + 1);
      const k = (a > t ? 1 : 0) | (b > t ? 2 : 0) | (c > t ? 4 : 0) | (d > t ? 8 : 0);
      const edges = TABLE[k];
      if (!edges) continue;
      const at: Record<string, Point> = {
        s: [i + cross(a, b), j],
        e: [i + 1, j + cross(b, c)],
        n: [i + cross(d, c), j + 1],
        w: [i, j + cross(a, d)],
      };
      for (let q = 0; q < edges.length; q += 2) segments.push([at[edges[q]!]!, at[edges[q + 1]!]!]);
    }
  }
  // Joined end to end, whichever way round each segment came out: the table does not promise one.
  const key = ([x, y]: Point): string => `${x.toFixed(4)},${y.toFixed(4)}`;
  const ends = new Map<string, number[]>();
  segments.forEach((segment, index) => {
    for (const p of segment) (ends.get(key(p)) ?? ends.set(key(p), []).get(key(p))!).push(index);
  });
  const used = new Uint8Array(segments.length);
  const rings: Point[][] = [];
  segments.forEach((segment, index) => {
    if (used[index]) return;
    used[index] = 1;
    const ring: Point[] = [segment[0], segment[1]];
    let end = segment[1];
    for (;;) {
      const next = (ends.get(key(end)) ?? []).find((n) => !used[n]);
      if (next === undefined) break;
      used[next] = 1;
      const [p, q] = segments[next]!;
      end = key(p) === key(end) ? q : p;
      ring.push(end);
    }
    if (ring.length > 3) rings.push(ring);
  });
  return rings;
}

/** Chaikin's corner cutting: a marching-squares staircase becomes a line a hand would draw. */
function smooth(ring: [number, number][], times = 2): [number, number][] {
  let r = ring;
  for (let n = 0; n < times; n++) {
    const out: [number, number][] = [];
    for (let i = 0; i < r.length - 1; i++) {
      const [x0, y0] = r[i]!;
      const [x1, y1] = r[i + 1]!;
      out.push([0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1], [0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1]);
    }
    if (out[0]) out.push(out[0]);
    r = out;
  }
  return r;
}

/** A separable Gaussian blur, enough to turn scattered cells into a range. */
function blur(grid: Float32Array, nx: number, ny: number, sigma: number): Float32Array {
  const r = Math.ceil(sigma * 2.5);
  const weights = Array.from({ length: 2 * r + 1 }, (_, i) => Math.exp(-((i - r) ** 2) / (2 * sigma * sigma)));
  const sum = weights.reduce((a, b) => a + b, 0);
  const across = new Float32Array(nx * ny);
  const out = new Float32Array(nx * ny);
  for (let j = 0; j < ny; j++) {
    for (let i = 0; i < nx; i++) {
      let s = 0;
      for (let q = -r; q <= r; q++) if (i + q >= 0 && i + q < nx) s += (grid[j * nx + i + q] ?? 0) * (weights[q + r] ?? 0);
      across[j * nx + i] = s / sum;
    }
  }
  for (let j = 0; j < ny; j++) {
    for (let i = 0; i < nx; i++) {
      let s = 0;
      for (let q = -r; q <= r; q++) if (j + q >= 0 && j + q < ny) s += (across[(j + q) * nx + i] ?? 0) * (weights[q + r] ?? 0);
      out[j * nx + i] = s / sum;
    }
  }
  return out;
}
