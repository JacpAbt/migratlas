/**
 * The counterfactual ribbon: what happened, and what the attribution says would have.
 *
 * Drawn as inline SVG from `counterfactual.json`, so the geometry is the numbers rather than an
 * image of them. Nothing here computes anything: the slopes, the anchor and the divergence all
 * arrive fitted, and this file only decides how much of the axis to spend on them.
 *
 * That decision is the whole design. The two lines part by 0.89 days over thirty-one years, inside a
 * year-to-year scatter of several days. The axis is scaled to the *scatter*, so the observed points
 * fill the frame and the gap between the lines is as thin as it really is. Scaling to the gap
 * instead would fill the panel with a dramatic wedge and teach a reader to expect one from every
 * attributed signal, which is how a true result becomes a misleading picture.
 */

interface YearPoint {
  year: number;
  observed: number;
  stations: number;
  spread: number;
}

interface Line {
  key: string;
  label: string;
  per_decade: number;
  start: number;
  end: number;
  note: string;
}

interface RibbonDocument {
  schema_version: number;
  window: [number, number];
  unit: string;
  anchor: number;
  years: YearPoint[];
  lines: Line[];
  terms: Record<string, number>;
  divergence: number;
  caveat: string;
  method: string;
  supporting: string[];
}

const SUPPORTED_SCHEMA = 1;

const BOX = { width: 640, height: 300 };
// Wide right margin for the three end-labels, which carry the legend so no separate key is needed.
const PAD = { top: 20, right: 156, bottom: 36, left: 58 };

const REPOSITORY = "https://github.com/JacpAbt/migratlas/blob/main/";

const SVG = "http://www.w3.org/2000/svg";

function svg<K extends keyof SVGElementTagNameMap>(
  tag: K,
  attributes: Record<string, string | number> = {},
): SVGElementTagNameMap[K] {
  const node = document.createElementNS(SVG, tag);
  for (const [name, value] of Object.entries(attributes)) {
    node.setAttribute(name, String(value));
  }
  return node;
}

