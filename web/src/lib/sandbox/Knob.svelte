<script lang="ts">
  import { REPOSITORY } from "../ledger";
  import { compare, format, type Knob } from "./sandbox";

  let { knob }: { knob: Knob } = $props();

  let chosen = $state(knob.default);

  const variant = $derived(
    knob.variants.find((candidate) => candidate.key === chosen) ?? knob.variants[0]!,
  );
  const against = $derived(compare(knob, variant));
  const published = $derived(chosen === knob.default);
</script>

<!--
  One safeguard, switchable, on real data.

  Every value was produced by a real run of the reports' own functions with one parameter changed --
  `reports/sandbox.py` -- so this selects between numbers rather than simulating them. The published
  setting is marked as such, and the difference is stated in words as well as in digits, because
  "the number moved" is not the interesting part. Which direction it moved is.
-->
<div class="knob">
  <p class="knob__question">{knob.question}</p>

  <div class="knob__switch" role="radiogroup" aria-label={knob.question}>
    {#each knob.variants as option (option.key)}
      <label class="option" class:option--on={chosen === option.key}>
        <input type="radio" name={knob.key} value={option.key} bind:group={chosen} />
        <span>{option.label}</span>
        {#if option.key === knob.default}
          <em>published</em>
        {/if}
      </label>
    {/each}
  </div>

  <p class="knob__value" class:knob__value--alternative={!published}>
    {format(variant.value, variant.unit)}
  </p>

  {#if against}
    <p class="knob__delta">
      {format(against.delta, variant.unit)} against the published setting —
      <strong>{against.phrase}</strong>.
    </p>
  {:else}
    <p class="knob__delta knob__delta--published">This is the setting the claim is published at.</p>
  {/if}

  {#if variant.note}
    <p class="knob__note">{variant.note}</p>
  {/if}

  <p class="knob__why">{knob.why}</p>
  <p class="knob__source">
    <a href={`${REPOSITORY}src/migratlas/reports/sandbox.py`} rel="noopener" target="_blank">
      <code>{knob.source}</code>
    </a>
  </p>
</div>

<style>
  .knob {
    padding-top: var(--gap);
    border-top: 1px dotted var(--rule);
  }

  .knob__question {
    margin: 0;
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--ink);
  }

  .knob__switch {
    display: flex;
    flex-wrap: wrap;
    gap: var(--gap-tight);
    margin-top: var(--gap-tight);
  }

  .option {
    display: flex;
    align-items: baseline;
    gap: 0.3rem;
    padding: 2px var(--gap-tight);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--ink-soft);
    cursor: pointer;
  }

  .option:hover {
    background: var(--paper-sunken);
  }

  /* Marked by a drawn edge in the accent rather than a fill, so the published setting stays
     identifiable as *published* rather than as merely selected. */
  .option--on {
    border-color: var(--rust-ink);
    background: var(--paper-sunken);
    color: var(--ink);
  }

  /* The radio itself is the accessible control and the label is the visible one, so it is hidden
     rather than removed -- keyboard and screen-reader users get the real radiogroup. */
  .option input {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
  }

  .option em {
    font-style: normal;
    font-size: var(--size-label);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--rust);
  }

  .knob__value {
    margin: var(--gap-tight) 0 0;
    font-family: var(--font-mono);
    font-weight: 500;
    font-size: 1.25rem;
    color: var(--rust);
    font-variant-numeric: tabular-nums;
  }

  /* An alternative reads in ink, not the accent: only the published number gets to look published. */
  .knob__value--alternative {
    color: var(--ink);
  }

  .knob__delta {
    margin: 1px 0 0;
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--ink-soft);
  }

  .knob__delta strong {
    font-weight: 500;
    color: var(--ink);
  }

  .knob__delta--published {
    color: var(--pencil);
  }

  .knob__note,
  .knob__why {
    margin: var(--gap-tight) 0 0;
    font-size: 0.76rem;
    line-height: 1.5;
    color: var(--pencil);
  }

  .knob__source {
    margin: var(--gap-hair) 0 0;
    font-size: 0.7rem;
  }

  code {
    font-family: var(--font-mono);
    font-size: 0.68rem;
  }
</style>
