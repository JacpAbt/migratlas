/**
 * The furniture nobody owns: the browser's scrollbar.
 *
 * Everything else on this page is a Svelte component that can hold an `<svg>` and read a token. The
 * scrollbar cannot: a `::-webkit-scrollbar-thumb` takes background images and nothing else. So each
 * mark is drawn with the same pen into a detached element, serialised, and handed to CSS as a data
 * URI in a custom property. (MapLibre's controls were drawn here the same way, until the atlas
 * replaced the globe and its controls are words on the page.)
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
  // Graduations, the same idea as the atlas's clock: a scale printed on a page rather than a groove
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

/**
 * Redraw everything CSS cannot draw for itself.
 *
 * Called at boot and on every surface change, because the ink is baked into each data URI. Cheap
 * enough to run eagerly: four small drawings, well under a frame, against the alternative of a
 * black page with a parchment scrollbar down the side of it.
 */
export function drawFurniture(): void {
  drawScrollbar();
}
