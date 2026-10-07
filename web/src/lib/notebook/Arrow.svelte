<script lang="ts">
  import { arrow } from "./ink";

  let { seed, width = 64, height = 44 }: { seed: string; width?: number; height?: number } = $props();
  let host = $state<SVGSVGElement | null>(null);

  $effect(() => {
    if (!host) return;
    host.replaceChildren();
    arrow(host, seed, width, height, "var(--pencil)");
  });
</script>

<!-- The arrow a margin note draws back to its paragraph. Purely the ink; nothing here is read. -->
<svg bind:this={host} class="arrow" viewBox="0 0 {width} {height}" {width} {height} aria-hidden="true"></svg>

<style>
  .arrow {
    display: block;
    overflow: visible;
  }

  .arrow :global(path) {
    fill: none;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
</style>
