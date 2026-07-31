/**
 * The counterfactual ribbon's arithmetic and geometry, apart from its markup.
 *
 * Nothing here computes a result: the slopes, the anchor and the divergence all arrive fitted from
 * `reports/counterfactual.py`. What this file decides is how much of the axis to spend on them, and
 * that decision is the whole design -- see `docs/methods/counterfactual.md`.
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

export interface RibbonDocument {
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

export const RIBBON_SCHEMA = 1;

export const BOX = { width: 640, height: 300 };
/** Wide right margin: the end-labels carry the legend, so no separate key is needed. */
export const PAD = { top: 20, right: 156, bottom: 36, left: 58 };

export async function loadRibbon(base: string): Promise<RibbonDocument> {
  const response = await fetch(`${base}counterfactual.json`);
  if (!response.ok) throw new Error(`counterfactual.json: ${response.status}`);
  const document_ = (await response.json()) as RibbonDocument;
  if (document_.schema_version !== RIBBON_SCHEMA) {
    throw new Error(`counterfactual.json schema ${document_.schema_version}`);
  }
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

/**
 * The vertical extent: the spread of the observed years, never the gap between the lines.
 *
 * The *points* set it, not the points plus their intervals. Those intervals reach ±3.1 days on the
 * sparsest years, and they are a 95% interval on a mean across stations -- so a wide one says few
 * stations reported, not that the animals were erratic. Letting them set the frame widened the axis
 * to about fifteen days and squeezed the whole 1.7-day observed trend into seven pixels, hiding a
 * real result to make room for an artefact of sampling.
 */
export function verticalRange(document_: RibbonDocument): [number, number] {
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
 * themselves where the data puts them, joined back by a leader.
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
export function clipped(document_: RibbonDocument): number[] {
  const [low, high] = verticalRange(document_);
  return document_.years
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

export function scales(document_: RibbonDocument): Scales {
  const [first, last] = document_.window;
  const [low, high] = verticalRange(document_);
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
