/**
 * A map with no time in it, in the atlas's ink (ADR 0021 decision 7): a count as stippled dots, a
 * change as solid dots and rings, an assessment as cells inked or pencilled.
 *
 * Each value is one figure for the map's whole period, so nothing here reads the clock, and a still
 * map is drawn once into the settled sheet of the place it is on rather than every frame.
 *
 * Direction in the change map is carried by shape as well as colour -- a gain is a solid dot, a loss
 * a ring -- because the two ends of a diverging pair are exactly what a red-green reader cannot
 * separate, and which way a cell went is that map's whole content (ADR 0007's rule, which the
 * globe's version of this layer had to be tested for).
 */

import type { Cells, StillWords } from "./data";
import type { View } from "./geo";
import { rng, type Palette } from "./ink";

/** Kilometres in a degree of latitude, for a cell's size in pixels. */
const KM_PER_DEG = 111.2;

/** What a still map drew, for the suite to ask -- the map's answer, not the DOM's. */
export interface StillDrawn {
  dots: number;
  rings: number;
  squares: number;
}

/** A status's ink: the accent where a change could be measured, pencil of three strengths where not. */
export const STATUS_INK: Record<string, { tone: "accent" | "pencil"; alpha: number }> = {
  detectable: { tone: "accent", alpha: 0.8 },
  "too-short": { tone: "pencil", alpha: 0.62 },
  "no-time-axis": { tone: "pencil", alpha: 0.4 },
  "effort-not-measured": { tone: "pencil", alpha: 0.2 },
};

const unknownStatus = { tone: "pencil", alpha: 0.3 } as const;

export class StillMap {
  readonly kind: "count" | "change" | "status";
  /** The scale's end: the largest count, or the largest change either way. */
  readonly top: number;

  constructor(
    readonly words: StillWords,
    readonly cells: Cells,
  ) {
    let top = 0;
    let least = 0;
    for (const value of cells.v) {
      top = Math.max(top, Math.abs(value));
      least = Math.min(least, value);
    }
    this.top = top || 1;
    this.kind = cells.categories ? "status" : least < 0 ? "change" : "count";
  }

  /** Each category's share of the assessed cells, in percent, by name. */
  shares(): Record<string, number> {
    const names = this.cells.categories ?? [];
    const counts = names.map(() => 0);
    for (const value of this.cells.v) if (counts[value] !== undefined) counts[value] += 1;
    const total = this.cells.v.length || 1;
    return Object.fromEntries(names.map((name, i) => [name, (counts[i]! / total) * 100]));
  }

  /** A count's dot, as a fraction of its cell: logarithmic, so the typical cell still shows. */
  dot(value: number): number {
    const t = Math.log10(Math.max(1, value)) / Math.log10(Math.max(10, this.top));
    return 0.14 + 0.34 * Math.min(1, t);
  }

  /** A change's mark, as a fraction of its cell: linear in the change, the same scale both ways. */
  mark(value: number): number {
    return 0.12 + 0.36 * Math.min(1, Math.abs(value) / this.top);
  }

  /** Three counts for the key -- one, the scale's middle, its end -- each a round figure. */
  samples(): number[] {
    const round = (n: number): number => {
      const unit = 10 ** Math.floor(Math.log10(n));
      return Math.round(n / unit) * unit;
    };
    const middle = round(Math.sqrt(this.top));
    return [...new Set([1, middle, Math.round(this.top)])].filter((n) => n >= 1);
  }

