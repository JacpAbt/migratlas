/**
 * The map in the book's ink: land hatched by hand, the coast gone over twice, borders in a dashed
 * pencil, rivers, lakes and a graticule so faint it is there only when looked for.
 *
 * The colours are the book's tokens, read from the page, so the atlas follows the paper -- day,
 * night, or the reader's choice -- and nothing here names a hex (ADR 0008's rule).
 */

import type { Box, View } from "./geo";

/** A ring or a line, as longitude-latitude pairs. */
export type Line = readonly (readonly [number, number])[];

/** The colours the atlas draws in, resolved from the book's tokens. */
export interface Palette {
  ink: string;
  soft: string;
  pencil: string;
  rule: string;
  accent: string;
  ice: string;
  green: string;
  /** The body face, as a canvas font family: a canvas cannot read `var(--font-body)`. */
  font: string;
  dark: boolean;
}

/**
 * The tokens as colours a canvas accepts. A custom property reads back as written -- some are
 * `color-mix(...)` -- so each is resolved by giving it to a probe's `color` and reading that back.
 */
export function palette(host: Element): Palette {
  const probe = document.createElement("span");
  probe.style.display = "none";
  host.append(probe);
  const read = (token: string): string => {
    probe.style.color = `var(${token})`;
    return getComputedStyle(probe).color;
  };
  const colours = {
    ink: read("--ink"),
    soft: read("--ink-soft"),
    pencil: read("--pencil"),
    rule: read("--rule"),
    accent: read("--rust-ink"),
    ice: read("--night-shade"),
    green: read("--moss-ink"),
  };
  probe.style.color = "var(--paper)";
  probe.style.fontFamily = "var(--font-body)";
  const paper = getComputedStyle(probe).color;
  const font = getComputedStyle(probe).fontFamily;
  probe.remove();
  return { ...colours, font, dark: luminance(paper) < 0.4 };
}

function luminance(colour: string): number {
  const [r = 0, g = 0, b = 0] = (colour.match(/[\d.]+/g) ?? []).map(Number);
  return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
}

