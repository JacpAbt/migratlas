<script lang="ts">
  import Knob from "./Knob.svelte";
  import Refusal from "./Refusal.svelte";
  import Rule from "../notebook/Rule.svelte";
  import { knobsFor, refusalsFor, type SandboxDocument } from "./sandbox";

  let { doc, claim }: { doc: SandboxDocument | null; claim: string } = $props();

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

{#if knobs.length > 0 || refusals.length > 0}
  <section class="sandbox">
    <h3>Switch the safeguards off</h3>
    <Rule seed={`${claim}-sandbox`} tone="pencil" />

    {#if knobs.length > 0}
      <p class="sandbox__lead">
        Every setting below is a real run on the real data, with one parameter changed.
        {#if anyLarger}
          Worth noticing before you start: some of these make the effect <em>larger</em>, not
          smaller. The published number is the cautious one among defensible choices, which is not
          the story this kind of panel usually tells.
        {/if}
      </p>

      {#each knobs as knob (knob.key)}
        <Knob {knob} />
      {/each}
    {/if}

    {#each refusals as refusal (refusal.key)}
      <Refusal {refusal} />
    {/each}
  </section>
{/if}

<style>
  .sandbox {
    margin-top: var(--gap-wide);
    padding-top: var(--gap);
    border-top: 1px solid var(--rule);
  }

  h3 {
    margin: 0;
    font-family: var(--font-hand);
    font-weight: 400;
    font-size: 1.35rem;
    line-height: var(--leading-hand);
  }

  .sandbox :global(.rule) {
    max-width: 14rem;
    margin-bottom: var(--gap);
  }

  .sandbox__lead {
    margin: 0 0 var(--gap);
    font-size: 0.82rem;
    line-height: 1.55;
    color: var(--ink-soft);
  }

  .sandbox__lead em {
    font-style: italic;
    color: var(--ink);
  }
</style>
