/**
 * What the world chapter keeps between its mounts, and the clock it shares with the address.
 *
 * Module level and single, because what it holds is. `Book` renders a page snippet once per side and
 * again on a turning leaf, so anything on the world's pages exists several times over; and the
 * record page that sends a reader to an animal and the atlas that shows it are never mounted by the
 * same parent. The `Clock` especially: it owns the URL and a timer, and a second one would fight the
 * first over both.
 *
 * Deliberately not a generic store. Everything here is a singleton because the world is, and a
 * factory would invite a second atlas into a book that has one back pocket.
 *
 * **Named `pocket` and not `world`, and that is not taste.** This file began as `world.svelte.ts`
 * beside the `World.svelte` that uses it, and on a case-insensitive filesystem -- which is to say on
 * this project's own -- the import `./world.svelte` resolved to the *component*. The failure was
 * "does not provide an export named 'clock'" and a blank page, with both files present and correct
 * and `tsc` passing. A `.svelte.ts` module must not share a name with a `.svelte` component, in any
 * casing.
 */

import { Clock } from "../../state/time";

/** Outside the reactive graph, because it owns the URL and a timer. */
export const clock = new Clock();

export const world = $state({
  /*
    An animal the reader arrived for, waiting for the atlas to be ready to show it.

    The road from a claim to the one animal that carries its argument was built deliberately in the
    old shell and died silently when the book became the front door: `Reader` passed no `onspecimen`,
    so `Claim` rendered no invitation at all. It goes through this module because the record page
    and the world chapter are never mounted by the same parent.
  */
  preselect: null as number | null,
  /*
    The atlas as it last was, for a turning page to carry (ADR 0021): the live atlas is drawn over
    both pages and leaves with its spread, so the copies of the world's pages show this instead.
  */
  still: null as string | null,
});
