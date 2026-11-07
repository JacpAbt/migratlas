/**
 * The green wave as a wash under everything on the world view (ADR 0021 decision 5): each
 * one-degree cell tinted by how green its land is at this point of the year, read between the two
 * half-months either side of the clock.
 *
 * A climatology -- the mean of 1982 to 2022 for each half-month -- so it is no one year's spring, and
 * it is drawn under the animals' marks because it is not a response to anything: it is the season
 * they move through. A cell-half-month with no vegetated ground is absent, not zero, and draws as
 * no tint; between such a half-month and a green one the tint fades rather than the value, so bare
 * ground is never read as faintly green.
 *
 * Drawn faint and softened by the sheet's blur, so it reads as a wash in the ink's world rather
 * than as imagery -- the ADR's kill condition for this step is exactly that, and its remedy a toggle.
 */

import type { GreenWave } from "./data";
import { WEEKS } from "./data";
import type { View } from "./geo";
import type { Palette } from "./ink";

/** The strongest tint, at the greenest ground: a wash, not a fill. */
const MOST = 0.2;
/** NDVI in hundredths: below the first nothing a reader would call plant, above the second all green. */
const BARE = 10;
const LUSH = 80;
/** Tint levels: one path and one fill each. */
const LEVELS = 10;
/** How far the season moves, in half-months, before the wash is drawn again. */
const STEP = 0.04;

/** What one drawing of the wash inked, for the suite to ask. */
export interface WaveDrawn {
  cells: number;
  /** The tint-weighted mean latitude: north in the northern summer, south in its winter. */
  lat: number;
}

export class Wave {
  private corners: Float32Array | null = null;
  private cornersFor: View | null = null;
  private at = Number.NaN;
  last: WaveDrawn = { cells: 0, lat: 0 };

  constructor(private readonly data: GreenWave) {}

  /** Forget what was drawn, so the next frame draws again: the view or the paper changed. */
  reset(): void {
    this.at = Number.NaN;
  }

  /** Draw the wash at `week` if the season has moved enough since the last drawing; true if it drew. */
  frame(c: CanvasRenderingContext2D, week: number, view: View, pal: Palette, w: number, h: number): boolean {
    const position = (week / WEEKS) * this.data.bins;
    if (Math.abs(position - this.at) < STEP && this.cornersFor === view) return false;
    this.at = position;
    const corners = this.cornersOf(view);
    const { bins, hm, lat } = this.data;
    const first = Math.floor(position) % bins;
    const next = (first + 1) % bins;
    const f = position - Math.floor(position);

    const paths = Array.from({ length: LEVELS }, () => new Path2D());
    let cells = 0;
    let latSum = 0;
    let weight = 0;
    for (let i = 0; i < lat.length; i++) {
      const tint = tintOf(hm[i * bins + first]!) * (1 - f) + tintOf(hm[i * bins + next]!) * f;
      if (tint <= 0.02) continue;
      const level = Math.min(LEVELS - 1, Math.floor(tint * LEVELS));
      const k = i * 8;
      const path = paths[level]!;
      path.moveTo(corners[k]!, corners[k + 1]!);
      path.lineTo(corners[k + 2]!, corners[k + 3]!);
      path.lineTo(corners[k + 4]!, corners[k + 5]!);
      path.lineTo(corners[k + 6]!, corners[k + 7]!);
      path.closePath();
      cells += 1;
      latSum += lat[i]! * tint;
      weight += tint;
    }

    c.save();
    c.setTransform(c.canvas.width / w, 0, 0, c.canvas.height / h, 0, 0);
    c.clearRect(0, 0, w, h);
    c.fillStyle = pal.green;
    paths.forEach((path, level) => {
      c.globalAlpha = MOST * ((level + 0.5) / LEVELS);
      c.fill(path);
    });
    c.restore();
    this.last = { cells, lat: weight > 0 ? latSum / weight : 0 };
    return true;
  }

  /** Each cell's four corners on the sheet, projected once per view rather than every drawing. */
  private cornersOf(view: View): Float32Array {
    if (this.corners && this.cornersFor === view) return this.corners;
    const { lon, lat, size } = this.data;
    const half = size / 2;
    const out = new Float32Array(lon.length * 8);
    for (let i = 0; i < lon.length; i++) {
      const at = [
        view.project(lon[i]! - half, lat[i]! - half),
        view.project(lon[i]! + half, lat[i]! - half),
        view.project(lon[i]! + half, lat[i]! + half),
        view.project(lon[i]! - half, lat[i]! + half),
      ];
      for (let j = 0; j < 4; j++) {
        out[i * 8 + j * 2] = at[j]![0];
        out[i * 8 + j * 2 + 1] = at[j]![1];
      }
    }
    this.corners = out;
    this.cornersFor = view;
    return out;
  }
}

/** A half-month's NDVI as a tint from 0 to 1; no vegetated ground is no tint. */
function tintOf(ndvi: number): number {
  if (Number.isNaN(ndvi)) return 0;
  return Math.max(0, Math.min(1, (ndvi - BARE) / (LUSH - BARE))) ** 1.2;
}
