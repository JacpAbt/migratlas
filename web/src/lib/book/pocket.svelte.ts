/**
 * The one world, shared between the two halves of the spread.
 *
 * `Book` renders its page snippet once per side, so a component placed on the spread exists twice
 * over -- once on the verso and once on the recto. That is right for a page and wrong for the world:
 * the map mounts on the facing page and reports its layers through `onready`, while the controls
 * live on the argument page, and two instances of the same component cannot see each other's state.
 * The first attempt did exactly that and left the controls saying "bringing the map up" forever
 * while the map was already up beside them.
 *
 * So the state is module level and there is exactly one of it, which is also true of the thing it
 * describes. The `Clock` especially: it owns the URL and a timer, and a second one would fight the
 * first over both.
 *
 * Deliberately not a generic store. Everything here is a singleton because the world is, and a
 * factory would invite a second map into a book that has one back pocket.
 *
 * **Named `pocket` and not `world`, and that is not taste.** This file began as `world.svelte.ts`
 * beside the `World.svelte` that uses it, and on a case-insensitive filesystem -- which is to say on
 * this project's own -- the import `./world.svelte` resolved to the *component*. The failure was
 * "does not provide an export named 'clock'" and a blank page, with both files present and correct
 * and `tsc` passing. A `.svelte.ts` module must not share a name with a `.svelte` component, in any
 * casing.
 */

import type { Map as MapLibreMap } from "maplibre-gl";

import { Clock } from "../../state/time";
import type { DetectabilityDocument } from "../../layers/detectability";
import type { SpeciesSelection } from "../../layers/selection";
import type { LoadedLayer } from "../../layers/types";

/** Outside the reactive graph, because it owns the URL and a timer. */
export const clock = new Clock();

export const world = $state({
  day: clock.state.day,
  minute: clock.state.minute,
  layers: [] as LoadedLayer[],
  detectability: null as DetectabilityDocument | null,
  selection: null as SpeciesSelection | null,
  map: undefined as MapLibreMap | undefined,
  /*
    A species the reader arrived for, waiting for the panel to be ready to show it.

    The road from a claim to the one animal that carries its argument was built deliberately in the
    old shell and died silently when the book became the front door: `Reader` passed no `onspecimen`,
    so `Claim` rendered no invitation at all. It goes through this module for the same reason the
    map does -- the record page and the world chapter are never mounted by the same parent.
  */
  preselect: null as number | null,
  /*
    Which layers are drawn, by name, and the only answer to that question.

    It starts empty on the owner's decision: the chapter's brief is "every published layer, and no
    argument on top of it", and taken as *all of them at once* that defeated itself -- nine layers
    composited is a mush that reads as satellite imagery rather than as nine measurements, over a
    basemap that is already paper and ink. So the reader paints the map, and "every published layer"
    is a promise about what is available rather than about what is painted before anyone asks.

    One list rather than two, and that is the structural half. The map used to take its layers from
    each layer's *declared* initial visibility and the panel initialised its checkboxes from the same
    field -- an invariant held by both sides reading one number, and asserted by hand in
    `globe.spec.ts` because it had already been broken once. Now the panel writes here and the map
    reads here, so the two cannot disagree about what is drawn.
  */
  drawn: [] as string[],
  /*
    How far the phone's tool flap is open: the clock only, the layers as well, or everything.

    Here rather than inside the component because the render window mounts three leaves and drops the
    rest -- a reader who opens the flap, swipes back a page to re-read a claim and returns would find
    it shut, which is the state being thrown away rather than remembered. `peek` is the default
    because the clock is the control that most needs the map beside it.
  */
  flap: "peek" as "peek" | "half" | "full",
});

/**
 * Mirror the clock into state, once.
 *
 * A class with its own listeners is not reactive by itself, so the parts the page reads have to be
 * copied across. Subscribed here rather than in an effect because there is one subscription for the
 * session and an effect would make one per mounted instance -- which is the same two-instance
 * problem this module exists to solve, in a quieter form.
 */
clock.subscribe((state) => {
  world.day = state.day;
  world.minute = state.minute;
});

/** The moment the terminator is drawn for, rebuilt from the mirrored parts. */
export function instantOf(): Date {
  return new Date(Date.UTC(clock.state.year, 0, 1 + world.day, 0, world.minute));
}
