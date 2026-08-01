<script lang="ts">
  import Instrument from "../notebook/Instrument.svelte";
  import Rule from "../notebook/Rule.svelte";
  import Margin from "./Margin.svelte";
  import { DIRECTION_LABEL, instrumentFor, REPOSITORY, type Finding } from "../ledger";

  let { finding, draw = true }: { finding: Finding; draw?: boolean } = $props();

  const instrument = $derived(instrumentFor(finding));
</script>

<!--
  Wrapped so the card is a container query context. The card lives in three places at three
  widths -- a 66rem preview page, a 52rem sheet on a globe, and a phone -- and a media query asks
  about the viewport, not about the room it was given. On a 768px tablet the sheet is 522px while
  the viewport is comfortably past any breakpoint, so the two-column layout squeezed the claim
  body to 230px and wrapped the hand heading over nine lines.
-->
<div class="claim-frame">
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

    <!--
      Two registers, and which one is the heading is the decision. The plain sentence carries the
      finding to a reader with no statistics; `claim` is the scientific statement and is rendered
      here in full, unshortened, immediately under it. ADR 0007 refuses to let the layout decide
      what the science says, and nothing here shortens anything -- a second register was added
      above the first.
    -->
    <h2 class="claim__title">{finding.plain}</h2>
    <Rule seed={finding.key} {draw} />

    <p class="claim__matters">{finding.matters}</p>

    <!--
      The value is mono in every context, no exceptions. ADR 0007: the hand face has no tabular
      figures, so a measurement set in it stops reading as a measurement -- and it never animates
      to its value, because a counting number reads as a score rather than as an interval.
    -->
    <p class="claim__value">{finding.value}</p>
    <p class="claim__short-caveat">{finding.plain_caveat}</p>

    <div class="claim__prose">
      <p class="claim__precise">
        <span class="claim__register">Precisely</span>
        {finding.claim}
      </p>
      <p class="claim__scope">{finding.scope}</p>
      <p class="claim__caveat">{finding.caveat}</p>
    </div>

    <a class="claim__method" href={`${REPOSITORY}${finding.method}`} rel="noopener" target="_blank">
      Method and pre-registration
    </a>
  </div>

  <Margin {finding} />
</article>
</div>

<style>
  .claim-frame {
    container-type: inline-size;
  }

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

  /* Set at body size and full ink. Why a finding is worth knowing is not an aside to it, and
     printing it in the caveat register would say the opposite of what it is for. */
  .claim__matters {
    margin: var(--gap) 0 0;
    font-size: var(--size-body);
    line-height: var(--leading-body);
    max-width: 34rem;
    color: var(--ink);
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

  /* Directly under the number, because that is the thing most likely to be repeated without it.
     Smaller than the body, larger than the margin: a caveat has to arrive with the number, and it
     does not have to arrive at the same size. */
  .claim__short-caveat {
    margin: var(--gap-tight) 0 0;
    max-width: 34rem;
    font-size: 0.85rem;
    line-height: 1.5;
    color: var(--ink-soft);
  }

  .claim__prose {
    margin-top: var(--gap-wide);
    padding-top: var(--gap);
    border-top: 1px dotted var(--rule-faint);
    font-size: var(--size-body);
    line-height: var(--leading-body);
    max-width: 34rem;
  }

  .claim__prose p {
    margin: 0 0 var(--gap-tight);
  }

  /* The exact sentence, kept whole. The label exists so a reader can see this is the same finding
     said again rather than a further one -- without it the two registers read as two claims. */
  .claim__register {
    font-family: var(--font-mono);
    font-size: var(--size-label);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--pencil);
    margin-right: var(--gap-tight);
  }

  .claim__precise {
    color: var(--ink);
  }

  .claim__scope {
    color: var(--ink-soft);
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

  /* Below the width two columns need, the margin goes under the claim -- still always visible,
     still not behind a control. Only its position changes. A container query rather than a media
     query, so it responds to the sheet it is in and not to the size of the screen. */
  @container (max-width: 46rem) {
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
