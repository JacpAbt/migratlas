/**
 * The hand grows to fill the leaf.
 *
 * Pagination guarantees a page never overflows, and it does that by budgeting for the worst panel
 * of a kind -- so the ones that are not the worst come out short. Measured over the whole book at
 * 1600x900 the median page was 61% full, and thirty-six of a hundred and fourteen were under half:
 * a `how` page is a kicker, eight lines and a link, and the remaining two fifths of the leaf were
 * nothing at all. The owner's word for it was "half empty", and adding words to fix it would be
 * writing prose to fill a box, which is how a book starts lying.
 *
 * So the page is written larger instead, which is what a hand does with a page to itself. The
 * growth is mostly air -- leading and the gaps between blocks -- and only a little size, because
 * the complaint was spacing rather than legibility.
 *
 * **It only ever grows, and it verifies.** `pages.ts` budgets were measured at `--fit: 1`, so a
 * scale at or above one cannot invalidate them, and the search takes the largest step whose
 * measured content still clears the leaf. The overflow guard in `tests/book.spec.ts` is testing
 * the same pages it always was.
 */

/**
 * The two ceilings, and they are separate because they fail differently.
 *
 * The first version had one scale and split it, most of it into air, and a short record page came
 * out at line-height 1.94 -- four lines of hand with a finger's width between them, which reads as
 * a rendering fault rather than as generous setting. Air is the cheaper of the two only up to
 * about a fifth over; past that it stops looking like spacing and starts looking like a mistake.
 *
 * So both are capped where they still look deliberate, and a page too empty for either to reach
 * stays empty -- for a drawing, the way `How.svelte` fills its foot, or for nothing. Filling a leaf
 * is not worth making it unreadable, which is the same trade the type scale in `Book.svelte`
 * refuses.
 */
const AIR_MAX = 1.22;
const TYPE_MAX = 1.16;
/**
 * And the two floors, which are the same trade in the other direction.
 *
 * A page that does not fit has to give something up, and the choice is between smaller type and a
 * caveat the reader cannot see -- `pages.ts` refuses to drop a caveat to save a page, so it is the
 * type. Air goes first and further, because closing the gaps between blocks costs a reader nothing
 * until it starts to look like a mistake; the type itself stops at 0.88, which on this book's
 * smallest page is about 10.3px of body text and the last size these faces stay legible at.
 *
 * Deliberately not enough to save every page. At 1024x768 the worst leaf is half again too tall,
 * and a scale that swallowed that would put 8px type on the page -- so it keeps the floor and
 * scrolls inside `.page__inner`, which is what that backstop has always been for.
 */
const AIR_MIN = 0.76;
const TYPE_MIN = 0.84;

/** How full is full. Not 1: a line of descenders against the foot of the page reads as cut off. */
const TARGET = 0.94;

/**
 * And how full is too full: the page a reader would have to scroll.
 *
 * Separate from `TARGET` because they answer different questions. A page between the two is
 * neither growing nor overflowing and is left exactly as it is -- pulling it back to `TARGET`
 * would shrink pages that fit perfectly well, which a reader would see as the book changing size
 * for no reason.
 */
const FULL = 1;

/** Search resolution. Four probes cover it, and each probe is one layout flush. */
const STEPS = 12;

/** Probes below scale 1. Fewer, because the range below is narrower than the range above. */
const SHRINK_STEPS = 8;

/**
 * The bottom of the lowest thing on the page, relative to the top of its text.
 *
 * Deep rather than `scrollHeight`, and that is the whole reason an earlier sweep reported this
 * book 79% full when it was 61%: `.page__inner` is a full-height flex column, so its scroll height
 * is its client height whenever the content is short, and every under-filled page measured as
 * exactly perfect. What a reader sees is the last mark, so that is what is measured.
 */
function contentBottom(inner: HTMLElement): number {
  /* A drawing is one mark however many paths it took, so the walk stops at it. Descending would
     also mean a rect per path, and one plate is several hundred of them. */
  const DRAWN = new Set(["svg", "img", "canvas", "video", "hr"]);
  let low = Number.NEGATIVE_INFINITY;
  const stack: Element[] = [...inner.children];

  while (stack.length > 0) {
    const element = stack.pop() as Element;
    const box = element.getBoundingClientRect();
    if (box.height < 1 || box.width < 1) continue;
    const style = getComputedStyle(element);
    if (style.visibility === "hidden" || style.opacity === "0") continue;

    const tag = element.tagName.toLowerCase();
    if (DRAWN.has(tag)) {
      if (box.bottom > low) low = box.bottom;
      continue;
    }
    /* A box is only as low as what it holds. An empty one with a height is a spacer, and counting
       it is how a flex column that stretches to the leaf measures as a full page. */
    const paints =
      element.childElementCount === 0
        ? (element.textContent ?? "").trim().length > 0
        : style.backgroundImage !== "none" || parseFloat(style.borderBottomWidth) > 0;
    if (paints && box.bottom > low) low = box.bottom;
    stack.push(...element.children);
  }
  return low;
}

