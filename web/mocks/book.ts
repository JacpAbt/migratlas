/**
 * Wiring for the four book layouts: real ledger text, the real drawn coastline, real tokens.
 *
 * Two rules this file keeps, both so the mock cannot flatter the design:
 *
 * The prose is fetched from `findings.json` rather than typed in. Frontend prose is authored in
 * Python and rendered verbatim, so a mock with hand-written copy would be judging sentences the
 * build cannot produce. If the ledger is unreachable the page says so instead of substituting
 * plausible text.
 *
 * The map is the repository's own land geometry with the repository's own wobble already applied
 * -- `outline.json`, generated from `public/basemap/land.geojson` through `globe/coastline.ts`'s
 * formula including the cos(latitude) scaling. It is a still, not MapLibre, which is the honest
 * limit of this mock: it shows the treatment and the composition, not the interaction.
 */

import rough from "roughjs";

const CHAPTERS = [
  "Introduction",
  "What changed",
  "What did not",
  "What we cannot see",
  "What can be predicted",
  "Why it changed",
  "The world",
] as const;

/** The chapter these mocks are standing in, so tabs and heading cannot disagree. */
const OPEN_AT = 1;

const token = (name: string): string =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim();

// --- The claim, from the ledger --------------------------------------------

interface Finding {
  key: string;
  plain: string;
  value: string;
  matters: string;
  scope: string;
  plain_caveat: string;
}

async function claim(): Promise<Finding | null> {
  try {
    const response = await fetch("/findings.json");
    if (!response.ok) return null;
    const document_ = (await response.json()) as { findings: Finding[] };
    return document_.findings.find((f) => f.key === "autumn-advance") ?? null;
  } catch {
    return null;
  }
}

function fill(found: Finding | null): void {
  const from: Record<string, string> = found
    ? {
        plain: found.plain,
        value: found.value,
        matters: found.matters,
        scope: found.scope,
        caveat: found.plain_caveat,
      }
    : {};
  for (const node of document.querySelectorAll<HTMLElement>("[data-claim]")) {
    const which = node.dataset.claim ?? "";
    node.textContent =
      from[which] ?? "[ledger unreachable — run the dev server from web/ so /findings.json resolves]";
  }
}

// --- The tabs --------------------------------------------------------------

function tabs(): void {
  for (const nav of document.querySelectorAll<HTMLElement>("[data-tabs]")) {
    nav.replaceChildren(
      ...CHAPTERS.map((name, index) => {
        const tab = document.createElement("button");
        tab.type = "button";
        tab.className = index === OPEN_AT ? "tab is-on" : "tab";
        tab.textContent = name;
        return tab;
      }),
    );
  }
}

// --- The map --------------------------------------------------------------

interface Outline {
  width: number;
  height: number;
  paths: string[];
}

async function outline(): Promise<Outline | null> {
  try {
    const response = await fetch("/mocks/outline.json");
    return response.ok ? ((await response.json()) as Outline) : null;
  } catch {
    return null;
  }
}

