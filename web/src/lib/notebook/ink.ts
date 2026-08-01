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

/**
 * A rectangle drawn by hand: four wobbled sides, and the corners overshoot.
 *
 * The overshoot is the whole thing. A wobbled rectangle whose corners meet exactly reads as a
 * border with a rendering fault; one where the pen carries a couple of pixels past the turn reads
 * as drawn. Real hand-drawn boxes overshoot because stopping a pen exactly on a corner is harder
 * than not.
 *
 * One continuous path rather than four, so it can stroke on in a single dash animation and so a
 * reader watches it being drawn in the order a hand would draw it.
 */
export function boxDrawn(key: string, width: number, height: number, overshoot = 3): string {
  if (width <= 0 || height <= 0) return "";
  const next = jitter(hash(key) ^ 0x2f6a88c1);
  const wobble = () => next() * 0.8;

  // Along each side, a control point roughly every 60px, same cadence as `underline`. Fewer and
  // the side is a straight line with a kink; more and it reads as a squiggle.
  const along = (
    from: [number, number],
    to: [number, number],
    perpendicular: [number, number],
  ): string[] => {
    const span = Math.hypot(to[0] - from[0], to[1] - from[1]);
    const steps = Math.max(2, Math.round(span / 60));
    const points: string[] = [];
    for (let step = 1; step <= steps; step += 1) {
      const t = step / steps;
      const drift = Math.sin(t * Math.PI) * 0.6 + wobble();
      points.push(
        `${(from[0] + (to[0] - from[0]) * t + perpendicular[0] * drift).toFixed(1)} ` +
          `${(from[1] + (to[1] - from[1]) * t + perpendicular[1] * drift).toFixed(1)}`,
      );
    }
    return points;
  };

  const [w, h, o] = [width, height, overshoot];
  return [
    `M ${o.toFixed(1)} ${(1 + wobble()).toFixed(1)}`,
    `L ${along([o, 1], [w - 1, 1], [0, -1]).join(" L ")}`,
    `L ${along([w - 1, 1], [w - 1, h - 1], [1, 0]).join(" L ")}`,
    `L ${along([w - 1, h - 1], [1, h - 1], [0, 1]).join(" L ")}`,
    `L ${along([1, h - 1], [1, 1], [-1, 0]).join(" L ")}`,
    // Past the start, which is what makes it a drawn box rather than a closed shape.
    `L ${(1 + o).toFixed(1)} ${(1 - wobble()).toFixed(1)}`,
  ].join(" ");
}

/**
 * The outline of a sheet of paper, torn out along its left edge.
 *
 * A closed path, so it can be filled as the card's ground and clipped to. Only the left edge is
 * ragged: this is a leaf torn from a bound notebook, not hand-made paper with a deckle on all four
 * sides. One irregular edge reads as "removed from something"; four read as an effect.
 *
 * The right and bottom edges get a much smaller waver -- a cut edge is straight, and a cut edge
 * that is *perfectly* straight beside a torn one gives the whole card away as a rectangle with a
 * decoration attached to one side.
 */
export function sheetEdge(key: string, width: number, height: number): string {
  if (width <= 0 || height <= 0) return "";
  const next = jitter(hash(key) ^ 0x71c3d2a5);

  // A tear is a low-frequency wander with high-frequency nicks in it, and the nicks are what stop
  // it reading as a wave. Every 9px, because at 20 the tear looks like a coastline and at 4 the
  // path gets long enough to matter in a clip.
  const tears: string[] = [];
  const steps = Math.max(6, Math.round(height / 9));
  for (let step = steps; step >= 0; step -= 1) {
    const y = (step / steps) * height;
    const wander = Math.sin((step / steps) * Math.PI * 1.7) * 1.6;
    const nick = next() * 1.4 + (step % 3 === 0 ? next() * 1.1 : 0);
    tears.push(`${Math.max(0, wander + nick + 2).toFixed(1)} ${y.toFixed(1)}`);
  }

  const cut = (at: number) => (at + next() * 0.35).toFixed(2);
  return [
    `M 2 0`,
    `L ${cut(width)} 0`,
    `L ${cut(width)} ${cut(height)}`,
    `L 2 ${height.toFixed(1)}`,
    `L ${tears.join(" L ")}`,
    "Z",
  ].join(" ");
}

/**
 * A lasso: the loop drawn round something on a page to mean *this one*.
 *
 * An ellipse that does not close and overshoots where it started, because that is what happens
 * when a hand comes back round to a point it is not looking at. The gap is at the top left, where
 * a right-handed loop drawn clockwise from the lower left tends to end.
 *
 * Used where a checked state would otherwise be a background colour. A circled option reads as a
 * choice someone made; a filled pill reads as a setting the interface has.
 */
export function lasso(key: string, width: number, height: number): string {
  if (width <= 0 || height <= 0) return "";
  const next = jitter(hash(key) ^ 0x13a7f0e9);
  const [cx, cy] = [width / 2, height / 2];
  const [rx, ry] = [width / 2 - 1, height / 2 - 1];

  // From just past the top left, clockwise, and a little past the start again.
  const from = -2.5;
  const to = 3.9;
  const steps = 22;
  const points: string[] = [];
  for (let step = 0; step <= steps; step += 1) {
    const angle = from + ((to - from) * step) / steps;
    const wobble = 1 + next() * 0.035;
    points.push(
      `${(cx + Math.cos(angle) * rx * wobble).toFixed(1)} ` +
        `${(cy + Math.sin(angle) * ry * wobble).toFixed(1)}`,
    );
  }
  return `M ${points.join(" L ")}`;
}

/** A tick, in two strokes as a hand makes it: a short fall and a long rise. */
export function tick(key: string, size: number): string {
  if (size <= 0) return "";
  const next = jitter(hash(key) ^ 0x4d2b9f31);
  const nudge = () => next() * 0.5;
  return (
    `M ${(size * 0.18 + nudge()).toFixed(1)} ${(size * 0.52 + nudge()).toFixed(1)} ` +
    `L ${(size * 0.42 + nudge()).toFixed(1)} ${(size * 0.78 + nudge()).toFixed(1)} ` +
    `L ${(size * 0.86 + nudge()).toFixed(1)} ${(size * 0.2 + nudge()).toFixed(1)}`
  );
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
