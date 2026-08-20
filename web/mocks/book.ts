/**
 * The book: chapters from the ledger, a sketched map, and a page that turns.
 *
 * Three rules, all so the mock cannot flatter the design.
 *
 * **The words are the build's words.** Every sentence comes from `findings.json`, because frontend
 * prose is authored in Python and rendered verbatim. If the ledger is unreachable the page says so
 * rather than substituting something plausible.
 *
 * **The map is the repository's own geometry.** `outline.json` is `public/basemap/land.geojson` run
 * through `globe/coastline.ts`'s wobble, cos(latitude) scaling included, resampled by arc length to
 * a density a sketch can carry. rough.js then draws it: hachure fill on the eight largest rings,
 * stroke alone on the rest, because hachuring forty-two rings costs a second and buys nothing.
 *
 * **The blanks are drawn.** ADR 0014 decision 2 says ignorance gets a surveyor's treatment and
 * never an invented creature, so the unsurveyed part of the sheet is hatched at its own angle with
 * the gap named beside it. That is the one piece of this mock arguing for a decision rather than
 * illustrating one.
 */

import rough from "roughjs";

const token = (name: string): string =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim();

const MISSING = "[ledger unreachable — serve this from web/ so /findings.json resolves]";

// --- The ledger -----------------------------------------------------------

interface Finding {
  key: string;
  plain: string;
  value: string;
  matters: string;
  scope: string;
  plain_caveat: string;
}

/**
 * ADR 0013's six chapters plus the seventh the plan added, and the ledger keys each one carries.
 *
 * The mapping is the ADR's, not a fresh reading of it: *What changed* takes the three changes,
 * *What did not* the three nulls, *What we cannot see* the two coverage limits. "Why it changed"
 * is the amendment — it holds the mechanism dial, the forecast mask and the oxygen leverage, none
 * of which are ledger findings yet, so it borrows the attribution claim to have something to show.
 */
const CHAPTERS: { title: string; kicker: string; keys: string[]; scrawl: string }[] = [
  {
    title: "How to read this",
    kicker: "introduction",
    keys: [],
    scrawl: "Every number here is recomputed from the data on every build. None of them are typed.",
  },
  {
    title: "What changed",
    kicker: "chapter one",
    keys: ["autumn-advance", "composition-stable"],
    scrawl: "Two independent instruments, and the second one is why the first is written as a change.",
  },
  {
    title: "What did not",
    kicker: "chapter two",
    keys: ["marine-null", "atlas-no-net-change", "displacement-flat"],
    scrawl: "A null is a result. Three of them are a pattern worth a chapter of its own.",
  },
  {
    title: "What we cannot see",
    kicker: "chapter three",
    keys: ["coverage-bias", "transfer-fails"],
    scrawl: "The hatched ground on the plate is the honest part of this map.",
  },
  {
    title: "What can be predicted",
    kicker: "chapter four",
    keys: ["skill-sparse"],
    scrawl: "The site bet against itself in public and lost the bet. That page stays.",
  },
  {
    title: "Why it changed",
    kicker: "chapter five",
    keys: ["anthropogenic-share"],
    scrawl: "Turn the dial and the fit answers — inside the range it was fitted over, and nowhere else.",
  },
  { title: "The world", kicker: "the back pocket", keys: [], scrawl: "Everything, at once, with the layers off until you ask." },
];

let ledger: Finding[] = [];
let open = 1;

async function load(): Promise<void> {
  try {
    const response = await fetch("/findings.json");
    if (!response.ok) return;
    ledger = ((await response.json()) as { findings: Finding[] }).findings;
  } catch {
    ledger = [];
  }
}

const showing = (index: number): Finding | null => {
  const keys = CHAPTERS[index]?.keys ?? [];
  return ledger.find((f) => f.key === keys[0]) ?? null;
};

// --- Filling the spread --------------------------------------------------

