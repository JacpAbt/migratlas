<script lang="ts">
  import Rule from "../notebook/Rule.svelte";
  import type { IntroductionDocument } from "./introduction";

  let {
    document_,
    opening = false,
    from = 0,
    to = 0,
  }: {
    document_: IntroductionDocument | null;
    /** The title, the standfirst and the counted sentence, which belong on one page only. */
    opening?: boolean;
    /** The half-open slice of passages this page carries. */
    from?: number;
    to?: number;
  } = $props();

  const passages = $derived((document_?.passages ?? []).slice(from, to));
</script>

<!--
  The opening spread. Every sentence here comes from `reports/introduction.py` and is rendered
  verbatim: an introduction written in this file would be the one page on the site whose prose
  nothing holds to account.

  Which passages land on which page is `book/pages.ts`, not this component: the introduction runs
  across as many spreads as it has passages, and a component that split them in half would be
  deciding the book's length. Here it renders the slice it is given.
-->
{#if !document_}
  <p class="intro__missing" role="status">The introduction did not load.</p>
{:else}
  {#if opening}
    <p class="intro__kicker">{document_.title}</p>
    <h1 class="intro__standfirst">{document_.standfirst}</h1>
    <Rule seed="introduction" />
    <p class="intro__counted">{document_.counted}</p>
  {/if}

  {#each passages as passage (passage.heading)}
    <section class="intro__passage">
      <h2>{passage.heading}</h2>
      <p>{passage.body}</p>
    </section>
  {/each}
{/if}

<style>
  .intro__missing {
    margin: 0;
    font-size: var(--size-margin);
    color: var(--status-open);
  }

  .intro__kicker {
    margin: 0 0 var(--gap-hair);
    font-size: var(--size-label);
    letter-spacing: var(--tracking-label);
    text-transform: uppercase;
    color: var(--moss);
  }

  .intro__standfirst {
    margin: 0;
    font-family: var(--font-hand);
    font-size: var(--size-claim);
    line-height: var(--leading-hand);
    font-weight: 400;
  }

  /* The counted sentence, in the face that holds a column of figures: three of its numbers are read
     from the ledger on every build, and setting them in a hand would make them look written down. */
  .intro__counted {
    margin: var(--gap) 0 0;
    font-family: var(--font-mono);
    font-size: var(--size-margin);
    color: var(--ink-soft);
  }

  .intro__passage {
    margin-top: var(--gap-wide);
  }

  .intro__passage h2 {
    margin: 0 0 var(--gap-tight);
    font-family: var(--font-hand);
    font-size: calc(1.05rem * var(--font-scale-hand));
    line-height: var(--leading-hand);
    font-weight: 400;
    color: var(--rust);
  }

  .intro__passage p {
    margin: 0;
    font-size: var(--size-body);
  }
</style>