/** The height a page has for text, which is also half of what its fit is a function of. */
function roomOf(inner: HTMLElement): number {
  const style = getComputedStyle(inner);
  return (
    inner.getBoundingClientRect().height -
    parseFloat(style.paddingTop) -
    parseFloat(style.paddingBottom)
  );
}

/** The filled fraction of the page at whatever scale is currently set. */
function fillOf(inner: HTMLElement): number {
  const box = inner.getBoundingClientRect();
  const style = getComputedStyle(inner);
  const top = box.top + parseFloat(style.paddingTop);
  const room = roomOf(inner);
  if (room <= 0) return 1;
  const bottom = contentBottom(inner);
  return bottom === Number.NEGATIVE_INFINITY ? 0 : (bottom - top) / room;
}

/**
 * Set the page's scale from a step, where zero is the size every budget was measured at.
 *
 * One function for both directions so there is one definition of what a step means, and the two
 * ranges are divided separately because they hold different numbers of probes.
 */
function apply(inner: HTMLElement, step: number): void {
  const at = step / (step < 0 ? SHRINK_STEPS : STEPS);
  const air = step < 0 ? 1 - (1 - AIR_MIN) * -at : 1 + (AIR_MAX - 1) * at;
  const type = step < 0 ? 1 - (1 - TYPE_MIN) * -at : 1 + (TYPE_MAX - 1) * at;
  inner.style.setProperty("--fit-air", air.toFixed(4));
  inner.style.setProperty("--fit-type", type.toFixed(4));
}

/**
 * Write this page in the largest hand that still fits.
 *
 * Binary search over the step table rather than a ratio: content height goes as roughly the square
 * of the type size and the gaps are a third term, so solving for the scale in one pass overshoots
 * on a page of short paragraphs and undershoots on a page of one long one. Four probes and the
 * answer is measured rather than modelled.
 */
function refit(inner: HTMLElement): void {
  const room = roomOf(inner);
  if (room <= 0) return;

  const signature = signatureOf(inner, room);
  const known = measured.get(signature);
  if (known !== undefined) {
    apply(inner, known);
    return;
  }

  apply(inner, 0);
  const fill = fillOf(inner);

  if (fill <= TARGET) {
    // Room to spare: write it larger, up to the step where it would stop fitting.
    let low = 0;
    let high = STEPS;
    while (low < high) {
      const mid = Math.ceil((low + high) / 2);
      apply(inner, mid);
      if (fillOf(inner) <= TARGET) low = mid;
      else high = mid - 1;
    }
    apply(inner, low);
    remember(signature, low);
    return;
  }

  if (fill > FULL) {
    /*
      Off the end of the leaf: write it smaller, down to the step where it comes back on.

      The same search mirrored, and the same guarantee -- the answer is the *largest* step whose
      measured content fits, so a page gives up the least it can. A page that does not fit even at
      the floor keeps the floor, because smaller than that is unreadable and an unreadable page is
      a worse answer than one the reader can scroll.
    */
    let low = -SHRINK_STEPS;
    let high = 0;
    while (low < high) {
      const mid = Math.ceil((low + high) / 2);
      apply(inner, mid);
      if (fillOf(inner) <= FULL) low = mid;
      else high = mid - 1;
    }
    apply(inner, low);
    remember(signature, low);
    return;
  }

  // Between the two: full enough to leave alone, not so full that it spills.
  remember(signature, 0);
}

/**
 * What has already been measured, so the turn does not measure it again.
 *
 * The turning leaf and the page parked under it are copies of pages the reader is looking at, and
 * a copy cannot measure itself: `.leaf` is mid-`rotateY` from the frame it mounts, so every rect
 * inside it is horizontally squashed and at ninety degrees they are all zero wide. Searching there
 * would fit the page to a sliver and the turn would flicker from one hand to another.
 *
 * The cache is what makes that unnecessary rather than a special case: a page's fit is a function
 * of what is on it and how much leaf there is, both of which a copy shares exactly with its
 * original, so the copy looks up the answer instead of taking a measurement it cannot take.
 */
