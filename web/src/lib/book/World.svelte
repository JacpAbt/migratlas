<script lang="ts">
  import Globe from "../globe/Globe.svelte";
  import Explore from "../shell/Explore.svelte";
  import { clock, instantOf, world } from "./pocket.svelte";
  import { SpeciesSurfaces } from "../../search/taxon";
  import { exploreView } from "../story";

  let { base, side }: { base: string; side: "verso" | "recto" } = $props();

  const surfaces = $derived(new SpeciesSurfaces(base));

  /**
   * What this chapter draws, which is every published layer that says it should be drawn.
   *
   * Two mistakes in one line, and the second was already solved in the shell this replaced.
   *
   * `meta.name`: a `LoadedLayer` keeps its name there, so `layer.name` was `undefined` for every one
   * of them. `exploreView` was handed a list of undefineds, `Globe` asked
   * `view.layers.includes(layer.meta.name)` of it and got false every time, and the chapter whose
   * whole purpose is to show every published layer drew none of them -- a sphere with nothing on it,
   * and no error anywhere.
   *
   * And the filter, which `Shell.svelte` had and this did not inherit: the detectability wash
   * *declares itself off*. Fifty thousand cells over the whole sphere, and it is the layer about
   * where change cannot be measured, so switching it on unasked gives a reader a surface they did
   * not ask for over everything else -- with its own checkbox saying it is not there, because the
   * panel goes on reading the declared value. Filtered here rather than in `story.ts`, because "off
   * until somebody asks for it" is a property of the layer and a view is only a list of names.
   *
   * Both halves were found by tests moved off the old shell, which ask what the map actually drew
   * and whether the panel agrees with it.
   */
  const view = $derived(
    exploreView(
      world.layers.filter((layer) => layer.visible ?? true).map((layer) => layer.meta.name),
    ),
  );
</script>

<!--
  The world, in the back pocket. ADR 0013 decision 4 gives this chapter the scroll, the layers, the
  clock and the search -- and `shell/Explore.svelte` already *is* those four, so it is mounted here
  rather than rebuilt. The rebuild is structural, not stylistic.

  The map is on the facing page and the apparatus on the argument page, which is the arrangement
  every other chapter uses: the thing being shown on the right, the thing you do about it on the
  left. Both halves read one shared state, because `Book` renders its snippet once per side and two
  instances of this component cannot see each other -- see `pocket.svelte.ts`.

  **The projection is still the question ADR 0013 left open**, and the arithmetic half of its spike
  now says something worth knowing. Mercator is conformal, so it does not distort these layers'
  *shape*: the Svalbard herd's aspect is 0.86 on the sphere and 0.86 on the sheet. What it distorts
  is area, by 1/cos squared. Measured per vertex, the herd takes 23 times its fair share of a flat
  sheet and the ice edge up to 42 times at its poleward extremes, against 1.7 for the radar band.
  That misleads only where both are on screen at once, which is exactly what a whole-world view is.
  So the globe stays the default until somebody looks at the alternative, and MapLibre's own control
  switches it.
-->
{#if side === "recto"}
  <div class="world">
    <Globe
      {base}
      {view}
      week={Math.floor(world.day / 7)}
      instant={instantOf()}
      onready={(report) => {
        world.layers = report.layers;
        world.detectability = report.detectability;
        world.selection = report.selection;
        world.map = report.map;
      }}
    />
  </div>
{:else}
  <p class="world__lead">
    Every published layer, and no argument on top of it. Switch them on, move the clock, or find a
    species.
  </p>
  {#if world.selection}
    <Explore
      layers={world.layers}
      {clock}
      day={world.day}
      minute={world.minute}
      selection={world.selection}
      {surfaces}
      detectability={world.detectability}
      preselect={world.preselect}
      onpreselected={() => (world.preselect = null)}
      onfocus={(at) => world.map?.flyTo({ center: at, zoom: 3, essential: true })}
    />
  {:else}
    <p class="world__waiting" role="status">Bringing the map up…</p>
  {/if}
{/if}

<style>
  /*
    The map fills the page and keeps its own corner rather than being inset like a plate. A plate is
    a figure a reader looks at; this is a thing a reader uses, and an inset map with a caption would
    promise the wrong interaction.
  */
  .world {
    position: absolute;
    inset: 0;
    overflow: hidden;
  }

  .world__lead {
    margin: 0 0 var(--gap);
    font-family: var(--font-hand);
    font-size: var(--size-lede);
    line-height: var(--leading-hand);
  }

  .world__waiting {
    margin: 0;
    font-size: var(--size-margin);
    color: var(--ink-soft);
  }
</style>
