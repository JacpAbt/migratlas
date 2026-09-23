/**
 * The chapter openers, as published by `reports/chapters.py`.
 *
 * Fetched rather than written here, for the reason every other document on this site is: frontend
 * prose is authored in Python and rendered verbatim, and an argument hard-coded in a component is
 * the one prose on the site that nothing holds to account. These paragraphs quote the ledger, so a
 * figure in an opener is the same object the record page shows.
 *
 * **Why this document exists at all.** The chapters carried claims and nothing between them, which
 * is what the owner read as a mess of single points with no story behind it. The claims were never
 * the problem: what was missing was the sentence saying why one chapter follows another.
 *
 * The schema check is `introduction.ts`'s and for the same reason: a document whose shape has moved
 * renders as a page of blanks, which looks like a design decision.
 */

export interface ChapterOpener {
  /** The question a reader arrives with. */
  question: string;
  /** The account, a paragraph an entry. Carries no digits, by a rule the Python enforces. */
  paragraphs: string[];
  /**
   * The claims it rests on, by ledger key. Not rendered.
   *
   * This was `figures`, one `key — value` line per claim printed under the account in the mono face,
   * and a first reading of the book met it as the first number in every chapter and took it for
   * code. The values are on the record pages; the leaf keeps only the list, which the Python guards.
   */
  keys: string[];
}

export interface ChaptersDocument {
  schema_version: number;
  chapters: Record<string, ChapterOpener>;
}

export const CHAPTERS_SCHEMA = 4;

export async function loadChapters(base: string): Promise<ChaptersDocument> {
  const response = await fetch(`${base}chapters.json`);
  if (!response.ok) throw new Error(`chapters.json: ${response.status}`);
  const document_ = (await response.json()) as ChaptersDocument;
  if (document_.schema_version !== CHAPTERS_SCHEMA) {
    throw new Error(`chapters.json schema ${document_.schema_version}`);
  }
  return document_;
}

/** One chapter's opener, or null where the document is missing or does not carry it. */
export function openerOf(
  document_: ChaptersDocument | null,
  slug: string,
): ChapterOpener | null {
  return document_?.chapters[slug] ?? null;
}
