<script lang="ts">
  import Surface from "../notebook/Surface.svelte";
  import TypeChoice from "../notebook/TypeChoice.svelte";
  import { drawFurniture } from "../notebook/furniture";
  import {
    applySurface,
    storedSurface,
    watchSystem,
    type Surface as SurfaceChoice,
  } from "../../state/surface";
  import { applyType, storedType, type TypeChoice as TypeName } from "../../state/type";

  /**
   * Which paper this is read on.
   *
   * Applied on mount rather than initialised from it: the stored choice has to reach
   * `document.documentElement` before anything reads a token off it.
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
    The scrollbar cannot hold a `var()` -- its ink is baked into a data URI -- so nothing repaints it
    on its own. This runs on the stored choice too and not only on a click, otherwise a reader who
    chose night last week gets a black page with a parchment scrollbar down the side. The atlas
    repaints its own ink when the surface attribute changes, so it needs nothing from here.
  */
  function follow(): void {
    drawFurniture();
  }

  /*
    Reads `surface`, which is what makes this run again when the paper changes. It used to read it
    inside the globe's palette call, and when that call went the effect had nothing reactive left in
    it: it ran once, and the scrollbar stayed in day ink on night paper.
  */
  $effect(() => {
    void surface;
    follow();
  });

  // And when the machine changes its mind while the choice is "system".
  $effect(() =>
    watchSystem(() => {
      if (surface === "system") follow();
    }),
  );
</script>

<!--
  The two settings a reader makes about how the page reaches them, on the desk beside the book.

  Inherited from `shell/Shell.svelte`, since deleted, when the book became the front door. They are not part of the
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

  /*
    On the spread they are a slip of paper lying on the table, a corner of tape holding it -- the
    owner wanted the switches to belong to the table rather than float over it, and dark labels on
    walnut would not be legible anyway. The phone has no table, and keeps them as they were.
  */
  @media (width >= 62rem) {
    .settings {
      padding: 6px 12px 7px;
      rotate: -1.6deg;
      background: var(--paper);
      border-radius: 1px;
      box-shadow:
        0 1px 1px rgb(0 0 0 / 18%),
        2px 5px 9px rgb(20 10 2 / 35%);
    }

    .settings::before {
      content: "";
      position: absolute;
      left: 50%;
      top: -7px;
      width: 46px;
      height: 15px;
      translate: -50% 0;
      rotate: 3deg;
      background: rgb(245 238 215 / 62%);
      box-shadow: 0 0 1px rgb(0 0 0 / 15%);
    }
  }
</style>
