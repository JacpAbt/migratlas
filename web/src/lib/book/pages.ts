/**
 * What is on each page, and how many pages there are.
 *
 * **A book's answer to "this does not fit on a page" is another page, not a scrollbar.** The first
 * build got that wrong in a way no test could see: `.page__inner` scrolled, so every chapter fitted
 * by definition. Measured at 1600x900, against a page whose budget is 826px, the left page of
 * "What did not" held 6,855px -- eight and a third screens of text on one leaf, with the sentence at
 * the fold cut in half. A page that scrolls is a document wearing a book's clothes.
 *
 * So the unit of the book is a **panel**: one page's worth of one thing. Panels are declared, not
 * measured, and the split points are the ones the material already had -- which is why they fit.
 * Every number below was measured on the shipped book before this module existed:
 *
 * | panel | what it carries | measured | budget |
 * | --- | --- | --- | --- |
 * | `finding` | the banner, the plain sentence, why it matters, the plain caveat | 526-680 | 826 |
 * | `figure` | the plate or chart, with its legend | ~460 | 826 |
 * | `record` | "Precisely", the value, the scope, the caveat, the method, what it survived | 274-821 | 826 |
 * | `bias` | the risk-of-bias table, which is the margin's tall section | 433-1092 | 826 |
 * | `survived` | what the claim survived, which is the same question from the other side | 231-463 | 826 |
 * | `figure` again | a chart, its reading, its notes: `figures.ts` declares how many | 1285-2232 split | 826 |
 * | `panel` | one safeguard knob, or one dial, or one refusal | 435-586 each | 826 |
 *
 * Everything that overflowed a page is split here rather than shortened, and every split is at a
 * seam the material already had: the bias table and what the claim survived take a page together,
 * the counterfactual ribbon puts its charts on one page and the reading of them on the next, the
 * coverage assessment separates what could be measured from what is held back from the map, and the
 * knobs go one to a page. Nothing was cut to make it fit -- `reports/findings.py` refuses to publish
 * a claim without its caveat, and a layout that dropped one to save a page would be doing by
 * omission what that refusal exists to prevent.
 *
 * `tests/book.spec.ts` asserts no page exceeds its own budget at either supported width. That guard
 * is the point of declaring panels at all: without it the next paragraph added to a claim silently
 * reintroduces the scrollbar.
 */

import type { IntroductionDocument } from "./introduction";
import type { SandboxDocument } from "../sandbox/sandbox";
import { figurePages } from "./figures";
import { dialRefusalsFor, dialsFor } from "../sandbox/response";
import { knobsFor, refusalsFor } from "../sandbox/sandbox";
import { CHAPTERS, type Chapter } from "../story";
import type { Finding } from "../ledger";

/** One page's worth of one thing. */
export type Panel =
  | { kind: "opening" }
  | { kind: "intro"; from: number; to: number }
  | { kind: "finding"; key: string }
  /** Which of the figure's declared pages, by index into `figures.ts`. */
  | { kind: "figure"; key: string; at: number }
  | { kind: "record"; key: string }
  | { kind: "bias"; key: string }
  | { kind: "survived"; key: string }
  /** One knob or one refusal, from whichever of the two documents keys it to this claim. */
  | { kind: "panel"; doc: "safeguards" | "dial"; key: string; part: "knobs" | "refusals"; at: number }
  | { kind: "world"; part: "map" | "apparatus" }
  | { kind: "blank" };

/** Two facing pages. */
export interface Spread {
  chapter: Chapter;
  /** Position within the chapter, so a page has an address a reader can be sent to. */
  at: number;
  verso: Panel;
  recto: Panel;
}

/**
 * How many passages the introduction puts on one page.
 *
 * Measured: its passages run 171 to 426px and the standfirst is 426 on its own, so the opening page
 * takes the standfirst and the counted line and nothing else, and two passages fill a page after it.
 */
const PASSAGES_PER_PAGE = 2;

/** The documents the pagination depends on. All of them, because a page count cannot arrive late. */
export interface Sources {
  findings: readonly Finding[];
  introduction: IntroductionDocument | null;
  safeguards: SandboxDocument | null;
  dial: SandboxDocument | null;
}

function pair(chapter: Chapter, at: number, verso: Panel, recto: Panel): Spread {
  return { chapter, at, verso, recto };
}

/*
  Pages into spreads, two at a time, and an odd count ends on blank paper.

  Nothing is padded to an even number of pages and nothing is allowed to share a leaf with the next
  thing either: a spread whose left page ends one argument and whose right page starts another reads
  as one argument with a non-sequitur in it. Blank paper in a sketchbook is not a defect.
*/
function fold(chapter: Chapter, pages: readonly Panel[], from: number): Spread[] {
  const spreads: Spread[] = [];
  for (let page = 0; page < pages.length; page += 2) {
    spreads.push(
      pair(chapter, from + spreads.length, pages[page]!, pages[page + 1] ?? { kind: "blank" }),
    );
  }
  return spreads;
}

