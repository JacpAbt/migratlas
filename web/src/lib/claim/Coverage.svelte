<script lang="ts">
  import { legendRows, type DetectabilityDocument } from "../../layers/detectability";

  let { doc }: { doc: DetectabilityDocument | null } = $props();

  const rows = $derived(doc ? legendRows(doc) : []);
  const detectable = $derived(rows.find((row) => row.status === "detectable")?.share ?? 0);
</script>

<!--
  The detectability assessment, as the evidence for the coverage-bias claim.

  It belongs here rather than in a floating panel because it *is* that claim's evidence: the claim
  says global extent and measurable change are different data, and this is the number. Four
  unlabelled greys are not a map of anything, so the legend is required, not decorative.
-->
{#if doc}
  <section class="coverage" aria-label="Where change could be measured">
    <p class="coverage__lead">
      <strong>{detectable.toFixed(1)}%</strong> of the cells this lake covers could support a trend.
      Switch the layer on to see where.
    </p>

    <ul class="coverage__legend">
      {#each rows as row (row.status)}
        <li>
          <span class="coverage__swatch" style="background: {row.colour}"></span>
          <span class="coverage__means">{row.means}</span>
          <em>{row.share.toFixed(1)}%</em>
        </li>
      {/each}
    </ul>

    <table class="coverage__sources">
      <caption>Per source, ordered by what it can support</caption>
      <thead>
        <tr><th scope="col">Source</th><th scope="col">Realm</th><th scope="col">Best it can do</th></tr>
      </thead>
      <tbody>
        {#each doc.coverage as source (source.source_id)}
          <tr>
            <th scope="row">{source.source_id}</th>
            <td>{source.realm}</td>
            <td class="coverage__ceiling">{source.ceiling.replace(/-/g, " ")}</td>
          </tr>
        {/each}
      </tbody>
    </table>

    <p class="coverage__caveat">{doc.caveat}</p>
  </section>
{/if}

<style>
  .coverage {
    font-size: 0.8rem;
    line-height: 1.5;
  }

  .coverage__lead {
    margin: 0;
  }

  .coverage__lead strong {
    font-family: var(--font-mono);
    font-weight: 500;
    font-size: 1.15rem;
    color: var(--rust);
  }

  .coverage__legend {
    margin: var(--gap) 0 0;
    padding: 0;
    list-style: none;
    font-size: 0.76rem;
  }

  .coverage__legend li {
    display: flex;
    align-items: baseline;
    gap: var(--gap-tight);
    margin-top: var(--gap-hair);
  }

  .coverage__swatch {
    flex: none;
    width: 0.6rem;
    height: 0.6rem;
    border: 1px solid var(--rule);
    border-radius: 50%;
  }

  .coverage__means {
    flex: 1;
  }

  .coverage__legend em,
  .coverage__ceiling {
    font-family: var(--font-mono);
    font-style: normal;
    font-size: 0.7rem;
    color: var(--pencil);
    font-variant-numeric: tabular-nums;
  }

  .coverage__sources {
    width: 100%;
    margin: var(--gap) 0 0;
    border-collapse: collapse;
    font-size: 0.72rem;
    text-align: left;
  }

  caption {
    margin-bottom: var(--gap-hair);
    font-family: var(--font-mono);
    font-size: var(--size-label);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--pencil);
    text-align: left;
  }

  th,
  td {
    padding: 2px var(--gap-tight) 2px 0;
    border-bottom: 1px dotted var(--rule-faint);
    font-weight: 400;
    vertical-align: top;
  }

  thead th {
    font-family: var(--font-mono);
    font-size: var(--size-label);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--pencil);
  }

  tbody th {
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--ink);
  }

  .coverage__caveat {
    margin: var(--gap) 0 0;
    padding-top: var(--gap-tight);
    border-top: 1px dotted var(--rule);
    font-size: 0.76rem;
    color: var(--pencil);
  }
</style>
