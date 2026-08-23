/**
 * Turning a leaf of the notebook, when the browser will do it and never otherwise.
 *
 * The paper turns and the world does not. That is the whole design constraint: the globe is live
 * behind the sheet, it is the thing the claim is about, and freezing it into a snapshot for the
 * duration of a page turn would say the opposite -- that the map is a picture the card is printed
 * over. So the root snapshot is switched off in CSS and only the sheet carries a
 * `view-transition-name`; MapLibre's canvas is never captured and keeps rendering throughout.
 */

/** The subset of the View Transitions API this uses, so `lib.dom` version drift cannot break tsc. */
interface ViewTransitionCapable {
  startViewTransition?: (update: () => Promise<void> | void) => { finished: Promise<void> };
}

/**
 * Whether motion is wanted, read from the token rather than from `matchMedia`.
 *
 * One block in `tokens.css` zeroes every duration, so asking CSS what it resolved to keeps every
 * animation in the project answering to the same switch. A second `matchMedia` call here would be
 * a second place that has to remember the rule.
 *
 * Exported for the book's own page turn, which is a CSS 3D rotation rather than a view transition
 * and so cannot use `turnPage` -- but must answer the same switch, for exactly the reason above.
 */
/**
 * A CSS duration token, in milliseconds.
 *
 * **The unit is not the one the stylesheet was written in.** `tokens.css` says `--draw-slow: 900ms`
 * and the minifier in the production build emits `.9s`, because that is three bytes shorter --
 * so `Number.parseFloat` on the computed value returns `0.9` in the shipped app and `900` in dev.
 *
 * That shipped. `Book.svelte` used the parsed figure as the delay after which the turning leaf is
 * cleared, so in the built application the leaf was destroyed **121ms into a 900ms rotation**: the
 * page turn worked perfectly on the dev server and flickered in production, which is the shape of
 * defect this project has paid for before. Nothing caught it because `book.spec.ts` asserts the turn
 * by driving the animation's own timeline with the animation paused, and never waits for the clock.
 *
 * So durations are read through here, and a unit is handled rather than assumed.
 */
export function durationMs(value: string, fallback = 0): number {
  const text = value.trim();
  const amount = Number.parseFloat(text);
  if (!Number.isFinite(amount)) return fallback;
  // `ms` before `s`, or every millisecond value is read as a second.
  return text.endsWith("ms") ? amount : amount * 1000;
}

/** One duration token, in milliseconds, as the browser resolved it. */
export function drawMs(token = "--draw", fallback = 0): number {
  return durationMs(
    getComputedStyle(document.documentElement).getPropertyValue(token),
    fallback,
  );
}

export function still(): boolean {
  // Compared as a number and not against the strings `0ms` and `0s`: the same minifier that turns
  // `900ms` into `.9s` is free to emit `0s` for `0ms`, and a third spelling would slip past.
  return drawMs() === 0;
}

/**
 * Apply `update`, as a page turn where that is possible.
 *
 * Falls through to a plain call in three cases, and each is deliberate rather than a gap: a browser
 * with no View Transitions, a reader who has asked for reduced motion, and any error inside the
 * update. In all three the new claim is simply *there*, which is the correct end state of the
 * animation rather than a degraded version of it.
 *
 * `update` must both change the state and wait for the DOM to catch up -- in Svelte that means
 * awaiting `tick()`. A transition that resolves before the new sheet exists captures the old one
 * twice and cross-fades nothing.
 */
export function turnPage(update: () => Promise<void> | void): void {
  const host = document as unknown as ViewTransitionCapable;
  if (!host.startViewTransition || still()) {
    void update();
    return;
  }
  host.startViewTransition(update);
}
