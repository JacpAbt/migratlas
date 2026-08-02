/**
 * Hand-drawn geometry, on top of rough.js.
 *
 * This file used to roll its own wobble: an FNV-1a hash, a linear congruential jitter, and a
 * control point every 55px. It worked and it was a much worse version of a library that already
 * exists. rough.js is 9 KB gzipped, is what Excalidraw draws with, and does the thing properly --
 * every stroke is drawn twice with controlled divergence, which is what a pen actually does and
 * what a single wobbled path never quite looks like.
 *
 * Two properties carried over from the hand-rolled version, because both are load-bearing:
 *
 * **Deterministic.** Every call takes a seed derived from a stable string -- usually the claim's
 * own key -- so a claim's hand never changes between renders. rough.js redraws differently on
 * every call without one, which turns a quiet line into a flicker and makes a screenshot test
 * meaningless.
 *
 * **Generated at the real pixel size, never stretched.** A path drawn in a 100-unit box and
 * stretched with `preserveAspectRatio="none"` keeps its geometry in user units while the stroke
 * and any dash pattern are applied in screen units: a 2px pen becomes 2px by 9px, and a dasharray
 * meant to cover a line becomes four dashes and a gap. Every helper here takes the measured size.
 */

import rough from "roughjs";
import type { Options } from "roughjs/bin/core";

/** FNV-1a, 32-bit. rough.js wants a numeric seed and the callers all have a string. */
export function seedOf(text: string): number {
  let value = 0x811c9dc5;
  for (let index = 0; index < text.length; index += 1) {
    value ^= text.charCodeAt(index);
    value = Math.imul(value, 0x01000193);
  }
  return value >>> 0;
}

/** A generator bound to one `<svg>`, so a component can draw into itself in one line. */
export function pen(host: SVGSVGElement) {
  return rough.svg(host);
}

/**
 * Append a drawing and name what it is.
 *
 * rough.js hands back an anonymous `<g>` of `<path>`s, which is fine to look at and useless to
 * select: the browser suite reaches for these by name, and "the second path inside the third svg"
 * is not a contract anybody can keep. Every mark this file makes carries an `ink-*` class saying
 * which mark it is.
 */
function mark(host: SVGSVGElement, name: string, node: SVGGElement): void {
  node.classList.add(`ink-${name}`);
  host.append(node);
}

/**
 * House defaults.
 *
 * `roughness` around 1.5 is a pen held normally; above 2.5 it reads as a shake rather than a
 * hand. `bowing` is how much a straight line drifts off true over its length, and a little of it
 * is what stops a long rule looking like a ruler.
 */
export const HAND: Options = { roughness: 1.6, bowing: 1.3, strokeWidth: 1.5 };

/** Height of the box a rule is drawn in, so the component and the generator agree on one number. */
export const RULE_HEIGHT = 10;

/** Width of the box a margin bracket is drawn in. */
export const BRACKET_WIDTH = 9;

/** An underline that does not sit flat, drawn across `width` pixels. */
export function underline(host: SVGSVGElement, key: string, width: number, stroke: string): void {
  if (width <= 0) return;
  mark(
    host,
    "rule",
    pen(host).line(2, RULE_HEIGHT / 2 + 1, width - 4, RULE_HEIGHT / 2 - 1, {
      ...HAND,
      stroke,
      strokeWidth: 2.2,
      bowing: 2.1,
      seed: seedOf(key),
    }),
  );
}

/** A bracket for the margin: a vertical stroke with hooked ends, as drawn beside a paragraph. */
export function bracket(host: SVGSVGElement, key: string, height: number, stroke: string): void {
  if (height <= 0) return;
  mark(
    host,
    "bracket",
    pen(host).linearPath(
      [
        [BRACKET_WIDTH - 2, 1],
        [2, 7],
        [2, height - 7],
        [BRACKET_WIDTH - 2, height - 1],
      ],
      { ...HAND, stroke, strokeWidth: 1.3, roughness: 2.1, seed: seedOf(key) },
    ),
  );
}

