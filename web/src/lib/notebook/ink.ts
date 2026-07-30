/**
 * Hand-drawn geometry: the paths that make a rule read as drawn and an instrument as sketched.
 *
 * All of it is deterministic. A wobble seeded from `Math.random()` would redraw differently on every
 * render, which turns a quiet line into a flicker, and would make a screenshot test meaningless. The
 * seed comes from the claim's own key instead, so each claim has its own consistent hand and the
 * same claim looks the same forever.
 *
 * **Paths are generated at the real pixel size, never stretched.** The first version drew a rule in
 * a 100-unit box and stretched it with `preserveAspectRatio="none"` plus `vector-effect:
 * non-scaling-stroke`. Those two do not compose: the path stays in user units while the dash pattern
 * is applied in screen units, so a `stroke-dasharray: 110` meant to cover the whole line became four
 * dashes and a gap. Generating at the measured width costs a `clientWidth` read and removes the
 * whole class of problem -- the stroke is uniform because nothing is scaled.
 */

/** FNV-1a, 32-bit. Any small stable string hash would do; this one is four lines and has no bias. */
function hash(text: string): number {
  let value = 0x811c9dc5;
  for (let index = 0; index < text.length; index += 1) {
    value ^= text.charCodeAt(index);
    value = Math.imul(value, 0x01000193);
  }
  return value >>> 0;
}

/** A deterministic sequence in [-1, 1] from a seed. Not good randomness; good enough for a pen. */
function jitter(seed: number): () => number {
  let state = seed || 1;
  return () => {
    state = (Math.imul(state, 1103515245) + 12345) >>> 0;
    return (state / 0xffffffff) * 2 - 1;
  };
}

/** Height of the box a rule is drawn in, so the component and the generator agree on one number. */
export const RULE_HEIGHT = 8;

/**
 * An underline that does not sit flat, generated across `width` pixels.
 *
 * One control point about every 55px: closer and the wobble reads as noise, further and the line
 * looks like a deliberate curve. A drawn line drifts across its length *and* wobbles locally, so
 * there is a low-frequency arc plus per-point jitter, both kept under about 1.5px — more than that
 * stops reading as a line and starts reading as a squiggle.
 */
export function underline(key: string, width: number): string {
  if (width <= 0) return "";
  const next = jitter(hash(key));
  const steps = Math.max(4, Math.round(width / 55));
  const points: string[] = [];
  for (let step = 0; step <= steps; step += 1) {
    const x = (step / steps) * width;
    const drift = Math.sin((step / steps) * Math.PI) * 0.8;
    const y = RULE_HEIGHT / 2 + drift + next() * 0.7;
    points.push(`${x.toFixed(1)} ${y.toFixed(2)}`);
  }
  return `M ${points.join(" L ")}`;
}

/** Width of the box a margin bracket is drawn in. */
export const BRACKET_WIDTH = 8;

/**
 * A bracket for the margin: a vertical stroke with hooked ends, as drawn beside a paragraph.
 *
 * Generated across `height` pixels for the same reason as `underline`. The hooks are a fixed 3px
 * whatever the height, which is the point: stretched, a 400px-tall margin turned a 2px hook into an
 * 8px flag.
 */
export function bracket(key: string, height: number): string {
  if (height <= 0) return "";
  const next = jitter(hash(key) ^ 0x5bf03635);
  const steps = Math.max(4, Math.round(height / 70));
  const spine: string[] = [];
  for (let step = 0; step <= steps; step += 1) {
    const y = 3 + (step / steps) * (height - 6);
    spine.push(`${(BRACKET_WIDTH - 2.5 + next() * 0.7).toFixed(2)} ${y.toFixed(1)}`);
  }
  return `M 2.5 1 L ${spine.join(" L ")} L 2.5 ${(height - 1).toFixed(1)}`;
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
