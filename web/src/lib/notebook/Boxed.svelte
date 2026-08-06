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

  let host = $state<SVGSVGElement | null>(null);
  let width = $state(0);
  let height = $state(0);

  const stroke = $derived(
    tone === "rust" ? "var(--rust-ink)" : active ? "var(--pencil)" : "var(--rule)",
  );

  $effect(() => {
    if (!host || width <= 0 || height <= 0) return;
    host.replaceChildren();

    // A box is always drawn: it is the control's shape, and a button with no edge is a word.
    // A lasso is only drawn round the one in force -- looping every option would say nothing,
    // and the unchosen ones are meant to be just words.
    if (shape === "box") {
      boxDrawn(host, seed, width, height, stroke, tone === "rust" ? 1.7 : 1.4);
    } else if (active) {
      lasso(host, seed, width, height, "var(--rust-ink)");
    }

    if (active && shape === "box") {
      // A second pass from a different seed, so the two strokes do not sit exactly on each other,
      // which is what going over a line actually looks like. Lighter, because going over a line
      // thickens it unevenly rather than doubling the ink.
      const before = host.childElementCount;
      boxDrawn(host, `${seed}:again`, width, height, stroke, 1.2);
      for (const node of [...host.children].slice(before)) {
        (node as SVGElement).style.opacity = "0.55";
      }
    }
  });
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
  class="boxed"
  bind:clientWidth={width}
  bind:clientHeight={height}
  aria-hidden="true"
>
  <svg bind:this={host} viewBox="0 0 {Math.max(width, 1)} {Math.max(height, 1)}"></svg>
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

  .boxed :global(path) {
    fill: none;
    stroke-linecap: round;
    stroke-linejoin: round;
    transition: stroke var(--fade);
  }
</style>
