/** Direction A applied to every part. Every mark is rough.js; every ratio below is measured. */

import rough from "roughjs";

const token = (name: string) =>
  getComputedStyle(document.body).getPropertyValue(name).trim() || "#000";

/* ------------------------------------------------------------------ contrast
   Measured in the browser against the paper actually behind the text, the same way
   `notebook.spec.ts` does it -- a green chosen by eye is a green that fails at 2x on a laptop.
*/
function luminance(colour: string): number {
  const probe = document.createElement("span");
  probe.style.color = colour;
  document.body.append(probe);
  const parts = getComputedStyle(probe).color.match(/[\d.]+/g)?.map(Number) ?? [0, 0, 0];
  probe.remove();
  const [r = 0, g = 0, b = 0] = parts.map((v) => {
    const c = v / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function ratio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

const GREENS: [string, string, string][] = [
  ["#4a6b4e", "moss", "body text, labels, headings"],
  ["#5d8562", "moss ink", "drawn marks: ticks, brackets, rules"],
  ["#3f7d4c", "brighter", "text, but only on the paler paper"],
  ["#55a065", "brighter ink", "drawn marks on the paler paper"],
  ["#67916c", "too light", "fails for text on either paper"],
];

function swatches(): void {
  const host = document.getElementById("swatches");
  if (!host) return;
  const paper = getComputedStyle(document.querySelector(".sheet")!).backgroundColor;
  host.replaceChildren();
  for (const [hex, name, use] of GREENS) {
    const r = ratio(hex, paper);
    const text = use.includes("drawn") ? 3 : 4.5;
    const row = document.createElement("label");
    row.className = "sw";
    row.innerHTML =
      `<span class="sw__chip" style="background:${hex}"></span>` +
      `<span class="sw__name" style="color:${hex}">${name} · ${hex}</span>` +
      `<span class="sw__use">${use}</span>` +
      `<span class="sw__r ${r >= text ? "pass" : "fail"}">${r.toFixed(2)}:1 · needs ${text}</span>`;
    host.append(row);
  }
}

/* --------------------------------------------------------------------- marks */
function draw(): void {
  for (const node of document.querySelectorAll<SVGSVGElement>("svg[data-rough]")) {
    const box = node.getBoundingClientRect();
    const w = Math.max(box.width, 6);
    const h = Math.max(box.height, 6);
    node.setAttribute("viewBox", `0 0 ${w} ${h}`);
    node.replaceChildren();
    const rc = rough.svg(node);
    const kind = node.dataset.rough ?? "";
    const seed = [...kind].reduce((a, c) => a + c.charCodeAt(0), 11);
    const ink = token("--ink");
    const moss = token("--moss-ink");
    const rust = token("--rust-ink");
    const pencil = token("--pencil");

    switch (kind) {
      case "track": {
        // A ruled scale: the line, then twelve graduations, which on the year slider are months.
        const y = h / 2;
        node.append(
          rc.line(4, y, w - 4, y, { stroke: pencil, strokeWidth: 1.5, roughness: 1.7, bowing: 1.2, seed }),
        );
        const ticks = node.closest("[data-slider='year']") ? 12 : 8;
        for (let i = 0; i <= ticks; i += 1) {
          const x = 4 + ((w - 8) * i) / ticks;
          const tall = i % 3 === 0;
          node.append(
            rc.line(x, y + 3, x, y + (tall ? 10 : 6), {
              stroke: tall ? moss : pencil,
              strokeWidth: 1.1,
              roughness: 1.4,
              seed: seed + i,
            }),
          );
        }
        break;
      }

      case "pencil": {
        // A pencil stub: a body, a shoulder, a rust point.
        node.append(
          rc.polygon(
            [[4, 2], [16, 2], [16, 22], [10, 30], [4, 22]],
            { stroke: ink, strokeWidth: 1.4, roughness: 1.5, fill: token("--paper"), fillStyle: "solid", seed },
          ),
          rc.line(4, 22, 16, 22, { stroke: ink, strokeWidth: 1.1, roughness: 1.3, seed }),
          rc.polygon([[7, 25], [13, 25], [10, 30]], {
            stroke: rust, strokeWidth: 1, roughness: 1.1, fill: rust, fillStyle: "solid", seed,
          }),
        );
        break;
      }

      case "btn":
      case "box":
        node.append(
          rc.rectangle(3, 3, w - 6, h - 6, {
            stroke: node.parentElement?.querySelector("input") ? pencil : ink,
            strokeWidth: 1.5,
            roughness: 2.1,
            bowing: 1.5,
            seed,
          }),
        );
        break;

      case "tickbox": {
        const on = node.parentElement?.querySelector("input")?.checked;
        node.append(
          rc.rectangle(2, 3, 15, 15, { stroke: pencil, strokeWidth: 1.3, roughness: 2.2, seed }),
        );
        if (on) {
          node.append(
            rc.linearPath([[4, 11], [8, 16], [17, 1]], {
              stroke: moss, strokeWidth: 2.2, roughness: 1.4, seed,
            }),
          );
        }
        break;
      }

      case "lasso": {
        if (!node.parentElement?.classList.contains("opt--on")) break;
        /*
          An ellipse inscribed in a box touches it at four points, so the corners of the text poke
          out -- which is exactly what a wide two-line row looks like when it is circled.
          Circumscribing it properly needs semi-axes of 1.41x, and a loop that tall around a
          full-width row reads as an accident rather than as a mark.

          So the shape follows the thing. A short pill gets the loop, drawn a little outside its
          own box because that is what circling looks like. Anything wide gets a drawn box. Both
          mean "this one", and neither leaves a word outside the mark.
        */
        const wide = w > 190;
        node.append(
          wide
            ? rc.rectangle(2, 2, w - 4, h - 4, {
                stroke: rust, strokeWidth: 1.6, roughness: 2.3, bowing: 1.4, seed,
              })
            : rc.ellipse(w / 2, h / 2, w * 1.02, h * 1.06, {
                stroke: rust, strokeWidth: 1.6, roughness: 2.4, bowing: 2, seed,
              }),
        );
        break;
      }

      case "ul":
        node.append(
          rc.line(2, 5, w - 8, 4, { stroke: rust, strokeWidth: 2.2, roughness: 1.7, bowing: 2.2, seed }),
        );
        break;

      case "dogear":
        // A tab is a page corner showing past the one on top of it.
        node.append(
          rc.linearPath(
            [[6, h], [2, 6], [w - 8, 2], [w - 2, h - 5], [w - 5, h]],
            { stroke: pencil, strokeWidth: 1.3, roughness: 2, seed },
          ),
          rc.line(w - 12, h - 2, w - 2, h - 9, { stroke: rust, strokeWidth: 1.4, roughness: 1.6, seed }),
        );
        break;

      case "fish":
        // A pressed specimen, not a cartoon: outline only, the way a plate is drawn.
        node.append(
          rc.curve([[4, 15], [18, 4], [42, 6], [52, 15]], { stroke: moss, strokeWidth: 1.4, roughness: 1.5, seed }),
          rc.curve([[4, 15], [18, 26], [42, 24], [52, 15]], { stroke: moss, strokeWidth: 1.4, roughness: 1.5, seed }),
          rc.polygon([[52, 15], [61, 6], [59, 15], [61, 24]], { stroke: moss, strokeWidth: 1.3, roughness: 1.6, seed }),
          rc.circle(13, 13, 3.4, { stroke: moss, strokeWidth: 1.1, roughness: 1.2, seed }),
          rc.curve([[26, 6], [32, 1], [38, 7]], { stroke: moss, strokeWidth: 1.1, roughness: 1.7, seed }),
        );
        break;

      case "thumb": {
        // The scrollbar thumb, drawn. Same trick as the track: a scrollbar pseudo-element cannot
        // hold an SVG child, but it can take a `background-image`, so the mark is generated here
        // and handed over as a data URI.
        break;
      }

      case "scale":
        node.append(
          rc.linearPath([[1, 2], [1, 9], [w - 1, 9], [w - 1, 2]], {
            stroke: "#e6dcc6", strokeWidth: 1.4, roughness: 1.6, seed,
          }),
          rc.line(w / 2, 5, w / 2, 9, { stroke: "#e6dcc6", strokeWidth: 1.1, roughness: 1.3, seed }),
        );
        break;
    }
  }
  place();
}

/** Put each pencil thumb where its range value says. */
function place(): void {
  for (const slider of document.querySelectorAll<HTMLElement>(".slider")) {
    const input = slider.querySelector("input");
    const thumb = slider.querySelector<SVGElement>(".slider__thumb");
    if (!input || !thumb) continue;
    const frac = (input.valueAsNumber - Number(input.min)) / (Number(input.max) - Number(input.min));
    thumb.style.left = `calc(${frac * 100}% - ${frac * 20}px)`;
  }
}

/* ---------------------------------------------------------------- scrollbar
   The one vertical line the browser draws for us, drawn by the same pen.

   A scrollbar pseudo-element cannot hold an SVG child, so the track is generated here with
   rough.js into a detached SVG, serialised, and handed to CSS as a data URI in `--scroll-track`.
   Regenerated on a palette change, because the ink colour is baked into the markup.
*/
/** Serialise a detached rough.js drawing to a CSS `url()`. */
function asDataUri(svg: SVGSVGElement): string {
  return `url("data:image/svg+xml;utf8,${encodeURIComponent(svg.outerHTML)}")`;
}

function blank(w: number, h: number): SVGSVGElement {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  svg.setAttribute("width", String(w));
  svg.setAttribute("height", String(h));
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
  return svg;
}

/**
 * The thumb, drawn rather than a rounded rectangle.
 *
 * Three slices, because a scrollbar thumb is any height and a single image would stretch: a drawn
 * cap at each end and a tiling middle, composited as three background layers. The caps are where
 * the hand shows, and they are the part that does not stretch.
 */
function scrollThumb(): void {
  const w = 11;
  const pencil = token("--pencil");
  const rust = token("--rust-ink");

  const cap = (top: boolean): string => {
    const svg = blank(w, 10);
    const rc = rough.svg(svg);
    svg.append(
      rc.curve(
        top ? [[1, 9], [2, 2], [w / 2, 1], [w - 2, 2], [w - 1, 9]]
            : [[1, 1], [2, 8], [w / 2, 9], [w - 2, 8], [w - 1, 1]],
        { stroke: rust, strokeWidth: 1.7, roughness: 1.5, seed: top ? 5 : 9 },
      ),
    );
    return asDataUri(svg);
  };

  const middle = blank(w, 60);
  const rc = rough.svg(middle);
  // Two long strokes rather than a filled shape: a graphite stub read end-on is two edges and the
  // paper between them, and a fill would read as a scrollbar again.
  middle.append(
    rc.line(2, -2, 2, 62, { stroke: pencil, strokeWidth: 1.5, roughness: 1.1, bowing: 0.4, seed: 13 }),
    rc.line(w - 2, -2, w - 2, 62, { stroke: pencil, strokeWidth: 1.5, roughness: 1.1, bowing: 0.4, seed: 17 }),
  );

  const root = document.documentElement.style;
  root.setProperty("--thumb-top", cap(true));
  root.setProperty("--thumb-mid", asDataUri(middle));
  root.setProperty("--thumb-bottom", cap(false));
}

function scrollTrack(): void {
  const tile = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const w = 15;
  const h = 240;
  tile.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  tile.setAttribute("width", String(w));
  tile.setAttribute("height", String(h));
  tile.setAttribute("viewBox", `0 0 ${w} ${h}`);

  const rc = rough.svg(tile);
  const pencil = token("--pencil");
  // Drawn as one long wobbling line rather than a repeated short one: a tile whose ends do not
  // meet reads as a dashed line, and the seam lands somewhere different at every scroll height.
  tile.append(
    rc.line(w / 2, -2, w / 2, h + 2, {
      stroke: pencil,
      strokeWidth: 1.1,
      roughness: 1.5,
      bowing: 0.6,
      seed: 41,
    }),
  );
  // Faint graduations, the same idea as the sliders: a scale rather than a groove.
  for (let y = 12; y < h; y += 40) {
    tile.append(
      rc.line(w / 2 - 3, y, w / 2 + 3, y, {
        stroke: pencil, strokeWidth: 0.9, roughness: 1.2, seed: 41 + y,
      }),
    );
  }

  const uri = `url("data:image/svg+xml;utf8,${encodeURIComponent(tile.outerHTML)}")`;
  document.documentElement.style.setProperty("--scroll-track", uri);
}

/* --------------------------------------------------------------- colour vision
   Every palette colour, put through the three dichromacies.

   The Vienot-Brettel-Mollon linear approximation, which is what browsers and design tools use.
   Worth running rather than assuming, because this palette is green *and* orange -- the single
   pairing red-green dichromats cannot separate, and that is roughly 8% of men. The project
   already refuses to let colour be the only signal anywhere; this is how you find out whether
   that rule is doing real work or merely sounding good.
*/
const CVD: Record<string, number[]> = {
  protanopia: [0.1121, 0.8853, -0.0005, 0.1127, 0.8897, -0.0001, 0.0045, 0.0085, 1.0],
  deuteranopia: [0.292, 0.7054, -0.0003, 0.2934, 0.7089, 0.0, -0.0195, 0.0333, 1.0],
  tritanopia: [1.0, 0.1502, -0.1516, 0.0, 0.8529, 0.1472, 0.0, 0.2578, 0.7423],
};

function toHex(colour: string): string {
  const probe = document.createElement("span");
  probe.style.color = colour;
  document.body.append(probe);
  const parts = getComputedStyle(probe).color.match(/[\d.]+/g)?.map(Number) ?? [0, 0, 0];
  probe.remove();
  return "#" + parts.slice(0, 3).map((v) => Math.round(v).toString(16).padStart(2, "0")).join("");
}

function simulate(hex: string, kind: string): string {
  const m = CVD[kind];
  if (!m) return hex;
  const n = Number.parseInt(hex.slice(1), 16);
  const lin = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => {
    const c = v / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  const out = [0, 1, 2].map((row) => {
    const value =
      (m[row * 3] ?? 0) * (lin[0] ?? 0) +
      (m[row * 3 + 1] ?? 0) * (lin[1] ?? 0) +
      (m[row * 3 + 2] ?? 0) * (lin[2] ?? 0);
    return Math.max(0, Math.min(1, value));
  });
  return (
    "#" +
    out
      .map((c) => {
        const s = c <= 0.0031308 ? c * 12.92 : 1.055 * c ** (1 / 2.4) - 0.055;
        return Math.round(s * 255).toString(16).padStart(2, "0");
      })
      .join("")
  );
}

/** Perceptual distance, so "can these two be told apart" is a number rather than a look. */
function distance(a: string, b: string): number {
  const rgb = (h: string) => {
    const n = Number.parseInt(h.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  };
  const [r1 = 0, g1 = 0, b1 = 0] = rgb(a);
  const [r2 = 0, g2 = 0, b2 = 0] = rgb(b);
  const rm = (r1 + r2) / 2;
  return Math.sqrt(
    (2 + rm / 256) * (r1 - r2) ** 2 + 4 * (g1 - g2) ** 2 + (2 + (255 - rm) / 256) * (b1 - b2) ** 2,
  );
}

/** Distance below which two colours stop being reliably separable for a dichromat. */
const SEPARABLE = 60;

function colourVision(): void {
  const host = document.getElementById("cvd");
  if (!host) return;
  const palette: [string, string][] = [
    ["moss", toHex(token("--moss-ink"))],
    ["rust", toHex(token("--rust-ink"))],
    ["ink", toHex(token("--ink"))],
    ["pencil", toHex(token("--pencil"))],
  ];

  let html = "";
  for (const kind of ["normal", "protanopia", "deuteranopia", "tritanopia"]) {
    const seen = palette.map(
      ([name, hex]) => [name, kind === "normal" ? hex : simulate(hex, kind)] as const,
    );
    const cells = seen
      .map(([name, c]) => `<div class="cv__cell"><span style="background:${c}"></span><em>${name}</em></div>`)
      .join("");
    const gap = distance(seen[0]?.[1] ?? "#000", seen[1]?.[1] ?? "#000");
    const verdict =
      gap > SEPARABLE
        ? `green vs rust: ${gap.toFixed(0)}`
        : `green vs rust: ${gap.toFixed(0)} - not separable by colour alone`;
    html += `<div class="cv__row"><b>${kind}</b>${cells}<i class="${gap > SEPARABLE ? "ok" : "warn"}">${verdict}</i></div>`;
  }
  host.innerHTML = html;
}

/* ------------------------------------------------------------------- the type */
const PRESETS: [string, string, string, string[]][] = [
  ["font-hand", "Hand throughout", "Virgil for headings, Shantell Sans for body and every small label. Nothing on the page is typed.", ["Virgil", "Shantell"]],
  ["font-clear", "Hand for headings only", "Excalifont on the headings, Atkinson Hyperlegible everywhere else — a face drawn by the Braille Institute for low vision.", ["Excalifont", "Atkinson"]],
  ["font-dyslexic", "Made for dyslexia", "OpenDyslexic: weighted bottoms, wide apertures, and no two letters that are each other mirrored.", ["OpenDyslexic"]],
];

/** Does this family actually render, or is the browser quietly substituting? */
function resolves(family: string): boolean {
  const probe = document.createElement("span");
  probe.style.cssText = "position:absolute;visibility:hidden;font-size:80px;white-space:pre";
  probe.textContent = "Handgloves 0123456789";
  document.body.append(probe);
  probe.style.fontFamily = "monospace";
  const mono = probe.getBoundingClientRect().width;
  probe.style.fontFamily = `"${family}", monospace`;
  const got = probe.getBoundingClientRect().width;
  probe.remove();
  return Math.abs(got - mono) > 1;
}

async function fontpick(): Promise<void> {
  const host = document.getElementById("fontpick");
  if (!host) return;
  // A declared face is not downloaded until something uses it, so ask for each one by name before
  // reporting on whether it resolved -- otherwise every answer is "no" on first paint.
  await Promise.all(
    PRESETS.flatMap(([, , , faces]) => faces.map((f) => document.fonts.load(`16px "${f}"`))),
  );
  host.replaceChildren();
  for (const [cls, name, note, faces] of PRESETS) {
    const missing = faces.filter((f) => !resolves(f));
    const label = document.createElement("label");
    label.className = "fp";
    label.innerHTML =
      `<input type="radio" name="font" ${document.body.classList.contains(cls) ? "checked" : ""}>` +
      `<svg data-rough="lasso"></svg>` +
      `<b>${name}</b><span>${note}</span>` +
      `<span class="fp__state ${missing.length ? "no" : "ok"}">` +
      `${missing.length ? `not loading: ${missing.join(", ")}` : "loaded"}</span>`;
    label.classList.toggle("opt--on", document.body.classList.contains(cls));
    label.querySelector("input")?.addEventListener("change", () => {
      document.body.classList.remove(...PRESETS.map(([c]) => c));
      document.body.classList.add(cls);
      void fontpick();
      repaint();
    });
    host.append(label);
  }
  draw();
}

document.body.classList.add("font-hand");

draw();
swatches();
scrollTrack();
scrollThumb();
colourVision();
void fontpick();
addEventListener("resize", draw);
for (const input of document.querySelectorAll<HTMLInputElement>(".slider input")) {
  input.addEventListener("input", place);
}
for (const box of document.querySelectorAll<HTMLInputElement>('.layers input, .knob input')) {
  box.addEventListener("change", () => {
    for (const opt of document.querySelectorAll(".opt")) {
      opt.classList.toggle("opt--on", !!opt.querySelector<HTMLInputElement>("input")?.checked);
    }
    draw();
  });
}
function repaint(): void {
  draw();
  swatches();
  scrollTrack();
  scrollThumb();
  colourVision();
}

for (const id of ["dark", "pale"]) {
  document.getElementById(id)?.addEventListener("change", (event) => {
    document.body.classList.toggle(id, (event.target as HTMLInputElement).checked);
    repaint();
  });
}

document.getElementById("sky")?.addEventListener("change", (event) => {
  const wanted = (event.target as HTMLSelectElement).value;
  document.body.classList.remove("sky-indigo", "sky-stars");
  if (wanted) document.body.classList.add(wanted);
  // Night is implied by choosing a sky: nobody picks a starfield for the day page.
  const dark = document.getElementById("dark") as HTMLInputElement | null;
  if (dark && !dark.checked) {
    dark.checked = true;
    document.body.classList.add("dark");
  }
  repaint();
});
