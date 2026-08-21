<script lang="ts">
  import Knob from "./Knob.svelte";
  import Refusal from "./Refusal.svelte";
  import Rule from "../notebook/Rule.svelte";
  import { dialRefusalsFor, dialsFor, type ResponseDocument } from "./response";

  let { doc, claim }: { doc: ResponseDocument | null; claim: string } = $props();

  const dials = $derived(dialsFor(doc, claim));
  const refusals = $derived(dialRefusalsFor(doc, claim));

  /**
   * Whether any dial is flat, so the lead can say so before the reader starts turning things.
   *
   * A dial whose published setting sits inside its own interval is a driver that measures nothing,
   * and the wind dial is exactly that. Saying it up front is the difference between publishing a
   * null and letting a reader discover a shrug.
   */
  const anyFlat = $derived(
    dials.some((dial) => {
      const published = dial.variants.find((v) => v.key === dial.default);
      return published !== undefined && published.ci95 !== null
        && Math.abs(published.value) < published.ci95;
    }),
  );
</script>

<!--
  The dial: what the fitted response says a different world would look like.

  Every number is read from the fit `anthropogenic-share` already rests on -- nothing is recomputed
  in the browser and nothing is simulated. The two refusals are not decoration: one bounds the dial at
  the range the fit is informed over, and one says plainly that a sensitivity is not a forecast, which
  is a distinction this project spent two phases earning the right to make.
-->
{#if dials.length > 0}
  <section class="response">
    <h3>Turn one thing up, and see what the fit says</h3>
    <Rule seed={`${claim}-response`} tone="pencil" />

    <p class="response__lead">
      These are not predictions. Each setting reads the fitted response <em>backwards through the
      record</em>: what a season like that has been followed by, at these stations, over thirty
      years. What next year holds is a different question, and the last panel below is this
      project refusing to answer it.
      {#if anyFlat}
        One of the dials is flat, and it is published because it is flat — a panel carrying only the
        drivers that worked would be a panel choosing its own story.
      {/if}
    </p>

    {#each dials as dial (dial.key)}
      <Knob knob={dial} />
    {/each}

    {#each refusals as refusal (refusal.key)}
      <Refusal {refusal} />
    {/each}
  </section>
{/if}

<style>
  .response {
    margin-top: var(--gap-wide);
    padding-top: var(--gap);
    border-top: 1px solid var(--rule);
  }

  h3 {
    margin: 0;
    font-family: var(--font-hand);
    font-weight: 400;
    font-size: calc(1.35rem * var(--font-scale-hand));
    line-height: var(--leading-hand);
  }

  .response :global(.rule) {
    max-width: 14rem;
    margin-bottom: var(--gap);
  }

  .response__lead {
    margin: 0 0 var(--gap);
    font-size: 0.82rem;
    line-height: 1.55;
    color: var(--ink-soft);
  }

  .response__lead em {
    font-style: italic;
    color: var(--ink);
  }
</style>