/**
 * The spreads one claim needs, which is however many its own material needs.
 *
 * Four pages for a claim with a plate and no audit; ten for `autumn-advance`, which has three
 * safeguard knobs. Padding every claim to the longest would have added a dozen blank spreads, and a
 * book where every chapter is the same length is a form rather than a book.
 */
function claimSpreads(chapter: Chapter, key: string, at: number, sources: Sources): Spread[] {
  const pages: Panel[] = [{ kind: "finding", key }];
  figurePages(key).forEach((_page, at) => pages.push({ kind: "figure", key, at }));
  pages.push({ kind: "record", key }, { kind: "bias", key }, { kind: "survived", key });

  /*
    One knob and one refusal per page, in the order `claim/Evidence.svelte` fixed: how much to trust
    the number, and only then what a different world would do to it.

    Each document brings its own selectors and that is not tidiness. The safeguards' one refusal is
    keyed to `marine-null` by `sandbox.ts`, while the dial's two travel *with its dials* -- so
    `refusalsFor` on the response document returns nothing at all. Written with one pair of selectors
    for both, the dial's two refusals got no pages and were unreachable in a book that prints
    everything; the test that opens the dial is what said so.
  */
  for (const source of [
    { doc: "safeguards" as const, held: sources.safeguards, knobs: knobsFor, refusals: refusalsFor },
    { doc: "dial" as const, held: sources.dial, knobs: dialsFor, refusals: dialRefusalsFor },
  ]) {
    for (const [part, items] of [
      ["knobs", source.knobs(source.held, key)],
      ["refusals", source.refusals(source.held, key)],
    ] as const) {
      items.forEach((_item, index) =>
        pages.push({ kind: "panel", doc: source.doc, key, part, at: index }),
      );
    }
  }

  return fold(chapter, pages, at);
}

/**
 * The introduction, across as many spreads as its passages need.
 *
 * Only pages that carry something: the first attempt stepped two spreads at a time and allocated a
 * page for passages four to six of a document that has four, so the book held a leaf that rendered
 * nothing at all. A phone test looking for content on the leaf before the second chapter is what
 * found it.
 */
function introSpreads(chapter: Chapter, doc: IntroductionDocument | null): Spread[] {
  const passages = doc?.passages.length ?? 0;
  const pages: Panel[] = [{ kind: "opening" }];
  for (let from = 0; from < passages; from += PASSAGES_PER_PAGE) {
    pages.push({ kind: "intro", from, to: Math.min(from + PASSAGES_PER_PAGE, passages) });
  }
  return fold(chapter, pages, 0);
}

/**
 * Every spread in the book, in reading order.
 *
 * Derived from the documents rather than declared, so adding a claim to `findings.json` adds its
 * spreads and its page numbers without anybody editing a table. The two chapters that carry no
 * claim of their own keep the shapes they already had: the introduction is prose across as many
 * spreads as it has passages, and the world is one spread with the map on it.
 */
export function spreadsOf(
  sources: Sources,
  chapters: readonly Chapter[] = CHAPTERS,
): readonly Spread[] {
  const opening = chapters[0];
  const world = chapters[chapters.length - 1];
  const out: Spread[] = [];

  for (const chapter of chapters) {
    if (chapter === opening) {
      out.push(...introSpreads(chapter, sources.introduction));
      continue;
    }
    if (chapter === world) {
      out.push(pair(chapter, 0, { kind: "world", part: "apparatus" }, { kind: "world", part: "map" }));
      continue;
    }
    let at = 0;
    for (const key of chapter.keys) {
      if (!sources.findings.some((finding) => finding.key === key)) continue;
      const spreads = claimSpreads(chapter, key, at, sources);
      out.push(...spreads);
      at += spreads.length;
    }
    // A chapter whose claims are all missing from the ledger still gets a leaf, so the tab it is
    // reachable by does not open onto the previous chapter.
    if (at === 0) out.push(pair(chapter, 0, { kind: "blank" }, { kind: "blank" }));
  }

  return out;
}

/** Index of the first spread of a chapter, which is where its tab goes. */
export function openingOf(spreads: readonly Spread[], slug: string): number {
  const at = spreads.findIndex((spread) => spread.chapter.slug === slug);
  return at < 0 ? 0 : at;
}

/**
 * Folio numbers for a spread: verso then recto.
 *
 * One-based and counted over the whole book, because that is what a page number is for -- "017" in
 * the corner has to mean the same thing on every leaf or it is decoration. The book opens on a
 * recto, as books do, so the first spread's verso is the inside of the cover and carries no number.
 */
export function folio(index: number): [number | null, number] {
  return index === 0 ? [null, 1] : [index * 2, index * 2 + 1];
}
