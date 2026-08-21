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
