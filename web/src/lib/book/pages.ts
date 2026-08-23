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
 * | `how` | how it was measured, in plain words, and the pre-registration | 320-379 | 826 |
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
import { CHAPTERS, inRealm, type Chapter } from "../story";
import type { Finding } from "../ledger";

/** One page's worth of one thing. */
export type Panel =
  | { kind: "opening" }
  | { kind: "intro"; from: number; to: number }
  /**
   * What was found: the sentence, and why it matters -- one page, or two.
   *
   * `all` is the spread's. A phone takes them apart because the four blocks together ran 21 to 67px
   * past a 375px leaf, and the seam is the owner's own reading order: what we found, and then what
   * follows from it. The plain sentence alone on a leaf is also the better opening.
   */
  | { kind: "finding"; key: string; part: "all" | "said" | "matters" }
  /** How it was measured, in plain words: the page between the finding and its figure. */
  | { kind: "how"; key: string }
  /** Which of the figure's declared pages, by index into `figures.ts`. */
  | { kind: "figure"; key: string; at: number }
  /**
   * The number, with its scope and its caveat -- in one page, or in two.
   *
   * `all` is the spread's. A phone gets `value` and `caveat`, because this is the panel that
   * overflowed a 375px column worst: 517 pixels past the leaf on the coverage claim, whose value is
   * two eight-digit counts and two percentages. The seam is the one the register already has -- the
   * measurement and the precise sentence, then what would make them wrong.
   */
  | { kind: "record"; key: string; part: "all" | "value" | "caveat" }
  /**
   * The risk-of-bias assessment: six domains on one page, or half of them on each of two.
   *
   * The table is the tallest thing in the margin -- 433 to 1,092px on the spread, which is why it is
   * a page at all -- and in a 375px column every domain's finding is a paragraph. Split by domain,
   * because a row is the unit the assessment already has.
   */
  | { kind: "bias"; key: string; part: "all" | "first" | "rest" }
  | { kind: "survived"; key: string }
  /** One knob or one refusal, from whichever of the two documents keys it to this claim. */
  | { kind: "panel"; doc: "safeguards" | "dial"; key: string; part: "knobs" | "refusals"; at: number }
  /**
   * The world: its map, its tools, or both on one leaf.
   *
   * A spread gives the tools the left page and the map the right. A phone cannot: the clock and the
   * layer switches are controls whose whole purpose is watching the map answer, and on separate
   * leaves that is not slow, it is pointless -- which ADR 0015 decision 8 left open and named. So
   * `all` is the phone's: one leaf, the globe filling it, and the tools in a flap over its foot.
   */
  | { kind: "world"; part: "map" | "apparatus" | "all" }
  /**
   * A chapter the realm filter emptied, which is a different silence from a missing claim.
   *
   * Carries its own chapter, like `finding` carries its key. A panel is handed to the page snippet
   * without the spread around it, so a panel that needs to name its chapter has to hold it.
   */
  | { kind: "absent"; realm: string; chapter: string }
  | { kind: "blank" };

/** Two facing pages. */
export interface Spread {
  chapter: Chapter;
  /** Position within the chapter, so a page has an address a reader can be sent to. */
  at: number;
  verso: Panel;
  recto: Panel;
}

/** One page, on its own, which is what a phone shows. */
export interface Leaf {
  chapter: Chapter;
  /** Position within the chapter, so a page has an address a reader can be sent to. */
  at: number;
  panel: Panel;
  /** Null on the very first leaf, which is a title page and carries no number, as on the spread. */
  folio: number | null;
}

/**
 * One run of pages that must not be interleaved with another: a claim, the introduction, the world.
 *
 * The unit exists because the two containers disagree about what to do with the same pages, and the
 * owner's answer to that was that they should: forcing one shape onto both is worse than letting each
 * be itself. A spread pads each of these to an even count, so a leaf that ends one argument never
 * faces a leaf that starts the next. A phone shows one page at a time, so it has nothing to pad
 * against and those blanks are dead swipes -- it concatenates instead.
 *
 * Both read the same list. What differs is the arrangement, not the content, which is the line worth
 * holding: two containers, one authored book.
 */
interface Section {
  chapter: Chapter;
  pages: Panel[];
}

/**
 * How many passages the introduction puts on one page.
 *
 * Measured: its passages run 171 to 426px and the standfirst is 426 on its own, so the opening page
 * takes the standfirst and the counted line and nothing else, and two passages fill a page after it.
 */
const PASSAGES_PER_PAGE = 2;

/**
 * And one on a phone.
 *
 * Two passages of 171 to 426px fit an 826px page at the spread's reading scale. In a 375px column
 * the same prose reflows about 1.8 times taller and the first pair ran 22px past the leaf, which is
 * the whole argument for the phone arranging these pages itself.
 */
const PASSAGES_PER_LEAF = 1;

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
function claimPages(key: string, sources: Sources, narrow: boolean): Panel[] {
  /*
    What we found, how we found it, the picture, then the numbers.

    The owner's reading order, and the `how` page is the one that was missing: a claim went from a
    plain sentence straight to a plate, with the procedure represented by a link to a filename. Its
    own page rather than a paragraph added to the first one, because the finding panel measures 526
    to 680 of its 826 and a plain method is another 150 -- the split is where the material already
    had a seam, which is the rule every other split in this file follows.
  */
  const pages: Panel[] = narrow
    ? [
        { kind: "finding", key, part: "said" },
        { kind: "finding", key, part: "matters" },
        { kind: "how", key },
      ]
    : [{ kind: "finding", key, part: "all" }, { kind: "how", key }];
  figurePages(key, narrow).forEach((_page, at) => pages.push({ kind: "figure", key, at }));
  // The record is one page on a spread and two on a phone. Its own seam, stated where the panel is.
  pages.push(
    ...(narrow
      ? ([
          { kind: "record", key, part: "value" },
          { kind: "record", key, part: "caveat" },
        ] as Panel[])
      : ([{ kind: "record", key, part: "all" }] as Panel[])),
  );
  pages.push(
    ...(narrow
      ? ([
          { kind: "bias", key, part: "first" },
          { kind: "bias", key, part: "rest" },
        ] as Panel[])
      : ([{ kind: "bias", key, part: "all" }] as Panel[])),
  );
  pages.push({ kind: "survived", key });

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

  return pages;
}