/**
 * A rectangle drawn by hand, for a control you press.
 *
 * rough.js overshoots its corners on its own, which is the thing that separates a drawn box from
 * a border: a hand does not stop a pen exactly on a corner.
 */
export function boxDrawn(
  host: SVGSVGElement,
  key: string,
  width: number,
  height: number,
  stroke: string,
  strokeWidth = 1.5,
): void {
  if (width <= 0 || height <= 0) return;
  mark(
    host,
    "box",
    pen(host).rectangle(3, 3, width - 6, height - 6, {
      ...HAND,
      stroke,
      strokeWidth,
      roughness: 2.1,
      bowing: 1.5,
      seed: seedOf(key),
    }),
  );
}

/**
 * The mark round a chosen thing, and the shape follows the thing.
 *
 * An ellipse inscribed in a box touches it at four points, so the corners of the text poke out --
 * which is exactly what a wide row looks like when it is circled. Circumscribing properly needs
 * semi-axes of 1.41x, and a loop that tall reads as an accident. So: a loop for a short pill, a
 * drawn box for anything wide. Both mean "this one", and neither leaves a word outside the mark.
 */
export const LASSO_MAX_WIDTH = 190;

export function lasso(
  host: SVGSVGElement,
  key: string,
  width: number,
  height: number,
  stroke: string,
): void {
  if (width <= 0 || height <= 0) return;
  const rc = pen(host);
  const seed = seedOf(key);
  mark(
    host,
    "lasso",
    width > LASSO_MAX_WIDTH
      ? rc.rectangle(2, 2, width - 4, height - 4, {
          ...HAND,
          stroke,
          strokeWidth: 1.6,
          roughness: 2.3,
          bowing: 1.4,
          seed,
        })
      : rc.ellipse(width / 2, height / 2, width * 1.02, height * 1.06, {
          ...HAND,
          stroke,
          strokeWidth: 1.6,
          roughness: 2.4,
          bowing: 2,
          seed,
        }),
  );
}

/** A tick, in the two strokes a hand makes: a short fall and a long rise, overshooting its box. */
export function tick(host: SVGSVGElement, key: string, size: number, stroke: string): void {
  mark(
    host,
    "tick",
    pen(host).linearPath(
      [
        [size * 0.16, size * 0.52],
        [size * 0.4, size * 0.8],
        [size * 0.92, size * 0.06],
      ],
      { ...HAND, stroke, strokeWidth: 2.1, roughness: 1.4, seed: seedOf(key) },
    ),
  );
}

/**
 * The outline of a sheet of paper, torn out along its left edge.
 *
 * Not a rough.js shape: this is a closed path used as a `clip-path`, so it has to be geometry
 * rather than a stroked drawing. Only the left edge is ragged -- a leaf torn from a bound
 * notebook, not hand-made paper with a deckle on four sides. One irregular edge reads as "removed
 * from something"; four read as an effect.
 */
export function sheetEdge(key: string, width: number, height: number): string {
  if (width <= 0 || height <= 0) return "";
  let state = seedOf(key) || 1;
  const next = (): number => {
    state = (Math.imul(state, 1103515245) + 12345) >>> 0;
    return (state / 0xffffffff) * 2 - 1;
  };

  // A tear is a low-frequency wander with high-frequency nicks in it, and the nicks are what stop
  // it reading as a wave. Every 9px: at 20 it looks like a coastline, at 4 the path gets long
  // enough to matter in a clip.
  const tears: string[] = [];
  const steps = Math.max(6, Math.round(height / 9));
  for (let step = steps; step >= 0; step -= 1) {
    const y = (step / steps) * height;
    const wander = Math.sin((step / steps) * Math.PI * 1.7) * 1.6;
    const nick = next() * 1.4 + (step % 3 === 0 ? next() * 1.1 : 0);
    tears.push(`${Math.max(0, wander + nick + 2).toFixed(1)} ${y.toFixed(1)}`);
  }

  // A cut edge is straight, and one that is *perfectly* straight beside a torn one gives the card
  // away as a rectangle with a decoration attached to one side.
  const cut = (at: number) => (at + next() * 0.35).toFixed(2);
  return [
    "M 2 0",
    `L ${cut(width)} 0`,
    `L ${cut(width)} ${cut(height)}`,
    `L 2 ${height.toFixed(1)}`,
    `L ${tears.join(" L ")}`,
    "Z",
  ].join(" ");
}

