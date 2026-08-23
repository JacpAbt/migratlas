<script lang="ts">
  import Knob from "./Knob.svelte";
  import Refusal from "./Refusal.svelte";
  import Rule from "../notebook/Rule.svelte";
  import { dialRefusalsFor, dialsFor, type ResponseDocument } from "./response";

  let {
    doc,
    claim,
    part = "all",
    slice = null,
  }: {
    doc: ResponseDocument | null;
    claim: string;
    /**
     * Which half of the panel to render.
     *
     * "all" is the whole panel under a claim, which is what `claim/Evidence.svelte` mounts. The book
     * takes it in two because it does not fit a page: measured at 1600x900 the safeguards ran 890 to
     * 1,178px and the dial 1,762px against an 826px page, so the knobs take the left leaf and the
     * refusals the right. Nothing is hidden by either -- both halves are always in the book, one
     * page apart.
     */
    part?: "all" | "knobs" | "refusals";
    /**
     * One item per page, which is what a page turned out to hold.
     *
     * Measured at 1600x900 against an 826px page: three safeguard knobs came to 1,306px and two
     * dials to 1,173px, so roughly 435 and 586 each -- two on a page overflows either way. The lead
     * paragraph rides with the first knob only, because repeating it on every leaf would be four
     * copies of the same sentence in one chapter.
     */
    slice?: { kind: "knob" | "refusal"; at: number } | null;
  } = $props();

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
{#if (part !== "refusals" && dials.length > 0) || (part !== "knobs" && refusals.length > 0)}
  <section class="response">
    <h3>
      {part === "refusals"
        ? "And what this will not be turned into"
        : "Turn one thing up, and see what the fit says"}
    </h3>
    <Rule seed={`${claim}-response`} tone="pencil" />

    {#if part !== "refusals" && (!slice || slice.at === 0)}
      <p class="response__lead">
        These are not predictions. Each setting reads the fitted response <em>backwards through the
        record</em>: what a season like that has been followed by, at these stations, over thirty
        years. What next year holds is a different question, and the {part === "all"
          ? "last panel below"
          : "facing page"} is this project refusing to answer it.
        {#if anyFlat}
          One of the dials is flat, and it is published because it is flat — a panel carrying only
          the drivers that worked would be a panel choosing its own story.
        {/if}
      </p>
    {/if}

    {#each part === "refusals" ? [] : slice ? dials.slice(slice.at, slice.at + 1) : dials as dial (dial.key)}
      <Knob knob={dial} />
    {/each}

    {#each part === "knobs" ? [] : slice ? refusals.slice(slice.at, slice.at + 1) : refusals as refusal (refusal.key)}
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