/**
 * The introduction, across as many spreads as its passages need.
 *
 * Only pages that carry something: the first attempt stepped two spreads at a time and allocated a
 * page for passages four to six of a document that has four, so the book held a leaf that rendered
 * nothing at all. A phone test looking for content on the leaf before the second chapter is what
 * found it.
 */
function introPages(doc: IntroductionDocument | null, narrow: boolean): Panel[] {
  const passages = doc?.passages.length ?? 0;
  const each = narrow ? PASSAGES_PER_LEAF : PASSAGES_PER_PAGE;
  const pages: Panel[] = [{ kind: "opening" }];
  for (let from = 0; from < passages; from += each) {
    pages.push({ kind: "intro", from, to: Math.min(from + each, passages) });
  }
  return pages;
}

/**
 * Every spread in the book, in reading order.
 *
 * Derived from the documents rather than declared, so adding a claim to `findings.json` adds its
 * spreads and its page numbers without anybody editing a table. The two chapters that carry no
 * claim of their own keep the shapes they already had: the introduction is prose across as many
 * spreads as it has passages, and the world is one spread with the map on it.
 */
function sectionsOf(
  sources: Sources,
  chapters: readonly Chapter[],
  realm: string,
  narrow: boolean,
): Section[] {
  const opening = chapters[0];
  const world = chapters[chapters.length - 1];
  const out: Section[] = [];

  for (const chapter of chapters) {
    if (chapter === opening) {
      out.push({ chapter, pages: introPages(sources.introduction, narrow) });
      continue;
    }
    if (chapter === world) {
      out.push({
        chapter,
        pages: narrow
          ? [{ kind: "world", part: "all" }]
          : [
              { kind: "world", part: "apparatus" },
              { kind: "world", part: "map" },
            ],
      });
      continue;
    }
    // Published first, then filtered, because the two reasons a chapter can come out empty need
    // different pages and telling them apart needs both counts.
    const published = chapter.keys.flatMap(
      (key) => sources.findings.find((finding) => finding.key === key) ?? [],
    );

    let drawn = 0;
    for (const finding of published) {
      if (!inRealm(finding, realm)) continue;
      out.push({ chapter, pages: claimPages(finding.key, sources, narrow) });
      drawn += 1;
    }

    /*
      A chapter that came out empty still gets a leaf, so the tab it is reachable by does not open
      onto the previous chapter -- and which leaf depends on why it is empty.

      Filtered to nothing is the interesting case and it gets words: the claims exist and every one
      of them was measured in another realm, which is a fact about where the instruments are. Empty
      because the ledger does not hold them is blank paper, because there is nothing true to say
      about a chapter whose claims never arrived.
    */
    if (drawn === 0) {
      const empty: Panel =
        realm !== "" && published.length > 0
          ? { kind: "absent", realm, chapter: chapter.title }
          : { kind: "blank" };
      out.push({ chapter, pages: [empty] });
    }
  }

  return out;
}

export function spreadsOf(
  sources: Sources,
  chapters: readonly Chapter[] = CHAPTERS,
  realm = "",
): readonly Spread[] {
  const out: Spread[] = [];
  let chapter: Chapter | null = null;
  let at = 0;

  for (const section of sectionsOf(sources, chapters, realm, false)) {
    // `at` is the offset within the chapter, so it restarts where the chapter does.
    if (section.chapter !== chapter) {
      chapter = section.chapter;
      at = 0;
    }
    const spreads = fold(section.chapter, section.pages, at);
    out.push(...spreads);
    at += spreads.length;
  }

  return out;
}

/**
 * The same book as a flat run of pages, which is what a phone reads.
 *
 * Not the spreads flattened. That is what it used to be, and it carried two of the spread's
 * decisions onto a screen that has no use for either: the blank that pads a section to an even page
 * count, which on a phone is a swipe onto nothing, and a folio computed from a spread index.
 *
 * The owner's call, when the measurements came in: a phone and a spread can be different, because
 * the logic is different and forcing one onto the other is worse. So this is its own arrangement of
 * the same authored pages -- no padding, and numbered by leaf.
 */
export function leavesOf(
  sources: Sources,
  chapters: readonly Chapter[] = CHAPTERS,
  realm = "",
): readonly Leaf[] {
  const out: Leaf[] = [];
  let chapter: Chapter | null = null;
  let at = 0;

  for (const section of sectionsOf(sources, chapters, realm, true)) {
    if (section.chapter !== chapter) {
      chapter = section.chapter;
      at = 0;
    }
    for (const panel of section.pages) {
      // The first leaf of the book is a title page and carries no number, which is the convention
      // the spread already keeps -- `folio(0)` returns null for its verso for the same reason.
      out.push({ chapter: section.chapter, at, panel, folio: out.length === 0 ? null : out.length });
      at += 1;
    }
  }

  return out;
}

/** Index of the first spread of a chapter, which is where its tab goes. */
export function openingOf(
  pages: readonly { chapter: Chapter }[],
  slug: string,
): number {
  const at = pages.findIndex((page) => page.chapter.slug === slug);
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