  /** Draw onto a settled sheet through `view`; `w` and `h` are the sheet's CSS size. */
  draw(c: CanvasRenderingContext2D, view: View, pal: Palette, w: number, h: number): StillDrawn {
    const { lon, lat, v, size } = this.cells;
    const at = this.middle();
    const cellPx = view.pxPerKm(at[0], at[1]) * KM_PER_DEG * size;
    const drawn: StillDrawn = { dots: 0, rings: 0, squares: 0 };
    const off = (x: number, y: number): boolean => x < -cellPx || y < -cellPx || x > w + cellPx || y > h + cellPx;
    c.save();

    if (this.kind === "status") {
      const names = this.cells.categories ?? [];
      const half = size / 2;
      names.forEach((name, index) => {
        const ink = STATUS_INK[name] ?? unknownStatus;
        c.beginPath();
        for (let i = 0; i < v.length; i++) {
          if (v[i] !== index) continue;
          const [x, y] = view.project(lon[i]!, lat[i]!);
          if (off(x, y)) continue;
          // The corners projected, not a square round the centre: at high latitude Equal Earth
          // narrows a degree of longitude, and squares would overlap into a darker band.
          const a = view.project(lon[i]! - half, lat[i]! - half);
          const b = view.project(lon[i]! + half, lat[i]! - half);
          const d = view.project(lon[i]! + half, lat[i]! + half);
          const e = view.project(lon[i]! - half, lat[i]! + half);
          c.moveTo(a[0], a[1]);
          c.lineTo(b[0], b[1]);
          c.lineTo(d[0], d[1]);
          c.lineTo(e[0], e[1]);
          c.closePath();
          drawn.squares += 1;
        }
        c.globalAlpha = ink.alpha;
        c.fillStyle = ink.tone === "accent" ? pal.accent : pal.pencil;
        c.fill();
      });
    } else if (this.kind === "change") {
      const gains = new Path2D();
      const losses = new Path2D();
      const level = new Path2D();
      for (let i = 0; i < v.length; i++) {
        const [x, y] = view.project(lon[i]!, lat[i]!);
        if (off(x, y)) continue;
        const r = Math.max(1, cellPx * this.mark(v[i]!));
        if (v[i]! > 0) {
          gains.moveTo(x + r, y);
          gains.arc(x, y, r, 0, Math.PI * 2);
          drawn.dots += 1;
        } else if (v[i]! < 0) {
          losses.moveTo(x + r, y);
          losses.arc(x, y, r, 0, Math.PI * 2);
          drawn.rings += 1;
        } else {
          level.moveTo(x + 1, y);
          level.arc(x, y, 1, 0, Math.PI * 2);
        }
      }
      c.globalAlpha = 0.85;
      c.fillStyle = pal.ink;
      c.fill(gains);
      c.lineWidth = Math.max(1, cellPx * 0.09);
      c.strokeStyle = pal.accent;
      c.stroke(losses);
      c.globalAlpha = 0.6;
      c.fillStyle = pal.pencil;
      c.fill(level);
    } else {
      // Stippled: a dot a little off its cell's centre, the same wobble on every redraw, and binned
      // by strength so a sparse cell is faint rather than as loud as a hotspot.
      const wobble = rng(this.words.name.length * 7919 + v.length);
      const bins = Array.from({ length: 8 }, () => new Path2D());
      const span = Math.log10(Math.max(10, this.top));
      for (let i = 0; i < v.length; i++) {
        const [cx, cy] = view.project(lon[i]!, lat[i]!);
        const x = cx + (wobble() - 0.5) * cellPx * 0.16;
        const y = cy + (wobble() - 0.5) * cellPx * 0.16;
        if (off(x, y)) continue;
        const r = Math.max(0.5, cellPx * this.dot(v[i]!));
        const bin = Math.min(7, Math.floor((Math.log10(Math.max(1, v[i]!)) / span) * 8));
        bins[bin]!.moveTo(x + r, y);
        bins[bin]!.arc(x, y, r, 0, Math.PI * 2);
        drawn.dots += 1;
      }
      c.fillStyle = pal.ink;
      bins.forEach((path, bin) => {
        c.globalAlpha = 0.3 + (0.6 * (bin + 0.5)) / 8;
        c.fill(path);
      });
    }

    c.restore();
    return drawn;
  }

  /** The middle of the cells, where a cell's size in pixels is read. */
  private middle(): [number, number] {
    const { lon, lat } = this.cells;
    if (lon.length === 0) return [0, 0];
    let x = 0;
    let y = 0;
    for (let i = 0; i < lon.length; i++) {
      x += lon[i]!;
      y += lat[i]!;
    }
    return [x / lon.length, y / lon.length];
  }
}
