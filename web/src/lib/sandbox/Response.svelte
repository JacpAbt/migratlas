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
     *
     * Or on a page of its own: `lead` is the heading and that paragraph and nothing else, and
     * `apart` tells the first knob its lead already has one. Only the roomy spread asks for either.
     */
    slice?: { kind: "lead" | "knob" | "refusal"; at: number; apart?: boolean } | null;
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

    {#if part !== "refusals" && (!slice || slice.kind === "lead" || (slice.at === 0 && !slice.apart))}
      <p class="response__lead">
        These are not predictions. Each setting reads the fitted response <em>backwards through the
        record</em>: what a season like that has been followed by, at these stations, over thirty
        years. What next year holds is a different question, and the {part === "all"
          ? "last panel below"
          : slice?.kind === "lead"
            ? "page after the dials"
            : "facing page"} is this project refusing to answer it.
        {#if anyFlat}
          One of the dials is flat, and it is published because it is flat — a panel carrying only
          the drivers that worked would be a panel choosing its own story.
        {/if}
      </p>
    {/if}

    {#each part === "refusals" || slice?.kind === "lead" ? [] : slice ? dials.slice(slice.at, slice.at + 1) : dials as dial (dial.key)}
      <Knob knob={dial} />
    {/each}

    {#each part === "knobs" ? [] : slice ? refusals.slice(slice.at, slice.at + 1) : refusals as refusal (refusal.key)}
      <Refusal {refusal} />
    {/each}
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
  .response {
    margin-top: var(--gap-wide);
    padding-top: var(--gap);
    border-top: 1px solid var(--rule);
  }

  /*
    Except where it opens the page, which in the book is every time.

    The margin parts this section from the claim above it, which is what `claim/Evidence.svelte`
    mounts it under; a leaf that begins with it has nothing above to part it from, and the gap was
    the page's own head margin paid twice. It was also the difference on the one knob page the
    dyslexia setting could not fit at 1024x768 -- 13px over at the floor of the fit.
  */
  .response:first-child {
    margin-top: 0;
  }

  h3 {
    margin: 0;
    font-family: var(--font-hand);
    font-weight: 400;
    font-size: calc(var(--size-margin) * 2.05 * var(--font-scale-hand));
    line-height: var(--leading-hand);
  }

  .response :global(.rule) {
    max-width: 14rem;
    margin-bottom: var(--gap);
  }

  .response__lead {
    margin: 0 0 var(--gap);
    font-size: calc(var(--size-margin) * 1.24);
    line-height: 1.55;
    color: var(--ink-soft);
  }

  .response__lead em {
    font-style: italic;
    color: var(--ink);
  }
</style>
