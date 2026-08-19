/**
 * The response dial: the fitted sensitivity read forwards, and the two questions it will not answer.
 *
 * Deliberately the same shape as `sandbox.json` and deliberately a different document. The types are
 * shared because a dial position and a switched-off safeguard render identically — a labelled option
 * with a number and a note — and a second vocabulary would mean two components doing one job. The
 * documents are separate because the *claims* are not the same: the sandbox says "the correction
 * changes the answer", and this says "the world changing would change the answer". Mixing them would
 * put a scenario next to a robustness check under one heading, and a reader would have no way to tell
 * which they were looking at.
 *
 * Nothing here is a forecast. `reports/response.py` carries the argument in full; the short version
 * is that Phase 3a found interannual skill at 20 of 143 stations and Phase 3d refused the standing
 * prediction its licence, so the panel ships its own refusals beside the dial rather than trusting
 * the reader to supply them.
 */

import type { Knob, Refusal, SandboxDocument } from "./sandbox";

/** Same fields as the sandbox document, so the same components render it. */
export type ResponseDocument = SandboxDocument;

export const RESPONSE_SCHEMA = 1;

export async function loadResponse(base: string): Promise<ResponseDocument> {
  const response = await fetch(`${base}response.json`);
  if (!response.ok) throw new Error(`response.json: ${response.status}`);
  const document_ = (await response.json()) as ResponseDocument;
  if (document_.schema_version !== RESPONSE_SCHEMA) {
    throw new Error(`response.json schema ${document_.schema_version}`);
  }
  return document_;
}

/** Which claims have a dial. Keyed in the Python, because the claim a fit belongs to is not framing. */
export function dialsFor(doc: ResponseDocument | null, claim: string): Knob[] {
  return doc?.knobs.filter((dial) => dial.claim === claim) ?? [];
}

/**
 * The refusals travel with the dials rather than with a claim key of their own.
 *
 * Both of them are about the dial — one bounds it, one says what it is not — so a claim card showing
 * the dial must show them, and a card without the dial has nothing for them to refuse. Deriving this
 * from `dialsFor` rather than keying it separately means the two cannot drift apart.
 */
export function dialRefusalsFor(doc: ResponseDocument | null, claim: string): Refusal[] {
  return dialsFor(doc, claim).length > 0 ? (doc?.refusals ?? []) : [];
}
