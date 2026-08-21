/**
 * The introduction, as published by `reports/introduction.py`.
 *
 * Fetched rather than written here, and that is the point: frontend prose is authored in Python and
 * rendered verbatim, so an introduction hard-coded in a component would be the one page on the site
 * whose sentences nothing holds to account. Three of its figures are counted from the ledger and the
 * registry, so the opening paragraph cannot claim a size the project does not have.
 *
 * The schema check is the same one `response.ts` makes and for the same reason: a document whose
 * shape has moved renders as a page of blanks, which looks like a design decision.
 */

export interface Passage {
  heading: string;
  body: string;
}

export interface IntroductionDocument {
  schema_version: number;
  title: string;
  standfirst: string;
  /** The sentence carrying the counted figures. */
  counted: string;
  passages: Passage[];
}

export const INTRODUCTION_SCHEMA = 1;

export async function loadIntroduction(base: string): Promise<IntroductionDocument> {
  const response = await fetch(`${base}introduction.json`);
  if (!response.ok) throw new Error(`introduction.json: ${response.status}`);
  const document_ = (await response.json()) as IntroductionDocument;
  if (document_.schema_version !== INTRODUCTION_SCHEMA) {
    throw new Error(`introduction.json schema ${document_.schema_version}`);
  }
  return document_;
}

/**
 * Split the passages across the spread.
 *
 * A book's opening spread is not one page with the other left blank. The standfirst and the counted
 * sentence sit with the first half, the rest carries onto the facing page, and the split follows the
 * count so adding a fifth passage does not silently leave it off the end.
 */
export function acrossTheSpread(document_: IntroductionDocument | null): {
  verso: Passage[];
  recto: Passage[];
} {
  const passages = document_?.passages ?? [];
  const half = Math.ceil(passages.length / 2);
  return { verso: passages.slice(0, half), recto: passages.slice(half) };
}
