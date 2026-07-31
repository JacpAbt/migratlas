/**
 * The counterfactual charts' arithmetic and geometry, apart from their markup.
 *
 * Nothing here computes a result: the slopes, the divergences and the disagreement all arrive
 * fitted from `reports/counterfactual.py`. What this file decides is the *frame* the two ribbons
 * are drawn in, and that decision is the whole design -- see `docs/methods/counterfactual.md`.
 *
 * **One frame, shared by both charts.** Two ribbons drawn to their own extents would be a lie in
 * two directions at once. Vertically, DAMIP's lines part by 0.89 days and ATTRICI's by 0.29, and
 * that difference *is* the finding -- rescaling each chart to fill itself would make the two gaps
 * look the same size. Horizontally, DAMIP runs to 2025 and ATTRICI stops in 2019, so fitting each
 * to its own window would stretch the shorter one and make a shallower slope look steeper. Sharing
 * both axes costs the second chart an empty right-hand quarter, which is exactly the point: the
 * reader sees the counterfactual run out six years early instead of reading it in a caption.
 */

export interface YearPoint {
  year: number;
  observed: number;
  stations: number;
  spread: number;
}

export interface Line {
  key: string;
  label: string;
  per_decade: number;
  start: number;
  end: number;
  note: string;
}

/** One counterfactual: its question, its two lines, and everything needed to read it alone. */
export interface RibbonDocument {
  key: string;
  question: string;
  method_note: string;
  window: [number, number];
  years: YearPoint[];
  lines: Line[];
  terms: Record<string, number>;
  divergence: number;
  caveat: string;
  method: string;
}

export interface Comparison {
  schema_version: number;
  unit: string;
  ribbons: RibbonDocument[];
  /** Why two honest counterfactuals give different numbers. The reason both are shown. */
  disagreement: string;
  shared_caveat: string;
  supporting: string[];
}

export const RIBBON_SCHEMA = 2;

export const BOX = { width: 640, height: 300 };
/** Wide right margin: the end-labels carry the legend, so no separate key is needed. */
export const PAD = { top: 20, right: 156, bottom: 36, left: 58 };

export async function loadRibbon(base: string): Promise<Comparison> {
  const response = await fetch(`${base}counterfactual.json`);
  if (!response.ok) throw new Error(`counterfactual.json: ${response.status}`);
  const document_ = (await response.json()) as Comparison;
  if (document_.schema_version !== RIBBON_SCHEMA) {
    throw new Error(`counterfactual.json schema ${document_.schema_version}`);
  }
  if (document_.ribbons.length === 0) throw new Error("counterfactual.json has no ribbons");
  return document_;
}

/**
 * Day-of-year to a label a reader can place in a calendar.
 *
 * "day 268" means nothing to anyone; "25 Sep" means the end of September. Built on a non-leap year
 * because the series is a mean over thirty-one of them, and a one-day ambiguity is far below the
 * scatter being drawn.
 */
export function asDate(dayOfYear: number): string {
  const date = new Date(Date.UTC(2001, 0, Math.round(dayOfYear)));
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
}

export interface Frame {
  years: [number, number];
  days: [number, number];
}

/**
 * The one frame both charts are drawn in.
 *
 * The vertical extent comes from the observed *points* and the fitted lines -- never from the
 * points plus their intervals. Those intervals reach ±3.1 days on the sparsest years, and they are
 * a 95% interval on a mean across stations, so a wide one says few stations reported rather than
 * that the animals were erratic. Letting them set the frame widened the axis to about fifteen days
 * and squeezed the whole 1.7-day observed trend into seven pixels, hiding a real result to make
 * room for an artefact of sampling.
 */
export function frameOf(comparison: Comparison): Frame {
  const days: number[] = [];
  const years: number[] = [];
  for (const ribbon of comparison.ribbons) {
    years.push(...ribbon.window);
    for (const point of ribbon.years) days.push(point.observed);
    for (const line of ribbon.lines) days.push(line.start, line.end);
  }
  const low = Math.min(...days);
  const high = Math.max(...days);
  const margin = (high - low) * 0.08;
  return {
    years: [Math.min(...years), Math.max(...years)],
    days: [low - margin, high + margin],
  };
}

/**
 * Push labels apart when they would print on top of each other.
 *
 * ATTRICI's two lines end 0.29 days apart, which is the finding and also nearly unreadable: one
 * label lands almost on the other. Nudging the later one down keeps both legible while leaving the
 * lines themselves where the data puts them, joined back by a leader.
 */
export function stack(positions: number[], gap = 28): number[] {
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

/** Years whose sampling interval runs past the frame, named under the chart rather than left odd. */
export function clipped(ribbon: RibbonDocument, frame: Frame): number[] {
  const [low, high] = frame.days;
  return ribbon.years
    .filter((point) => point.observed - point.spread < low || point.observed + point.spread > high)
    .map((point) => point.year);
}

export interface Scales {
  xOf: (year: number) => number;
  yOf: (day: number) => number;
  clamp: (y: number) => number;
  plotWidth: number;
  plotHeight: number;
}

export function scales(frame: Frame): Scales {
  const [first, last] = frame.years;
  const [low, high] = frame.days;
  const plotWidth = BOX.width - PAD.left - PAD.right;
  const plotHeight = BOX.height - PAD.top - PAD.bottom;
  return {
    plotWidth,
    plotHeight,
    xOf: (year) => PAD.left + ((year - first) / (last - first)) * plotWidth,
    // Earlier dates are lower numbers, and an advance should read as *up*. Inverting here means the
    // lines rise as the animals get earlier, which is the direction the sentence describes.
    yOf: (day) => PAD.top + ((day - low) / (high - low)) * plotHeight,
    clamp: (y) => Math.min(Math.max(y, PAD.top), PAD.top + plotHeight),
  };
}

/** A typographic minus, because at 11px a hyphen disappears and the sign is the whole meaning. */
export function rate(perDecade: number): string {
  return `${perDecade.toFixed(2).replace("-", "−")} d/decade`;
}
