<script lang="ts">
  import { REPOSITORY } from "../ledger";
  import Boxed from "../notebook/Boxed.svelte";
  import DrawnLink from "../notebook/DrawnLink.svelte";
  import { format, type Refusal } from "./sandbox";

  let { refusal }: { refusal: Refusal } = $props();

  let shown = $state(false);

  // Every row here is computed over the same 17.2M rows, so printing n four times is noise. Stated
  // once when they agree, per-row when they do not -- because then it is the interesting part.
  const counts = $derived(new Set(refusal.evidence.map((item) => item.n).filter(Boolean)));
  const sharedCount = $derived(counts.size === 1 ? [...counts][0] : null);
  // Written generically once this component picked up a second document. The sentence used to say
  // "All four ... taxon-cell rows", which was true of the one refusal that existed and would have
  // been wrong about any other -- a hardcoded row count and a hardcoded unit, both reachable the
  // moment `response.json` started rendering through here.
  const rowCount = $derived(refusal.evidence.length);
</script>

<!--
  The analysis we refused to run.

  This is the sandbox's most useful entry and the only one that is not a switch: the numbers below are
  real, the naive reading of them is the one most papers in this area would report, and it must not be
  reported, because the dominant confound points the same way as the prediction.

  The naive figure sits behind a click — the one place in this project where something does. Not to
  hide it: it is a claim we say is unsupported, and printing "+4.42° poleward" at full size next to a
  claim card would put a wrong number on the page in the same register as the right ones. The button
  says what it will show, so nothing is concealed, and clicking is the reader choosing to see the
  mistake rather than being shown it as a result.
-->
<section class="refusal">
  <Boxed seed="refusal-{refusal.key}" tone="rust" />
  <p class="refusal__label">The analysis we did not run</p>
  <p class="refusal__question">{refusal.question}</p>
  <p class="refusal__naive">{refusal.naive}</p>

  {#if shown}
    <dl class="refusal__rows">
      {#each refusal.evidence as item (item.key)}
        <dt>{item.label}</dt>
        <dd>
          <span class="refusal__number">{format(item.value, item.unit)}</span>
          {#if item.n && !sharedCount}<em>n = {item.n.toLocaleString()}</em>{/if}
        </dd>
      {/each}
    </dl>
    {#if sharedCount}
      <p class="refusal__n">
        All {rowCount} over the same {sharedCount.toLocaleString()} rows.
      </p>
    {/if}
  {:else}
    <button type="button" onclick={() => (shown = true)}>
      <Boxed seed="refusal-show-{refusal.key}" tone="rust" />
      Show me the wrong answer, and the numbers behind it
    </button>
  {/if}

  <p class="refusal__verdict"><strong>Why it is not reported.</strong> {refusal.verdict}</p>
  <p class="refusal__method">
    <DrawnLink href={`${REPOSITORY}${refusal.method}`} seed="refusal-plan-{refusal.key}">
      The plan, written down before we looked
    </DrawnLink>
  </p>
</section>

<style>
  /*
    Every size here is a multiple of `--size-margin`, not a rem.

    Sized in rem, this component's text neither grew on a tall window nor shrank on a short one, so
    `fit.ts` could scale everything on its page except the words -- and its pages were among the
    last to run off the leaf at 1280x720 and 1024x768. Each factor is the old rem over 0.66, the
    token's root value, so a phone -- which reads the root tokens -- is exactly as it was, and on
    the spread the words follow the page like everything else on it.
  */
  /*
    A scrap of paper laid on the page, turned a little, with its edge drawn in rust.

    It was a callout -- a sunken panel with a coloured left border and rounded corners -- which is the
    one shape on the page that came from an interface rather than a sketchbook; the owner read it as
    computer-made. What it has to say has not changed: it holds a number the project calls wrong, so
    it still sits on a darker sheet than the page, and the rust edge says why at a glance.
  */
  .refusal {
    position: relative;
    rotate: -0.4deg;
    margin-top: var(--gap);
    padding: var(--gap);
    /* Its own ground, and a drawn edge in the accent: this is the one block on the page that
       contains a number we say is wrong, so it should not look like the rest. */
    background: var(--paper-sunken);
  }

  .refusal__label {
    margin: 0;
    font-family: var(--font-body);
    font-size: var(--size-label);
    font-weight: 500;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--rust);
  }

  .refusal__question {
    margin: var(--gap-hair) 0 0;
    font-family: var(--font-hand);
    font-size: calc(var(--size-margin) * 1.97 * var(--font-scale-hand));
    line-height: var(--leading-hand);
    color: var(--ink);
  }

  .refusal__naive {
    margin: var(--gap-tight) 0 0;
    font-size: calc(var(--size-margin) * 1.24);
    line-height: 1.5;
    color: var(--ink-soft);
  }

  /* Drawn round like a knob's setting, and written like everything else a reader is asked to do. */
  button {
    position: relative;
    margin-top: var(--gap-tight);
    padding: 4px var(--gap-tight) 5px;
    background: transparent;
    border: 0;
    font-family: var(--font-body);
    font-size: calc(var(--size-margin) * 1.12);
    color: var(--rust);
    cursor: pointer;
  }

  button:hover {
    color: var(--rust-ink);
  }

  .refusal__rows {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 0 var(--gap-tight);
    margin: var(--gap-tight) 0 0;
    font-size: calc(var(--size-margin) * 1.12);
  }

  dt {
    color: var(--ink-soft);
    line-height: 1.5;
  }

  dd {
    margin: 0;
    text-align: right;
    white-space: nowrap;
  }

  .refusal__number {
    font-family: var(--font-mono);
    color: var(--ink);
    font-variant-numeric: tabular-nums;
  }

  .refusal__n {
    margin: var(--gap-hair) 0 0;
    font-family: var(--font-body);
    font-size: var(--size-label);
    color: var(--pencil);
  }

  .refusal__rows em {
    display: block;
    font-family: var(--font-mono);
    font-style: normal;
    font-size: var(--size-label);
    color: var(--pencil);
  }

  .refusal__verdict {
    margin: var(--gap) 0 0;
    font-size: calc(var(--size-margin) * 1.18);
    line-height: 1.5;
    color: var(--ink);
  }

  .refusal__verdict strong {
    font-weight: 600;
  }

  .refusal__method {
    margin: var(--gap-hair) 0 0;
  }
</style>
