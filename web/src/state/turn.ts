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
 */
function still(): boolean {
  const draw = getComputedStyle(document.documentElement).getPropertyValue("--draw").trim();
  return draw === "0ms" || draw === "0s";
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
