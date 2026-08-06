/**
 * The confound sandbox: the same analysis with its safeguards switched off.
 *
 * Every variant here was computed from the lake by `reports/sandbox.py`, running the reports' own
 * functions with one parameter changed. Nothing is recomputed in the browser and nothing is
 * simulated — switching a knob selects a number that a real run produced.
 *
 * **The result is not the one the framing invites.** Dropping the speed weighting takes the autumn
 * advance from −0.56 to −0.65, and fitting a break at the detected outage takes it to −0.90. Three
 * of the four alternative break specifications are *larger* than the published one. So the
 * safeguards are not hiding a smaller truth; the published number is the conservative choice among
 * defensible ones, and the panel has to say so rather than let a reader assume the usual story.
 */

export interface Variant {
  key: string;
  label: string;
  value: number;
  unit: string;
  n: number | null;
  ci95: number | null;
  note: string;
}

export interface Knob {
  key: string;
  /** Asked in the second person, because the reader is about to do it. */
  question: string;
  /** What the safeguard is for. Without this a knob is a toy. */
  why: string;
  plain_why: string;
  /** The ledger claim this knob belongs to, so it can be shown with it. */
  claim: string;
  /** Where in the code the parameter lives, so the reader can check. */
  source: string;
  default: string;
  variants: Variant[];
}

export interface Refusal {
  key: string;
  question: string;
  naive: string;
  evidence: Variant[];
  verdict: string;
  method: string;
}

export interface SandboxDocument {
  schema_version: number;
  knobs: Knob[];
  refusals: Refusal[];
}

export const SANDBOX_SCHEMA = 2;

export async function loadSandbox(base: string): Promise<SandboxDocument> {
  const response = await fetch(`${base}sandbox.json`);
  if (!response.ok) throw new Error(`sandbox.json: ${response.status}`);
  const document_ = (await response.json()) as SandboxDocument;
  if (document_.schema_version !== SANDBOX_SCHEMA) {
    throw new Error(`sandbox.json schema ${document_.schema_version}`);
  }
  return document_;
}

/** Which claims the sandbox has anything to say about. */
export function knobsFor(doc: SandboxDocument | null, claim: string): Knob[] {
  return doc?.knobs.filter((knob) => knob.claim === claim) ?? [];
}

/**
 * The refusal belongs to the marine null.
 *
 * That claim says there is no single global poleward shift; the refusal is the analysis that would
 * have said there was, and why it must not be run. Keyed here rather than in the Python because it
 * is a presentation decision — `sandbox.py` has no opinion about which claim card it appears on.
 */
export function refusalsFor(doc: SandboxDocument | null, claim: string): Refusal[] {
  return claim === "marine-null" ? (doc?.refusals ?? []) : [];
}

/**
 * Enough digits to see the knob move, and no more.
 *
 * Years are integers: the percentile of a first-recorded year printed as "1985.00 year", which reads
 * as a measurement to two decimal places of something that is counted.
 */
export function format(value: number, unit: string): string {
  if (unit === "year") return `${value.toFixed(0)} ${unit}`;
  const digits = Math.abs(value) < 0.1 ? 3 : 2;
  return `${value.toFixed(digits).replace("-", "−")} ${unit}`;
}

export interface Comparison {
  /** Signed difference from the published variant, in the variant's own unit. */
  delta: number;
  /** True when the alternative shows a *larger* effect than the published one. */
  larger: boolean;
  /** How the published number reads against this one, in a phrase. */
  phrase: string;
}

export function compare(knob: Knob, variant: Variant): Comparison | null {
  const published = knob.variants.find((candidate) => candidate.key === knob.default);
  if (!published || published.key === variant.key) return null;

  const delta = variant.value - published.value;
  const larger = Math.abs(variant.value) > Math.abs(published.value);
  // Both directions matter and they mean different things. A larger effect means the published
  // number is the cautious one; a smaller one means the safeguard is load-bearing. Saying only
  // "the number moved" would waste the distinction.
  const phrase = larger
    ? "a larger effect than the number we publish"
    : "a smaller effect than the number we publish";
  return { delta, larger, phrase };
}
