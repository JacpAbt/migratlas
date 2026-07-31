<script lang="ts">
  import RibbonChart from "./RibbonChart.svelte";
  import { frameOf, loadRibbon, type Comparison } from "./ribbon";

  let { base }: { base: string } = $props();

  let doc = $state<Comparison | null>(null);
  let failure = $state<string | null>(null);
  let drawn = $state(false);

  $effect(() => {
    loadRibbon(base)
      .then((loaded) => {
        doc = loaded;
        // Two frames, not one: the first paints the undrawn lines so the transition has a state to
        // start from. Setting it in the same frame makes the browser skip straight to the end.
        requestAnimationFrame(() => requestAnimationFrame(() => (drawn = true)));
      })
      .catch((error: unknown) => (failure = String(error)));
  });

  const frame = $derived(doc ? frameOf(doc) : null);
</script>

<!--
  Two counterfactuals, one chart each, and the reason they disagree.

  The layout carries an argument the charts cannot make on their own. A reader who takes the first
  number and leaves has been misled, so the set is an ordered list -- "1 of 2" is announced, and the
  second chart is visibly there before the first is finished being read. The explanation of the gap
  then sits *after* both, styled as the conclusion rather than as a caveat, because it is the thing
  worth taking away: the distance between two honest answers is itself a measurement.

  Why not one chart with four lines: two of the four would nearly coincide and two would sit far
  apart, which invites a reader to average them. These are different quantities, and an average of
  them answers no question at all.
-->
<div class="pair">
  {#if failure}
    <p class="pair__failure">The counterfactual is unavailable. {failure}</p>
  {:else if doc && frame}
    <ol class="pair__set">
      {#each doc.ribbons as ribbon (ribbon.key)}
        <li>
          <RibbonChart {ribbon} {frame} {drawn} />
        </li>
      {/each}
    </ol>

    <section class="pair__gap" aria-labelledby="ribbon-disagreement">
      <h4 id="ribbon-disagreement">
        {doc.ribbons.length > 1 ? "Why the two answers differ" : "Why there is only one answer"}
      </h4>
      <p>{doc.disagreement}</p>
    </section>

    <p class="pair__caveat">{doc.shared_caveat}</p>

    {#if doc.supporting.length > 0}
      <ul class="pair__supporting">
        {#each doc.supporting as line (line)}
          <li>{line}</li>
        {/each}
      </ul>
    {/if}
  {:else}
    <p class="pair__failure">Reading the counterfactuals…</p>
  {/if}
</div>

<style>
  /* Stacked, never side by side. The claim body is about 31rem wide, so two 640-unit charts beside
     each other would be 240px each -- and stacking is the better comparison anyway: both charts
     share one frame, so a reader compares the two gaps by looking straight down. */
  .pair__set {
    display: grid;
    gap: var(--gap-wide);
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .pair__gap {
    margin-top: var(--gap-wide);
    padding: var(--gap);
    border: 1px solid var(--rule);
    border-left: 3px solid var(--rust);
    border-radius: var(--radius);
    background: var(--paper-sunken);
  }

  .pair__gap h4 {
    margin: 0 0 var(--gap-tight);
    font-family: var(--font-hand);
    font-size: 1.15rem;
    font-weight: 400;
    line-height: var(--leading-hand);
  }

  /* Deliberately larger than the per-chart caveats. It is the conclusion, and setting it at
     footnote size would tell a reader to skip the one paragraph they most need. */
  .pair__gap p {
    margin: 0;
    font-size: var(--size-body);
    line-height: var(--leading-body);
  }

  .pair__caveat {
    margin: var(--gap) 0 0;
    padding-top: var(--gap-tight);
    border-top: 1px dotted var(--rule);
    color: var(--pencil);
    font-size: 0.78rem;
    line-height: 1.5;
  }

  .pair__supporting {
    margin: var(--gap-tight) 0 0;
    padding-left: 1.1rem;
    color: var(--pencil);
    font-size: 0.76rem;
    line-height: 1.5;
  }

  .pair__supporting li {
    margin-top: var(--gap-hair);
  }

  .pair__failure {
    margin: 0;
    font-family: var(--font-mono);
    font-size: var(--size-margin);
    color: var(--pencil);
  }
</style>
