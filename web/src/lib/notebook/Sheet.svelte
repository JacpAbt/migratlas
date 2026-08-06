<script lang="ts">
  import type { Snippet } from "svelte";

  import { boxDrawn, sheetEdge } from "./ink";

  let { seed, children }: { seed: string; children: Snippet } = $props();

  // Measured, never stretched. `ink.ts` explains why at length: a path generated in a unit box and
  // stretched with preserveAspectRatio keeps its geometry in user units while the stroke and the
  // dash pattern are applied in screen units, so a wobble becomes an ellipse and a 2px pen becomes
  // 2px by 9px. Everything here is generated at the size it will be drawn at.
  let width = $state(0);
  let height = $state(0);

  const ground = $derived(sheetEdge(seed, width, height));

  let ink = $state<SVGSVGElement | null>(null);

  // Redrawn on resize and on a palette change. rough.js draws each stroke twice, so the edge has
  // to be regenerated rather than restyled -- there is no single path to recolour.
  $effect(() => {
    if (!ink || width <= 0 || height <= 0) return;
    ink.replaceChildren();
    boxDrawn(ink, seed, width, height, "var(--rule)", 1.4);
  });
</script>

<!--
  A sheet of paper, rather than a div with a border and a radius.

  The old card was `1px solid var(--rule)` with `border-radius: 3px`, which is the single most
  un-notebook-like object available: a stroked rounded rectangle is a UI card. Paper has an edge
  that was cut or torn, a ground that is not perfectly flat, and a shadow because it is lying on
  something.

  Three layers, and each is doing a different job:

  - the **ground**, a filled path in the paper colour, torn down its left edge -- a leaf out of a
    bound notebook.
  - the **grain**, the same two low-alpha gradients as before but now clipped to the ground, so the
    texture stops at the tear instead of at a rectangle two pixels outside it.
  - the **edge**, a drawn line round the outside. Not a border: it overshoots its corners, and it
    is the one thing here that reads immediately as having been made by a hand.
-->
<div class="sheet" bind:clientWidth={width} bind:clientHeight={height}>
  <div class="sheet__lift" aria-hidden="true">
    <div class="sheet__ground" style={ground ? `clip-path: path('${ground}')` : undefined}></div>
  </div>
  <svg
    bind:this={ink}
    class="sheet__ink"
    viewBox="0 0 {Math.max(width, 1)} {Math.max(height, 1)}"
    aria-hidden="true"
  ></svg>
  {@render children()}
</div>

<style>
  .sheet {
    position: relative;
    /* No background of its own. The ground below is the paper, so the shadow can follow the tear
       instead of outlining the rectangle the tear was cut out of. */
  }

  /*
    Two nested divs, and the nesting is the point.

    `clip-path` and `box-shadow` do not compose: the shadow is painted by the element and then the
    element is clipped, so a torn card with a box-shadow has no shadow at all. `filter:
    drop-shadow()` *does* follow an arbitrary silhouette -- but the rendering order is filter, then
    clip -- so it has to sit on an ancestor of the clipped node rather than on the node itself.

    And it cannot go on `.sheet`, because a filter applies to the whole subtree: every word on the
    card would get its own drop shadow.
  */
  .sheet__lift {
    position: absolute;
    inset: 0;
    filter: drop-shadow(var(--shadow-sheet));
  }

  /* The blend is not optional and this is where that was learned. Without it the grain is painted
     *over* the paper rather than into it, so every card on the site was the raw texture -- a grey
     slab in both surfaces, with the paper colour underneath it and invisible. Anything that paints
     paper takes all three of these together. */
  .sheet__ground {
    position: absolute;
    inset: 0;
    background-color: var(--paper);
    background-image: var(--grain);
    background-size: var(--grain-size);
    background-blend-mode: var(--grain-blend);
  }

  .sheet__ink {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    /* Above the ground and below the words. A drawn edge that crosses the text would be a mark on
       the page rather than the shape of it. */
    z-index: 0;
  }

  .sheet__ink :global(path) {
    fill: none;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  /* The content sits above the ink so a heading can overlap the edge without being crossed out. */
  .sheet > :global(:not(.sheet__ink, .sheet__lift)) {
    position: relative;
    z-index: 1;
  }
</style>
