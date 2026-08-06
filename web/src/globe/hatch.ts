/**
 * The land, hatched in pencil.
 *
 * MapLibre draws WebGL from vector data, so nothing on the globe can be handed to rough.js the way
 * a mark on the page is. What it *does* take is a repeating image: `map.addImage` registers one and
 * `fill-pattern` tiles it across a fill. So the drawing happens once, into a canvas, and the sphere
 * is filled with it.
 *
 * The wobble here is hand-rolled, which needs saying because `notebook/ink.ts` exists precisely to
 * stop that happening twice. The reason is tiling, and it is not a preference. rough.js draws each
 * stroke twice with random divergence: a tile whose edges are drawn independently does not meet its
 * own opposite edge, and `fill-pattern` would repeat that mismatch into a grid across every
 * continent. Everything here is periodic by construction instead -- see `strokes` for the three
 * conditions that makes it, each of which was got wrong once.
 *
 * A pencil line is not a sum of sines. Four of them with unrelated phases read as one at this size,
 * and the honest alternative -- a random walk -- cannot close on itself.
 *
 * One consequence worth knowing: `fill-pattern` tiles in *screen* space, so the hatch does not turn
 * with the globe. That is the right way round here. The hatch is the paper the world is drawn on,
 * not a feature of the world, and a texture that rotated with the sphere would claim to be one.
 */

import { palette, type Palette } from "./flavor";

/** Tile side in CSS pixels. */
const TILE = 96;

/**
 * How many hatch lines a tile-width of horizontal shift crosses.
 *
 * This is the number the tiling turns on, and getting it wrong is what the first version did. The
 * lines run at 45 degrees as `y = x + c`, so shifting the tile sideways by `TILE` turns the line at
 * `c` into the line at `c - TILE` -- which is only *another line of the same family* if `TILE` is a
 * whole number of `c`-steps. Rotating the canvas by 45 degrees and stepping by a round 8px, as this
 * did, makes it 8.49 steps: every seam offset the whole family by half a spacing. It did not read as
 * a grid only because a diagonal line hides a jog along its own direction.
 *
 * So the step is `TILE / LINES` by construction, and the perpendicular spacing is whatever that
 * makes it -- 8.49px rather than a number anybody chose.
 */
const LINES = 8;

/** Generated at 2x and declared as such, so the strokes stay strokes on a dense display. */
const SCALE = 2;

/**
 * Lateral wander of one hatch line, in pixels, at position `t` along the tile (0 to 1).
 *
 * Whole cycles per tile, and *only* whole cycles: the term has to be `2πk` for an integer k, or
 * `wander(t + 1)` is not `wander(t)` and the tile does not meet itself. The first version of this
 * used `7π` and `11π`, which are three and a half and five and a half cycles -- so two of the four
 * terms arrived at the seam inverted, and the comment above them said integer frequencies while the
 * line below it did not have any. It measured as a seam of 3.4 against an interior roughness of 2.7.
 *
 * The amplitudes fall off with frequency the way a hand does: a long slow drift with smaller
 * corrections inside it.
 */
const CYCLES = [1, 2, 4, 7] as const;
const AMPLITUDES = [1.5, 0.7, 0.35, 0.18] as const;

function wander(t: number, seed: number): number {
  let offset = 0;
  for (const [index, cycles] of CYCLES.entries()) {
    const phase = (seed * (index + 1) * 2.399963) % (Math.PI * 2);
    offset += AMPLITUDES[index]! * Math.sin(2 * Math.PI * cycles * t + phase);
  }
  return offset;
}

/** A deterministic 0-1 from an integer, so a tile is the same tile on every render. */
function noise(index: number): number {
  const value = Math.sin(index * 12.9898) * 43758.5453;
  return value - Math.floor(value);
}

export interface Pattern {
  data: ImageData;
  pixelRatio: number;
}

/**
 * Draw the hatch tile for a surface.
 *
 * The mean of the finished tile is the palette's own land colour, not something near it. The strokes
 * darken, so the ground is lifted by exactly what they take back -- the same arithmetic the paper
 * grain needed, and for the same reason: `flavor.ts` records land-against-ocean as a measured ratio,
 * and a pattern that quietly darkens the land makes that figure describe nothing.
 */
