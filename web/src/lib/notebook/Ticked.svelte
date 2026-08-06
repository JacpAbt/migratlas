<script lang="ts">
  import { boxDrawn, tick } from "./ink";

  let {
    seed,
    on,
    /** A control has a box to tick. A list of things that passed is just the marks. */
    box = true,
  }: { seed: string; on: boolean; box?: boolean } = $props();

  const BOX = 16;

  let host = $state<SVGSVGElement | null>(null);

  $effect(() => {
    if (!host) return;
    host.replaceChildren();
    if (box) boxDrawn(host, seed, BOX, BOX, "var(--rule)", 1.3);
    // In a control the tick is the accent, because the control is a choice. In a list of things a
    // claim survived it is the "addressed" colour, because that is what those items are.
    tick(host, seed, BOX, box ? "var(--rust-ink)" : "var(--status-addressed)");
    length = [...host.querySelectorAll("path")].slice(box ? 1 : 0).reduce(
      (total, path) => total + path.getTotalLength(),
      0,
    );
  });

  let length = $state(0);
</script>

<!--
  A drawn box with a drawn tick in it.

  Purely the ink: the `<input type="checkbox">` beside it is the control, and stays one. Generated
  at a fixed 16px rather than measured, because unlike a card or a button this never changes size --
  and paying a ResizeObserver for each of a dozen layer rows to learn "still 16" is not free.

  The tick is two strokes as a hand makes one, a short fall and a long rise, and it overshoots the
  box like every other mark here. A tick that fits neatly inside its box is a glyph.
-->
<svg
  bind:this={host}
  class="ticked"
  class:ticked--on={on}
  viewBox="0 0 {BOX} {BOX}"
  width={BOX}
  height={BOX}
  style="--length: {Math.ceil(length) || 1}"
  aria-hidden="true"
></svg>

<style>
  .ticked {
    flex: none;
    overflow: visible;
  }

  .ticked :global(path) {
    fill: none;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  /* Only the tick animates; its box is already there. Named rather than positional: rough.js nests
     each mark in its own `<g>`, so `path:not(:first-child)` -- which used to mean "not the box" --
     now matches nothing, because every path is the first child of its own group. */
  .ticked :global(.ink-tick path) {
    stroke-dasharray: var(--length);
    stroke-dashoffset: var(--length);
    transition: stroke-dashoffset var(--draw-quick) var(--ease-pen);
  }

  .ticked--on :global(.ink-tick path) {
    stroke-dashoffset: 0;
  }
</style>
