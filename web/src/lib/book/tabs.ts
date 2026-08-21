/**
 * Which colour each chapter's tab is cut from.
 *
 * Data rather than CSS, because there are two containers -- the spread and the mobile leaves -- and
 * the same seven tabs appear in both. As `nth-child` rules in one component's scoped styles this
 * would have to be written twice, and two copies of a palette assignment is one copy that goes
 * stale the first time a chapter is added.
 *
 * Every value is a token from `tokens.css`. Nothing here introduces a colour: the tab's stock is the
 * page's own paper with a little of one hue mixed into it, which is also why it inverts with the
 * surface for free -- on the night page the same declaration lands as dark tinted stock rather than
 * a pastel one.
 */

/**
 * Seven hues the stylesheet already had, ordered so no two neighbours share one.
 *
 * The greys sit at the ends, where the introduction and the back pocket are, and the saturated ones
 * are spread through the middle where the claims are.
 */
const TINTS: readonly string[] = [
  "--pencil",
  "--rust",
  "--line-counterfactual",
  "--detect-short",
  "--moss",
  "--rust-ink",
  "--ink-soft",
];

/**
 * How much paper stays in the stock, per tab.
 *
 * Three of these are not the common figure, and both exceptions are measured rather than chosen.
 * The dark palette's accents are *lighter* than its page -- rust is #a3441f by day and #ffa870 by
 * night -- so the mix that tints a cream tab darker tints a near-black one lighter, and the ink on
 * it fell to 3.74:1 against this project's 4.5 floor for text. `--tab-accent` carries the eased
 * figure for the dark surfaces. The yellow is lighter than the page in *both* surfaces, so it needs
 * less of itself outright.
 */
const MIXES: Readonly<Record<number, string>> = {
  1: "var(--tab-accent)",
  3: "84%",
  5: "var(--tab-accent)",
};

/** The custom properties one tab needs, ready for `style=`. */
export function tabStyle(index: number): string {
  const tint = TINTS[index % TINTS.length] ?? "--pencil";
  const mix = MIXES[index] ?? "var(--tab-stock)";
  return `--tint: var(${tint}); --mix: ${mix}`;
}
