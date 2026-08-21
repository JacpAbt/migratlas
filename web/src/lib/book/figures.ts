/**
 * Which claims have a figure of their own, what it is, and how many pages it takes.
 *
 * Lifted from `claim/Evidence.svelte` rather than reinvented, including its reasoning: only two
 * claims have a figure that adds something the sentence does not. A chart per claim would be
 * decoration -- the marine null and the composition control are both "indistinguishable from zero",
 * and a flat line drawn three times teaches nothing the value already said.
 *
 * Everything else gets the drawn plate, which answers a different question: where on Earth.
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
  part: "chart" | "reading" | "notes" | "measured" | "held";
  /** The heading on that page. */
  title: string;
}

export interface FigureKind {
  kind: "ribbon" | "coverage";
  pages: readonly FigurePage[];
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
export const FIGURES: Readonly<Record<string, FigureKind>> = {
  "anthropogenic-share": {
    kind: "ribbon",
    pages: [
      { part: "chart", title: "The world without us" },
      { part: "chart", title: "The world without us, continued" },
      { part: "reading", title: "Why the two answers differ" },
      { part: "notes", title: "What both reconstructions survived" },
    ],
  },
  "coverage-bias": {
    kind: "coverage",
    pages: [
      { part: "measured", title: "Where change could be measured" },
      { part: "held", title: "Held, and never drawn" },
    ],
  },
};

/** How many charts this figure's own document must hold, for the guard test to check. */
export const RIBBON_CHARTS = FIGURES["anthropogenic-share"]!.pages.filter(
  (page) => page.part === "chart",
).length;

/** The pages this claim's figure needs. A plate is one page and has no slice. */
export function figurePages(key: string): readonly FigurePage[] {
  return FIGURES[key]?.pages ?? [{ part: "chart", title: "" }];
}