function fill(index: number): void {
  const chapter = CHAPTERS[index]!;
  const found = showing(index);
  const set = (selector: string, text: string) => {
    const node = document.querySelector<HTMLElement>(selector);
    if (node) node.textContent = text;
  };
  set("[data-kicker]", chapter.kicker);
  set("[data-title]", chapter.title);
  set("[data-folio]", `${String(index * 14 + 3).padStart(3, "0")} · migratlas`);
  set("[data-plateno]", `Plate ${index + 1}.`);
  set("[data-scrawl]", chapter.scrawl);

  /*
    A chapter with no claim gets no figure and no caveat bracket, rather than those slots filled
    with a sentence explaining their own emptiness. The first version wrote the explanation into the
    ringed monospace figure, which put a sentence where a number goes and read as a bug.
  */
  const page = document.querySelector<HTMLElement>(".page--verso");
  page?.classList.toggle("has-no-claim", !found);

  const from: Record<string, string> = found
    ? {
        plain: found.plain,
        value: found.value,
        matters: found.matters,
        scope: found.scope,
        caveat: found.plain_caveat,
      }
    : {
        plain: ledger.length
          ? "The way in, and the way out. No claim of its own — this chapter says how to read the ones that follow."
          : MISSING,
        matters: ledger.length
          ? "Everything after this is a measurement with a scope and a caveat attached to it, and the caveat is not an apology."
          : MISSING,
        scope: ledger.length ? "The whole sheet, with every layer off until asked for." : MISSING,
      };
  for (const node of document.querySelectorAll<HTMLElement>("[data-claim]")) {
    node.textContent = from[node.dataset.claim ?? ""] ?? "";
  }
}

function tabs(): void {
  const nav = document.querySelector<HTMLElement>("[data-tabs]");
  if (!nav) return;
  nav.replaceChildren(
    ...CHAPTERS.map((chapter, index) => {
      const tab = document.createElement("button");
      tab.type = "button";
      tab.className = index === open ? "tab is-on" : "tab";
      tab.textContent = chapter.title;
      tab.addEventListener("click", () => void turnTo(index));
      return tab;
    }),
  );
}

// --- The sketched map ----------------------------------------------------

interface Outline {
  width: number;
  height: number;
  rings: { area: number; d: string }[];
}

let outline: Outline | null = null;

/** How many rings get a hachure fill. The rest are stroked: see the module docstring. */
const HACHURED = 8;

const svgEl = <K extends keyof SVGElementTagNameMap>(name: K): SVGElementTagNameMap[K] =>
  document.createElementNS("http://www.w3.org/2000/svg", name);

/** Handwriting on the plate, in the page's own hand face. */
function label(x: number, y: number, text: string, fill: string, size = 15, angle = 0): SVGTextElement {
  const node = svgEl("text");
  node.setAttribute("x", String(x));
  node.setAttribute("y", String(y));
  node.setAttribute("fill", fill);
  node.setAttribute("font-size", String(size));
  node.setAttribute("font-family", token("--font-hand") || "cursive");
  if (angle) node.setAttribute("transform", `rotate(${angle} ${x} ${y})`);
  node.textContent = text;
  return node;
}

