<script lang="ts">
  import { boxDrawn, tick } from "./ink";

  let {
    seed,
    on,
    /** A control has a box to tick. A list of things that passed is just the marks. */
    box = true,
  }: { seed: string; on: boolean; box?: boolean } = $props();

  const BOX = 14;

  const frame = boxDrawn(seed, BOX, BOX, 1.5);
  const mark = tick(seed, BOX);
</script>

<!--
  A drawn box with a drawn tick in it.

  Purely the ink: the `<input type="checkbox">` beside it is the control, and stays one. Generated
  at a fixed 14px rather than measured, because unlike a card or a button this never changes size --
  and paying a ResizeObserver for each of a dozen layer rows to learn "still 14" is not free.

  The tick is two strokes as a hand makes one, a short fall and a long rise, and it overshoots the
  box like every other mark here. A tick that fits neatly inside its box is a glyph.
-->
<svg class="ticked" class:ticked--on={on} class:ticked--bare={!box} viewBox="0 0 {BOX} {BOX}" width={BOX} height={BOX} aria-hidden="true">
  {#if box}
    <path class="ticked__box" d={frame} />
  {/if}
  <path class="ticked__tick" d={mark} />
</svg>

<style>
  .ticked {
    flex: none;
    overflow: visible;
  }

  .ticked__box {
    fill: none;
    stroke: var(--rule);
    stroke-width: 1.2;
    stroke-linecap: round;
  }

  /* Drawn on rather than faded in: the mark travels the way a pen does, and under reduced motion
     `--draw-quick` is 0ms so it is simply there on the first frame. */
  .ticked__tick {
    fill: none;
    stroke: var(--status-addressed);
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-dasharray: 26;
    stroke-dashoffset: 26;
    transition: stroke-dashoffset var(--draw-quick) var(--ease-pen);
  }

  .ticked--on .ticked__tick {
    stroke-dashoffset: 0;
  }

  /* In a control the tick is the accent, because the control is a choice. In a list of things a
     claim survived it is the "addressed" green, because that is what those items are. */
  :global(.layers) .ticked__tick {
    stroke: var(--rust-ink);
  }
</style>
