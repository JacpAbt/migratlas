<script lang="ts">
  import Atlas from "../atlas/Atlas.svelte";
  import { world } from "./pocket.svelte";

  let {
    base,
    part,
    side = "recto",
  }: { base: string; part: "map" | "apparatus" | "all"; side?: "verso" | "recto" } = $props();

  let paper = $state<HTMLDivElement | null>(null);
  /** Whether this page is a copy on the turning leaf, or the page parked under it. */
  let copy = $state(false);

  $effect(() => {
    copy = paper?.closest(".leaf, .stale") !== null && paper !== null;
  });
</script>

<!--
  The world chapter: a drawn atlas (ADR 0021).

  On a spread the atlas is drawn over both pages at once, as an atlas plate crosses the fold, so it
  is not here: `Reader` hands it to `Book` as the spread's `across`. What each page holds is paper --
  and, on the turning leaf or the page parked under it, the half of the atlas it covered, as a still,
  so a page lifted off the atlas carries its picture rather than going blank.

  On a phone the world is one leaf, and the atlas is on it.
-->
{#if part === "all"}
  <div class="world world--leaf">
    <Atlas {base} layout="leaf" />
  </div>
{:else}
  <div class="world" bind:this={paper} aria-hidden="true">
    {#if copy && world.still}
      <img class="world__still world__still--{side}" src={world.still} alt="" />
    {/if}
  </div>
{/if}

<style>
  /* The page's whole area, over its padding: the atlas bleeds to the page's edge, not its margins. */
  .world {
    position: absolute;
    inset: 0;
    overflow: hidden;
  }

  /* The atlas was the spread's width; each page shows its own half of the picture. */
  .world__still {
    position: absolute;
    top: 0;
    width: 200%;
    height: 100%;
  }

  .world__still--verso {
    left: 0;
  }

  .world__still--recto {
    left: -100%;
  }
</style>
