<script lang="ts">
  import Knob from "./Knob.svelte";
  import Refusal from "./Refusal.svelte";
  import Rule from "../notebook/Rule.svelte";
  import { knobsFor, refusalsFor, type SandboxDocument } from "./sandbox";

  let {
    doc,
    claim,
    part = "all",
    slice = null,
  }: {
    doc: SandboxDocument | null;
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

  const knobs = $derived(knobsFor(doc, claim));
  const refusals = $derived(refusalsFor(doc, claim));
  const anyLarger = $derived(
    knobs.some((knob) => {
      const published = knob.variants.find((v) => v.key === knob.default);
      return (
        published &&
        knob.variants.some((v) => v.key !== knob.default && Math.abs(v.value) > Math.abs(published.value))
      );
    }),
  );
</script>

{#if (part !== "refusals" && knobs.length > 0) || (part !== "knobs" && refusals.length > 0)}
  <section class="sandbox">
    <h3>
      {part === "refusals" ? "And what we would not compute" : "Switch the safeguards off"}
    </h3>
    <Rule seed={`${claim}-sandbox`} tone="pencil" />

    {#if part !== "refusals" && knobs.length > 0}
      {#if !slice || slice.at === 0}
      <p class="sandbox__lead">
        Every setting below is a real run on the real data, with one parameter changed.
        {#if anyLarger}
          Worth noticing before you start: some of these make the effect <em>larger</em>, not
          smaller. The published number is the cautious one among defensible choices, which is not
          the story this kind of panel usually tells.
        {/if}
      </p>
      {/if}

      {#each slice ? knobs.slice(slice.at, slice.at + 1) : knobs as knob (knob.key)}
        <Knob {knob} />
      {/each}
    {/if}

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
  .sandbox {
    margin-top: var(--gap-wide);
    padding-top: var(--gap);
    border-top: 1px solid var(--rule);
  }

  h3 {
    margin: 0;
    font-family: var(--font-hand);
    font-weight: 400;
    font-size: calc(var(--size-margin) * 2.05 * var(--font-scale-hand));
    line-height: var(--leading-hand);
  }

  .sandbox :global(.rule) {
    max-width: 14rem;
    margin-bottom: var(--gap);
  }

  .sandbox__lead {
    margin: 0 0 var(--gap);
    font-size: calc(var(--size-margin) * 1.24);
    line-height: 1.55;
    color: var(--ink-soft);
  }

  .sandbox__lead em {
    font-style: italic;
    color: var(--ink);
  }
</style>
