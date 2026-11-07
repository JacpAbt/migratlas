/**
 * The detectability assessment as the book reads it: the document, and the coverage figure's legend.
 *
 * Where change could ever be measured is a report about the lake rather than a slice of it, so it
 * ships as `detectability.json` and not through the layer manifest. The atlas draws its grid as a
 * still map (`lib/atlas/still.ts`); this is what the claim's coverage figure needs, which is the
 * shares and their legend, and no map.
 *
 * The four statuses are kinds of problem -- no time axis, effort not measured, series too short,
 * and none of those -- not points on a scale, so they are coloured as categories.
 */

interface Coverage {
  source_id: string;
  realm: string;
  ceiling: string;
  reason: string;
  effort_note: string;
  cells: number;
  detectable_cells: number;
  years: [number, number];
}

/** A source the gate holds and never draws. Rendered as a list, never as an absence. */
export interface Withheld {
  source_id: string;
  realm: string;
  taxon: string;
  sensitivity: string;
  reason: string;
  /** The refusal in one sentence. Heads the full reason rather than replacing it. */
  plain_reason: string;
  span: [number, number];
  individuals: number;
}

interface DetectabilityDocument {
  schema_version: number;
  min_years: number;
  grid: { cell_size_deg: number; x: number[]; y: number[]; v: number[]; categories: string[] };
  coverage: Coverage[];
  withheld: Withheld[];
  summary: Record<string, number>;
  caveat: string;
  method: string;
  supporting: string[];
}

const SUPPORTED_SCHEMA = 3;

/**
 * One token per status, keyed by name so a reordering upstream cannot silently recolour the legend.
 *
 * Read from CSS rather than written here, because the night surface has to reach them and these four
 * were picked to read as "mostly grey" against parchment -- they do not transfer to slate. The
 * accent for `detectable` is the same one the ledger uses for "change detected".
 */
const TOKENS: Record<string, string> = {
  "no-time-axis": "--detect-none",
  "effort-not-measured": "--detect-no-effort",
  "too-short": "--detect-short",
  detectable: "--detect-yes",
};

/** A status the assessment does not publish. A token like the rest, so it follows the surface. */
const FALLBACK_TOKEN = "--detect-unknown";

/** Resolve a status's token against the live surface. */
export function colourFor(status: string): string {
  const resolved = (token: string): string =>
    getComputedStyle(document.documentElement).getPropertyValue(token).trim();
  return resolved(TOKENS[status] ?? FALLBACK_TOKEN) || resolved(FALLBACK_TOKEN) || "#b5afa3";
}

/**
 * Plain-language legend text. The status slug is precise and says nothing to a first-time reader.
 *
 * Typed here, against the rule that frontend prose is authored in Python, and the atlas's key says
 * the same four things in `reports/atlas.py`: both should read one list the assessment publishes.
 */
const MEANS: Record<string, string> = {
  "no-time-axis": "one pooled epoch — nothing to trend",
  "effort-not-measured": "records, but no measure of how hard anyone looked",
  "too-short": "a repeated protocol, not yet long enough",
  detectable: "a long enough series with effort accounted for",
};

/** Legend rows, best first, so the eye starts at the colour that matters and works down into grey. */
export function legendRows(
  document_: DetectabilityDocument,
): { status: string; means: string; colour: string; share: number }[] {
  const total = Object.values(document_.summary).reduce((sum, n) => sum + n, 0);
  return [...document_.grid.categories].reverse().map((status) => ({
    status,
    means: MEANS[status] ?? status,
    colour: colourFor(status),
    share: total > 0 ? ((document_.summary[status] ?? 0) / total) * 100 : 0,
  }));
}

export type { Coverage, DetectabilityDocument };

/*
  Fetched once per session and shared. Not a micro-optimisation at this size: turning a page mounts
  the outgoing chapter's figure alongside the incoming one, so a turn on and off the coverage chapter
  asked for its 460 KB twice. Worth knowing at the call site: nearly all of that is the fifty
  thousand cells the atlas's still map draws, so a page wanting only the shares should fetch it when
  that page opens rather than at boot.
*/
let assessment: Promise<DetectabilityDocument> | undefined;

export async function loadDetectability(base: string): Promise<DetectabilityDocument> {
  assessment ??= (async () => {
    const response = await fetch(`${base}detectability.json`);
    if (!response.ok) throw new Error(`detectability.json: ${response.status}`);
    const document_ = (await response.json()) as DetectabilityDocument;
    if (document_.schema_version !== SUPPORTED_SCHEMA) {
      // Refuse rather than guess: an old shape read against new data shows a confident wrong number.
      throw new Error(`detectability.json schema ${document_.schema_version}`);
    }
    return document_;
  })();
  return assessment;
}
