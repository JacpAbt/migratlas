<script lang="ts">
  import { TaxonIndex, type TaxonHit } from "../../search/taxon";
  import type { Words } from "./data";

  /**
   * The search across every animal with a map or a study (ADR 0021 decision 7). The index is fetched
   * the first time the box is used, not when the atlas opens: 106 KB compressed that a reader
   * watching what moves never needs. `index` is handed out so a caller arriving with a key -- a
   * claim's specimen -- resolves it through the same list a reader's typing does.
   */
  let {
    base,
    said,
    onchoose,
    index = $bindable(null),
  }: {
    base: string;
    said: Words["search"];
    onchoose: (hit: TaxonHit) => void;
    index?: TaxonIndex | null;
  } = $props();

  let query = $state("");
  let problem = $state("");
  let loading: Promise<TaxonIndex | null> | null = null;

  /** The list of animals, fetched once; null if it could not be read, which the box then says. */
  export function load(): Promise<TaxonIndex | null> {
    loading ??= TaxonIndex.load(`${base}taxon-index.json`)
      .then((loaded) => (index = loaded))
      .catch(() => {
        problem = said.unread;
        loading = null;
        return null;
      });
    return loading;
  }

  // Every row has a map, a study or both, so a hit is never a dead end.
  const hits = $derived(index && query.trim().length > 1 ? index.search(query) : []);

  function pick(hit: TaxonHit): void {
    query = "";
    onchoose(hit);
  }
</script>

<div class="find">
  <label for="find-animal">{said.label}</label>
  <input
    id="find-animal"
    type="search"
    autocomplete="off"
    spellcheck="false"
    bind:value={query}
    onfocus={() => void load()}
    placeholder={index ? `${index.animals.toLocaleString("en-GB")} ${said.animals}` : ""}
  />
  {#if hits.length > 0}
    <ul class="hits" aria-label={said.label}>
      {#each hits as hit (`${hit.key}:${hit.layer}`)}
        <li>
          <button type="button" onclick={() => pick(hit)}>
            <span class="hits__name">{hit.scientific}</span>
            {#if hit.vernacular}<span class="hits__common">{hit.vernacular}</span>{/if}
            <em>{hit.layer ? `${hit.cells.toLocaleString("en-GB")} ${said.cells}` : said.study}</em>
          </button>
        </li>
      {/each}
    </ul>
  {/if}
  {#if problem}<p class="find__problem">{problem}</p>{/if}
</div>

<style>
  .find {
    display: grid;
    gap: 0.2em;
    margin-top: 0.4em;
  }

  label {
    color: var(--pencil);
  }

  input {
    font: inherit;
    color: var(--ink);
    background: none;
    border: 0;
    border-bottom: 1px solid color-mix(in srgb, var(--pencil) 70%, transparent);
    padding: 0.15em 0.1em;
    min-width: 0;
  }

  input:focus-visible {
    outline: 1.5px solid var(--rust-ink);
    outline-offset: 2px;
  }

  .hits {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
  }

  .hits button {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 0 0.6em;
    width: 100%;
    font: inherit;
    text-align: left;
    color: var(--ink);
    background: none;
    border: 0;
    padding: 0.15em 0.1em;
    cursor: pointer;
  }

  .hits button:hover,
  .hits button:focus-visible {
    color: var(--rust);
  }

  .hits__name {
    font-style: italic;
  }

  .hits__common {
    grid-column: 1;
    color: var(--ink-soft);
  }

  .hits em {
    grid-column: 2;
    grid-row: 1;
    font-style: normal;
    color: var(--pencil);
    font-variant-numeric: tabular-nums;
  }

  .find__problem {
    margin: 0;
    color: var(--rust);
  }
</style>
