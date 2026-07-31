<script lang="ts">
  import { TaxonIndex, type SpeciesSurfaces, type TaxonHit } from "../../search/taxon";
  import type { SpeciesSelection } from "../../layers/selection";

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
  let problem = $state<string | null>(null);

  $effect(() => {
    TaxonIndex.load(`${import.meta.env.BASE_URL}taxon-index.json`)
      .then((loaded) => (index = loaded))
      .catch(() => (problem = "The species index could not be read."));
  });

  // Every entry in the index has a published surface behind it, so a hit is never a dead end.
  const hits = $derived(index && query.trim().length > 1 ? index.search(query) : []);

  async function choose(hit: TaxonHit): Promise<void> {
    if (!selection) return;
    const grid = await surfaces.get(hit);
    if (!grid) {
      problem = `No published surface for ${hit.scientific}.`;
      return;
    }
    const { center } = selection.show(hit, grid);
    chosen = hit;
    query = "";
    onfocus(center);
  }

  function clear(): void {
    selection?.clear();
    chosen = null;
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
            <em>{hit.cells.toLocaleString()} cells</em>
          </button>
        </li>
      {/each}
    </ul>
  {/if}

  {#if chosen}
    <p class="chosen">
      Showing <strong>{chosen.scientific}</strong> from {chosen.layer_title}
      <button type="button" class="chosen__clear" onclick={clear}>clear</button>
    </p>
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
