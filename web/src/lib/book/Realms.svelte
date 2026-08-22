<script lang="ts">
  import { REALMS } from "../story";

  let {
    open,
    onpick,
    foot = false,
  }: {
    open: string;
    onpick: (slug: string) => void;
    /**
     * Which edge the strip is on, which is the only thing the two containers disagree about.
     *
     * A tab is rounded away from the edge it grows out of. The spread's strip hangs below the book,
     * so it is rounded at the bottom; a phone's sits on the foot of the screen with nothing under it
     * to hang into, so it grows upwards and is rounded at the top. One flag rather than a rotation,
     * because rotating the strip rotates the words in it.
     */
    foot?: boolean;
  } = $props();
</script>

<!--
  The second level of index tabs: which realm the book is read in.

  Chapters are the questions and these are the filter, which is why they are smaller, greyer and on
  the other edge. The active one takes `--tint` from whichever chapter is open, so the two levels
  read as one index rather than as two competing sets of tabs -- the parent sets that property, the
  same `tabStyle` call it uses for the chapter tab itself.

  Positioning is deliberately not here. There are two containers and the tail of a spread is not the
  foot of a phone, so each parent places this strip and only the tabs themselves are shared.
-->
<nav class="realms" class:realms--foot={foot} aria-label="Realms">
  {#each REALMS as realm (realm.slug)}
    {@const here = realm.slug === open}
    <button
      type="button"
      class="realm"
      class:is-on={here}
      aria-current={here ? "true" : undefined}
      onclick={() => onpick(realm.slug)}
    >
      {realm.tab}
    </button>
  {/each}
</nav>

<style>
  .realms {
    display: flex;
    gap: 3px;
  }

  .realm {
    /*
      Sized by the parent or not at all. `--book-h` exists on the spread and not on the phone, and a
      `var()` that resolves to nothing takes its whole declaration with it -- so the fraction-of-the-
      book figure is passed in as `--realm-size` and this is the fallback rather than the rule.
    */
    font-family: var(--font-body);
    font-size: var(--realm-size, 0.66rem);
    /* Tight, because this strip stands in the slack under the book and there are 21 pixels of it. */
    padding: 0.22em 0.66em 0.26em;
    color: var(--ink-soft);
    /* Grey stock at rest: a sub-tab in the chapter's own colour would compete with the chapter. */
    background: color-mix(in srgb, var(--paper) var(--tab-stock), var(--pencil));
    border: 1px solid color-mix(in srgb, var(--pencil) 40%, var(--rule));
    border-top: none;
    border-radius: 0 0 7px 7px;
    cursor: pointer;
    box-shadow: 2px 2px 3px rgb(0 0 0 / 10%);
  }

  .realms--foot .realm {
    border-top: 1px solid color-mix(in srgb, var(--pencil) 40%, var(--rule));
    border-bottom: none;
    border-radius: 7px 7px 0 0;
    box-shadow: 2px -2px 3px rgb(0 0 0 / 10%);
  }

  .realm:hover {
    background: color-mix(in srgb, var(--paper) calc(var(--tab-stock) - 10%), var(--pencil));
  }

  /* The open realm is cut from the open chapter's stock, which is the whole of how the two levels
     are shown to belong together. `--tint` and `--mix` come from the parent's `tabStyle`. */
  .realm.is-on {
    color: var(--ink);
    background: color-mix(in srgb, var(--paper) calc(var(--mix, 88%) - 6%), var(--tint, var(--pencil)));
    border-color: var(--tint, var(--pencil));
    box-shadow: 2px 3px 5px rgb(0 0 0 / 14%);
  }
</style>
