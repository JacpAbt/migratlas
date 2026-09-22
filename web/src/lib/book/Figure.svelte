<script lang="ts">
  import Plate from "./Plate.svelte";
  import Coverage from "../claim/Coverage.svelte";
  import Headline from "../claim/Headline.svelte";
  import Ribbon from "../claim/Ribbon.svelte";
  import { headlineOf, loadHeadlines, type HeadlineDocument } from "../claim/headline";
  import Rule from "../notebook/Rule.svelte";
  import { FIGURES, figurePages } from "./figures";
  import { loadDetectability, type DetectabilityDocument } from "../../layers/detectability";
  import type { Finding } from "../ledger";

  let {
    finding,
    number,
    base,
    at = 0,
    narrow = false,
  }: {
    finding: Finding;
    number: number;
    base: string;
    /** Which of the figure's declared pages. A plate has only the one. */
    at?: number;
    /*
      Which list `at` indexes, which is the container's to say.

      `figures.ts` declares a narrow page list for the two figures that do not fit a 375px column, so
      the same index means a different page on a phone -- and resolving it against the wide list there
      would render the reading where the sources belong. `Reader` knows which container is mounted;
      this component does not, and should not have to guess from a media query it cannot see.
    */
    narrow?: boolean;
  } = $props();

  const declared = $derived(figurePages(finding.key, narrow));
  const leaf = $derived(declared[at] ?? declared[0]!);

  /** Which chart, counting only the chart pages before this one. */
  const chart = $derived(declared.slice(0, at).filter((page) => page.part === "chart").length);

  const figure = $derived(FIGURES[finding.key]);

  /*
    Fetched here rather than at boot, and this component only exists while the chapter that needs it
    is open — so the fetch is naturally lazy. That matters: `detectability.json` is about 460 KB,
    nearly all of it the fifty thousand grid cells the map wash draws, and this page wants four
    percentages out of it. Paying that on every chapter would be paying it mostly for nothing.
  */
  let assessment = $state<DetectabilityDocument | null>(null);
  let failed = $state(false);

  $effect(() => {
    if (figure?.kind !== "coverage") return;
    loadDetectability(base)
      .then((loaded) => (assessment = loaded))
      .catch(() => (failed = true));
  });

  /*
    The headline document, fetched the same lazy way and for the same reason: it is wanted by nine
    claim pages and by nothing else. A failure to load, or a claim the analyses withheld, leaves
    the page as it was before charts existed -- the plate alone -- rather than blank.
  */
  let headlines = $state<HeadlineDocument | null>(null);
  let headlinesSettled = $state(false);

  $effect(() => {
    if (figure?.kind !== "headline") return;
    loadHeadlines(base)
      .then((loaded) => (headlines = loaded))
      .catch(() => undefined)
      .finally(() => (headlinesSettled = true));
  });

  const drawn = $derived(figure?.kind === "headline" ? headlineOf(headlines, finding.key) : null);
</script>

<!--
  The facing page's figure.

  A book spread puts the argument on the left and the figure on the right, so this is whichever
  figure the chapter's claim actually has: the counterfactual ribbon, the coverage assessment, or —
  where the claim has neither — the drawn plate saying where on Earth it is.
-->
{#if figure?.kind === "headline"}
  <!--
    The result, drawn, and the plate under it smaller and more crooked: a notebook page with a
    chart on it and the map of where it was measured taped in below. Until the document arrives
    the page waits rather than showing a plate that will jump; if it never arrives, or the claim
    has no chart, the plate takes the page as it always did.
  -->
  <section class="figure figure--headline">
    {#if drawn}
      <Headline headline={drawn} />
      <Plate {finding} {number} {base} compact />
    {:else if headlinesSettled}
      <Plate {finding} {number} {base} />
    {:else}
      <p class="figure__waiting" role="status">Drawing the result…</p>
    {/if}
  </section>
{:else if figure}
  <section class="figure">
    <h2>{leaf.title}</h2>
    <Rule seed={`${finding.key}-figure`} tone="pencil" />
    {#if figure.kind === "ribbon"}
      <Ribbon {base} part={leaf.part} at={chart} />
    {:else if assessment}
      <Coverage doc={assessment} part={leaf.part} />
    {:else if failed}
      <p class="figure__failure" role="status">The coverage assessment did not load.</p>
    {:else}
      <p class="figure__waiting" role="status">Reading the coverage assessment…</p>
    {/if}
  </section>
{:else}
  <Plate {finding} {number} {base} />
{/if}

<style>
  .figure {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .figure--headline {
    gap: var(--gap);
  }

  h2 {
    margin: 0;
    font-family: var(--font-hand);
    font-weight: 400;
    /* Above ADR 0007's 20px floor for the hand face, and below the claim's own heading, so the
       figure reads as part of the claim rather than as a second claim. */
    font-size: 1.35rem;
    line-height: var(--leading-hand);
  }

  .figure :global(.rule) {
    max-width: 14rem;
    margin-bottom: var(--gap);
  }

  .figure__failure {
    margin: 0;
    font-size: var(--size-margin);
    color: var(--status-open);
  }

  .figure__waiting {
    margin: 0;
    font-size: var(--size-margin);
    color: var(--ink-soft);
  }
</style>
