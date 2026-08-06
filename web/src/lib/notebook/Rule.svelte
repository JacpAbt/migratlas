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
  let host = $state<SVGSVGElement | null>(null);
  let started = $state(false);
  let length = $state(0);

  const stroke = $derived(
    tone === "rust" ? "var(--rust-ink)" : tone === "pencil" ? "var(--pencil)" : "var(--rule)",
  );

  // Redrawn whenever the width or the ink changes. rough.js draws each stroke twice, so the two
  // passes have to be regenerated together rather than restyled.
  $effect(() => {
    if (!host || width <= 0) return;
    host.replaceChildren();
    underline(host, seed, width, stroke);
    // Measured off the real path rather than assumed from the width: rough.js draws a line as two
    // overlapping strokes, so the drawn length is roughly twice the span and a dasharray sized to
    // the width would leave the second pass permanently half-drawn.
    length = [...host.querySelectorAll("path")].reduce((total, path) => total + path.getTotalLength(), 0);
  });

  $effect(() => {
    // Guarded on width so the animation starts when there is a line to draw, not on first paint at
    // zero width -- where it would complete instantly and then be replaced by an undrawn line.
    if (!draw || width <= 0) return;
    const frame = requestAnimationFrame(() => (started = true));
    return () => cancelAnimationFrame(frame);
  });

  const drawn = $derived(!draw || started);
</script>

<svg
  bind:this={host}
  class="rule rule--{tone}"
  class:rule--drawn={drawn}
  bind:clientWidth={width}
  viewBox="0 0 {Math.max(width, 1)} {RULE_HEIGHT}"
  height={RULE_HEIGHT}
  style="--length: {Math.ceil(length) || 1}"
  aria-hidden="true"
></svg>

<style>
  .rule {
    display: block;
    width: 100%;
    height: 10px;
    overflow: visible;
  }

  .rule :global(path) {
    fill: none;
    stroke-linecap: round;
    stroke-dasharray: var(--length);
    stroke-dashoffset: var(--length);
    transition: stroke-dashoffset var(--draw) var(--ease-pen);
  }

  .rule--drawn :global(path) {
    stroke-dashoffset: 0;
  }
</style>
