<script lang="ts">
  import type { Snippet } from "svelte";

  import Page from "./Page.svelte";
  import Realms from "./Realms.svelte";
  import { folio, openingOf, type Panel, type Spread } from "./pages";
  import { tabStyle } from "./tabs";
  import type { Chapter } from "../story";

  let {
    chapters,
    spreads,
    open,
    realm,
    onopen,
    onfilter,
    page,
  }: {
    chapters: readonly Chapter[];
    spreads: readonly Spread[];
    /** Index of the open spread. */
    open: number;
    /** Which realm the book is being read in. Empty for all of them. */
    realm: string;
    onopen: (at: number) => void;
    onfilter: (realm: string) => void;
    /**
     * What goes on a page, given the panel and which side it is.
     *
     * The same signature `Book` takes, and deliberately so: `Reader` hands one snippet to whichever
     * container the window gets, so a phone and a monitor show the same pages rather than two
     * authored versions of them.
     */
    page: Snippet<[Panel, "verso" | "recto"]>;
  } = $props();

  /** How long the rail has to be still before the chapter goes in the URL. */
  const SETTLE_MS = 140;

  /**
   * Every leaf, in reading order.
   *
   * One page per leaf, so a spread becomes two of them -- which is the whole of why a phone gets its
   * own container: the same pages, one at a time. The folio comes from `pages.ts` so the number on a
   * phone is the number on a monitor; a book whose page 17 moved when you rotated the device would
   * not be a book.
   */
  const leaves = $derived(
    spreads.flatMap((spread, at) => {
      const numbers = folio(at);
      return [
        { spread, at, side: "verso" as const, panel: spread.verso, folio: numbers[0] },
        { spread, at, side: "recto" as const, panel: spread.recto, folio: numbers[1] },
      ];
    }),
  );

  const here = $derived(spreads[open]?.chapter ?? chapters[0]!);

  let rail = $state<HTMLDivElement | null>(null);
  let fanned = $state(false);

  /** The leaf nearest the rail's left edge, which is the one being read. */
  let at = $state(0);

  /**
   * The last slug this component reported, so the answer coming back does not undo the swipe.
   *
   * A plain `let` and not `$state`: the effect below must re-run when `open` changes and never
   * because of this, which is the whole of how the two directions stay apart. It starts at -1, which
   * is no spread, so the first run aligns the rail with whatever the URL asked for.
   */
  let reported = -1;
  let quiet: ReturnType<typeof setTimeout> | undefined;

  function sheets(el: HTMLElement): HTMLElement[] {
    return [...el.querySelectorAll<HTMLElement>("[data-leaf]")];
  }

  /** Measured rather than divided: the rail's step is a `calc` and a peek, so this asks the DOM. */
  function nearest(el: HTMLElement): number {
    let best = 0;
    let gap = Infinity;
    for (const [index, sheet] of sheets(el).entries()) {
      const away = Math.abs(sheet.offsetLeft - el.scrollLeft);
      if (away < gap) {
        gap = away;
        best = index;
      }
    }
    return best;
  }

  /*
    A tab is a jump and not a turn, so it does not animate.

    Smooth-scrolling from the first chapter to the sixth drags eight leaves past the reader at speed,
    and eight leaves is seven more than the window mounts -- so most of what went by would be blank
    paper. The motion in this container belongs to the swipe; a tab means "be there", and the fan
    closing is the transition.
  */
  function goTo(at: number): void {
    const el = rail;
    if (!el) return;
    const first = leaves.findIndex((leaf) => leaf.at === at);
    const sheet = sheets(el)[first];
    if (!sheet) return;
    // Said, not inferred. `at` decides which leaves hold content, and waiting for the scroll event
    // to report a position this function already knows is how the destination arrives blank.
    at = first;
    el.scrollTo({ left: sheet.offsetLeft, behavior: "instant" });
  }

  /*
    Two cadences, because they answer different questions.

    Which leaves are mounted follows the scroll at once, so a fling never lands on blank paper. The
    URL waits for the rail to stop: reported per leaf crossed, a flick through four chapters would
    push four history entries and make the back button a rewind of the gesture rather than of the
    reading.
  */
  function onscroll(): void {
    const el = rail;
    if (!el) return;
    /*
      Straight through, with no frame throttle. Scroll events are already dispatched at most once a
      frame, so a `requestAnimationFrame` gate here buys nothing -- and it costs the thing `Book`
      documents for `animationend`: a callback that never arrives in a tab that is not compositing.
      Written that way first, and the mounted window then latched on leaf zero for good, because the
      only code that cleared the gate was the frame that never came.
    */
    at = nearest(el);
    clearTimeout(quiet);
    quiet = setTimeout(() => {
      at = nearest(el);
      const spread = leaves[at]?.at;
      if (spread === undefined || spread === open) return;
      reported = spread;
      onopen(spread);
    }, SETTLE_MS);
  }

  $effect(() => {
    if (!rail || open === reported || leaves.length === 0) return;
    reported = open;
    goTo(open);
  });

  $effect(() => {
    if (!fanned) return;
    const shut = (event: KeyboardEvent) => {
      if (event.key === "Escape") fanned = false;
    };
    addEventListener("keydown", shut);
    return () => removeEventListener("keydown", shut);
  });

  $effect(() => () => clearTimeout(quiet));

  function pick(slug: string): void {
    fanned = false;
    const at = openingOf(spreads, slug);
    // Tapping the chapter you are already reading means "back to its first page", which no change to
    // `open` can express when you are already on it -- so that one goes straight to the rail.
    if (at === open) goTo(at);
    else onopen(at);
  }
