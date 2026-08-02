/**
 * The furniture nobody owns: the browser's scrollbar and MapLibre's controls.
 *
 * Everything else on this page is a Svelte component that can hold an `<svg>` and read a token.
 * These cannot. A `::-webkit-scrollbar-thumb` takes background images and nothing else, and the
 * zoom buttons are nodes MapLibre creates and Svelte therefore cannot scope a style to. So each
 * mark is drawn with the same pen into a detached element, serialised, and handed to CSS as a data
 * URI in a custom property.
 *
 * The cost of that trick is that a data URI cannot carry `var()`: the ink has to be resolved to a
 * hex before it is baked in, which is why `drawFurniture` runs again on every surface change rather
 * than only at boot.
 */

import { HAND, pen, seedOf } from "./ink";

/** Serialise a detached drawing to a CSS `url()`. */
function asDataUri(svg: SVGSVGElement): string {
  return `url("data:image/svg+xml;utf8,${encodeURIComponent(svg.outerHTML)}")`;
}

/**
 * A detached canvas to draw into.
 *
 * The line caps go on the root as presentation attributes rather than in a stylesheet, because a
 * data URI has no stylesheet: rough.js sets `stroke`, `stroke-width` and `fill` on each path and
 * leaves the caps to CSS, so without these the strokes end square and every drawn mark on the
 * furniture has a different finish from every drawn mark on the page.
 */
function blank(width: number, height: number): SVGSVGElement {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  return svg;
}

/** A token resolved to the colour it currently holds, since a data URI cannot hold a `var()`. */
function ink(token: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(token).trim();
}

/** Width of the scrollbar, shared between the drawing and the CSS that places it. */
export const BAR = 15;

/**
 * The scrollbar: a ruled line with a pencil stub sliding down it.
 *
 * The thumb is three images rather than one. A thumb is whatever height the content makes it, so a
 * single stretched drawing would have caps that grow with the page length -- a long document would
 * give it a long blunt nose. A drawn cap at each end that does not stretch, and a tiling middle,
 * keep the stub the same stub at every scroll depth.
 */
function drawScrollbar(): void {
  const pencil = ink("--pencil");
  const rust = ink("--rust-ink");
  const root = document.documentElement.style;

  // One long line rather than a short tile repeated: a tile whose two ends do not meet reads as a
  // dashed line, and the seam lands somewhere different for every length of page.
  const track = blank(BAR, 240);
  const rc = pen(track);
  const centre = BAR / 2;
  track.append(
    rc.line(centre, -2, centre, 242, {
      ...HAND,
      stroke: pencil,
      strokeWidth: 1.1,
      roughness: 1.5,
      bowing: 0.6,
      seed: seedOf("scroll-track"),
    }),
  );
  // Graduations, the same idea as the sliders below: a scale printed on a page rather than a groove
  // cut in a widget. They carry no information here -- a scroll position is not a quantity anyone
  // reads off -- so they are faint and wide apart.
  for (let y = 12; y < 240; y += 40) {
    track.append(
      rc.line(centre - 3, y, centre + 3, y, {
        ...HAND,
        stroke: pencil,
        strokeWidth: 0.9,
        roughness: 1.2,
        seed: seedOf(`scroll-tick-${y}`),
      }),
    );
  }
  root.setProperty("--scroll-track", asDataUri(track));

  const width = BAR - 4;
  const cap = (top: boolean): string => {
    const svg = blank(width, 10);
    svg.append(
      pen(svg).curve(
        top
          ? [
              [1, 9],
              [2, 3],
              [width / 2, 1],
              [width - 2, 3],
              [width - 1, 9],
            ]
          : [
              [1, 1],
              [2, 7],
              [width / 2, 9],
              [width - 2, 7],
              [width - 1, 1],
            ],
        {
          ...HAND,
          stroke: top ? rust : pencil,
          strokeWidth: 1.6,
          roughness: 1.4,
          seed: seedOf(`scroll-cap-${top}`),
        },
      ),
    );
    return asDataUri(svg);
  };

  // Two long strokes rather than a filled shape. A graphite stub seen end-on is two edges with the
  // paper between them; a fill would put a grey lozenge back on the page.
  const middle = blank(width, 60);
  const mid = pen(middle);
  for (const [name, x] of [
    ["stub-left", 2],
    ["stub-right", width - 2],
  ] as const) {
    middle.append(
      mid.line(x, -2, x, 62, {
        ...HAND,
        stroke: pencil,
        strokeWidth: 1.5,
        roughness: 1,
        bowing: 0.4,
        seed: seedOf(name),
      }),
    );
  }

  // The point of the pencil is the end you push, so the rust cap goes on top.
  root.setProperty("--thumb-top", cap(true));
  root.setProperty("--thumb-mid", asDataUri(middle));
  root.setProperty("--thumb-bottom", cap(false));
}

/** Side of a MapLibre control button, fixed by its own stylesheet. */
const BUTTON = 29;

/**
 * MapLibre's zoom and projection buttons, as drawn boxes with drawn marks in them.
 *
 * A separate box per button rather than one round the group: the group is two buttons in one corner
 * and one in another, so its height is not a number this file can know, and a stretched box would
 * be a different box in each corner. Three seeds, because three identical drawings stacked read as
 * a repeated image rather than as three things somebody drew.
 *
 * The two projection states are told apart by shape and not by tint -- a sphere with a meridian
 * against a flat sheet with a fold -- because a control whose state is only a colour has no state
 * for a reader who cannot see the difference.
 */
