<script lang="ts">
  import { world } from "./pocket.svelte";
  import Surface from "../notebook/Surface.svelte";
  import TypeChoice from "../notebook/TypeChoice.svelte";
  import { drawFurniture } from "../notebook/furniture";
  import { setPalette } from "../../globe/flavor";
  import { repaintBasemap } from "../../globe/map";
  import {
    applySurface,
    isNight,
    storedSurface,
    watchSystem,
    type Surface as SurfaceChoice,
  } from "../../state/surface";
  import { applyType, storedType, type TypeChoice as TypeName } from "../../state/type";

  /**
   * Which paper this is read on.
   *
   * Applied on mount rather than initialised from it: the stored choice has to reach
   * `document.documentElement` before anything reads a token off it, and the globe's palette is set
   * from the same value so the sphere and the page can never disagree about what surface it is.
   */
  let surface = $state<SurfaceChoice>("system");

  /** Which type the page is set in. Independent of the surface: black paper and a legible face is a
      combination someone will want, and neither setting reads the other. */
  let typeChoice = $state<TypeName>("hand");

  $effect(() => {
    surface = applySurface(storedSurface());
    typeChoice = applyType(storedType());
  });

  /*
    The globe's colours are JavaScript, not CSS, so nothing repaints them on its own, and neither the
    scrollbar nor MapLibre's buttons can hold a `var()` -- their ink is baked into a data URI. This
    runs on the stored choice too and not only on a click, otherwise a reader who chose night last
    week gets a black page around a parchment globe with a parchment scrollbar down the side.

    The map is read out of `pocket.svelte.ts` rather than passed in, because it is the world
    chapter's and this control is on the desk: the two are never mounted by the same parent, and on
    every other page of the book there is no map to repaint at all.
  */
  function follow(): void {
    setPalette(isNight(surface));
    drawFurniture();
    const map = world.map;
    if (!map) return;
    repaintBasemap(map);
    for (const layer of world.layers) layer.repaint?.();
  }

  $effect(follow);

  // And when the machine changes its mind while the choice is "system".
  $effect(() =>
    watchSystem(() => {
      if (surface === "system") follow();
    }),
  );
</script>

<!--
  The two settings a reader makes about how the page reaches them, on the desk beside the book.

  Inherited from `shell/Shell.svelte` when the book became the front door. They are not part of the
  book: a book does not carry a switch for what paper it is printed on, so they sit on the desk in
  the corner a pencil tray would be, out of the way of the thumb tabs on the fore-edge and the
  folios in the outer corners.

  Both are radiogroups rather than toggles, and `Surface`'s own comment says why at length: "follow
  the machine" is a choice and not the absence of one.
-->
<div class="settings">
  <TypeChoice choice={typeChoice} onchoose={(next) => (typeChoice = applyType(next))} />
  <Surface {surface} onchoose={(next) => (surface = applySurface(next))} />
</div>

<style>
  .settings {
    position: fixed;
    top: var(--gap-tight);
    left: var(--gap-tight);
    z-index: 20;
    display: flex;
    align-items: center;
    gap: var(--gap);
    flex-wrap: wrap;
  }
</style>
