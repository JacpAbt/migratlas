<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    side,
    fill = false,
    folio = null,
    onturn,
    children,
  }: {
    side: "verso" | "recto";
    /** Absolutely fill the parent, for the two places a page stands in for another one. */
    fill?: boolean;
    /**
     * The folio, counted over the whole book. Null on the one page that has none.
     *
     * Printed here rather than by the container because it is part of the page, and because a number
     * only means something if it is on every leaf: the mock printed "017" in a corner while every
     * chapter was one scrolling page, so the number was decoration. It is not decoration now.
     */
    folio?: number | null;
    /**
     * Turn from this page, if there is anywhere to turn.
     *
     * A book has no "next" button; it has a corner you put your thumb on. So the folio in the outer
     * corner is the control, which is one mark doing two jobs and needs no icon nobody would draw by
     * hand. The first attempt printed the number twice -- once on the page and once on a separate
     * corner button beside it -- which is how this got noticed.
     */
    onturn?: () => void;
    children: Snippet;
  } = $props();
</script>

<!--
  A leaf of the book: paper, grain, the curl into the binding, and room for whatever is set on it.

  **This component is the reason the turn is not a pile of bugs.** ADR 0015 decision 5 records five
  separate defects from the mock, all with one cause: the turning page was a DOM *clone* of a real
  page, and a clone is missing whatever the original got from its context. It lost the class that
  carried the padding, so prose jumped twenty pixels. It lost the paper its own grain needed to
  multiply against, so the covered page went pale. It sat a border-width off the page it stood in
  for. It was shaded twice because the face had a gradient and the clone brought another.

  So there is exactly one page component, and the leaf and the parked page are *instances* of it
  with different props. Every one of those five is now unreachable rather than fixed.
-->
<div class="page page--{side}" class:page--fill={fill}>
  <div class="page__grain" aria-hidden="true"></div>
  <div class="page__curl" aria-hidden="true"></div>
  <div class="page__inner">
    {@render children()}
  </div>
  {#if folio !== null && onturn}
    <button
      type="button"
      class="page__folio page__folio--turn"
      data-turn={side === "recto" ? "on" : "back"}
      aria-label={side === "recto" ? "Turn the page" : "Turn back"}
      onclick={onturn}
    >
      {String(folio).padStart(3, "0")} · migratlas
    </button>
  {:else if folio !== null}
    <p class="page__folio">{String(folio).padStart(3, "0")} · migratlas</p>
  {/if}
</div>

<style>
  .page {
    position: relative;
    overflow: hidden;
    /*
      No background. The spread beneath is the paper, so a page is a window onto it -- which is what
      lets the grain below multiply against the paper rather than against nothing. The two places a
      page stands in for another one sit in their own stacking context and therefore *do* need a
      ground; `page--fill` gives them one.
    */
  }

  .page--fill {
    position: absolute;
    inset: 0;
    background: var(--paper);
  }

  .page__inner {
    position: relative;
    height: 100%;
    display: flex;
    flex-direction: column;
    padding: var(--page-pad);
    /* A backstop, not a feature. `pages.ts` puts one panel on a page precisely so this never
       engages, and `tests/book.spec.ts` walks all seventy pages at both supported sizes asserting
       that it does not. It stays because a reader at 200% zoom with a font this project did not
       choose should get a scrollbar rather than a truncated caveat. */
    overflow-y: auto;
    overscroll-behavior: contain;
  }

  /* Extra room on the bound edge: the pages meet on the crease, so there is no gutter column
     holding the text off it. */
  .page--verso .page__inner {
    padding-right: calc(var(--page-pad) + var(--book-fold) / 2);
  }

  .page--recto .page__inner {
    padding-left: calc(var(--page-pad) + var(--book-fold) / 2);
  }

  /* The outer corner, where a thumb goes. */
  .page__folio {
    position: absolute;
    bottom: 0;
    /* Above a full-bleed panel: the world's map fills its page absolutely and would otherwise take
       the corner with it. */
    z-index: 3;
    margin: 0;
    padding: var(--gap) var(--gap-wide);
    font-family: var(--font-mono);
    font-size: var(--size-label);
    letter-spacing: var(--tracking-label);
    color: var(--pencil);
    background: none;
    border: none;
    pointer-events: none;
  }

  .page__folio--turn {
    cursor: pointer;
    pointer-events: auto;
    transition: color var(--draw-quick) var(--ease-pen);
  }

  .page__folio--turn:hover,
  .page__folio--turn:focus-visible {
    color: var(--rust);
  }

  .page--verso .page__folio {
    left: 0;
  }

  .page--recto .page__folio {
    right: 0;
  }

  .page__grain {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background-image: var(--grain);
    background-size: var(--grain-size);
    mix-blend-mode: var(--grain-blend);
    opacity: 0.9;
  }

  /*
    Paper does not lie flat next to a binding: the inner edge darkens towards the fold and the outer
    edge catches a little light. Light rather than paint, so it survives a surface change, and one
    element rather than a pseudo-element on `.page` because the mock put it in two places at once
    and shaded the turning sheet twice.
  */
  .page__curl {
    position: absolute;
    inset: 0;
    pointer-events: none;
  }

  .page--verso .page__curl {
    background:
      linear-gradient(to right, rgb(255 255 255 / 5%) 0 6%, transparent 22%),
      linear-gradient(to left, rgb(0 0 0 / 13%), transparent 16%);
  }

  .page--recto .page__curl {
    background:
      linear-gradient(to left, rgb(255 255 255 / 5%) 0 6%, transparent 22%),
      linear-gradient(to right, rgb(0 0 0 / 13%), transparent 16%);
  }

  @media (width < 62rem) {
    /* One page at a time, so neither edge is bound. The head and the foot are the container's to
       set, because what sits over the top and bottom of the page is the container's furniture:
       `Leaves` puts a thumb tab in the bottom corner and the type controls are fixed over the top,
       and text running under either is text nobody can read. */
    .page--verso .page__inner,
    .page--recto .page__inner {
      padding: var(--page-head, var(--page-pad)) var(--page-pad)
        var(--page-foot, var(--page-pad));
    }

    .page__curl {
      display: none;
    }
  }
</style>
