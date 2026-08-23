<script lang="ts">
  import Rule from "../notebook/Rule.svelte";
  import { REPOSITORY, type Finding } from "../ledger";

  let { finding, draw = true }: { finding: Finding; draw?: boolean } = $props();
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
</div>

<style>
  .how {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
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
  .how__method {
    margin-top: var(--gap-wide);
    font-family: var(--font-mono);
    font-size: var(--size-margin);
    color: var(--rust);
    text-decoration-thickness: 1px;
    text-underline-offset: 3px;
  }
</style>
