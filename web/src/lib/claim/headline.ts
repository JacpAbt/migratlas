/**
 * Each claim's headline result as a picture, published by `reports/headline.py`.
 *
 * Nothing here computes a result. The document carries values the ledger's own functions
 * produced -- a year's mean passage date, a species' change, a sea's slope -- and this module
 * decides only the frame they are drawn in. Three shapes, because the claims are of three kinds:
 * a trend over years, a pile of units, or a handful of units worth naming.
 */

export interface Point {
  year: number;
  value: number;
  n: number;
}

export interface Trend {
  per_decade: number;
  start: number;
  end: number;
}

export interface Series {
  key: string;
  label: string;
  points: Point[];
  trend: Trend | null;
}

export interface Years {
  kind: "years";
  unit: string;
  series: Series[];
}

export interface Bin {
  low: number;
  high: number;
  count: number;
}

export interface Mark {
  value: number;
  label: string;
}

export interface Histogram {
  kind: "histogram";
  unit: string;
  bins: Bin[];
  marks: Mark[];
  n: number;
  clipped: number;
}

export interface Bar {
  label: string;
  value: number;
  low: number | null;
  high: number | null;
}

export interface Strip {
  kind: "strip";
  unit: string;
  bars: Bar[];
  marks: Mark[];
}

export interface Headline {
  key: string;
  title: string;
  reading: string;
  chart: Years | Histogram | Strip;
}

export interface HeadlineDocument {
  schema_version: number;
  headlines: Headline[];
}

export const HEADLINE_SCHEMA = 1;

export async function loadHeadlines(base: string): Promise<HeadlineDocument> {
  const response = await fetch(`${base}headline.json`);
  if (!response.ok) throw new Error(`headline.json: ${response.status}`);
  const document_ = (await response.json()) as HeadlineDocument;
  if (document_.schema_version !== HEADLINE_SCHEMA) {
    throw new Error(`headline.json schema ${document_.schema_version}`);
  }
  return document_;
}

/** The headline drawn for a claim, or null where the analysis withheld it. */
export function headlineOf(document_: HeadlineDocument | null, key: string): Headline | null {
  return document_?.headlines.find((h) => h.key === key) ?? null;
}

/** A linear scale from a data range onto a pixel range. */
export function linear(
  domain: [number, number],
  range: [number, number],
): (value: number) => number {
  const [d0, d1] = domain;
  const [r0, r1] = range;
  const span = d1 - d0 || 1;
  return (value) => r0 + ((value - d0) / span) * (r1 - r0);
}

/** The value range a years chart is drawn over: its points and its lines, with a little air. */
export function valueRange(chart: Years): [number, number] {
  const values: number[] = [];
  for (const series of chart.series) {
    for (const point of series.points) values.push(point.value);
    if (series.trend) values.push(series.trend.start, series.trend.end);
  }
  const low = Math.min(...values);
  const high = Math.max(...values);
  const margin = (high - low || 1) * 0.1;
  return [low - margin, high + margin];
}

export function yearRange(chart: Years): [number, number] {
  const years = chart.series.flatMap((s) => s.points.map((p) => p.year));
  return [Math.min(...years), Math.max(...years)];
}

/**
 * A value as a reader would say it, in the chart's unit.
 *
 * Day-of-year becomes a date, because "day 268" means nothing and "25 Sep" means the end of
 * September; a share becomes a percentage; everything else is rounded to what its span needs.
 */
export function tickLabel(value: number, unit: string, span: number): string {
  if (unit === "day of year") {
    const date = new Date(Date.UTC(2001, 0, Math.round(value)));
    return date.toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
  }
  if (unit.startsWith("%")) return `${Math.round(value)}%`;
  const decimals = span < 0.5 ? 3 : span < 5 ? 2 : span < 50 ? 1 : 0;
  return value.toFixed(decimals).replace("-", "−");
}
