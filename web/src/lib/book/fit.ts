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

/**
 * The height a page has for text at the scale it is currently written in.
 *
 * Its layout height rather than its drawn one, so that a sheet drawn foreshortened in mid-turn
 * still reports the page it is. Not a key for the cache -- the foot it reserves for the folio grows
 * and shrinks with the fit, so this moves whenever the scale does; see `signatureOf`.
 */
function roomOf(inner: HTMLElement): number {
  const style = getComputedStyle(inner);
  return inner.clientHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom);
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
 * Whether the page would scroll, which `fillOf` cannot see.
 *
 * The fill is measured to the last mark that paints, and a trailing margin paints nothing -- but
 * the leaf's scroll height includes it, so a page could measure as fitting and still carry a
 * scrollbar. Four pages did: 3 and 4px over their leaves at 1280x720 and 1024x768 in the clear and
 * dyslexia settings, at scales above the floor that one step smaller would have cleared, and the
 * overflow guard reads exactly this number. A page fits when both agree.
 */
function scrolls(inner: HTMLElement): boolean {
  return inner.scrollHeight > inner.clientHeight;
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

/** A page's fit: its step, and whether it had to set down what it could do without. */
interface Answer {
  step: number;
  crowded: boolean;
}

/**
 * Apply an answer: the scale, and the crowding that lets a page's droppable parts go.
 *
 * `[data-droppable]` marks what a page can do without and still say everything -- a margin note
 * repeating a sentence the book prints elsewhere. `Page.svelte` hides it on a crowded page.
 */
function settle(inner: HTMLElement, answer: Answer): void {
  inner.toggleAttribute("data-crowded", answer.crowded);
  apply(inner, answer.step);
}

/**
 * Write this page in the largest hand that still fits.
 *
 * Binary search over the step table rather than a ratio: content height goes as roughly the square
 * of the type size and the gaps are a third term, so solving for the scale in one pass overshoots
 * on a page of short paragraphs and undershoots on a page of one long one. Four probes and the
 * answer is measured rather than modelled.
 *
 * And if the floor is not enough, the page sets down its droppable parts and is fitted again. The
 * record pages' margin notes made four of the longest 4 to 75px too tall for a 1024x768 leaf at the
 * floor; the note repeats the finding page's plain caveat, so it is the thing to give way, and only
 * where the page has run out of room -- everywhere else it stays.
 */
function refit(inner: HTMLElement): void {
  if (roomOf(inner) <= 0) return;

  const signature = signatureOf(inner);
  const known = measured.get(signature);
  if (known !== undefined) {
    settle(inner, known);
    return;
  }

  // A fresh page is measured with everything on it.
  inner.toggleAttribute("data-crowded", false);
  let answer = search(inner);
  if (!answer.fits && inner.querySelector("[data-droppable]")) {
    inner.toggleAttribute("data-crowded", true);
    answer = { ...search(inner), crowded: true };
  }
  settle(inner, answer);
  remember(signature, { step: answer.step, crowded: answer.crowded });
}

/** The search itself, on whatever the page currently shows. */
function search(inner: HTMLElement): Answer & { fits: boolean } {
  apply(inner, 0);
  const fill = fillOf(inner);
  const over = fill > FULL || scrolls(inner);

  if (!over && fill <= TARGET) {
    // Room to spare: write it larger, up to the step where it would stop fitting.
    let low = 0;
    let high = STEPS;
    while (low < high) {
      const mid = Math.ceil((low + high) / 2);
      apply(inner, mid);
      if (fillOf(inner) <= TARGET && !scrolls(inner)) low = mid;
      else high = mid - 1;
    }
    apply(inner, low);
    return { step: low, crowded: false, fits: true };
  }

  if (over) {
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
      if (fillOf(inner) <= FULL && !scrolls(inner)) low = mid;
      else high = mid - 1;
    }
    apply(inner, low);
    return { step: low, crowded: false, fits: fillOf(inner) <= FULL && !scrolls(inner) };
  }

  // Between the two: full enough to leave alone, not so full that it spills.
  return { step: 0, crowded: false, fits: true };
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
 *
 * And only looks it up -- see `follow`. It used to measure itself on a miss, and a miss is exactly
 * what a face landing mid-turn produces, since that empties the cache: the copy then measured the
 * foreshortened sheet, came out a step larger than the page beneath, and the type shrank by that
 * step the moment the turn ended. The owner saw it as the text moving up as the page landed.
 */
const measured = new Map<string, Answer>();

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

/** The turning copies, told whenever a page they may stand for has been measured. */
const copies = new Set<() => void>();

/** Anything else in the book measured in its type, which has to be told the same thing. */
const others = new Set<() => void>();

/**
 * Call `again` whenever the book's type may have changed: a face landing, or a type setting chosen.
 *
 * The same moments the pages re-fit at, offered to the other thing that measures text -- the strip
 * chart, whose margin is its longest name. Returns the unsubscribe, for an effect to hand back.
 */
export function onTypeChange(again: () => void): () => void {
  others.add(again);
  return () => others.delete(again);
}

/** Forget every answer and measure the live pages again: their type has changed under them. */
function refitAll(): void {
  measured.clear();
  for (const again of waiting) again();
  for (const again of others) again();
}

if (typeof document !== "undefined" && document.fonts) {
  void document.fonts.ready.then(() => {
    settled = true;
    // Everything in it was measured against the wrong face.
    refitAll();
  });
  /*
    And every face that lands afterwards, which `ready` never reports.

    That promise resolves once, for the loads under way at the moment it is asked, and no face here
    is preloaded: each is requested when text first needs it. So a face requested after `ready` had
    settled landed with nothing to re-fit, and the page kept a scale measured against the fallback.
    Main's first CI run found the title page 51px over its leaf at 1280x720 that way, on a tree two
    earlier runs had passed -- the race goes whichever way a runner's timing and its fallback face
    send it. `loadingdone` fires for every batch of faces that finishes, whenever that is.
  */
  document.fonts.addEventListener("loadingdone", refitAll);
} else {
  settled = true;
}

/*
  And every change of the type setting, which the pages' own observers cannot see.

  A preset swaps the faces and the scale through `data-type` on the root element: custom properties
  change, nothing inside `.page__inner` mutates and the leaf does not resize. Measured before this
  existed: choosing the dyslexia setting on a fitted spread left both leaves at the hand's scale and
  put the facing page 185px under its fold. The faces the new preset needs are then fetched, and
  `loadingdone` above re-fits again once they land.
*/
if (typeof document !== "undefined" && typeof MutationObserver !== "undefined") {
  new MutationObserver(refitAll).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-type"],
  });
}

