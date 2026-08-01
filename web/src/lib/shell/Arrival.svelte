<script lang="ts">
  import Instrument from "../notebook/Instrument.svelte";
  import Rule from "../notebook/Rule.svelte";
  import Sheet from "../notebook/Sheet.svelte";
  import { instrumentFor, type Finding } from "../ledger";

  let {
    finding,
    onshow,
    onexplore,
  }: { finding: Finding; onshow: () => void; onexplore: () => void } = $props();
</script>

<!--
  What a visitor lands on: one argument, with the globe already running behind it.

  ADR 0007 decision 3. Deliberately not a map with panels round it, and deliberately not a tour: two
  ways out are offered in the same breath, so the reader who wants the evidence and the reader who
  wants to poke at a globe both get what they came for on the first click.

  The number is here, in full, with its interval. An arrival screen that said "something is changing"
  and made you click for the figure would be doing the opposite of what this project is for.
-->
<section class="arrival" aria-labelledby="arrival-claim">
  <Sheet seed="arrival">
   <div class="arrival__card">
    <header class="arrival__head">
      <Instrument kind={instrumentFor(finding)} size={40} />
      <p class="arrival__kicker">Migratlas · what the radar saw</p>
    </header>

    <h1 id="arrival-claim">{finding.plain}</h1>
    <Rule seed="arrival" />

    <p class="arrival__value">{finding.value}</p>
    <p class="arrival__matters">{finding.matters}</p>

    <div class="arrival__ways">
      <button type="button" class="way way--primary" onclick={onshow}>
        Show me how you know
      </button>
      <button type="button" class="way" onclick={onexplore}> Just let me explore </button>
    </div>

    <!-- The caveat is on the arrival screen too, not one screen later. This is the first number a
         visitor sees and it is the one most likely to be repeated without its qualification.

         The short register here, and the full one on the claim itself. That is not the caveat
         being softened: the plain sentence is the whole of what a first-time reader can carry, and
         a visitor who bounces off fourteen hundred characters leaves with no caveat at all. -->
    <p class="arrival__caveat">{finding.plain_caveat}</p>
   </div>
  </Sheet>
</section>

<style>
  .arrival {
    position: absolute;
    inset: 0;
    z-index: 2;
    display: grid;
    place-items: center;
    padding: var(--gap-wide);
    /* No full-page scrim: the globe should stay legible behind the card, because it is the thing
       the card is about. The card carries its own ground instead. */
    pointer-events: none;
  }

  /* The paper is `Sheet`'s job now -- ground, grain, torn edge, shadow. What is left here is the
     room the words need and the way the leaf lands. */
  .arrival :global(.sheet) {
    pointer-events: auto;
    max-width: 34rem;
    animation: settle var(--draw-slow) var(--ease-pen) both;
  }

  .arrival__card {
    padding: var(--gap-wide) var(--gap-wide) var(--gap-wide) calc(var(--gap-wide) + 0.4rem);
  }

  /* Lands rather than fades: a page put down on a desk. Zeroed with the motion token, where it
     resolves to the end state on the first frame. */
  @keyframes settle {
    from {
      opacity: 0;
      transform: translateY(10px) rotate(-0.35deg);
    }
    to {
      opacity: 1;
      transform: none;
    }
  }

  .arrival__head {
    display: flex;
    align-items: center;
    gap: var(--gap-tight);
  }

  .arrival__kicker {
    margin: 0;
    font-family: var(--font-mono);
    font-size: var(--size-label);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--pencil);
  }

  h1 {
    margin: var(--gap-tight) 0 0;
    font-family: var(--font-hand);
    font-weight: 400;
    font-size: clamp(1.7rem, 1.2rem + 2.2vw, 2.45rem);
    line-height: var(--leading-hand);
    text-wrap: balance;
  }

  .arrival__value {
    margin: var(--gap) 0 0;
    font-family: var(--font-mono);
    font-weight: 500;
    /* Shrinks rather than wrapping. "-0.56 +/- 0.25 days per decade" breaking after "days" put
       "decade" alone on a line, which reads as two facts instead of one measurement. */
    font-size: clamp(1.05rem, 0.7rem + 1.6vw, 1.5rem);
    color: var(--rust);
    font-variant-numeric: tabular-nums;
  }

  .arrival__matters {
    margin: var(--gap-tight) 0 0;
    font-size: var(--size-body);
    line-height: var(--leading-body);
  }

  .arrival__ways {
    display: flex;
    flex-wrap: wrap;
    gap: var(--gap-tight);
    margin-top: var(--gap-wide);
  }

  .way {
    padding: 0.5rem 0.9rem;
    background: transparent;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    font-family: var(--font-mono);
    font-size: 0.78rem;
    color: var(--ink);
    cursor: pointer;
    transition: background-color var(--fade), border-color var(--fade);
  }

  .way:hover {
    background: var(--paper-sunken);
    border-color: var(--pencil);
  }

  .way--primary {
    border-color: var(--rust);
    color: var(--rust);
  }

  .arrival__caveat {
    margin: var(--gap) 0 0;
    padding-top: var(--gap-tight);
    border-top: 1px dotted var(--rule);
    font-size: 0.8rem;
    line-height: 1.5;
    color: var(--ink-soft);
  }

  .arrival__card :global(.rule) {
    max-width: 22rem;
  }

  @media (max-width: 40rem) {
    .arrival {
      /* Top-aligned on a phone: centred, a tall card with a four-line hand heading pushes the
         buttons off the bottom of the viewport. */
      place-items: start center;
      padding: var(--gap);
      overflow-y: auto;
    }

    .arrival__card {
      padding: var(--gap) var(--gap) var(--gap) calc(var(--gap) + 0.4rem);
    }

    /* Full width each, stacked: side by side at this width they were 44px tall and 3px apart, and
       the primary one is the whole point of the screen. */
    .way {
      flex: 1 1 100%;
      text-align: center;
    }
  }
</style>
