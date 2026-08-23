<script lang="ts">
  import Globe from "../globe/Globe.svelte";
  import Explore from "../world/Explore.svelte";
  import { clock, instantOf, world } from "./pocket.svelte";
  import { SpeciesSurfaces } from "../../search/taxon";
  import { exploreView, sphereZoom } from "../story";

  let { base, part }: { base: string; part: "map" | "apparatus" | "all" } = $props();

  /*
    How far the flap is open, and what the handle offers next.

    Three states rather than two, because the tools are three questions of decreasing urgency: when,
    then what is drawn, then under what terms and which animal. A peek is the clock alone, which is
    the one control that is meaningless without the map beside it.
  */
  const FLAP: Record<string, { next: "peek" | "half" | "full"; says: string }> = {
    peek: { next: "half", says: "Layers" },
    half: { next: "full", says: "Terms and search" },
    full: { next: "peek", says: "Close" },
  };
  const flap = $derived(FLAP[world.flap] ?? FLAP.peek!);

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
   * And the filter, which the deleted `Shell.svelte` had and this did not inherit: the detectability wash
   * *declares itself off*. Fifty thousand cells over the whole sphere, and it is the layer about
   * where change cannot be measured, so switching it on unasked gives a reader a surface they did
   * not ask for over everything else -- with its own checkbox saying it is not there, because the
   * panel goes on reading the declared value. Filtered here rather than in `story.ts`, because "off
   * until somebody asks for it" is a property of the layer and a view is only a list of names.
   *
   * Both halves were found by tests moved off the old shell, which ask what the map actually drew
   * and whether the panel agrees with it.
   */
  /*
    Measured, so the sphere fills the page it is on.

    The map is a page of a spread, not a window, and its size changes with the window -- so the zoom
    is computed from the box rather than carried as a constant. `sphereZoom` has the arithmetic.
  */
  let mapWidth = $state(0);
  let mapHeight = $state(0);

  const view = $derived(exploreView(world.drawn, sphereZoom(mapWidth, mapHeight)));
</script>

<!--
  The world, in the back pocket. ADR 0013 decision 4 gives this chapter the scroll, the layers, the
  clock and the search -- and `world/Explore.svelte` already *is* those four, so it is mounted here
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
{#if part === "all"}
  <!--
    One leaf: the globe, and the tools in a flap tucked into its foot.

    ADR 0015 decision 8 left this open and named the reason -- the spread's arrangement puts the
    clock on one leaf and the map on the next, and a control whose whole purpose is watching the map
    answer is not slow that way, it is pointless. The owner's shape, chosen 2026-08-23.

    It covers the foot of the map, which is the opposite of what the same chapter's licence notice
    was corrected for on a spread. The difference is who opened it: that notice un-compacted itself
    over a quarter of the map unasked, and this is a flap the reader pulls up and pushes back. The
    objection was never that nothing may cover a map.
  -->
  <div class="world world--one" bind:clientWidth={mapWidth} bind:clientHeight={mapHeight}>
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

    <div class="flap flap--{world.flap}">
      <button
        type="button"
        class="flap__grip"
        aria-expanded={world.flap !== "peek"}
        onclick={() => (world.flap = flap.next)}
      >
        <span class="flap__says">{flap.says}</span>
        <span class="flap__arrow" aria-hidden="true">{world.flap === "full" ? "⌄" : "⌃"}</span>
      </button>

      {#if world.selection}
        <div class="flap__slip">
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
            shown={world.drawn}
            only={world.flap === "peek" ? "clock" : "all"}
            ontoggle={(name, on) => {
              world.drawn = on ? [...world.drawn, name] : world.drawn.filter((d) => d !== name);
            }}
            onfocus={(at) => world.map?.flyTo({ center: at, zoom: 3, essential: true })}
          />
        </div>
      {/if}
    </div>
  </div>
{:else if part === "map"}
  <div class="world" bind:clientWidth={mapWidth} bind:clientHeight={mapHeight}>
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
      shown={world.drawn}
      ontoggle={(name, on) => {
        world.drawn = on ? [...world.drawn, name] : world.drawn.filter((drawn) => drawn !== name);
      }}
      onfocus={(at) => world.map?.flyTo({ center: at, zoom: 3, essential: true })}
    />
  {:else}
    <p class="world__waiting" role="status">Bringing the map up…</p>
  {/if}
{/if}

<style>
  /* --- One leaf, on a phone -------------------------------------------------- */

  .world--one {
    position: relative;
    /* The globe takes the whole leaf and the flap sits over it, rather than the two sharing a column:
       a map given "whatever is left" is a map that changes size when the flap opens. */
    height: 100%;
  }

  /*
    Tucked into the foot of the page, the way the plate is taped to it: paper a shade off the page,
    a hard top edge and its shadow above rather than below, because it lies *on* the leaf.
  */
  .flap {
    position: absolute;
    /*
      Stopped at the page's own foot, not the leaf's edge.

      `.world` is `inset: 0` on purpose -- the map bleeds over the page's padding so it fills the
      leaf rather than sitting in it like a plate -- and a flap that inherited that bleed printed its
      clock underneath the folio and the realm tabs. `--page-foot` is the same knob the text
      respects, declared by the container that owns the furniture down there.
    */
    inset: auto 0 var(--page-foot, 0);
    z-index: 3;
    display: flex;
    flex-direction: column;
    max-height: 100%;
    background: var(--plate-paper);
    border-top: 1px solid var(--rule);
    box-shadow: 0 -3px 10px rgb(0 0 0 / 14%);
  }

  .flap__grip {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--gap-tight);
    padding: 0.35rem var(--gap-tight);
    font-family: var(--font-body);
    font-size: var(--size-label);
    letter-spacing: var(--tracking-label);
    text-transform: uppercase;
    color: var(--ink-soft);
    background: none;
    border: none;
    cursor: pointer;
  }

  .flap__arrow {
    font-size: 1.1rem;
    line-height: 1;
    color: var(--pencil);
  }

  /* Scrolls inside the flap rather than growing past the leaf: the flap is furniture on a page and
     the page's own budget is not its to spend. */
  .flap__slip {
    min-height: 0;
    overflow-y: auto;
    padding: 0 var(--gap-tight) var(--gap-tight);
  }

  /* The three depths. A peek is the clock; the others are fractions of the leaf rather than of the
     content, so the map keeps a knowable share of the screen either way. */
  .flap--half {
    height: 52%;
  }

  .flap--full {
    height: 82%;
  }

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