function drawMapButtons(): void {
  const stroke = ink("--ink-soft");
  const root = document.documentElement.style;
  const half = BUTTON / 2;

  /**
   * The ground each of these sits on: a small chip of paper laid on the map.
   *
   * Filled, unlike every drawn box on a card, and the reason is what is behind it. A card is on
   * paper already, so a box drawn on it needs no ground; these are over a globe of coastlines and
   * data, where an unfilled box is a wire frame with a map showing through the middle of it. The
   * fill is part of the drawing rather than a CSS background so its edge follows the wobble --
   * a paper-coloured rectangle behind a hand-drawn box is a rectangle, which is the thing this
   * whole pass exists to get rid of.
   */
  const chip = (key: string, size: number): string => {
    const svg = blank(size, size);
    svg.append(
      pen(svg).rectangle(3, 3, size - 6, size - 6, {
        ...HAND,
        stroke: ink("--pencil"),
        strokeWidth: 1.2,
        roughness: 2,
        bowing: 1.4,
        fill: ink("--paper"),
        fillStyle: "solid",
        seed: seedOf(key),
      }),
    );
    return asDataUri(svg);
  };

  const icon = (draw: (rc: ReturnType<typeof pen>) => SVGGElement[]): string => {
    const svg = blank(BUTTON, BUTTON);
    svg.append(...draw(pen(svg)));
    return asDataUri(svg);
  };

  const marks: Record<string, string> = {
    "zoom-in": icon((rc) => [
      rc.line(9, half, BUTTON - 9, half, { ...HAND, stroke, seed: seedOf("plus-h") }),
      rc.line(half, 9, half, BUTTON - 9, { ...HAND, stroke, seed: seedOf("plus-v") }),
    ]),
    "zoom-out": icon((rc) => [
      rc.line(9, half, BUTTON - 9, half, { ...HAND, stroke, seed: seedOf("minus") }),
    ]),
    // Currently a globe: a sphere with an equator and a meridian across it.
    "globe-enabled": icon((rc) => [
      rc.circle(half, half, 17, { ...HAND, stroke, roughness: 1.2, seed: seedOf("sphere") }),
      rc.ellipse(half, half, 7.5, 17, { ...HAND, stroke, roughness: 1.2, seed: seedOf("meridian") }),
      rc.line(6, half, BUTTON - 6, half, {
        ...HAND,
        stroke,
        strokeWidth: 1.2,
        seed: seedOf("equator"),
      }),
    ]),
    // Currently flat: a sheet with a fold down it, which is what a projection is.
    globe: icon((rc) => [
      rc.rectangle(6, 9, 17, 11, { ...HAND, stroke, roughness: 1.2, seed: seedOf("sheet") }),
      rc.line(half, 8, half, 21, {
        ...HAND,
        stroke,
        strokeWidth: 1.1,
        roughness: 1.8,
        seed: seedOf("fold"),
      }),
    ]),
  };

  for (const [role, mark] of Object.entries(marks)) {
    root.setProperty(`--ctrl-${role}`, `${mark}, ${chip(`ctrl-${role}`, BUTTON)}`);
  }

  // The attribution's own button, which MapLibre draws as a 24px disc. Only the chip: the "i" on it
  // stays a letter, because a hand-drawn one at that size is a smudge rather than a character.
  root.setProperty("--ctrl-info", chip("ctrl-info", 24));
}

/**
 * The scale bar, as a measure drawn on the page.
 *
 * Split in three for a reason opposite to the scrollbar thumb's: MapLibre sets this element's width
 * in pixels to whatever the current zoom makes the round distance, so it *must* follow that width
 * exactly -- a measure that does not match the distance printed on it is a lie. The rule is one
 * near-horizontal stroke and is allowed to stretch, which costs nothing because stretching a
 * horizontal line horizontally does not change how thick it looks. The end ticks are vertical, so
 * they are separate images pinned to each end and never stretched at all.
 */
function drawScaleBar(): void {
  const stroke = ink("--ink-soft");
  const root = document.documentElement.style;

  const rule = blank(240, 6);
  rule.append(
    pen(rule).line(0, 3.5, 240, 2.6, {
      ...HAND,
      stroke,
      strokeWidth: 1.4,
      bowing: 0.8,
      seed: seedOf("scale-rule"),
    }),
  );
  root.setProperty("--scale-rule", asDataUri(rule));

  for (const end of ["left", "right"] as const) {
    const tick = blank(4, 9);
    tick.append(
      pen(tick).line(2, 8, 2, 0, {
        ...HAND,
        stroke,
        strokeWidth: 1.4,
        roughness: 1.2,
        seed: seedOf(`scale-${end}`),
      }),
    );
    root.setProperty(`--scale-${end}`, asDataUri(tick));
  }
}

/**
 * Redraw everything CSS cannot draw for itself.
 *
 * Called at boot and on every surface change, because the ink is baked into each data URI. Cheap
 * enough to run eagerly: nine small drawings, well under a frame, against the alternative of a
 * black page with a parchment scrollbar down the side of it.
 */
export function drawFurniture(): void {
  drawScrollbar();
  drawMapButtons();
  drawScaleBar();
}