/**
 * The instruments.
 *
 * One per evidence shape, because ADR 0007 puts apparatus where an illustration would go whenever
 * the data cannot identify what it counted. Each is a list of strokes so a component can draw them
 * in order and give the faint ones their own weight; a single path would force one style on all of
 * them. Drawn in a 48 x 48 box, and this one *is* scaled uniformly, so a stroke stays a stroke.
 */
export interface Sketch {
  /** Solid strokes: the object itself. */
  strokes: string[];
  /** Dashed, fainter strokes: what the instrument reaches, rather than what it is. */
  reach?: string[];
  /** Small filled marks -- a feed horn, a route's start. */
  dots?: [number, number, number][];
  /** Read out to anyone who cannot see it. */
  label: string;
}

/** Ticks along a path used by more than one sketch, so the spacing rule lives in one place. */
function ticks(count: number, from: number, to: number, y: number, height: number): string[] {
  const out: string[] = [];
  for (let index = 0; index < count; index += 1) {
    const x = from + ((to - from) * index) / (count - 1);
    out.push(`M ${x.toFixed(1)} ${(y - height / 2).toFixed(1)} l 0 ${height}`);
  }
  return out;
}

export const SKETCHES: Record<string, Sketch> = {
  radar: {
    strokes: [
      // The dish as a lens: a curved face and the rim behind it.
      "M 9 27 C 12 11 26 5 37 12",
      "M 9 27 C 17 24 30 19 37 12",
      "M 21 16 l 5 5",
      // Mast and base.
      "M 20 26 l -2 13",
      "M 11 39 l 15 0",
    ],
    reach: [
      // What it can see, not what it is: two range arcs off the dish face.
      "M 40 8 A 15 15 0 0 1 45 21",
      "M 34 3 A 22 22 0 0 1 45 15",
    ],
    dots: [[24, 20, 1.4]],
    label: "a weather radar: one instrument, one protocol, nightly",
  },
  trawl: {
    strokes: [
      // Net mouth, then the cone tapering to the cod end.
      "M 10 9 L 10 39",
      "M 10 9 C 22 14 33 20 41 24",
      "M 10 39 C 22 34 33 28 41 24",
      // A few meshes, enough to read as netting without becoming a texture.
      "M 15 13 L 19 32",
      "M 22 17 L 26 30",
      "M 29 21 L 32 28",
      // Tow warps.
      "M 10 9 L 3 5",
      "M 10 39 L 3 43",
    ],
    reach: ["M 41 24 L 46 24"],
    label: "a bottom trawl: the same gear over the same stations",
  },
  route: {
    strokes: [
      // A walked line, and the stops along it. BBS is 50 three-minute stops; twelve ticks read as
      // "regularly spaced stops" where fifty would read as a comb.
      "M 5 27 C 13 20 21 33 30 25 C 36 20 41 24 44 21",
      ...ticks(12, 6, 43, 26, 6),
    ],
    dots: [
      [5, 27, 1.8],
      [44, 21, 1.4],
    ],
    label: "a survey route: the same stops, the same season, every year",
  },
  grid: {
    strokes: [
      // A graticule patch, curved so it reads as part of a sphere rather than as graph paper.
      "M 7 12 C 18 9 31 9 42 12",
      "M 6 24 C 18 21 31 21 43 24",
      "M 7 36 C 18 33 31 33 42 36",
      "M 12 10 C 10 20 10 29 12 38",
      "M 24 9 C 23 20 23 28 24 39",
      "M 36 10 C 38 20 38 29 36 38",
    ],
    // Two cells shaded: a gridded surface says something about a cell, never about a place in it.
    reach: [
      "M 13 12 L 23 11 L 23 22 L 13 23 Z",
      "M 25 23 L 36 23 L 36 34 L 25 34 Z",
    ],
    label: "a gridded surface: one value per cell, and nothing finer",
  },
};