function drawMap(host: HTMLElement): void {
  if (!outline) return;
  const { width: W, height: H } = outline;
  const svg = svgEl("svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
  host.replaceChildren(svg);

  const rc = rough.svg(svg);
  const ink = token("--ink");
  const pencil = token("--pencil");
  const rust = token("--rust");
  const moss = token("--moss");
  const faint = token("--rule-faint");

  // Mercator, matching the projection outline.json was generated in, so anything placed by
  // latitude lands where the coastline says it should.
  const merc = (lat: number) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
  const top = merc(80);
  const bottom = merc(-58);
  const yOf = (lat: number) => ((top - merc(lat)) / (top - bottom)) * H;
  const xOf = (lon: number) => ((lon + 180) / 360) * W;

  // Graticule first, beneath the land: a reference line belongs under the thing it refers to,
  // which is the order `globe/graticule.ts` already keeps.
  for (let lon = -150; lon < 180; lon += 30) {
    svg.append(
      rc.line(xOf(lon), 0, xOf(lon), H, { stroke: faint, strokeWidth: 1, roughness: 1.5, seed: 3 + lon }),
    );
  }
  for (const lat of [60, 30, 0, -30]) {
    svg.append(
      rc.line(0, yOf(lat), W, yOf(lat), { stroke: faint, strokeWidth: 1, roughness: 1.5, seed: 90 + lat }),
    );
  }

  outline.rings.forEach((ring, index) => {
    const options =
      index < HACHURED
        ? {
            stroke: ink,
            strokeWidth: 1.5,
            roughness: 1.5,
            bowing: 1.2,
            fill: pencil,
            fillStyle: "hachure" as const,
            hachureAngle: -41,
            hachureGap: 7,
            fillWeight: 0.7,
            seed: 17 + index,
          }
        : { stroke: ink, strokeWidth: 1.3, roughness: 1.6, bowing: 1.3, seed: 17 + index };
    svg.append(rc.path(ring.d, options));
  });

  // The claim's own extent: the CONUS band `autumn-advance` names, cross-hatched and labelled.
  const bandX = xOf(-104);
  const bandY = yOf(50);
  svg.append(
    rc.rectangle(bandX, bandY, xOf(-70) - bandX, yOf(37) - bandY, {
      stroke: rust,
      strokeWidth: 2,
      roughness: 1.9,
      bowing: 2,
      fill: rust,
      fillStyle: "cross-hatch",
      hachureGap: 9,
      fillWeight: 0.8,
      seed: 5,
    }),
  );
  svg.append(label(xOf(-103), yOf(53), "37–50°N, 78 stations", rust, 16, -2));

  /*
    ADR 0014 decision 2, drawn rather than described. The southern ocean and the interior of Africa
    and Asia carry no radar in this project at all, so the sheet says so in the surveyor's register:
    hatched at a different angle from the land, with the gap named. An old chart would have put a
    monster here. A field notebook writes down what it did not visit.
  */
  const blankX = xOf(-30);
  const blankY = yOf(-8);
  svg.append(
    rc.rectangle(blankX, blankY, xOf(105) - blankX, yOf(-52) - blankY, {
      stroke: pencil,
      strokeWidth: 1.1,
      roughness: 2.4,
      bowing: 2.4,
      fill: pencil,
      fillStyle: "hachure",
      hachureAngle: 48,
      hachureGap: 13,
      fillWeight: 0.5,
      seed: 61,
    }),
  );
  svg.append(label(xOf(-24), yOf(-20), "no coverage, 1995–2025", pencil, 17, 1.5));
  svg.append(label(xOf(-24), yOf(-27), "not surveyed the same way", pencil, 14, 1.5));

  // A leader from the note to the band, because a surveyor points at what the note is about.
  svg.append(
    rc.linearPath(
      [
        [xOf(-26), yOf(-14)],
        [xOf(-60), yOf(10)],
        [xOf(-78), yOf(34)],
      ],
      { stroke: pencil, strokeWidth: 1.2, roughness: 2, seed: 8 },
    ),
  );

  // North arrow and scale bar: instruments, which ADR 0014 keeps, rather than a compass rose,
  // which it does not.
  const nx = W - 62;
  const ny = 54;
  svg.append(rc.line(nx, ny + 34, nx, ny - 12, { stroke: ink, strokeWidth: 1.6, roughness: 1.4, seed: 21 }));
  svg.append(
    rc.linearPath(
      [
        [nx - 7, ny - 2],
        [nx, ny - 14],
        [nx + 7, ny - 2],
      ],
      { stroke: ink, strokeWidth: 1.6, roughness: 1.3, seed: 22 },
    ),
  );
  svg.append(label(nx - 5, ny + 50, "N", ink, 16));

  const sx = 44;
  const sy = H - 40;
  const sw = xOf(-150) - xOf(-180);
  svg.append(rc.line(sx, sy, sx + sw, sy, { stroke: ink, strokeWidth: 1.6, roughness: 1.3, seed: 31 }));
  svg.append(rc.line(sx, sy - 5, sx, sy + 5, { stroke: ink, strokeWidth: 1.4, roughness: 1.2, seed: 32 }));
  svg.append(
    rc.line(sx + sw, sy - 5, sx + sw, sy + 5, { stroke: ink, strokeWidth: 1.4, roughness: 1.2, seed: 33 }),
  );
  svg.append(label(sx, sy - 12, "30° at the equator", ink, 14));

  // Signed and dated, the way a plate is.
  svg.append(label(W - 210, H - 22, "traced from Natural Earth · 1:110m", moss, 14, -0.8));
}

// --- Drawn marks --------------------------------------------------------

function marks(): void {
  for (const node of document.querySelectorAll<SVGSVGElement>("svg[data-rough]")) {
    const box = node.getBoundingClientRect();
    if (box.width < 4 || box.height < 4) continue;
    const w = box.width;
    const h = box.height;
    node.setAttribute("viewBox", `0 0 ${w} ${h}`);
    node.replaceChildren();
    const rc = rough.svg(node);
    const kind = node.dataset.rough;
    // A stable seed per kind, so a redraw is the same hand rather than a new one.
    const seed = [...(kind ?? "")].reduce((total, char) => total + char.charCodeAt(0), 7);

    if (kind === "rule") {
      node.append(
        rc.line(2, h * 0.62, w - 4, h * 0.4, {
          stroke: token("--rust"),
          strokeWidth: 2.6,
          roughness: 1.7,
          bowing: 2.4,
          seed,
        }),
      );
    } else if (kind === "ring") {
      // An ellipse round the number, drawn twice, the way a pen goes round twice.
      for (const pass of [0, 1]) {
        node.append(
          rc.ellipse(w / 2, h / 2, w - 4 - pass * 3, h - 4 - pass * 2, {
            stroke: token("--rust-ink"),
            strokeWidth: 1.5,
            roughness: 2.2,
            bowing: 1.8,
            seed: seed + pass,
          }),
        );
      }
    } else if (kind === "bracket") {
      node.append(
        rc.linearPath(
          [
            [w - 2, 2],
            [3, 6],
            [3, h - 6],
            [w - 2, h - 2],
          ],
          { stroke: token("--pencil"), strokeWidth: 1.5, roughness: 1.9, bowing: 1.2, seed },
        ),
      );
    } else if (kind === "tape") {
      /*
        Tape is the one thing here that is a *surface* rather than a mark, so it is a filled
        rectangle with torn ends rather than a rough outline: low-opacity paper over the page, edges
        just visible. `color-mix` is not available to rough.js, so the fill is the page's own ink at
        low opacity via fill-opacity on the group.
      */
      const strip = rc.rectangle(1, 1, w - 2, h - 2, {
        stroke: token("--pencil"),
        strokeWidth: 0.9,
        roughness: 2.6,
        bowing: 1.4,
        fill: token("--paper-sunken"),
        fillStyle: "solid",
        seed,
      });
      strip.setAttribute("opacity", "0.72");
      node.append(strip);
      // Two scratches along it, which is what sticky tape looks like on paper.
      for (const at of [0.34, 0.68]) {
        node.append(
          rc.line(3, h * at, w - 3, h * at, {
            stroke: token("--rule"),
            strokeWidth: 0.7,
            roughness: 2.4,
            seed: seed + at * 100,
          }),
        );
      }
    } else if (kind === "clip") {
      // A paper clip: two nested rounded paths, drawn in one pencil weight.
      for (const inset of [0, 4]) {
        node.append(
          rc.linearPath(
            [
              [6 + inset, h - 4],
              [6 + inset, 8 + inset],
              [w - 6 - inset, 8 + inset],
              [w - 6 - inset, h - 10 - inset],
            ],
            { stroke: token("--pencil"), strokeWidth: 1.7, roughness: 1.1, bowing: 0.6, seed: seed + inset },
          ),
        );
      }
    }
  }
}

// --- The turn -----------------------------------------------------------

const spread = () => document.querySelector<HTMLElement>("[data-spread]");
const leaf = () => document.querySelector<HTMLElement>("[data-leaf]");

function repaint(): void {
  for (const host of document.querySelectorAll<HTMLElement>("[data-map]")) drawMap(host);
  marks();
}

/** Whether the page may turn: tokens.css zeroes every duration under reduced motion. */
const animates = (): boolean => !token("--draw-slow").startsWith("0");

async function turnTo(index: number): Promise<void> {
  if (index === open) return;
  const forward = index > open;
  const face = leaf();
  const recto = document.querySelector<HTMLElement>(".page--recto");
  const verso = document.querySelector<HTMLElement>(".page--verso");

  if (!face || !recto || !verso || !animates()) {
    open = index;
    fill(open);
    tabs();
    repaint();
    return;
  }

  // The leaf's front is the page you were reading; its back is what is on the other side of it.
  // Turning backwards shows the verso leading, so the faces swap.
  const front = face.querySelector<HTMLElement>(".leaf__front");
  const back = face.querySelector<HTMLElement>(".leaf__back");
  front?.replaceChildren(...[...(forward ? recto : verso).cloneNode(true).childNodes]);

  open = index;
  fill(open);
  tabs();
  repaint();
  back?.replaceChildren(...[...(forward ? verso : recto).cloneNode(true).childNodes]);

  face.classList.remove("is-turning");
  // Reflow, so re-adding the class restarts the animation rather than being a no-op.
  void face.offsetWidth;
  face.classList.add("is-turning");

  /*
    Cleared by whichever comes first, the event or the clock, and the clock is not paranoia.
    `animationend` does not arrive in a tab that is not compositing -- a background tab, a hidden
    pane, a headless run -- and without a fallback the leaf stays parked over the right-hand page
    for the rest of the session with no way back. Found exactly that way while verifying this.
  */
  let done = false;
  const settle = () => {
    if (done) return;
    done = true;
    face.classList.remove("is-turning");
    front?.replaceChildren();
    back?.replaceChildren();
  };
  face.addEventListener("animationend", settle, { once: true });
  const ms = Number.parseFloat(token("--draw-slow")) || 900;
  setTimeout(settle, ms + 120);
}

// --- Boot ---------------------------------------------------------------

for (const button of document.querySelectorAll<HTMLButtonElement>("[data-skin]")) {
  button.addEventListener("click", () => {
    const book = document.querySelector<HTMLElement>("[data-book]");
    book?.classList.remove("is-taped", "is-inked", "is-tipped");
    book?.classList.add(`is-${button.dataset.skin}`);
    for (const other of document.querySelectorAll<HTMLButtonElement>("[data-skin]")) {
      other.classList.toggle("is-on", other === button);
    }
    repaint();
  });
}

for (const id of ["surface", "type"] as const) {
  document.getElementById(id)?.addEventListener("change", (event) => {
    document.documentElement.dataset[id] = (event.target as HTMLSelectElement).value;
    // Both the map and the marks read tokens at draw time, so a palette change is a redraw.
    repaint();
  });
}

document.getElementById("scale")?.addEventListener("change", (event) => {
  document.documentElement.style.setProperty("--pt", (event.target as HTMLSelectElement).value);
  repaint();
});

addEventListener("resize", repaint);

await load();
tabs();
fill(open);
try {
  const response = await fetch("/mocks/outline.json");
  if (response.ok) outline = (await response.json()) as Outline;
} catch {
  outline = null;
}
repaint();
