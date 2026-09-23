<script lang="ts">
  import { legendRows, type DetectabilityDocument } from "../../layers/detectability";

  let {
    doc,
    part = "all",
  }: {
    doc: DetectabilityDocument | null;
    /**
     * Which part. The assessment overflowed an 826px page by 459, and it had a seam already: the
     * cells that could carry a trend, and then the sources held back from the map entirely.
     *
     * `summary` and `sources` are the phone's halves of `measured`. Sixteen rows of a three-column
     * table put it 126px past a 375px leaf, and the table is not the summary -- it is the working
     * behind it, which is exactly the seam.
     *
     * **`measured` still means both**, which is what the spread asks for and what it always meant.
     * Redefining it as the summary alone was the first attempt, and it silently took the table off
     * the desktop's page: the same word for "the whole thing" and "the first half of it" is how a
     * split for one container quietly changes the other.
     */
    part?: "all" | "measured" | "summary" | "sources" | "held" | "held-first" | "held-more";
  } = $props();

  const rows = $derived(doc ? legendRows(doc) : []);

  /*
    Which withheld sources this page carries.

    Both of them and their three paragraphs each ran 66px past a 375px leaf, and a source is the unit
    -- who is held, in plain words why, and then the citation. So the first takes one leaf and the
    rest take the next, which is one page per refusal at today's two.

    `held-first` and not `held`, which was the first attempt and took a source off the *spread*: the
    wide page asks for `held` meaning all of them, and redefining it as the first one silently
    published one refusal where the lake holds two. The same mistake as `measured` and `summary` two
    fields up, made twice in one change -- one word cannot mean both the whole thing and its first
    half, however obvious the shorter name looks.
  */
  const withheld = $derived.by(() => {
    const all = doc?.withheld ?? [];
    if (part === "held-first") return all.slice(0, 1);
    if (part === "held-more") return all.slice(1);
    return all;
  });
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
    {#if part === "all" || part === "measured" || part === "summary"}
    <p class="coverage__lead">
      <strong>{detectable.toFixed(1)}%</strong> of the squares these records cover have been
      counted often enough to show a change. The globe in the last chapter shows where.
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

    {/if}

    {#if part === "all" || part === "measured" || part === "sources"}
    <table class="coverage__sources">
      <caption>Per source, ordered by what it can support</caption>
      <thead>
        <tr><th scope="col">Source</th><th scope="col">Where</th><th scope="col">Best it can do</th></tr>
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
    {/if}

    {#if part === "all" || part === "held" || part === "held-first" || part === "held-more"}
    {#if withheld.length > 0}
      <!--
        Named, not omitted. A map that silently skipped these would read as a map with no wolves in
        it, which is the opposite of true: the lake holds them and will not draw one fix. Listing
        them is also the only way a reader can tell a refusal from a gap in coverage.
      -->
      <!-- The heading only where this rides under a claim. On its own page `book/figures.ts`
           carries the title, and printing it twice is what the first pass did. -->
      <section class="held" aria-labelledby={part === "all" ? "coverage-held" : undefined}>
        {#if part === "all"}
          <h4 id="coverage-held">Held, and never drawn</h4>
        {/if}
        <!-- The count is of every withheld source, not of the ones on this leaf: "1 source is
             classified" printed on each of two pages would be a false statement twice. Printed once,
             on the first of them. -->
        {#if part !== "held-more"}
          <p class="held__lead">
            {doc.withheld.length} source{doc.withheld.length === 1 ? "" : "s"} in these records
            {doc.withheld.length === 1 ? "is" : "are"} classified as high sensitivity. Individual
            locations are withheld entirely — not coarsened, not delayed. Nothing below is on the map.
          </p>
        {/if}
        <ul class="held__list">
          {#each withheld as source (source.source_id)}
            <li>
              <p class="held__who">
                <em>{source.taxon}</em>
                <span class="held__meta">
                  {source.span[0]}–{source.span[1]} · {source.individuals} animals · {source.realm}
                </span>
              </p>
              <p class="held__plain">{source.plain_reason}</p>
              <p class="held__why">{source.reason}</p>
            </li>
          {/each}
        </ul>
        <!-- On the last of them, because it is the closing statement about the refusal. -->
        {#if part !== "held-first"}
          <p class="held__note">
            A trend computed from them may still be reported: a rate of change over a population
            locates no animal. It is the map that is refused, never the finding.
          </p>
        {/if}
      </section>
    {/if}
    {/if}

    <!-- With the summary rather than with the table: it qualifies what the percentage means, and the
         table is the working behind it. -->
    {#if part === "all" || part === "measured" || part === "summary"}
      <p class="coverage__caveat">{doc.caveat}</p>
    {/if}
  </section>
{/if}

<style>
  /*
    Every size here is a multiple of `--size-margin`, not a rem.

    Sized in rem, this component's text neither grew on a tall window nor shrank on a short one, so
    `fit.ts` could scale everything on its page except the words -- and its pages were among the
    last to run off the leaf at 1280x720 and 1024x768. Each factor is the old rem over 0.66, the
    token's root value, so a phone -- which reads the root tokens -- is exactly as it was, and on
    the spread the words follow the page like everything else on it.
  */
  .coverage {
    font-size: calc(var(--size-margin) * 1.21);
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
    font-size: calc(var(--size-margin) * 1.59 * var(--font-scale-hand));
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
    font-size: calc(var(--size-margin) * 1.15);
  }

  .held__note {
    margin: var(--gap) 0 0;
    color: var(--pencil);
    font-size: calc(var(--size-margin) * 1.15);
  }

  .coverage__lead {
    margin: 0;
  }

  .coverage__lead strong {
    font-family: var(--font-mono);
    font-weight: 500;
    font-size: calc(var(--size-margin) * 1.74);
    color: var(--rust);
  }

  .coverage__legend {
    margin: var(--gap) 0 0;
    padding: 0;
    list-style: none;
    font-size: calc(var(--size-margin) * 1.15);
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
    font-size: calc(var(--size-margin) * 1.06);
    color: var(--pencil);
    font-variant-numeric: tabular-nums;
  }

  .coverage__sources {
    width: 100%;
    margin: var(--gap) 0 0;
    border-collapse: collapse;
    font-size: calc(var(--size-margin) * 1.09);
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
    /* In the page's own air rather than 2px: sixteen rows of fixed padding were the last 9px this
       page could not give back at 1024x768. 0.6 of the hairline gap is the same 2px at the
       reference window, and breathes with the page everywhere else. */
    padding: calc(var(--gap-hair) * 0.6) var(--gap-tight) calc(var(--gap-hair) * 0.6) 0;
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
    font-size: calc(var(--size-margin) * 1.06);
    color: var(--ink);
  }

  .coverage__caveat {
    margin: var(--gap) 0 0;
    padding-top: var(--gap-tight);
    border-top: 1px dotted var(--rule);
    font-size: calc(var(--size-margin) * 1.15);
    color: var(--pencil);
  }

  /* This list is the project's ethics in one screen, so the reason leads in plain words and the
     full rationale -- citation and all -- follows it rather than being cut. */
  .held__plain {
    margin: var(--gap-hair) 0 0;
    color: var(--ink);
  }
</style>
