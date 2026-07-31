<script lang="ts">
  import Coverage from "./Coverage.svelte";
  import Ribbon from "./Ribbon.svelte";
  import Rule from "../notebook/Rule.svelte";
  import Sandbox from "../sandbox/Sandbox.svelte";
  import type { DetectabilityDocument } from "../../layers/detectability";
  import type { Finding } from "../ledger";
  import type { SandboxDocument } from "../sandbox/sandbox";

  let {
    finding,
    base,
    detectability,
    sandbox,
  }: {
    finding: Finding;
    base: string;
    detectability: DetectabilityDocument | null;
    sandbox: SandboxDocument | null;
  } = $props();

  /**
   * Which claims have a figure, and what it is.
   *
   * Keyed rather than inferred, and only two entries, because only two claims have a figure that
   * adds something the sentence does not. A chart per claim would be decoration: the marine null and
   * the composition control are both "this number is indistinguishable from zero", and a flat line
   * drawn three times teaches nothing the value already said.
   */
  const FIGURES: Record<string, { kind: "ribbon" | "coverage"; title: string }> = {
    "anthropogenic-share": {
      kind: "ribbon",
      title: "The world without us",
    },
    "coverage-bias": {
      kind: "coverage",
      title: "Where change could be measured",
    },
  };

  const figure = $derived(FIGURES[finding.key]);
</script>

{#if figure}
  <section class="evidence">
    <h3>{figure.title}</h3>
    <Rule seed={`${finding.key}-evidence`} tone="pencil" />
    {#if figure.kind === "ribbon"}
      <Ribbon {base} />
    {:else}
      <Coverage doc={detectability} />
    {/if}
  </section>
{/if}

<!-- Outside the figure block: a claim can have knobs without having a chart, and the two claims with
     the most knobs are exactly the two without one. -->
<Sandbox doc={sandbox} claim={finding.key} />

<style>
  .evidence {
    margin-top: var(--gap-wide);
    padding-top: var(--gap);
    border-top: 1px solid var(--rule);
  }

  h3 {
    margin: 0;
    font-family: var(--font-hand);
    font-weight: 400;
    /* Above the 20px floor ADR 0007 sets for the hand face, and below the claim's own heading so the
       figure reads as part of the claim rather than as a second claim. */
    font-size: 1.35rem;
    line-height: var(--leading-hand);
  }

  .evidence :global(.rule) {
    max-width: 14rem;
    margin-bottom: var(--gap);
  }
</style>
