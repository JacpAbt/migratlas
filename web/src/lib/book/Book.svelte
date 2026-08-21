<script lang="ts">
  import type { Snippet } from "svelte";

  import Page from "./Page.svelte";
  import { folio, openingOf, type Panel, type Spread } from "./pages";
  import { tabStyle } from "./tabs";
  import { still } from "../../state/turn";
  import type { Chapter } from "../story";

  let {
    chapters,
    spreads,
    open,
    onopen,
    page,
  }: {
    chapters: readonly Chapter[];
    spreads: readonly Spread[];
    /** Index of the open spread. */
    open: number;
    onopen: (at: number) => void;
    /**
     * What goes on a page, given the panel and which side it is.
     *
     * A snippet rather than two slots, because the turn has to render the *outgoing* pages as well
     * as the open ones. With slots that means cloning DOM, which is where every defect ADR 0015
     * lists came from; with a snippet the leaf is another call with different arguments.
     */
    page: Snippet<[Panel, "verso" | "recto"]>;
  } = $props();

  const index = $derived(Math.min(Math.max(open, 0), Math.max(spreads.length - 1, 0)));
  const current = $derived(spreads[index] ?? spreads[0]);

  /** The spread being turned away from, and which way. Null when nothing is turning. */
  let leaving = $state<{ spread: Spread; forward: boolean } | null>(null);
  let settling: ReturnType<typeof setTimeout> | undefined;

  /*
    Which sheet moves, and what is on each of its sides.

    Forward lifts the recto and lays it left, so its front is the outgoing recto and its back is the
    incoming verso; the *covered* page is the left one, which must keep the outgoing verso until the
    leaf lands on it. Backward is the mirror. Getting this wrong is what made the mock's covered page
    change into the page about to cover it.
  */
  const lifted = $derived<"verso" | "recto">(leaving?.forward ? "recto" : "verso");
  const arriving = $derived<"verso" | "recto">(leaving?.forward ? "verso" : "recto");

  function go(to: number): void {
    if (to === index || to < 0 || to >= spreads.length) return;

    if (still()) {
      // Reduced motion is a full path and not a faster one: the new spread is simply there, which
      // is the animation's correct end state rather than a degraded version of it.
      onopen(to);
      return;
    }

    clearTimeout(settling);
    leaving = { spread: current!, forward: to > index };
    onopen(to);

    /*
      Cleared by whichever comes first, the event or the clock, and the clock is not paranoia:
      `animationend` never arrives in a tab that is not compositing -- a background tab, a hidden
      pane, a headless run -- and without it the leaf stays parked over half the spread for the rest
      of the session with no way back. Found exactly that way in the mock.
    */
    const ms = Number.parseFloat(
      getComputedStyle(document.documentElement).getPropertyValue("--draw-slow"),
    );
    settling = setTimeout(() => (leaving = null), (Number.isFinite(ms) ? ms : 900) + 120);
  }

  /* The folio in each outer corner is the button that turns that way -- see `Page.svelte`. Arrow
     keys do the same, because a reader on a keyboard should not have to find a corner. */
  const numbers = $derived(folio(index));

  function keys(event: KeyboardEvent): void {
    if (event.target !== document.body) return;
    if (event.key === "ArrowRight") go(index + 1);
    else if (event.key === "ArrowLeft") go(index - 1);
  }

  $effect(() => {
    addEventListener("keydown", keys);
    return () => removeEventListener("keydown", keys);
  });
</script>

<!--
  The book, on a desk. ADR 0015.

  Two pages meeting exactly on the centre line with the fold drawn *over* them, because a three
  column spread put the page edge at `50% + fold/2` while the crease was at `50%` -- so the turning
  page hinged twenty pixels outside the visible spine and appeared to snap into place.

  There is no `filter` on any ancestor of the leaf, and that is load-bearing rather than tidy: a
  filter flattens 3D transforms, so a drop-shadow here turned the rotation into a horizontal squash.
  The lift is box-shadows on the sheets.
