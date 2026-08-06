<script lang="ts">
  import { TaxonIndex, type SpeciesSurfaces, type TaxonHit } from "../../search/taxon";
  import type { SpeciesSelection } from "../../layers/selection";
  import Study from "../species/Study.svelte";
  import { SpeciesStudies, type SpeciesCard } from "../species/study";

  let {
    selection,
    surfaces,
    onfocus,
  }: {
    selection: SpeciesSelection | null;
    surfaces: SpeciesSurfaces;
    onfocus: (at: [number, number]) => void;
  } = $props();

  let index = $state<TaxonIndex | null>(null);
  let query = $state("");
  let chosen = $state<TaxonHit | null>(null);
  let card = $state<SpeciesCard | null>(null);
  let problem = $state<string | null>(null);

  // Fetched on selection, never on search: a keystroke must not cost a shard, and 2.2 MB of study
  // pages has no business loading for a reader who is looking at the globe.
  const studies = $derived(new SpeciesStudies(import.meta.env.BASE_URL));

  $effect(() => {
    TaxonIndex.load(`${import.meta.env.BASE_URL}taxon-index.json`)
      .then((loaded) => (index = loaded))
      .catch(() => (problem = "The species index could not be read."));
  });

  // Every entry has a surface, a study, or both, so a hit is never a dead end.
  const hits = $derived(index && query.trim().length > 1 ? index.search(query) : []);

  async function choose(hit: TaxonHit): Promise<void> {
    if (!selection) return;
    chosen = hit;
    card = null;
    query = "";
    problem = null;

    // A hit may have a study, a surface, or both. An animal measured by a survey has no layer --
    // FISHGLOB is not published as one -- and refusing it here is what left 689 of the 755 species
    // with a distribution shift unreachable from the search box that is meant to find them.
    if (hit.layer) {
      const grid = await surfaces.get(hit);
      if (grid) {
        const { center } = selection.show(hit, grid);
        onfocus(center);
      } else {
        problem = `No published surface for ${hit.scientific}.`;
      }
    } else {
      selection.clear();
    }
    // Awaited after the camera moves, so the globe answers immediately and the page arrives when
    // it arrives. A card that is null renders nothing rather than a spinner: the surface is
    // already the answer to "where", and this is the answer to "and what is known".
    card = await studies.get(hit.key);
  }

  function clear(): void {
    selection?.clear();
    chosen = null;
    card = null;
    problem = null;
  }
</script>

<div class="search">
  <label class="sr-only" for="taxon-search">Search for an animal</label>
  <input
    id="taxon-search"
    type="search"
    autocomplete="off"
    spellcheck="false"
    bind:value={query}
    placeholder={index ? `Search ${index.size.toLocaleString()} animals…` : "Loading…"}
  />

  {#if hits.length > 0}
    <ul class="hits" role="listbox">
      {#each hits as hit (`${hit.key}:${hit.layer}`)}
        <li>
          <button type="button" onclick={() => void choose(hit)}>
            <span class="hits__name">{hit.scientific}</span>
            <span class="hits__common">{hit.vernacular}</span>
            <em>{hit.layer ? `${hit.cells.toLocaleString()} cells` : "study"}</em>
          </button>
        </li>
      {/each}
    </ul>
  {/if}

  {#if chosen}
    <p class="chosen">
      {#if chosen.layer}
        Showing <strong>{chosen.scientific}</strong> from {chosen.layer_title}
      {:else}
        <strong>{chosen.scientific}</strong> — measured here, and drawn nowhere
      {/if}
      <button type="button" class="chosen__clear" onclick={clear}>clear</button>
    </p>
    {#if card}
      <Study {card} />
    {/if}
  {/if}

  {#if problem}
    <p class="problem">{problem}</p>
  {/if}
</div>

<style>
  .search {
    position: relative;
  }

  input {
    width: 100%;
    padding: var(--gap-hair) var(--gap-tight);
    background: var(--paper);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    font-family: var(--font-body);
    font-size: 0.8rem;
    color: var(--ink);
  }

  .hits {
    margin: var(--gap-hair) 0 0;
    padding: 0;
    list-style: none;
    max-height: 12rem;
    overflow-y: auto;
    border: 1px solid var(--rule-faint);
    border-radius: var(--radius);
  }

  .hits button {
    display: grid;
    /* Scientific name, common name, then the cell count. A row keyed on the taxon alone would
       collide: 95 taxa appear in both marine sources, so the layer is part of the identity. */
    grid-template-columns: 1fr auto;
    gap: 0 var(--gap-tight);
    width: 100%;
    padding: 3px var(--gap-tight);
    background: transparent;
    border: 0;
    font-family: inherit;
    font-size: 0.76rem;
    text-align: left;
    color: var(--ink);
    cursor: pointer;
  }

  .hits button:hover {
    background: var(--paper-sunken);
  }

  .hits__name {
    font-style: italic;
  }

  .hits__common {
    grid-column: 1;
    font-size: 0.7rem;
    color: var(--pencil);
  }

  .hits em {
    grid-row: 1 / 3;
    grid-column: 2;
    align-self: center;
    font-family: var(--font-mono);
    font-style: normal;
    font-size: var(--size-label);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--pencil);
  }

  .chosen {
    margin: var(--gap-tight) 0 0;
    font-size: 0.76rem;
    color: var(--ink-soft);
  }

  .chosen strong {
    font-style: italic;
    font-weight: 600;
  }

  .chosen__clear {
    margin-left: var(--gap-tight);
    padding: 0;
    background: none;
    border: 0;
    border-bottom: 1px solid currentColor;
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--rust);
    cursor: pointer;
  }

  .problem {
    margin: var(--gap-tight) 0 0;
    font-size: 0.72rem;
    color: var(--rust);
  }
</style>