function drawMap(host: HTMLElement, shape: Outline): void {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${shape.width} ${shape.height}`);
  svg.setAttribute("preserveAspectRatio", "xMidYMid slice");

  // Graticule under the land, as `globe/graticule.ts` orders them: a reference line belongs beneath
  // the thing it is a reference for.
  const grid = document.createElementNS("http://www.w3.org/2000/svg", "g");
  grid.setAttribute("stroke", token("--rule-faint"));
  grid.setAttribute("stroke-width", "1");
  grid.setAttribute("fill", "none");
  for (let i = 1; i < 12; i += 1) {
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    const x = (shape.width / 12) * i;
    line.setAttribute("x1", String(x));
    line.setAttribute("x2", String(x));
    line.setAttribute("y1", "0");
    line.setAttribute("y2", String(shape.height));
    grid.append(line);
  }
  for (let i = 1; i < 5; i += 1) {
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    const y = (shape.height / 5) * i;
    line.setAttribute("x1", "0");
    line.setAttribute("x2", String(shape.width));
    line.setAttribute("y1", String(y));
    line.setAttribute("y2", String(y));
    grid.append(line);
  }
  svg.append(grid);

  const land = document.createElementNS("http://www.w3.org/2000/svg", "g");
  land.setAttribute("fill", token("--paper"));
  land.setAttribute("stroke", token("--pencil"));
  land.setAttribute("stroke-width", "1.1");
  land.setAttribute("stroke-linejoin", "round");
  for (const d of shape.paths) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", d);
    land.append(path);
  }
  svg.append(land);

  // One claim's extent, drawn where the claim is about: the CONUS band between 37 and 50 N, which
  // is what `autumn-advance`'s scope names. Placed from the same projection the paths use.
  const merc = (lat: number) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
  const top = merc(78);
  const bottom = merc(-60);
  const yOf = (lat: number) => ((top - merc(lat)) / (top - bottom)) * shape.height;
  const xOf = (lon: number) => ((lon + 180) / 360) * shape.width;
  const band = document.createElementNS("http://www.w3.org/2000/svg", "rect");
  band.setAttribute("x", String(xOf(-104)));
  band.setAttribute("y", String(yOf(50)));
  band.setAttribute("width", String(xOf(-70) - xOf(-104)));
  band.setAttribute("height", String(yOf(37) - yOf(50)));
  band.setAttribute("fill", token("--rust-ink"));
  band.setAttribute("fill-opacity", "0.16");
  band.setAttribute("stroke", token("--rust"));
  band.setAttribute("stroke-width", "1.4");
  band.setAttribute("stroke-dasharray", "6 4");
  svg.append(band);

  host.replaceChildren(svg);
}

// --- The drawn marks -----------------------------------------------------

function marks(): void {
  for (const node of document.querySelectorAll<SVGSVGElement>("svg[data-rough]")) {
    const box = node.getBoundingClientRect();
    const w = Math.max(box.width, 8);
    const h = Math.max(box.height, 8);
    node.setAttribute("viewBox", `0 0 ${w} ${h}`);
    node.replaceChildren();
    // A stable seed per mark, so a redraw is the same hand rather than a new one.
    const rc = rough.svg(node);
    node.append(
      rc.line(2, h * 0.6, w - 4, h * 0.42, {
        stroke: token("--rust"),
        strokeWidth: 2.4,
        roughness: 1.6,
        bowing: 2,
        seed: 11,
      }),
    );
  }
}

// --- Boot ----------------------------------------------------------------

let shape: Outline | null = null;

function paintMaps(): void {
  if (!shape) return;
  for (const host of document.querySelectorAll<HTMLElement>("[data-map]")) {
    drawMap(host, shape);
  }
}

function show(which: string): void {
  for (const section of document.querySelectorAll<HTMLElement>(".mock")) {
    section.hidden = section.id !== which;
  }
  for (const button of document.querySelectorAll<HTMLButtonElement>("[data-go]")) {
    button.classList.toggle("is-on", button.dataset.go === which);
  }
  // Both of these measure laid-out boxes, so they cannot run while the section is hidden.
  paintMaps();
  marks();
}

for (const button of document.querySelectorAll<HTMLButtonElement>("[data-go]")) {
  button.addEventListener("click", () => show(button.dataset.go ?? "a"));
}

for (const id of ["surface", "type"] as const) {
  document.getElementById(id)?.addEventListener("change", (event) => {
    const value = (event.target as HTMLSelectElement).value;
    document.documentElement.dataset[id] = value;
    // The tokens just changed, and both the map and the drawn marks read tokens at draw time.
    paintMaps();
    marks();
  });
}

addEventListener("resize", () => {
  paintMaps();
  marks();
});

tabs();
fill(await claim());
shape = await outline();
show("a");
