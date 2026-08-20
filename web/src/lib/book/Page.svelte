<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    side,
    fill = false,
    children,
  }: {
    side: "verso" | "recto";
    /** Absolutely fill the parent, for the two places a page stands in for another one. */
    fill?: boolean;
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
  }

  /* Extra room on the bound edge: the pages meet on the crease, so there is no gutter column
     holding the text off it. */
  .page--verso .page__inner {
    padding-right: calc(var(--page-pad) + var(--book-fold) / 2);
  }

  .page--recto .page__inner {
    padding-left: calc(var(--page-pad) + var(--book-fold) / 2);
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
    /* One page at a time, so neither edge is bound. */
    .page--verso .page__inner,
    .page--recto .page__inner {
      padding: var(--page-pad);
    }

    .page__curl {
      display: none;
    }
  }
</style>
