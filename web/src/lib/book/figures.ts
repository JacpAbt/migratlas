/**
 * Which claims have a figure of their own, what it is, and how many pages it takes.
 *
 * Lifted from `claim/Evidence.svelte` rather than reinvented. Two claims have a figure of their
 * own that carries an argument -- the counterfactual ribbon and the coverage assessment. Nine more
 * carry a *headline* figure: the result the plain sentence states, drawn from the values the
 * ledger's own functions produced (`reports/headline.py`). This file used to argue that a chart
 * per claim would be decoration because a flat line teaches nothing; a first reading of the book
 * answered that a null drawn as a pile centred on zero teaches exactly what the sentence says,
 * and that a project about numbers showing none of them as pictures reads as a wall of text.
 *
 * A headline page still carries the plate, smaller and more crooked, because the owner wants the
 * maps around like a sketchbook's -- and because the plate answers the other question, where on
 * Earth. The two claims that keep a plate alone are the ones no honest single picture carries:
 * the transfer test is three numbers and the protocol disagreement a ratio of two scatters.
 *
 * It lives in a module of its own rather than inside `Figure.svelte` because `pages.ts` has to know
 * it too: a plate is one page and these two are four and two, so the fact decides the book's length.
 * Two copies of it would put the page count and the page contents in disagreement.
 *
 * **The page counts are declared here and the documents are asserted against them.** The ribbon's
 * own document is fetched lazily by the component that draws it, so the pagination cannot count its
 * charts -- and a page count that arrives late is a folio that renumbers itself under the reader.
 * `tests/book.spec.ts` asserts `ribbon.json` holds exactly the two reconstructions this claims, so a
 * third one added upstream fails the build rather than falling off the end of the book.
 */

/** One page of a multi-page figure. */
export interface FigurePage {
  /** Which slice of the figure component to render. */
  part:
    | "chart"
    | "reading"
    | "gap"
    | "precise"
    | "caveat"
    | "notes"
    | "measured"
    | "summary"
    | "sources"
    | "held"
    | "held-first"
    | "held-more";
  /** The heading on that page. */
  title: string;
}

export interface FigureKind {
  kind: "ribbon" | "coverage" | "headline";
  pages: readonly FigurePage[];
  /**
   * The same figure for a 375px column, where two of these pages do not fit.
   *
   * Measured on a phone: the coverage assessment's first page ran 126px past its leaf and the
   * ribbon's reading 345px. Each splits at a seam it already had -- the map's own summary and then
   * the table of sources behind it; the ribbon's question and then the answer to it. Declared rather
   * than derived, for the reason the wide list is declared: a page count that arrives late is a
   * folio that renumbers itself under the reader.
   *
   * Absent where the wide list already fits a narrow leaf, which is most figures -- a plate is one
   * page either way.
   */
  narrow?: readonly FigurePage[];
}

/*
  Each split is at a seam the figure already had, and each was measured at 1600x900 against an 826px
  page before being made: the ribbon overflowed by 1,406px whole, still by 536 with its charts alone
  on one page, and by 147 with its reading and its notes together. The coverage assessment overflowed
  by 459 whole and fits once what could be measured is separated from what is withheld.

  A repeated heading rather than an invented one on the ribbon's second chart: the two are two
  independent reconstructions of the same counterfactual, and giving the second a title of its own
  would be this file making a claim about the science instead of the report making it.
*/
/**
 * One page, no title of its own: the chart prints the title the document carries, and the plate
 * rides under it. Declared as a list so the guard in `tests/book.spec.ts` can hold the document
 * to it -- a headline drawn for a claim not declared here would never reach a page.
 */
export const HEADLINE_KEYS: readonly string[] = [
  "autumn-advance",
  "flight-advance",
  "composition-stable",
  "marine-null",
  "atlas-no-net-change",
  "displacement-flat",
  "seas-disagree",
  "skill-sparse",
  "projection-mask",
];

const HEADLINE: FigureKind = { kind: "headline", pages: [{ part: "chart", title: "" }] };

export const FIGURES: Readonly<Record<string, FigureKind>> = {
  ...Object.fromEntries(HEADLINE_KEYS.map((key) => [key, HEADLINE])),
  "anthropogenic-share": {
    kind: "ribbon",
    pages: [
      { part: "chart", title: "The world without us" },
      { part: "chart", title: "The world without us, continued" },
      { part: "reading", title: "Why the two answers differ" },
      { part: "notes", title: "What both reconstructions survived" },
    ],
    narrow: [
      { part: "chart", title: "The world without us" },
      { part: "chart", title: "The world without us, continued" },
      /*
        `gap` and `caveat` rather than `reading`, which is the two of them together.

        Named apart rather than expressed as "reading minus its caveat", because the gates in
        `Ribbon.svelte` read as unions of part names: a value meaning "some of reading" would have to
        be excluded from the wide case by hand, and the page that got it wrong would still render.
        Two names, two pages, and the wide list keeps the one it had.
      */
      { part: "gap", title: "Why the two answers differ" },
      { part: "precise", title: "Why the two answers differ, precisely" },
      { part: "caveat", title: "What to hold against both" },
      { part: "notes", title: "What both reconstructions survived" },
    ],
  },
  "coverage-bias": {
    kind: "coverage",
    pages: [
      { part: "measured", title: "Where change could be measured" },
      { part: "held", title: "Held, and never drawn" },
    ],
    narrow: [
      { part: "summary", title: "Where change could be measured" },
      { part: "sources", title: "What each source can support" },
      { part: "held-first", title: "Held, and never drawn" },
      { part: "held-more", title: "Held, and never drawn, continued" },
    ],
  },
};

/** How many charts this figure's own document must hold, for the guard test to check. */
export const RIBBON_CHARTS = FIGURES["anthropogenic-share"]!.pages.filter(
  (page) => page.part === "chart",
).length;

/** The pages this claim's figure needs. A plate is one page and has no slice. */
export function figurePages(key: string, narrow = false): readonly FigurePage[] {
  const figure = FIGURES[key];
  if (!figure) return [{ part: "chart", title: "" }];
  return (narrow && figure.narrow) || figure.pages;
}
