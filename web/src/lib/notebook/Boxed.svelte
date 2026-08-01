<script lang="ts">
  import { boxDrawn, lasso } from "./ink";

  let {
    seed,
    shape = "box",
    tone = "ink",
    active = false,
  }: {
    seed: string;
    /** `box` for a control you press. `lasso` for one you choose among others. */
    shape?: "box" | "lasso";
    /** `ink` is the ordinary hand. `rust` is the one thing on the screen you are meant to do. */
    tone?: "ink" | "rust";
    /** Drawn a second time, heavier, the way a hand goes over a line to mean it. */
    active?: boolean;
  } = $props();

  let width = $state(0);
  let height = $state(0);

  const drawn = $derived(
    shape === "lasso" ? lasso(seed, width, height) : boxDrawn(seed, width, height, 2),
  );
  // A second pass from a different seed, so the two strokes do not sit exactly on each other --
  // which is what going over a line actually looks like.
  const again = $derived(
    shape === "lasso" ? lasso(`${seed}:again`, width, height) : boxDrawn(`${seed}:again`, width, height, 3),
  );
</script>

<!--
  The mark round a control, drawn rather than bordered.

  Positioned absolutely inside whatever it is placed in, so a button keeps being a `<button>` and
  this is only its ink. Nothing here is focusable, nothing here is announced: the control is the
  control.

  Two states and no third. A hand does not have a hover colour -- it has "drawn" and "gone over
  twice" -- so pressed and selected are the second pass rather than a fill.
-->
<span
  class="boxed boxed--{tone}"
  class:boxed--active={active}
  bind:clientWidth={width}
  bind:clientHeight={height}
  aria-hidden="true"
>
  <svg viewBox="0 0 {Math.max(width, 1)} {Math.max(height, 1)}">
    <!-- A box is always drawn: it is the control's shape, and a button with no edge is a word.
         A lasso is only drawn when it is the one in force -- looping every option would say
         nothing, and the unchosen ones are meant to be just words. -->
    {#if shape === "box" || active}
      <path class="boxed__stroke" d={drawn} />
    {/if}
    {#if active}
      <path class="boxed__stroke boxed__stroke--again" d={again} />
    {/if}
  </svg>
</span>

<style>
  .boxed {
    position: absolute;
    inset: 0;
    pointer-events: none;
  }

  .boxed svg {
    width: 100%;
    height: 100%;
    overflow: visible;
  }

  .boxed__stroke {
    fill: none;
    stroke: var(--rule);
    stroke-width: 1.3;
    stroke-linecap: round;
    stroke-linejoin: round;
    transition: stroke var(--fade);
  }

  .boxed--rust .boxed__stroke {
    stroke: var(--rust-ink);
    stroke-width: 1.6;
  }

  .boxed--active .boxed__stroke {
    stroke: var(--pencil);
  }

  .boxed--rust.boxed--active .boxed__stroke {
    stroke: var(--rust-ink);
  }

  /* Lighter than the first pass. Going over a line does not double the ink, it thickens it
     unevenly, and two strokes at full weight read as a rendering error. */
  .boxed__stroke--again {
    opacity: 0.55;
  }
</style>