function element(tag: string, className?: string, text?: string): HTMLElement {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

/**
 * Day-of-year to a label a reader can place in a calendar.
 *
 * "day 268" means nothing to anyone; "25 Sep" means the end of September. Built on a non-leap year
 * because the series is a mean over thirty-one of them and a one-day ambiguity is far below the
 * scatter being drawn.
 */
function asDate(dayOfYear: number): string {
  const date = new Date(Date.UTC(2001, 0, Math.round(dayOfYear)));
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
}

/**
 * The vertical extent: the spread of the observed years, never the gap between the lines.
 *
 * The *points* set it, not the points plus their intervals. Those intervals reach ±3.1 days on the
 * sparsest years — they are a 95% interval on a mean across stations, so a wide one says few
 * stations reported, not that the birds were erratic. Letting them set the frame widened it to
 * about fifteen days and squeezed the whole 1.7-day observed trend into seven pixels, which hid a
 * real result to make room for an artefact of sampling. So the frame is the years, the bars are
 * clamped into it, and the two years that overflow are named under the chart.
 */
function verticalRange(document_: RibbonDocument): [number, number] {
  const values = document_.years.map(({ observed }) => observed);
  for (const line of document_.lines) values.push(line.start, line.end);
  const low = Math.min(...values);
  const high = Math.max(...values);
  const margin = (high - low) * 0.08;
  return [low - margin, high + margin];
}

/**
 * Push labels apart when they would print on top of each other.
 *
 * The two counterfactuals end 0.005 days apart, which is the finding and also unreadable: one label
 * lands exactly on the other. Nudging the later one down keeps both legible while leaving the lines
 * themselves where the data puts them.
 */
function stack(positions: number[], gap = 11): number[] {
  const order = positions.map((y, index) => ({ y, index })).sort((a, b) => a.y - b.y);
  let previous = -Infinity;
  const out = [...positions];
  for (const { y, index } of order) {
    const placed = Math.max(y, previous + gap);
    out[index] = placed;
    previous = placed;
  }
  return out;
}

function chart(document_: RibbonDocument): SVGSVGElement {
  const [first, last] = document_.window;
  const [low, high] = verticalRange(document_);

  const frame = svg("svg", {
    viewBox: `0 0 ${BOX.width} ${BOX.height}`,
    class: "ribbon__chart",
    role: "img",
    "aria-label":
      `Autumn passage date at ${document_.terms.stations} radar stations, ${first} to ${last}: ` +
      document_.lines.map((l) => `${l.label}, ${l.per_decade.toFixed(2)} days per decade`).join("; "),
  });

  const plotWidth = BOX.width - PAD.left - PAD.right;
  const plotHeight = BOX.height - PAD.top - PAD.bottom;
  const xOf = (year: number) => PAD.left + ((year - first) / (last - first)) * plotWidth;
  // Earlier dates are lower numbers, and an advance should read as *up*. Inverting here means the
  // lines rise as the animals get earlier, which is the direction the sentence describes.
  const yOf = (day: number) => PAD.top + ((day - low) / (high - low)) * plotHeight;
  const clamp = (y: number) => Math.min(Math.max(y, PAD.top), PAD.top + plotHeight);

  // --- Axes. Sparse on purpose: three date ticks and two years is all the frame needs.
  for (const day of [low, document_.anchor, high]) {
    const y = yOf(day);
    frame.append(svg("line", { class: "ribbon__gridline", x1: PAD.left, x2: PAD.left + plotWidth, y1: y, y2: y }));
    const label = svg("text", {
      class: "ribbon__tick",
      x: PAD.left - 7,
      y: y + 4,
      "text-anchor": "end",
    });
    label.textContent = asDate(day);
    frame.append(label);
  }
  for (const year of [first, last]) {
    const label = svg("text", {
      class: "ribbon__tick",
      x: xOf(year),
      y: BOX.height - PAD.bottom + 20,
      "text-anchor": year === first ? "start" : "end",
    });
    label.textContent = String(year);
    frame.append(label);
  }

  // --- The observed years, drawn behind the lines.
  // The scatter is the point of the panel as much as the lines are: it is what makes the size of
  // the divergence legible, so it is not decoration and it is not optional.
  for (const point of document_.years) {
    const x = xOf(point.year);
    if (point.spread > 0) {
      frame.append(
        svg("line", {
          class: "ribbon__spread",
          x1: x,
          x2: x,
          // Clamped, not scaled to. A bar that runs to the edge is telling the reader that year's
          // interval is wider than the frame, which is true and is what the note underneath says.
          y1: clamp(yOf(point.observed - point.spread)),
          y2: clamp(yOf(point.observed + point.spread)),
        }),
      );
    }
    const dot = svg("circle", { class: "ribbon__year", cx: x, cy: yOf(point.observed), r: 2.6 });
    const hover = svg("title");
    hover.textContent = `${point.year}: ${asDate(point.observed)}, ${point.stations} stations`;
    dot.append(hover);
    frame.append(dot);
  }

  // --- The lines, plus a label at the right-hand end of each.
  // Labels are placed on a de-overlapped copy of the endpoints, so a leader line joins each one
  // back to where its trend actually ends. Moving the label is a drawing fix; moving the line
  // would be a lie.
  const labelY = stack(
    document_.lines.map((line) => yOf(line.end) + 4),
    28,
  );
  document_.lines.forEach((line, index) => {
    frame.append(
      svg("line", {
        class: `ribbon__line ribbon__line--${line.key}`,
        x1: xOf(first),
        x2: xOf(last),
        y1: yOf(line.start),
        y2: yOf(line.end),
      }),
    );

    const y = labelY[index] ?? yOf(line.end) + 4;
    if (Math.abs(y - 4 - yOf(line.end)) > 1) {
      frame.append(
        svg("line", {
          class: `ribbon__leader ribbon__leader--${line.key}`,
          x1: xOf(last),
          x2: xOf(last) + 5,
          y1: yOf(line.end),
          y2: y - 4,
        }),
      );
    }

    const label = svg("text", {
      class: `ribbon__label ribbon__label--${line.key}`,
      x: xOf(last) + 7,
      y,
    });
    label.textContent = line.label;
    frame.append(label);

    const rate = svg("text", { class: "ribbon__rate", x: xOf(last) + 7, y: y + 13 });
    // A typographic minus rather than a hyphen: at this size a hyphen disappears, and the sign
    // is the difference between "earlier" and "later".
    rate.textContent = `${line.per_decade.toFixed(2).replace("-", "−")} d/decade`;
    frame.append(rate);
  });

  // --- The divergence, measured on the drawing rather than annotated beside it.
  const [observed, counterfactual] = ["observed", "counterfactual"].map((key) =>
    document_.lines.find((line) => line.key === key),
  );
  if (observed && counterfactual) {
    const x = xOf(last) - 2;
    frame.append(
      svg("line", {
        class: "ribbon__divergence",
        x1: x,
        x2: x,
        y1: yOf(observed.end),
        y2: yOf(counterfactual.end),
      }),
    );
  }
  return frame;
}

/**
 * Load and render the ribbon. Resolves to the number of lines drawn, so a caller — and the browser
 * test — can tell an empty panel apart from a failed fetch.
 */
export async function mountRibbon(container: HTMLElement, base: string): Promise<number> {
  let document_: RibbonDocument;
  try {
    const response = await fetch(`${base}counterfactual.json`);
    if (!response.ok) throw new Error(`counterfactual.json: ${response.status}`);
    document_ = (await response.json()) as RibbonDocument;
  } catch (error) {
    container.append(element("p", "finding__error", "The counterfactual is unavailable."));
    console.warn("could not load the counterfactual", error);
    return 0;
  }

  if (document_.schema_version !== SUPPORTED_SCHEMA) {
    container.append(
      element("p", "finding__error", "The counterfactual was built by an incompatible pipeline."),
    );
    console.warn(`counterfactual.json schema ${document_.schema_version}, expected ${SUPPORTED_SCHEMA}`);
    return 0;
  }

  container.append(chart(document_));

  // The number the chart cannot make big: stated in words directly under it, so a reader who only
  // sees two nearly-parallel lines learns that the near-parallel is the finding.
  const size = element(
    "p",
    "ribbon__size",
    `The two part by ${document_.divergence.toFixed(2)} days across ` +
      `${document_.window[1] - document_.window[0]} years.`,
  );
  container.append(size);

  // Named rather than left as a visual oddity: a bar running off the top of the frame is a year
  // with few reporting stations, and a reader is owed that instead of guessing at it.
  const [low, high] = verticalRange(document_);
  const clipped = document_.years.filter(
    (point) => point.observed - point.spread < low || point.observed + point.spread > high,
  );
  if (clipped.length > 0) {
    container.append(
      element(
        "p",
        "ribbon__clipped",
        `${clipped.length} of ${document_.years.length} years have a sampling interval wider than ` +
          `the frame (${clipped.map((point) => point.year).join(", ")}); their bars run to the edge.`,
      ),
    );
  }

  const notes = element("dl", "ribbon__notes");
  for (const line of document_.lines) {
    notes.append(element("dt", `ribbon__key ribbon__key--${line.key}`, line.label));
    notes.append(element("dd", undefined, line.note));
  }
  container.append(notes);

  container.append(element("p", "ribbon__caveat", document_.caveat));

  const method = element("a", "finding__method", "Method and pre-registration") as HTMLAnchorElement;
  method.href = `${REPOSITORY}${document_.method}`;
  method.rel = "noopener";
  method.target = "_blank";
  container.append(method);

  // Same reason as the findings panel: open, this covers a phone screen entirely, and there is no
  // way to ask the viewport how wide it is from the markup.
  const panel = container.closest("details");
  if (panel && window.matchMedia("(max-width: 48rem)").matches) panel.open = false;

  return document_.lines.length;
}
