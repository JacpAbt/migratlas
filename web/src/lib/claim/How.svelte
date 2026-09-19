<script lang="ts">
  import Instrument from "../notebook/Instrument.svelte";
  import Rule from "../notebook/Rule.svelte";
  import { SKETCHES } from "../notebook/ink";
  import { instrumentFor, REPOSITORY, type Finding } from "../ledger";

  let { finding, draw = true }: { finding: Finding; draw?: boolean } = $props();

  const instrument = $derived(instrumentFor(finding));
</script>

<!--
  How we found it, which is the register the book was missing.

  The reading order the owner asked for is what we found, then how we found it, then a picture, then
  the numbers -- and between the first and the third there was nothing. A claim went from a plain
  sentence to a plate to a value with an interval, and the only account of the procedure was a link
  to a pre-registration: a filename, which is a claim asking to be taken on trust.

  Its own component rather than another `part` of `Claim`. That component gates its elements with
  `part !== "record"` and `part !== "finding"`, so a third value would have rendered the banner, the
  heading and the caveat on this page as well -- the two-valued switch is load-bearing and adding to
  it is how the third page would have quietly become a copy of the first.

  The method link comes with it. It is the same link the record page carries, and it belongs beside
  the account of the method as well as beside the numbers: the reader who wants the pre-registration
  is the reader who has just read what was done.
-->
<div class="how">
  <p class="how__kicker">How we found it</p>
  <h2 class="how__lead">{finding.plain_how}</h2>
  <Rule seed="how-{finding.key}" {draw} />

  <a class="how__method" href={`${REPOSITORY}${finding.method}`} rel="noopener" target="_blank">
    Method and pre-registration
  </a>

  <!--
    The apparatus, drawn at the foot of the page where somebody would have drawn it.

    This page is a kicker, a few lines and a link, and it measured 44% full across all thirteen
    claims -- the emptiest page in the book after the audit. The fix is not more sentences: the
    owner asked for a notebook, and what a notebook does with a page about how a thing was measured
    is draw the thing. `Claim.svelte` already prints this sketch beside the banner at thumbnail
    size, and this is the same mark given the room the account of it deserves.

    It is also the only drawing the project allows. ADR 0007 decision 5: the radar cannot separate
    birds from bats from insects, so an animal here would contradict the caveat printed two pages
    on. What can be drawn is what did the looking.
  -->
  <figure class="how__sketch">
    <Instrument kind={instrument} />
    <figcaption>{SKETCHES[instrument].label}</figcaption>
  </figure>
</div>

<style>
  .how {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    /* A definite height, so the drawing below has something to be shrunk against. Stretching this
       box does not change what `fit.ts` measures: it counts what a box holds, never the box. */
    height: 100%;
  }

  .how__kicker {
    margin: 0 0 var(--gap-hair);
    font-size: var(--size-label);
    letter-spacing: var(--tracking-label);
    text-transform: uppercase;
    color: var(--moss);
  }

  /*
    The hand, at the size the claim's "why it matters" uses rather than the size of a title.

    This is a paragraph doing a heading's job: it is the only thing on the page, so setting it as
    body text left a page four-fifths empty, and setting it at claim size ran it off the leaf. The
    face is the hand because the register is the plain one -- the same choice `Claim` makes for the
    plain sentence and against the value.
  */
  .how__lead {
    margin: 0;
    font-family: var(--font-hand);
    font-size: calc(1.16rem * var(--font-scale-hand));
    line-height: var(--leading-hand);
    font-weight: 400;
  }

  /* The same three declarations the record page's link carries, including `--rust` rather than
     `--rust-ink`: the ink variant measured 4.03:1 on the day paper against this project's 4.5 floor,
     which the contrast suite said the moment the sample was added to it. */
  /*
    Under the link rather than pushed to the foot, and that is deliberate.

    `margin-top: auto` was the first version and it fought the thing it was added for: a drawing
    pinned to the bottom edge means the page always measures full, so `fit.ts` stops growing the
    text and the gap the drawing was meant to close opens up in the middle instead. Following the
    text means the page fills from the top and the drawing lands wherever the writing ended, which
    is where somebody would have drawn it anyway.
  */
  .how__sketch {
    display: flex;
    flex-direction: column;
    gap: var(--gap-tight);
    align-items: flex-start;
    margin: 0;
    padding-top: var(--gap-wide);
    /* Shrinkable, and that is the whole contract with pagination. The first version drew at a
       fixed fraction of the page and put the longest of the thirteen accounts 82px over its leaf
       -- `pages.ts` had budgeted this panel as text and the drawing was new weight it had never
       been measured with. Rather than budget it, the drawing gives way: somebody with half a page
       left draws it half the size. */
    flex: 0 1 auto;
    min-block-size: 0;
  }

  .how__sketch :global(.instrument) {
    flex: 0 1 auto;
    /* A floor rather than nothing: past about this the radar's dish and its mast are one blot, and
       a drawing nobody can read is worse than the white space it was covering. Below it the page
       overflows instead, which `fit.ts` sees and answers by writing smaller. */
    min-block-size: 3rem;
    /* Height first with the square declared, so shrinking takes the width with it. Sized against
       the book rather than the viewport, the way the type is. */
    block-size: clamp(4rem, calc(var(--book-h, 40rem) / 5.4), 11rem);
    inline-size: auto;
    aspect-ratio: 1;
    /* Nothing in a notebook is square to the page. */
    rotate: -2.4deg;
  }

  .how__sketch figcaption {
    font-family: var(--font-hand);
    font-size: var(--size-margin);
    line-height: var(--leading-hand);
    color: var(--pencil);
  }

  .how__method {
    margin-top: var(--gap-wide);
    font-family: var(--font-mono);
    font-size: var(--size-margin);
    color: var(--rust);
    text-decoration-thickness: 1px;
    text-underline-offset: 3px;
  }
</style>
