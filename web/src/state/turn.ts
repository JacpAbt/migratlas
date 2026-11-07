/**
 * How long the book's motion lasts, read from the stylesheet, and whether there is to be any.
 *
 * Every duration is a token in `tokens.css`, and one block there zeroes them all for a reader who
 * has asked for reduced motion. Reading the durations back from CSS keeps every animation in the
 * project answering to that one switch.
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

/**
 * Whether motion is wanted, read from the token rather than from `matchMedia`: a second
 * `matchMedia` call would be a second place that has to remember the rule. The book's page turn
 * answers to it.
 */
export function still(): boolean {
  // Compared as a number and not against the strings `0ms` and `0s`: the same minifier that turns
  // `900ms` into `.9s` is free to emit `0s` for `0ms`, and a third spelling would slip past.
  return drawMs() === 0;
}
