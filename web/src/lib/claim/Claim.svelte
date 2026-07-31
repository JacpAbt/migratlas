<script lang="ts">
  import Instrument from "../notebook/Instrument.svelte";
  import Rule from "../notebook/Rule.svelte";
  import Margin from "./Margin.svelte";
  import { DIRECTION_LABEL, instrumentFor, REPOSITORY, type Finding } from "../ledger";

  let { finding, draw = true }: { finding: Finding; draw?: boolean } = $props();

  const instrument = $derived(instrumentFor(finding));
</script>

<article class="claim claim--{finding.direction}">
  <!--
    The claim and the margin are two cells of a single-row grid, not two columns of a six-row one.
    Spanning the margin across named rows let its height -- which is several times the claim's --
    be distributed back into those rows, opening 300px gaps between the title, the number and the
    prose. A grid row is as tall as its tallest member, and the margin is always the tallest member.
  -->
  <div class="claim__body">
    <header class="claim__head">
      <Instrument kind={instrument} />
      <p class="claim__banner">{DIRECTION_LABEL[finding.direction]}</p>
    </header>

    <h2 class="claim__title">{finding.claim}</h2>
    <Rule seed={finding.key} {draw} />

    <!--
      The value is mono in every context, no exceptions. ADR 0007: the hand face has no tabular
      figures, so a measurement set in it stops reading as a measurement -- and it never animates
      to its value, because a counting number reads as a score rather than as an interval.
    -->
    <p class="claim__value">{finding.value}</p>

    <div class="claim__prose">
      <p class="claim__scope">{finding.scope}</p>
      <p class="claim__caveat">{finding.caveat}</p>
    </div>

    <a class="claim__method" href={`${REPOSITORY}${finding.method}`} rel="noopener" target="_blank">
      Method and pre-registration
    </a>
  </div>

  <Margin {finding} />
</article>

<style>
  .claim {
    display: grid;
    /* The margin is narrower here than the token's default, because inside a sheet on a globe there
       is less room than on a page of its own. Two columns need body + gap + margin to fit, which is
       what the 46rem breakpoint below is measured from. */
    grid-template-columns: minmax(0, 1fr) minmax(15rem, var(--margin-column));
    column-gap: var(--gap-wide);
    align-items: start;
    max-width: 66rem;
  }

  .claim__body {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .claim__head {
    display: flex;
    align-items: center;
    gap: var(--gap-tight);
    margin-bottom: var(--gap-tight);
  }

  .claim__banner {
    margin: 0;
    font-family: var(--font-mono);
    font-size: var(--size-label);
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--pencil);
  }

  /* Colour-coded by whether something changed, and never colour alone -- the banner above says the
     same thing in words. */
  .claim--change .claim__banner {
    color: var(--rust);
  }

  .claim__title {
    margin: 0;
    font-family: var(--font-hand);
    font-weight: 400;
    font-size: var(--size-claim);
    line-height: var(--leading-hand);
    color: var(--ink);
    /* Architects Daughter has the widest metrics of the four candidates tested, so a claim over
       about forty characters wraps. The ledger's `claim` is the scientific statement and stays a
       full sentence, so the layout budgets three lines rather than the sentence being shortened to
       fit -- that would be the layout deciding what the science says. */
    text-wrap: balance;
  }

  .claim__value {
    margin: var(--gap) 0 0;
    font-family: var(--font-mono);
    font-weight: 500;
    font-size: var(--size-value);
    line-height: 1.25;
    color: var(--rust);
    font-variant-numeric: tabular-nums;
  }

  .claim__prose {
    margin-top: var(--gap);
    font-size: var(--size-body);
    line-height: var(--leading-body);
    max-width: 34rem;
  }

  .claim__prose p {
    margin: 0 0 var(--gap-tight);
  }

  .claim__scope {
    color: var(--ink);
  }

  .claim__caveat {
    color: var(--ink-soft);
  }

  .claim__method {
    justify-self: start;
    margin-top: var(--gap-tight);
    font-family: var(--font-mono);
    font-size: var(--size-margin);
    color: var(--rust);
    text-decoration-thickness: 1px;
    text-underline-offset: 3px;
  }

  /* Child components need `:global` to be placed: Svelte scopes styles to the component that
     declares them, so a class on a child's root element is invisible from here without it. The rule
     was silently auto-placed into a row of its own until this existed. */
  /* Child components need `:global` to be reached: Svelte scopes styles to the component that
     declares them, so a class on a child's root element is invisible from here without it. */
  .claim__body :global(.rule) {
    margin-top: var(--gap-hair);
    max-width: 26rem;
  }

  /* On a phone there is no 12.5rem column, so the margin goes below the claim -- still always
     visible, still not behind a control. Only its position changes. */
  @media (max-width: 46rem) {
    .claim {
      grid-template-columns: minmax(0, 1fr);
    }

    .claim :global(.margin) {
      margin-top: var(--gap-wide);
      padding-top: var(--gap);
      border-top: 1px dotted var(--rule);
    }
  }
</style>