/**
 * What a page's fit is a function of: what is written on it, and how tall its leaf is.
 *
 * The leaf's height, and not the room inside it. The room is the leaf less its padding, and the
 * padding at the foot is reserved for the folio in the page's own fitted units -- so the room read
 * at one scale is not the room read at another, and a page's key depended on whatever scale it
 * happened to be at when it was asked. A turning copy, still at the default, never once matched
 * the page it copies: 571.8px of room against 564.9 on the same leaf. It measured itself instead,
 * which came out right only while the sheet was flat.
 */
function signatureOf(inner: HTMLElement): string {
  return `${inner.clientHeight}|${(inner.textContent ?? "").trim()}`;
}

function remember(signature: string, answer: Answer): void {
  // A measurement taken against the fallback face is applied but never kept.
  if (!settled) return;
  if (measured.size >= CACHE_MAX) measured.clear();
  measured.set(signature, answer);
  for (const again of copies) again();
}

/**
 * A copy's fit: the page it stands for's answer, or no change until there is one.
 *
 * Before the faces have settled nothing is remembered, so there is no answer to take and the copy
 * measures itself as it always did -- the first second of a visit, before anyone has turned a page.
 */
function follow(inner: HTMLElement): void {
  if (!settled) {
    refit(inner);
    return;
  }
  if (roomOf(inner) <= 0) return;
  const known = measured.get(signatureOf(inner));
  if (known !== undefined) settle(inner, known);
}

/**
 * Svelte action: keep one page fitted to whatever is set on it.
 *
 * The panel changes under this element rather than the element being replaced -- a turn re-renders
 * the snippet into the same `.page__inner` -- so the trigger is a mutation observer rather than
 * mount. Attributes are deliberately not observed: the fit writes two custom properties onto this
 * same element, and observing them would be a loop.
 */
export function fit(inner: HTMLElement, on: boolean | "copy"): { destroy: () => void } {
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
      if (on === "copy") follow(inner);
      else refit(inner);
    });
  };

  schedule();
  waiting.add(schedule);
  if (on === "copy") copies.add(schedule);
  const changes = new MutationObserver(schedule);
  changes.observe(inner, { childList: true, subtree: true, characterData: true });

  /* Only a real change of leaf, because a fit can move a scrollbar and a scrollbar resizes the
     box that was being observed -- which is a loop, not a resize. */
  let leaf = 0;
  const resizes = new ResizeObserver(() => {
    const now = inner.clientHeight;
    if (now === leaf) return;
    leaf = now;
    schedule();
  });
  resizes.observe(inner);

  return {
    destroy() {
      waiting.delete(schedule);
      copies.delete(schedule);
      changes.disconnect();
      resizes.disconnect();
    },
  };
}
