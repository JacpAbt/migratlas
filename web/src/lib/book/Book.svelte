<script lang="ts">
  import type { Snippet } from "svelte";

  import Page from "./Page.svelte";
  import { tabStyle } from "./tabs";
  import { still } from "../../state/turn";
  import type { Chapter } from "../story";

  let {
    chapters,
    open,
    onopen,
    page,
  }: {
    chapters: readonly Chapter[];
    /** Slug of the open chapter. */
    open: string;
    onopen: (slug: string) => void;
    /**
     * What goes on a page, given the chapter and which side it is.
     *
     * A snippet rather than two slots, because the turn has to render the *outgoing* chapter as
     * well as the open one. With slots that means cloning DOM, which is where every defect ADR 0015
     * lists came from; with a snippet the leaf is another call with different arguments.
     */
    page: Snippet<[Chapter, "verso" | "recto"]>;
  } = $props();

  const index = $derived(Math.max(0, chapters.findIndex((c) => c.slug === open)));
  const current = $derived(chapters[index] ?? chapters[0]!);

  /** The chapter being turned away from, and which way. Null when nothing is turning. */
  let leaving = $state<{ chapter: Chapter; forward: boolean } | null>(null);
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

  function go(slug: string): void {
    if (slug === open) return;
    const to = chapters.findIndex((c) => c.slug === slug);
    if (to < 0) return;

    if (still()) {
      // Reduced motion is a full path and not a faster one: the new spread is simply there, which
      // is the animation's correct end state rather than a degraded version of it.
      onopen(slug);
      return;
    }

    clearTimeout(settling);
    leaving = { chapter: current, forward: to > index };
    onopen(slug);

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
      <Page side="verso">{@render page(current, "verso")}</Page>
      <Page side="recto">{@render page(current, "recto")}</Page>

      {#if leaving}
        <!-- The outgoing page, held on the half the leaf is about to land on. -->
        <div class="stale stale--{arriving}" aria-hidden="true">
          <Page side={arriving} fill>{@render page(leaving.chapter, arriving)}</Page>
        </div>
        <!-- The shadow the turning page throws: a sibling, because a child would rotate with it. -->
        <div class="cast cast--{lifted}" aria-hidden="true"></div>
        <div class="leaf leaf--{lifted}" aria-hidden="true">
          <div class="leaf__face leaf__front">
            <Page side={lifted} fill>{@render page(leaving.chapter, lifted)}</Page>
          </div>
          <div class="leaf__face leaf__back">
            <Page side={arriving} fill>{@render page(current, arriving)}</Page>
          </div>
        </div>
      {/if}

      <div class="gutter" aria-hidden="true"><span class="gutter__line"></span></div>
    </div>

    <nav class="tabs" aria-label="chapters">
      {#each chapters as chapter, position (chapter.slug)}
        <button
          type="button"
          class="tab"
          style={tabStyle(position)}
          class:is-on={chapter.slug === current.slug}
          aria-current={chapter.slug === current.slug ? "page" : undefined}
          onclick={() => go(chapter.slug)}
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
    --page-pad: clamp(1.6rem, 3.2vw, 3.4rem);
    /* As large as the window allows in both axes, so it fills a wide monitor and still cannot run
       off the bottom of a short one. The subtraction is the chrome above it. */
    --book-h: min(calc(98vw / var(--ratio)), calc(100vh - 4.5rem));

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
