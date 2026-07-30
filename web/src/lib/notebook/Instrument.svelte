<script lang="ts">
  import { SKETCHES } from "./ink";
  import type { Instrument } from "../ledger";

  let { kind, size = 46 }: { kind: Instrument; size?: number } = $props();

  const sketch = $derived(SKETCHES[kind]);
</script>

<!--
  What the apparatus was, drawn where an illustration would go.

  ADR 0007 decision 5. The radar measures aerial biomass and cannot separate birds from bats from
  insects, so a swallow here would contradict the caveat printed two lines below it. The `<title>`
  is not decoration either: a reader using a screen reader gets the same statement about the
  instrument that a sighted reader gets from the drawing.
-->
<svg
  class="instrument"
  viewBox="0 0 48 48"
  width={size}
  height={size}
  role="img"
  aria-label={sketch.label}
>
  <title>{sketch.label}</title>
  {#each sketch.reach ?? [] as path (path)}
    <path class="instrument__reach" d={path} />
  {/each}
  {#each sketch.strokes as path (path)}
    <path class="instrument__stroke" d={path} />
  {/each}
  {#each sketch.dots ?? [] as [cx, cy, r] (`${cx}:${cy}`)}
    <circle class="instrument__dot" {cx} {cy} {r} />
  {/each}
</svg>

<style>
  .instrument {
    display: block;
    flex: none;
    overflow: visible;
  }

  .instrument__stroke {
    fill: none;
    stroke: var(--ink-soft);
    stroke-width: 1.6;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  /* What the instrument reaches rather than what it is: the radar's range arcs, the shaded cells of
     a grid. Fainter and dashed, so the object stays the object. */
  .instrument__reach {
    fill: none;
    stroke: var(--pencil);
    stroke-width: 1.1;
    stroke-dasharray: 2.5 2.5;
    stroke-linecap: round;
    opacity: 0.75;
  }

  .instrument__dot {
    fill: var(--rust-ink);
  }
</style>