export function hatchTile(skin: Palette = palette()): Pattern {
  const side = TILE * SCALE;
  const canvas = document.createElement("canvas");
  canvas.width = side;
  canvas.height = side;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) throw new Error("no 2d context for the hatch tile");

  // Ink and ground both come from the palette. The hatch is the coastline's colour at low alpha:
  // one hand, one pencil, and it follows the surface for free.
  const ALPHA = 0.28;
  const WIDTH = 1.1;

  // Fraction of the tile the strokes cover, so the ground can be lifted by the reciprocal. Measured
  // off the drawing below rather than derived from the geometry, because the wander changes it.
  context.fillStyle = "#000000";
  context.fillRect(0, 0, side, side);
  strokes(context, side, "#ffffff", 1, WIDTH);
  const covered = mean(context.getImageData(0, 0, side, side)) / 255;

  const ground = lift(skin.land, skin.coast, covered * ALPHA);
  context.fillStyle = ground;
  context.fillRect(0, 0, side, side);
  strokes(context, side, skin.coast, ALPHA, WIDTH);

  return { data: context.getImageData(0, 0, side, side), pixelRatio: SCALE };
}

/**
 * The hatch itself: `y = x + c`, drawn in tile coordinates rather than through a rotation.
 *
 * Three things make it seamless, and all three are the same requirement stated in a different
 * coordinate:
 *
 *   - `c` steps by `side / LINES`, so a shift of one tile lands on another line of the family.
 *   - the wander is a function of `x / side` at whole-number frequencies, so a shift of one tile is
 *     a shift of a whole period and leaves it unchanged.
 *   - the seed is the line index modulo `LINES`, so the line a shift lands on has the same hand as
 *     the line it came from.
 *
 * Drop any one and the tile stops meeting itself.
 */
function strokes(
  context: CanvasRenderingContext2D,
  side: number,
  colour: string,
  alpha: number,
  width: number,
): void {
  context.save();
  context.globalAlpha = alpha;
  context.strokeStyle = colour;
  context.lineCap = "butt";

  const step = side / LINES;
  const samples = 96;

  /*
    Every line is drawn a full tile past each edge, and that is not belt-and-braces.

    The geometry is exactly continuous without it -- line `c` at x = side and line `c + side` at
    x = 0 arrive at the same point with the same offset, which is what the three conditions above
    buy. What is not continuous is the *rasterisation*: a stroke has width, and one whose centre
    line ends at x = 0 has half its ink outside the canvas, so the first and last columns come out
    systematically pale. Measured, that alone was a seam of 4.1 against an interior roughness of 2.7.

    Drawing from -1 to 2 in t means the edge columns are covered by strokes that continue past them,
    and the periodicity is what makes that legitimate: `wander` at whole-number frequencies has the
    same value at t and t + 1, so the overhang is the same ink the neighbouring tile puts there.
  */
  for (let index = -2 * LINES; index <= 2 * LINES; index += 1) {
    const c = index * step;
    const seed = ((index % LINES) + LINES) % LINES;
    // Weight varies per line, because a hand does not press the same way twice. Keyed to the wrapped
    // seed rather than the index, or the two halves of a seam are drawn at different weights.
    context.lineWidth = width * SCALE * (0.7 + noise(seed) * 0.7);
    context.beginPath();
    for (let sample = 0; sample <= samples; sample += 1) {
      const t = -1 + (3 * sample) / samples;
      const x = t * side;
      // Perpendicular to a 45-degree line, so the offset splits evenly between the two axes.
      const off = (wander(t, seed + 1) * SCALE) / Math.SQRT2;
      const point: [number, number] = [x - off, x + c + off];
      if (sample === 0) context.moveTo(...point);
      else context.lineTo(...point);
    }
    context.stroke();
  }
  context.restore();
}

/** Mean of the red channel, which is enough: everything drawn here is grey or a single colour. */
function mean(image: ImageData): number {
  let total = 0;
  for (let index = 0; index < image.data.length; index += 4) total += image.data[index]!;
  return total / (image.data.length / 4);
}

/**
 * The ground colour that, once `share` of it is covered by `ink`, averages back to `target`.
 *
 * Solving `target = ground * (1 - share) + ink * share` per channel. Clamped, because a dark enough
 * ink over a light enough target has no solution and the honest failure is a slightly darker land
 * rather than a channel wrapping round.
 */
function lift(target: string, ink: string, share: number): string {
  const parse = (hex: string): [number, number, number] => {
    const value = Number.parseInt(hex.slice(1), 16);
    return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
  };
  const [tr, tg, tb] = parse(target);
  const [ir, ig, ib] = parse(ink);
  const solve = (t: number, i: number) =>
    Math.round(Math.min(255, Math.max(0, (t - i * share) / (1 - share))));
  return `rgb(${solve(tr, ir)} ${solve(tg, ig)} ${solve(tb, ib)})`;
}

/** Name the pattern goes into the style under. */
export const HATCH = "land-hatch";
