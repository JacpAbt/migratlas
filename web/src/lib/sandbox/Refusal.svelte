<script lang="ts">
  import { REPOSITORY } from "../ledger";
  import { format, type Refusal } from "./sandbox";

  let { refusal }: { refusal: Refusal } = $props();

  let shown = $state(false);

  // Every row here is computed over the same 17.2M rows, so printing n four times is noise. Stated
  // once when they agree, per-row when they do not -- because then it is the interesting part.
  const counts = $derived(new Set(refusal.evidence.map((item) => item.n).filter(Boolean)));
  const sharedCount = $derived(counts.size === 1 ? [...counts][0] : null);
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
      <p class="refusal__n">All four over the same {sharedCount.toLocaleString()} taxon-cell rows.</p>
    {/if}
  {:else}
    <button type="button" onclick={() => (shown = true)}>
      Show me the wrong answer, and the numbers behind it
    </button>
  {/if}

  <p class="refusal__verdict"><strong>Why it is not reported.</strong> {refusal.verdict}</p>
  <p class="refusal__method">
    <a href={`${REPOSITORY}${refusal.method}`} rel="noopener" target="_blank">
      {refusal.method}
    </a>
  </p>
</section>

<style>
  .refusal {
    margin-top: var(--gap);
    padding: var(--gap);
    /* Its own ground, and a drawn edge in the accent: this is the one block on the page that
       contains a number we say is wrong, so it should not look like the rest. */
    background: var(--paper-sunken);
    border-left: 2px solid var(--rust-ink);
    border-radius: 0 var(--radius) var(--radius) 0;
  }

  .refusal__label {
    margin: 0;
    font-family: var(--font-mono);
    font-size: var(--size-label);
    font-weight: 500;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--rust);
  }

  .refusal__question {
    margin: var(--gap-hair) 0 0;
    font-family: var(--font-hand);
    font-size: calc(1.3rem * var(--font-scale-hand));
    line-height: var(--leading-hand);
    color: var(--ink);
  }

  .refusal__naive {
    margin: var(--gap-tight) 0 0;
    font-size: 0.82rem;
    line-height: 1.5;
    color: var(--ink-soft);
  }

  button {
    margin-top: var(--gap-tight);
    padding: 3px var(--gap-tight);
    background: transparent;
    border: 1px solid var(--rust-ink);
    border-radius: var(--radius);
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--rust);
    cursor: pointer;
  }

  button:hover {
    background: var(--paper);
  }

  .refusal__rows {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 0 var(--gap-tight);
    margin: var(--gap-tight) 0 0;
    font-size: 0.74rem;
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
    font-family: var(--font-mono);
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
    font-size: 0.78rem;
    line-height: 1.5;
    color: var(--ink);
  }

  .refusal__verdict strong {
    font-weight: 600;
  }

  .refusal__method {
    margin: var(--gap-hair) 0 0;
    font-family: var(--font-mono);
    font-size: 0.68rem;
  }
</style>
