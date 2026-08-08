<script lang="ts">
  import Rule from "../notebook/Rule.svelte";
  import { REPOSITORY } from "../ledger";
  import { KIND_LABEL, type SpeciesCard } from "./study";

  let { card }: { card: SpeciesCard } = $props();
</script>

<!--
  One animal's page.

  The globe could already draw a species and could say nothing about it, which is a range map --
  what every other biodiversity site has. This is the half that is ours: a per-species result, with
  the same furniture every claim on this site carries, because a number about one fish deserves the
  audit a number about two thousand of them gets.

  The withheld card is the one worth building this for. It names an animal the lake holds 174,443
  locations of and draws none of, and says why. A page that quietly skipped it would read as a map
  with no wolves in it.
-->
<section class="study" aria-label="What is known about {card.scientific}">
  <header class="study__head">
    <h3>{card.scientific}</h3>
    {#if card.vernacular}<p class="study__common">{card.vernacular}</p>{/if}
  </header>
  <Rule seed={`species-${card.taxon_key}`} tone="pencil" />

  {#each card.studies as study (study.kind + study.source_id)}
    <article class="study__one study__one--{study.kind}">
      <p class="study__kind">{KIND_LABEL[study.kind]}</p>
      <p class="study__headline">{study.headline}</p>
      {#if study.value}<p class="study__value">{study.value}</p>{/if}
      <p class="study__detail">{study.detail}</p>

      {#if study.rows.length > 0}
        <!-- The finding's own argument, and the reason this exists. `marine-null` says surveys
             disagree in direction; until these rows were published the only number on the site was
             the median that averages them out, so a reader had to take the disagreement on trust. -->
        <dl class="study__rows">
          {#each study.rows as row (row.label)}
            <div>
              <dt>{row.label}</dt>
              <dd><span class="study__number">{row.value}</span> <em>{row.detail}</em></dd>
            </div>
          {/each}
        </dl>
      {/if}

      <p class="study__caveat">{study.caveat}</p>
      <a class="study__method" href={`${REPOSITORY}${study.method}`} rel="noopener" target="_blank">
        Method and pre-registration
      </a>
      {#if study.claim}
        <!-- The road back: this card is one line of a published claim's evidence, and until now a
             reader here could not reach the claim it argues for. The hash is the claim's address
             (ADR 0008 §8), so the shell's history handling does the navigation. -->
        <a class="study__claim" href={`#c=${study.claim}`}>Read the claim this evidence feeds</a>
      {/if}
    </article>
  {/each}
</section>

<style>
  .study {
    margin-top: var(--gap);
  }

  .study__head {
    display: flex;
    align-items: baseline;
    gap: var(--gap-tight);
    flex-wrap: wrap;
  }

  h3 {
    margin: 0;
    font-family: var(--font-hand);
    font-weight: 400;
    /* Above the 16px floor the hand face is allowed at, and a scientific name is the one place on
       this page where a hand is more honest than type: it is what a field notebook writes. */
    font-size: 1.15rem;
    line-height: 1.2;
    color: var(--ink);
  }

  .study__common {
    margin: 0;
    font-size: 0.78rem;
    color: var(--ink-soft);
  }

  .study__one {
    margin-top: var(--gap);
  }

  .study__kind {
    margin: 0;
    font-family: var(--font-mono);
    font-size: var(--size-label);
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--pencil);
  }

  /* The refusal is the loudest card on the page, deliberately. It is the one a reader is least
     likely to expect and the one this project most wants them to leave with. */
  .study__one--withheld .study__kind {
    color: var(--rust);
  }

  .study__headline {
    margin: var(--gap-hair) 0 0;
    font-size: 0.86rem;
    line-height: 1.45;
    color: var(--ink);
  }

  .study__value {
    margin: var(--gap-tight) 0 0;
    font-family: var(--font-mono);
    font-weight: 500;
    font-size: 0.95rem;
    color: var(--rust);
    font-variant-numeric: tabular-nums;
  }

  .study__detail,
  .study__caveat {
    margin: var(--gap-tight) 0 0;
    font-size: 0.76rem;
    line-height: 1.5;
    color: var(--ink-soft);
  }

  .study__rows {
    margin: var(--gap-tight) 0 0;
    padding-top: var(--gap-tight);
    border-top: 1px dotted var(--rule-faint);
  }

  .study__rows div {
    display: flex;
    justify-content: space-between;
    gap: var(--gap-tight);
    padding: 1px 0;
  }

  .study__rows dt {
    font-family: var(--font-mono);
    font-size: 0.68rem;
    color: var(--ink-soft);
  }

  .study__rows dd {
    margin: 0;
    text-align: right;
    font-size: 0.68rem;
    color: var(--ink-soft);
  }

  .study__number {
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
    color: var(--ink);
  }

  .study__rows em {
    font-style: normal;
    color: var(--pencil);
  }

  .study__claim {
    display: block;
    margin-top: 0.35rem;
    font-family: var(--font-mono);
    font-size: var(--size-margin);
    color: var(--rust);
    text-underline-offset: 3px;
  }

  .study__method {
    display: inline-block;
    margin-top: var(--gap-tight);
    font-family: var(--font-mono);
    font-size: var(--size-margin);
    color: var(--rust);
    text-underline-offset: 3px;
  }
</style>