-->
<div class="desk">
  <div class="book">
    <div class="block block--under" aria-hidden="true"></div>
    <div class="block block--edge" aria-hidden="true"></div>

    <div class="spread">
      {#if current}
        <Page
          side="verso"
          folio={numbers[0]}
          onturn={index > 0 ? () => go(index - 1) : undefined}
        >
          {@render page(current.verso, "verso")}
        </Page>
        <Page
          side="recto"
          folio={numbers[1]}
          onturn={index < spreads.length - 1 ? () => go(index + 1) : undefined}
        >
          {@render page(current.recto, "recto")}
        </Page>
      {/if}

      {#if leaving && current}
        <!-- The outgoing page, held on the half the leaf is about to land on. -->
        <div class="stale stale--{arriving}" aria-hidden="true">
          <Page side={arriving} fill>{@render page(leaving.spread[arriving], arriving)}</Page>
        </div>
        <!-- The shadow the turning page throws: a sibling, because a child would rotate with it. -->
        <div class="cast cast--{lifted}" aria-hidden="true"></div>
        <div class="leaf leaf--{lifted}" aria-hidden="true">
          <div class="leaf__face leaf__front">
            <Page side={lifted} fill>{@render page(leaving.spread[lifted], lifted)}</Page>
          </div>
          <div class="leaf__face leaf__back">
            <Page side={arriving} fill>{@render page(current[arriving], arriving)}</Page>
          </div>
        </div>
      {/if}

      <div class="gutter" aria-hidden="true"><span class="gutter__line"></span></div>

    </div>

    <nav class="tabs" aria-label="chapters">
      {#each chapters as chapter, position (chapter.slug)}
        {@const here = current?.chapter.slug === chapter.slug}
        <button
          type="button"
          class="tab"
          style={tabStyle(position)}
          class:is-on={here}
          aria-current={here ? "page" : undefined}
          onclick={() => go(openingOf(spreads, chapter.slug))}
        >
          {chapter.tab}
        </button>
      {/each}
    </nav>
  </div>
</div>

<style>
  .desk {
    display: grid;
    place-items: start center;
    padding: var(--gap) var(--gap-tight) 0;
    /* Two faint washes rather than a flat fill: a flat ground under a shadowed object reads as a
       rectangle floating on a colour. */
    background:
      radial-gradient(120% 80% at 30% 0%, rgb(255 255 255 / 5%), transparent 60%),
      radial-gradient(100% 90% at 75% 100%, rgb(0 0 0 / 7%), transparent 65%);
  }

  .book {
    --ratio: 1.58;
    --book-fold: 2.5rem;
    /* Trimmed from `clamp(1.6rem, 3.2vw, 3.4rem)`: on a short window the margin was taking 82px
       of an 728px page while five panels overflowed by less than that. */
    --page-pad: clamp(1.2rem, 2.5vw, 3rem);

    /*
      Reading sizes measured against the page, which is what pagination made necessary.

      `tokens.css` records that the book needed no reading *scale* -- and that was right about the
      thing it was about, a reader's 100/115/130% preference. This is a different quantity. A page
      that scrolls fits any content at any size by definition; a page that does not fit has to hold
      the same panel at 1600x900 and at 1280x800, where it is 826px and 726px tall. With the type
      fixed, twenty-three of twenty-eight spreads overflowed at the smaller size and nine at the
      larger, and every fix would have been a split that was wrong at the other size.

      So the type is a fraction of the book's own height and the spread is a scaled copy of itself at
      every window: the aspect is fixed, so the width scales with the height and the text reflows
      identically. The divisors are the current sizes at `--book-h: 828`, which is 1600x900 -- the
      size every panel in `pages.ts` was measured at. The clamps are floors and ceilings rather than
      preferences: below the floor the book stops shrinking its type and the guard test in
      `tests/book.spec.ts` fails instead, which is the honest failure.

      CSS cannot divide a length by a length, so this is `--book-h / n` rather than a ratio applied
      to the token. That is also why each line repeats the hand factor it needs.
    */
    --size-claim: clamp(1.08rem, calc(var(--book-h) / 26.9 * var(--font-scale-hand)), 2.6rem);
    --size-lede: clamp(0.86rem, calc(var(--book-h) / 50.2 * var(--font-scale-hand)), 1.5rem);
    --size-body: clamp(0.73rem, calc(var(--book-h) / 59.5), 1.15rem);
    --size-value: clamp(0.98rem, calc(var(--book-h) / 41.8), 1.7rem);
    --size-margin: clamp(0.56rem, calc(var(--book-h) / 85.6), 0.82rem);
    --size-label: clamp(0.53rem, calc(var(--book-h) / 91.2), 0.76rem);
    /* As large as the window allows in both axes, so it fills a wide monitor and still cannot run
       off the bottom of a short one. The subtraction is the chrome above it. */
    /* The subtraction is the chrome above it, measured rather than reserved: `.desk` puts 14px of
       padding over the book and the lift shadow needs a few more. 4.5rem was a guess that cost 40px
       of page on exactly the short windows where the pages were tightest. */
    --book-h: min(calc(98vw / var(--ratio)), calc(100vh - 2.6rem));

    position: relative;
    width: calc(var(--book-h) * var(--ratio));
    aspect-ratio: var(--ratio);
    perspective: 2800px;
  }

  .block {
    position: absolute;
    inset: 0;
    background: var(--paper);
    border: 1px solid color-mix(in srgb, var(--rule) 70%, var(--ink) 8%);
    box-shadow: 0 14px 22px rgb(0 0 0 / 18%);
  }

  .block--under {
    transform: rotate(-0.45deg) translate(-5px, 6px);
  }

  .block--edge {
    transform: rotate(0.3deg) translate(4px, 3px);
    /* Page edges seen almost end-on: a stack of fine lines, not a solid tone. */
    background:
      repeating-linear-gradient(
        to bottom,
        transparent 0 3px,
        color-mix(in srgb, var(--rule) 55%, transparent) 3px 4px
      ),
      var(--paper);
  }

  .spread {
    position: absolute;
    inset: 0;
    display: grid;
    grid-template-columns: 1fr 1fr;
    background: var(--paper);
    border: 1px solid var(--rule);
    box-shadow:
      0 22px 34px rgb(0 0 0 / 26%),
      0 3px 3px rgb(0 0 0 / 22%);
  }

  /* Above the leaf, and that is geometry: the crease is the axis the page rotates about, so at the
     hinge the page has zero width and can never pass in front of it. Under the leaf it vanished for
     the length of the turn and came back at the end. */
  .gutter {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 50%;
    width: var(--book-fold);
    transform: translateX(-50%);
    z-index: 7;
    pointer-events: none;
    background:
      linear-gradient(to right, rgb(0 0 0 / 12%), rgb(0 0 0 / 2%) 42%),
      linear-gradient(to left, rgb(0 0 0 / 12%), rgb(0 0 0 / 2%) 42%);
  }

  .gutter__line {
    position: absolute;
    inset: 0 auto;
    left: 50%;
    width: 1px;
    transform: translateX(-0.5px);
    background: linear-gradient(
      to bottom,
      transparent,
      color-mix(in srgb, var(--ink) 55%, transparent) 4%,
      color-mix(in srgb, var(--ink) 55%, transparent) 96%,
      transparent
    );
  }

  /* --- The turn --------------------------------------------------------- */

  .stale {
    position: absolute;
    top: 0;
    bottom: 0;
    z-index: 3;
    overflow: hidden;
    pointer-events: none;
  }

  .stale--verso {
    left: 0;
    right: 50%;
  }

  .stale--recto {
    left: 50%;
    right: 0;
  }

  .cast {
    position: absolute;
    inset: 0;
    z-index: 4;
    opacity: 0;
    pointer-events: none;
    animation: sweep var(--draw-slow) var(--ease-pen) forwards;
  }

  .cast--recto {
    background: linear-gradient(to right, rgb(0 0 0 / 30%), transparent 52%);
  }

  .cast--verso {
    background: linear-gradient(to left, rgb(0 0 0 / 30%), transparent 52%);
  }

  .leaf {
    position: absolute;
    top: 0;
    bottom: 0;
    z-index: 5;
    transform-style: preserve-3d;
    pointer-events: none;
    will-change: transform;
  }

  /* Forward: the right page lifts and swings left about the spine. */
  .leaf--recto {
    left: 50%;
    right: 0;
    transform-origin: left center;
    animation: turn-forward var(--draw-slow) var(--ease-pen) forwards;
  }

  /* Backward: the left page lifts and swings right about the same spine. */
  .leaf--verso {
    left: 0;
    right: 50%;
    transform-origin: right center;
    animation: turn-back var(--draw-slow) var(--ease-pen) forwards;
  }

  .leaf__face {
    position: absolute;
    inset: 0;
    backface-visibility: hidden;
    border: 1px solid var(--rule);
    overflow: hidden;
  }

  .leaf__back {
    transform: rotateY(180deg);
  }

  @keyframes turn-forward {
    from {
      transform: rotateY(0deg);
    }

    to {
      transform: rotateY(-180deg);
    }
  }

  @keyframes turn-back {
    from {
      transform: rotateY(0deg);
    }

    to {
      transform: rotateY(180deg);
    }
  }

  @keyframes sweep {
    0% {
      opacity: 0;
    }

    40% {
      opacity: 1;
    }

    100% {
      opacity: 0;
    }
  }

  /* --- Thumb tabs ------------------------------------------------------- */

  .tabs {
    position: absolute;
    inset: 0 0 0 auto;
    z-index: 6;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 3px;
    transform: translateX(calc(100% - 3px));
  }

  .tab {
    /*
      The body face, not the hand: `tokens.css` says Shantell Sans is "a marker face drawn for
      interfaces, so it survives 13px where a looser hand turns into texture", and a vertical tab is
      the smallest text on the page. Sized against the book's own height, because seven vertical
      labels stack to 38 times the font size -- at a fixed size they ran past the foot of a short
      window while the book kept shrinking around them.
    */
    font-family: var(--font-body);
    font-size: clamp(0.7rem, calc(var(--book-h) / 42), 0.95rem);
    writing-mode: vertical-rl;
    padding: 0.42em 0.72em;
    color: var(--ink);
    /* Coloured stock from the palette's own hues, mixed into the page's paper so it inverts with the
       surface for free. Which hue and how much of it are `tabs.ts`, because the mobile leaves carry
       the same seven tabs and a second copy of that assignment goes stale the first time a chapter
       is added. */
    background: color-mix(in srgb, var(--paper) var(--mix), var(--tint));
    border: 1px solid color-mix(in srgb, var(--tint) 45%, var(--rule));
    border-left: none;
    border-radius: 0 7px 7px 0;
    cursor: pointer;
    box-shadow: 2px 2px 3px rgb(0 0 0 / 12%);
  }

  .tab:hover {
    background: color-mix(in srgb, var(--paper) calc(var(--mix) - 12%), var(--tint));
  }

  /* Its own colour at strength rather than a different colour: an open tab is the same tab. */
  .tab.is-on {
    background: color-mix(in srgb, var(--paper) calc(var(--mix) - 22%), var(--tint));
    border-color: var(--tint);
    transform: translateX(3px);
    box-shadow: 3px 2px 5px rgb(0 0 0 / 16%);
  }

  @media (prefers-reduced-motion: reduce) {
    .leaf,
    .cast {
      animation: none;
      display: none;
    }
  }

</style>
