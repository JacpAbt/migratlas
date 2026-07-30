<script lang="ts">
  import { RULE_HEIGHT, underline } from "./ink";

  let {
    seed,
    tone = "rust",
    draw = true,
  }: { seed: string; tone?: "rust" | "pencil" | "rule"; draw?: boolean } = $props();

  // Measured, not stretched. See the note at the top of `ink.ts`: a stretched viewBox and a dash
  // animation cannot coexist, because the path lives in user units and the dashes in screen units.
  let width = $state(0);
  let drawn = $state(!draw);

  const path = $derived(underline(seed, width));

  $effect(() => {
    // Guarded on width so the animation starts when there is a line to draw, not on first paint at
    // zero width -- where it would complete instantly and then be replaced by an undrawn line.
    if (!draw || width <= 0) return;
    const frame = requestAnimationFrame(() => (drawn = true));
    return () => cancelAnimationFrame(frame);
  });
</script>

<svg
  class="rule rule--{tone}"
  class:rule--drawn={drawn}
  bind:clientWidth={width}
  viewBox="0 0 {Math.max(width, 1)} {RULE_HEIGHT}"
  height={RULE_HEIGHT}
  aria-hidden="true"
>
  <!-- The wobble is under 2px across the whole width, so the drawn length is the width to well
       within a pixel. Close enough to skip a `getTotalLength` layout read on every resize. -->
  <path d={path} style="--length: {Math.ceil(width * 1.02)}" />
</svg>

<style>
  .rule {
    display: block;
    width: 100%;
    height: 8px;
    overflow: visible;
  }

  .rule path {
    fill: none;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-dasharray: var(--length);
    stroke-dashoffset: var(--length);
    transition: stroke-dashoffset var(--draw) var(--ease-pen);
  }

  .rule--drawn path {
    stroke-dashoffset: 0;
  }

  .rule--rust path {
    stroke: var(--rust-ink);
  }

  .rule--pencil path {
    stroke: var(--pencil);
    stroke-width: 1.2;
  }

  .rule--rule path {
    stroke: var(--rule);
    stroke-width: 1;
  }
</style>
