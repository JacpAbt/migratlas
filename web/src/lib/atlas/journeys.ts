/**
 * The Arctic foxes from Bylot Island: each journey drawn a day at a time, a nib at its head.
 *
 * The published tracks carry no dates (`tiles/tracks.py`; ADR 0021 decision 9), so the clock here is
 * the day of each fox's own journey and every fox starts together on day one. Dating them would
 * publish something new and needs its own clearance.
 */

import type { View } from "./geo";
import type { Line, Palette } from "./ink";

/** The fox clock: most journeys end by here; longer ones are drawn whole at the end. */
export const JOURNEY_DAYS = 400;

export class Journeys {
  readonly longest: number;

  constructor(private readonly tracks: readonly Line[]) {
    this.longest = Math.max(...tracks.map((track) => track.length));
  }

  get count(): number {
    return this.tracks.length;
  }

  /** Draw every journey up to `day`; returns how many are still going. */
  frame(ctx: CanvasRenderingContext2D, day: number, view: View, pal: Palette, far: boolean): number {
    ctx.save();
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = pal.ink;
    ctx.globalAlpha = far ? 0.55 : 0.62;
    ctx.lineWidth = far ? 0.7 : 1;
    const path = new Path2D();
    const nibs: [number, number][] = [];
    for (const track of this.tracks) {
      const upto = Math.min(track.length - 1, day);
      const first = track[0];
      if (upto < 0 || !first) continue;
      const whole = Math.floor(upto);
      let [x, y] = view.project(first[0], first[1]);
      path.moveTo(x, y);
      let px = x;
      for (let i = 1; i <= whole; i++) {
        const point = track[i];
        if (!point) break;
        [x, y] = view.project(point[0], point[1]);
        // A fox does not cross the antimeridian; a jump this long is a projection's seam.
        if (Math.abs(x - px) > 400) path.moveTo(x, y);
        else path.lineTo(x, y);
        px = x;
      }
      const here = track[whole];
      const next = track[whole + 1];
      if (here && next) {
        const f = upto - whole;
        const [ax, ay] = view.project(here[0], here[1]);
        const [bx, by] = view.project(next[0], next[1]);
        x = ax + (bx - ax) * f;
        y = ay + (by - ay) * f;
        path.lineTo(x, y);
        nibs.push([x, y]);
      }
    }
    ctx.stroke(path);
    ctx.globalAlpha = 1;
    ctx.fillStyle = pal.accent;
    for (const [x, y] of nibs) {
      ctx.beginPath();
      ctx.arc(x, y, far ? 1.4 : 2.2, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
    return nibs.length;
  }
}
