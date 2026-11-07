/**
 * The sea ice's median edge, month by month, as a dotted line that gives way to the next month's.
 * The 1981-2010 climatology (`tiles/ice.py`): no one year's ice.
 */

import { WEEKS, type IceEdges } from "./data";
import type { View } from "./geo";
import type { Palette } from "./ink";

export class Ice {
  constructor(private readonly edges: IceEdges) {}

  frame(ctx: CanvasRenderingContext2D, week: number, view: View, pal: Palette): void {
    const month = ((week / WEEKS) * 12) % 12;
    const m0 = Math.floor(month);
    const f = month - m0;
    ctx.save();
    ctx.strokeStyle = pal.ice;
    ctx.lineWidth = 1.1;
    ctx.setLineDash([1.5, 3]);
    for (const byMonth of Object.values(this.edges)) {
      for (const [m, alpha] of [
        [m0 + 1, 1 - f],
        [((m0 + 1) % 12) + 1, f],
      ] as const) {
        const lines = byMonth[m];
        if (!lines || alpha < 0.02) continue;
        ctx.globalAlpha = alpha * 0.9;
        const path = new Path2D();
        for (const line of lines) {
          let px = Number.NaN;
          line.forEach(([lon, lat], i) => {
            const [x, y] = view.project(lon, lat);
            if (i === 0 || Math.abs(x - px) > 300) path.moveTo(x, y);
            else path.lineTo(x, y);
            px = x;
          });
        }
        ctx.stroke(path);
      }
    }
    ctx.restore();
  }
}