</script>

<!--
  The same book, on a phone: leaves you swipe.

  Not the spread squeezed. Two pages side by side on a 390px screen are two 195px columns, and every
  measurement in ADR 0015 -- the crease, the tab stack, the plate, the page padding -- was chosen
  against a shape that width does not have. So the width that cannot hold a spread gets a different
  object, and `Reader` mounts one container or the other rather than one that bends.

  What replaces the turn is the swipe itself. A `rotateY` page turn needs somewhere for the page to
  go and on a single-page screen there is nowhere; horizontal scroll-snap makes the gesture and the
  page turn one movement, which is closer to a real leaf than an animation of one would be. The next
  leaf's edge shows at the right for the reason a real book's does: otherwise nothing on screen says
  there is another page.

  Chapters are the fore-edge of a closed notebook, in the corner a thumb already rests in. Seven tabs
  at once is most of a phone screen, so the corner shows the tab you are on with the others stacked
  edge-on behind it, and a tap fans them out. The tints are `tabs.ts`, shared with the spread's own
  tabs -- the same seven colours mean the same seven chapters on either container.
-->
<div class="leaves">
  <div class="rail" bind:this={rail} {onscroll}>
    {#each leaves as leaf, index (`${leaf.at}-${leaf.side}`)}
      <article
        class="leaf"
        data-leaf
        data-chapter={leaf.spread.chapter.slug}
        data-side={leaf.side}
      >
        <Page side={leaf.side} fill folio={leaf.folio}>
          <!--
            The leaf you can see and the one either side of it. A rule about leaves and not about
            chapters, because it is a swipe that has to land on something: the world's map is a live
            MapLibre context and a phone should not be running one two chapters away, but it has to
            be running already when the leaf before it is on screen.
          -->
          {#if Math.abs(index - at) <= 1}
            {@render page(leaf.panel, leaf.side)}
          {/if}
        </Page>
      </article>
    {/each}
    <!-- The last leaf snaps flush only if there is a peek's worth of rail left after it. -->
    <div class="rail__stop" aria-hidden="true"></div>
  </div>

  {#if fanned}
    <button
      type="button"
      class="shade"
      aria-label="Close the chapter tabs"
      onclick={() => (fanned = false)}
    ></button>
  {/if}

  <!-- At the foot, which is both where a phone puts a filter and the same edge the spread uses. -->
  <div class="tail">
    <Realms open={realm} onpick={onfilter} foot />
  </div>

  <div class="edge">
    {#if fanned}
      <nav class="fan" aria-label="Chapters">
        {#each chapters as chapter, position (chapter.slug)}
          <button
            type="button"
            class="fan__tab"
            style="{tabStyle(position)}; --i: {position}"
            class:is-on={chapter.slug === open}
            aria-current={chapter.slug === open ? "page" : undefined}
            onclick={() => pick(chapter.slug)}
          >
            {chapter.tab}
          </button>
        {/each}
      </nav>
    {/if}

    <button
      type="button"
      class="thumb"
      style={tabStyle(chapters.indexOf(here))}
      aria-expanded={fanned}
      onclick={() => (fanned = !fanned)}
    >
      <span class="thumb__word">{here.tab}</span>
      <span class="thumb__stack" aria-hidden="true">
        {#each chapters as chapter, position (chapter.slug)}
          <span class="sliver" style={tabStyle(position)}></span>
        {/each}
      </span>
    </button>
  </div>
</div>

<style>
  .leaves {
    /*
      The measurements a page needs, which are the container's to give.

      `Book` scales its own against the book's height and `Page` reads them, so the first leaf
      mounted outside the book had `padding: var(--page-pad)` resolve to an invalid declaration the
      browser drops -- a page whose hand-written lede ran off both edges of the phone. A container
      that shows pages owes them this, and `tests/book.spec.ts` now asks a leaf whether it got it.

      The foot clears the fore-edge tab in the bottom corner. Measured at 51px, so this is that plus
      room to see the last line is the last line.
    */
    --page-pad: clamp(1.1rem, 4.5vw, 2rem);
    --page-foot: 4.25rem;

    position: relative;
    height: 100%;
    overflow: hidden;
  }

  /* Over the rail rather than in a row with it: the leaves are a scroll-snap track and a sibling
     in the same column would take a leaf's height off every page. Centred, because the fore-edge
     thumb owns the right-hand side. */
  .tail {
    position: absolute;
    inset: auto 0 0;
    z-index: 4;
    display: flex;
    justify-content: center;
    /* Room for the fore-edge thumb, which owns this corner. Centred in what is left rather than in
       the screen, so the two never share a pixel at any width. */
    padding-right: 7rem;
    --realm-size: 0.66rem;
  }

  .rail {
    --peek: 0.85rem;

    display: flex;
    height: 100%;
    overflow-x: auto;
    overflow-y: hidden;
    scroll-snap-type: x mandatory;
    /* So a swipe that runs out of leaves does not drag the page behind it. */
    overscroll-behavior-x: contain;
    scrollbar-width: none;
  }

  .rail::-webkit-scrollbar {
    display: none;
  }

  .leaf {
    position: relative;
    flex: 0 0 calc(100% - var(--peek));
    height: 100%;
    scroll-snap-align: start;
    /* The bound edge, drawn rather than shaded: the strip of the next leaf showing past this one is
       what a page edge looks like, and a line is what says it is one. */
    border-right: 1px solid var(--rule);
  }

  .rail__stop {
    flex: 0 0 var(--peek);
  }

  .shade {
    position: absolute;
    inset: 0;
    z-index: 8;
    padding: 0;
    border: none;
    background: rgb(0 0 0 / 22%);
    cursor: pointer;
  }

  /* --- The fore-edge ---------------------------------------------------- */

  .edge {
    position: absolute;
    /* Flush with the edge of the screen, because a tab with a gap behind it is a floating button.
       The rotation lets a corner run off, which is what a tab in a real notebook does. */
    right: 0;
    bottom: 0;
    z-index: 9;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
  }

  .thumb {
    display: flex;
    align-items: flex-end;
    gap: 0.5rem;
    /* A thumb target, not a chevron: the phone's whole navigation is this one control. */
    min-height: 2.9rem;
    padding: 0.55rem 0.85rem 0.7rem;
    font-family: var(--font-body);
    font-size: 0.9rem;
    color: var(--ink);
    background: color-mix(in srgb, var(--paper) var(--mix), var(--tint));
    border: 1px solid color-mix(in srgb, var(--tint) 45%, var(--rule));
    border-bottom: none;
    border-radius: 8px 8px 0 0;
    cursor: pointer;
    box-shadow: 0 -2px 6px rgb(0 0 0 / 14%);
    transform: rotate(-0.8deg);
  }

  /* The other six tabs, edge-on under the one that is out: a stack, not a menu glyph. */
  .thumb__stack {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding-bottom: 0.2em;
  }

  .sliver {
    width: 0.75rem;
    height: 2px;
    background: color-mix(in srgb, var(--paper) var(--mix), var(--tint));
    border: 1px solid color-mix(in srgb, var(--tint) 55%, var(--rule));
    border-radius: 0 2px 2px 0;
  }

  .fan {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 3px;
    max-height: 74vh;
    overflow-y: auto;
    padding: 0 0 0.3rem;
  }

  .fan__tab {
    min-width: 9rem;
    /* 44px, which is the smallest thing a thumb hits reliably. Measured: at 2.4rem the tabs came
       out 38px and the whole of this container's navigation is these seven. */
    min-height: 2.75rem;
    padding: 0.5rem 0.9rem;
    text-align: right;
    font-family: var(--font-body);
    font-size: 0.9rem;
    color: var(--ink);
    background: color-mix(in srgb, var(--paper) var(--mix), var(--tint));
    border: 1px solid color-mix(in srgb, var(--tint) 45%, var(--rule));
    border-right: none;
    border-radius: 8px 0 0 8px;
    cursor: pointer;
    box-shadow: -2px 2px 4px rgb(0 0 0 / 14%);
    /* Fanned rather than listed: each tab a hair further out and a hair more turned than the one
       above it, which is what a thumbed block of pages does. */
    transform: rotate(calc(var(--i) * 0.18deg)) translateX(calc(var(--i) * -1px));
    animation: fan-out var(--draw-quick) var(--ease-pen) backwards;
    /* A fraction of the duration rather than a fixed delay, so the reduced-motion block that zeroes
       every duration in `tokens.css` zeroes the stagger with it. */
    animation-delay: calc(var(--i) * var(--draw-quick) / 22);
  }

  .fan__tab.is-on {
    background: color-mix(in srgb, var(--paper) calc(var(--mix) - 22%), var(--tint));
    border-color: var(--tint);
    transform: rotate(calc(var(--i) * 0.18deg)) translateX(calc(var(--i) * -1px - 6px));
  }

  @keyframes fan-out {
    from {
      opacity: 0;
      transform: translateX(2.2rem);
    }
  }
</style>
