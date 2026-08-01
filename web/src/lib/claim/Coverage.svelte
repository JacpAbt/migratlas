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

    {#if doc.withheld.length > 0}
      <!--
        Named, not omitted. A map that silently skipped these would read as a map with no wolves in
        it, which is the opposite of true: the lake holds them and will not draw one fix. Listing
        them is also the only way a reader can tell a refusal from a gap in coverage.
      -->
      <section class="held" aria-labelledby="coverage-held">
        <h4 id="coverage-held">Held, and never drawn</h4>
        <p class="held__lead">
          {doc.withheld.length} source{doc.withheld.length === 1 ? "" : "s"} in this lake
          {doc.withheld.length === 1 ? "is" : "are"} classified as high sensitivity. Individual
          locations are withheld entirely — not coarsened, not delayed. Nothing below is on the map.
        </p>
        <ul class="held__list">
          {#each doc.withheld as source (source.source_id)}
            <li>
              <p class="held__who">
                <em>{source.taxon}</em>
                <span class="held__meta">
                  {source.span[0]}–{source.span[1]} · {source.individuals} animals · {source.realm}
                </span>
              </p>
              <p class="held__why">{source.reason}</p>
            </li>
          {/each}
        </ul>
        <p class="held__note">
          A trend computed from them may still be reported: a rate of change over a population
          locates no animal. It is the map that is refused, never the finding.
        </p>
      </section>
    {/if}

    <p class="coverage__caveat">{doc.caveat}</p>
  </section>
{/if}

<style>
  .coverage {
    font-size: 0.8rem;
    line-height: 1.5;
  }

  .held {
    margin-top: var(--gap-wide);
    padding: var(--gap);
    border: 1px solid var(--rule);
    /* The same rust edge the ledger gives a refusal, so a reader who has met one recognises this. */
    border-left: 3px solid var(--rust);
    border-radius: var(--radius);
    background: var(--paper-sunken);
  }

  .held h4 {
    margin: 0 0 var(--gap-tight);
    font-family: var(--font-hand);
    font-size: 1.05rem;
    font-weight: 400;
    line-height: var(--leading-hand);
  }

  .held__lead {
    margin: 0;
  }

  .held__list {
    margin: var(--gap) 0 0;
    padding: 0;
    list-style: none;
  }

  .held__list li + li {
    margin-top: var(--gap-tight);
    padding-top: var(--gap-tight);
    border-top: 1px dotted var(--rule);
  }

  .held__who {
    margin: 0;
    font-weight: 600;
  }

  .held__meta {
    margin-left: var(--gap-tight);
    color: var(--pencil);
    font-family: var(--font-mono);
    font-size: var(--size-margin);
    font-weight: 400;
  }

  .held__why {
    margin: var(--gap-hair) 0 0;
    color: var(--ink-soft);
    font-size: 0.76rem;
  }

  .held__note {
    margin: var(--gap) 0 0;
    color: var(--pencil);
    font-size: 0.76rem;
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