/** Seeded noise, so the hand's wobble is the same on every redraw and in every copy. */
export function rng(seed: number): () => number {
  let s = seed >>> 0 || 1;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

/** One level of detail of a map: its land, and what is drawn with it, and how strongly. */
export interface Part {
  land: readonly Line[];
  alpha: number;
  hatch: boolean;
  /**
   * A plate's box. Its land was cut to the box, so a ring runs along the box's edges where the cut
   * closed it; those segments fill but are not inked, or they draw straight false shores.
   */
  box?: Box;
  borders?: readonly Line[];
  rivers?: readonly Line[];
  creeks?: readonly Line[];
  lakes?: readonly Line[];
  labels?: readonly Label[];
  hatchAlpha?: number;
  riverAlpha?: number;
  riverWidth?: number;
}

/** A river's name, set along its line. */
export interface Label {
  text: string;
  lon: number;
  lat: number;
  angle: number;
}

/** A graticule's spacing, in degrees. */
export interface Graticule {
  lon: number;
  lat: number;
}

const onEdge = (box: Box, a: readonly [number, number], b: readonly [number, number]): boolean =>
  (a[0] === box.west && b[0] === box.west) ||
  (a[0] === box.east && b[0] === box.east) ||
  (a[1] === box.south && b[1] === box.south) ||
  (a[1] === box.north && b[1] === box.north);

/**
 * Draw a map onto `ctx`, in CSS pixels at `dpr`, from `parts` through `view`.
 *
 * A line is broken where it crosses the antimeridian, and where an inked outline runs along the
 * pole: Equal Earth draws the pole as a line, Antarctica's outline lies along it, and neither it nor
 * the antimeridian is a coast. A fill keeps the pole line, which is the continent's shape.
 */
export function drawMap(
  ctx: CanvasRenderingContext2D,
  view: View,
  size: { w: number; h: number; dpr: number },
  pal: Palette,
  parts: readonly Part[],
  options: { graticule?: Graticule | null; graticuleAlpha?: number } = {},
): void {
  const { w: W, h: H, dpr } = size;
  ctx.save();
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, W, H);

  const near = (line: Line): boolean => {
    const stride = Math.max(1, line.length >> 4);
    for (let i = 0; i < line.length; i += stride) {
      const point = line[i];
      if (!point) continue;
      const [x, y] = view.project(point[0], point[1]);
      if (x > -W * 0.5 && x < W * 1.5 && y > -H * 0.5 && y < H * 1.5) return true;
    }
    return false;
  };
  const wobble = rng(11);
  const trace = (path: Path2D, line: Line, inked: boolean, box?: Box): void => {
    let previous: readonly [number, number] | null = null;
    for (const point of line) {
      let [x, y] = view.project(point[0], point[1]);
      if (inked) {
        x += (wobble() - 0.5) * 0.9;
        y += (wobble() - 0.5) * 0.9;
      }
      const lifted =
        previous === null ||
        (Math.abs(point[0] - previous[0]) > 180 && !(Math.abs(point[1]) > 89.9 && Math.abs(previous[1]) > 89.9)) ||
        (inked && Math.abs(point[1]) > 89.9 && Math.abs(previous[1]) > 89.9) ||
        (inked && Math.abs(point[0]) > 179.9 && Math.abs(previous[0]) > 179.9) ||
        (inked && box !== undefined && onEdge(box, previous, point));
      if (lifted) path.moveTo(x, y);
      else path.lineTo(x, y);
      previous = point;
    }
  };

  const grid = options.graticule;
  const gridAlpha = options.graticuleAlpha ?? 1;
  if (grid && gridAlpha > 0) {
    const path = new Path2D();
    const wide = grid.lon >= 10 || !view.around;
    const [w0, w1, s0, s1] = wide
      ? [-180, 180, -80, 85]
      : [view.around!.west, view.around!.east, view.around!.south, view.around!.north];
    for (let lon = Math.ceil(w0 / grid.lon) * grid.lon; lon <= w1; lon += grid.lon) {
      trace(path, Array.from({ length: 61 }, (_, i) => [lon, s0 + ((s1 - s0) * i) / 60] as const), false);
    }
    for (let lat = Math.ceil(s0 / grid.lat) * grid.lat; lat <= s1; lat += grid.lat) {
      trace(path, Array.from({ length: 121 }, (_, i) => [w0 + ((w1 - w0) * i) / 120, lat] as const), false);
    }
    ctx.strokeStyle = pal.rule;
    ctx.globalAlpha = 0.6 * gridAlpha;
    ctx.lineWidth = 0.6;
    ctx.setLineDash([2, 5]);
    ctx.stroke(path);
    ctx.setLineDash([]);
  }

  for (const part of parts) {
    if (part.alpha <= 0.01) continue;
    const shown = part.land.filter(near);
    const fill = new Path2D();
    for (const ring of shown) {
      trace(fill, ring, false);
      fill.closePath();
    }
    if (part.hatch) {
      ctx.save();
      ctx.clip(fill, "evenodd");
      ctx.strokeStyle = pal.pencil;
      ctx.globalAlpha = part.alpha * (part.hatchAlpha ?? 1) * (pal.dark ? 0.32 : 0.4);
      ctx.lineWidth = 0.75;
      const jitter = rng(3);
      const hatch = new Path2D();
      for (let c = -H; c < W + H; c += 6.5) {
        const j = (jitter() - 0.5) * 1.6;
        hatch.moveTo(c + j, 0);
        hatch.lineTo(c + H + j + (jitter() - 0.5) * 3, H);
      }
      ctx.stroke(hatch);
      ctx.restore();
    }
    if (part.lakes) {
      const water = new Path2D();
      for (const ring of part.lakes.filter(near)) {
        trace(water, ring, false);
        water.closePath();
      }
      // A lake is a hole in the hatching, outlined: cut out, then inked thin.
      ctx.save();
      ctx.globalCompositeOperation = "destination-out";
      ctx.globalAlpha = part.alpha;
      ctx.fill(water, "evenodd");
      ctx.restore();
      ctx.strokeStyle = pal.ink;
      ctx.globalAlpha = part.alpha * 0.55;
      ctx.lineWidth = 0.7;
      ctx.stroke(water);
    }
    const coast = new Path2D();
    for (const ring of shown) trace(coast, ring, true, part.box);
    ctx.strokeStyle = pal.ink;
    ctx.globalAlpha = part.alpha * 0.9;
    ctx.lineWidth = 1.2;
    ctx.stroke(coast);
    ctx.globalAlpha = part.alpha * 0.35;
    ctx.lineWidth = 0.6;
    ctx.stroke(coast);
    if (part.borders) {
      const borders = new Path2D();
      for (const line of part.borders.filter(near)) trace(borders, line, true);
      ctx.strokeStyle = pal.pencil;
      ctx.globalAlpha = part.alpha * 0.55;
      ctx.lineWidth = 0.75;
      ctx.setLineDash([5, 4]);
      ctx.stroke(borders);
      ctx.setLineDash([]);
    }
    for (const [lines, alpha, width] of [
      [part.creeks, 0.4, 0.6],
      [part.rivers, part.riverAlpha ?? 0.4, part.riverWidth ?? 0.7],
    ] as const) {
      if (!lines) continue;
      const path = new Path2D();
      for (const line of lines.filter(near)) trace(path, line, true);
      ctx.strokeStyle = pal.ink;
      ctx.globalAlpha = part.alpha * alpha;
      ctx.lineWidth = width;
      ctx.stroke(path);
    }
    if (part.labels && part.alpha > 0.5) {
      ctx.fillStyle = pal.soft;
      ctx.globalAlpha = part.alpha * 0.85;
      ctx.font = `italic 12px ${pal.font}`;
      for (const label of part.labels) {
        const [x, y] = view.project(label.lon, label.lat);
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(label.angle);
        ctx.fillText(label.text, 0, -3);
        ctx.restore();
      }
    }
  }
  ctx.globalAlpha = 1;
  ctx.restore();
}