const measured = new Map<string, number>();

/**
 * Enough for the book twice over at one size, and dropped wholesale rather than by age.
 *
 * The key carries the height of the leaf, so dragging a window edge mints a fresh entry per pixel
 * for every page it passes -- each holding that page's whole text. Emptying it costs one search
 * per page on the size the reader stops at, which is the size they will then sit and read at.
 */
const CACHE_MAX = 400;

/**
 * Whether the book's own faces have arrived, and why nothing is believed until they have.
 *
 * How many lines a paragraph takes is a fact about a font, so a fit measured against the fallback
 * is a fit of the wrong page -- and the fallback is taller here, so a page measures full, declines
 * to grow, and caches that. Nothing afterwards disturbs it: swapping a face changes text metrics
 * without mutating the DOM or resizing the leaf, so neither observer fires, and the spread the
 * reader lands on keeps the fallback's answer for the rest of the session.
 *
 * Found in the browser and not in the suite, which is the part worth remembering. Playwright
 * navigates with the faces already in cache and applied before the app renders, so every page
 * measured correctly there; the same page loaded in the pane cached a refusal to grow and sat at
 * 1.00 where a settled font gives it 1.22.
 */
let settled = false;

/** The live pages, so the one answer that arrives late can reach all of them. */
const waiting = new Set<() => void>();

if (typeof document !== "undefined" && document.fonts) {
  void document.fonts.ready.then(() => {
    settled = true;
    // Everything in it was measured against the wrong face.
    measured.clear();
    for (const again of waiting) again();
  });
} else {
  settled = true;
}

function signatureOf(inner: HTMLElement, room: number): string {
  return `${Math.round(room)}|${(inner.textContent ?? "").trim()}`;
}

function remember(signature: string, step: number): void {
  // A measurement taken against the fallback face is applied but never kept.
  if (!settled) return;
  if (measured.size >= CACHE_MAX) measured.clear();
  measured.set(signature, step);
}

/**
 * Svelte action: keep one page fitted to whatever is set on it.
 *
 * The panel changes under this element rather than the element being replaced -- a turn re-renders
 * the snippet into the same `.page__inner` -- so the trigger is a mutation observer rather than
 * mount. Attributes are deliberately not observed: the fit writes two custom properties onto this
 * same element, and observing them would be a loop.
 */
export function fit(inner: HTMLElement, on: boolean): { destroy: () => void } {
  /* The flag is the action's argument rather than a wrapper in the component, because Svelte
     hoists a template's function references to module scope where it can and a local arrow
     declared for the purpose came back as `ReferenceError: maybeFit is not defined` at runtime --
     past both `tsc` and the production build, and visible only in the browser's console. An
     imported function is already module scope, so there is nothing left to hoist wrongly. */
  if (!on) return { destroy: () => {} };

  /*
    A microtask, and the two things it is not.

    It is not an animation frame. A frame never arrives in a tab that is not compositing -- a
    background tab, a hidden pane, a headless run -- which is the same trap `Book.svelte` records
    for `animationend`, and the whole book rendered unfitted with nothing in the console to say so.

    It is not a timer either, which is what replaced the frame and was wrong in a quieter way. This
    element outlives the panel on it: a turn renders new content into the same `.page__inner`, so
    between the content arriving and a timer firing the *previous* page's scale is applied to the
    new page. On a long panel that overflows the leaf for a tick -- a flash of type too big, and
    three pages of the book failing the overflow guard depending on when it happened to look. A
    microtask runs after the mutation and before the paint, so no frame ever shows an unfitted or
    a wrongly fitted page.
  */
  let queued = false;
  const schedule = (): void => {
    if (queued) return;
    queued = true;
    queueMicrotask(() => {
      queued = false;
      refit(inner);
    });
  };

  schedule();
  waiting.add(schedule);
  const changes = new MutationObserver(schedule);
  changes.observe(inner, { childList: true, subtree: true, characterData: true });

  /* Only a real change of leaf, because a fit can move a scrollbar and a scrollbar resizes the
     box that was being observed -- which is a loop, not a resize. */
  let room = 0;
  const resizes = new ResizeObserver(() => {
    const now = Math.round(roomOf(inner));
    if (now === room) return;
    room = now;
    schedule();
  });
  resizes.observe(inner);

  return {
    destroy() {
      waiting.delete(schedule);
      changes.disconnect();
      resizes.disconnect();
    },
  };
}
