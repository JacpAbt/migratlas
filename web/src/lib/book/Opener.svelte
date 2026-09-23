<!--
  The leaf a chapter opens on: its question, and the argument that answers it before any claim does.

  Set as a question and a paragraph rather than as a heading and body text, because the question is
  the thing a reader is holding when they arrive and the chapter title is only its subject. The
  fore-edge tab says "Where"; this leaf says "Are the places changing, and do they follow the
  warming?" and then answers it in a voice, with the ledger's own numbers inside the sentences.

  No figure, no claim and no number on this leaf on purpose. It is the one page in each chapter that
  is argument rather than evidence, and putting a number's picture beside it would invite a reader
  to check the argument against one claim instead of against the chapter. The values used to close
  the leaf as a mono block of `key — value` lines; that was the first number a reader met in every
  chapter, and it read as code. They are on the record pages, where a reader looking for them looks.

  What closes the leaf instead is drawn: the instruments the chapter's claims were measured with,
  a little crooked at the foot with a pencil caption each, which is what a notebook does with the
  bottom of a page. The only drawing the project allows is the apparatus (ADR 0007 decision 5), so
  these are `notebook/ink.ts`'s sketches and nothing new -- and they say something true about the
  chapter: what did the looking.
-->
<script lang="ts">
  import Instrument from "../notebook/Instrument.svelte";
  import { SKETCHES } from "../notebook/ink";
  import type { ChapterOpener } from "./chapters";
  import type { Instrument as Kind } from "../ledger";

  const {
    chapter,
    opener,
    from,
    to,
    instruments = [],
  }: {
    chapter: string;
    opener: ChapterOpener;
    from: number;
    to: number;
    /** What the chapter's claims were measured with, each once. Drawn on the closing leaf. */
    instruments?: Kind[];
  } = $props();

  const shown = $derived(opener.paragraphs.slice(from, to));
  /* The question heads the account, so it belongs on the leaf the account starts on; the
     drawings close it, so they belong on the leaf it ends on. */
  const opens = $derived(from === 0);
  const closes = $derived(to >= opener.paragraphs.length);

  /*
    Nothing in a notebook is square to the page. Each kind leans its own way and sits its own
    height, fixed per kind rather than random so the leaf is the same on every visit.
  */
  const LEAN: Record<Kind, number> = { radar: -6, trawl: 5, route: -4, grid: 7 };
  const DROP: Record<Kind, number> = { radar: 0, trawl: 0.7, route: 0.35, grid: 0.9 };
</script>

<article class="opener">
  <p class="opener__chapter">{chapter}</p>
  {#if opens}
    <h2 class="opener__question">{opener.question}</h2>
  {/if}
  {#each shown as paragraph (paragraph)}
    <p class="opener__body">{paragraph}</p>
  {/each}
  {#if closes && instruments.length > 0}
    <figure class="opener__doodles" aria-label="What this chapter's claims were measured with">
      {#each instruments as kind (kind)}
        <div class="doodle" style="--lean: {LEAN[kind]}deg; --drop: {DROP[kind]}rem">
          <Instrument {kind} />
          <figcaption>{SKETCHES[kind].label}</figcaption>
        </div>
      {/each}
    </figure>
  {/if}
</article>

<style>
  .opener {
    display: flex;
    flex-direction: column;
    gap: 0.9rem;
    height: 100%;
    justify-content: center;
    padding: 0 0.4rem;
  }

  /*
    Sized against the book like every other panel. These three were hardcoded in rem and read
    about 13% larger than their neighbours on a 1280x800 window, where every other panel had
    scaled down with the page; the drawing at the foot would have overflowed exactly there.
  */
  .opener__chapter {
    color: var(--ink-faint);
    flex: none;
    font-size: calc(var(--size-label) * 1.15);
    letter-spacing: 0.09em;
    margin: 0;
    text-transform: uppercase;
  }

  .opener__question {
    flex: none;
    font-size: calc(var(--size-body) * 1.42);
    font-weight: 600;
    line-height: 1.25;
    margin: 0;
    text-wrap: balance;
  }

  /*
    Wider measure and a larger size than a record page, because this is the one leaf meant to be
    read straight through rather than consulted. The first line is not indented -- nothing precedes
    it -- and the paragraph carries its own leading rather than the book's tighter default.
    `flex: none` so that when the leaf is tight it is the drawing below that gives way, never the
    words.
  */
  .opener__body {
    flex: none;
    font-size: calc(var(--size-body) * 1.03);
    line-height: 1.6;
    margin: 0;
    text-align: justify;
    hyphens: auto;
  }

  /*
    The drawings, in flow under the words rather than pinned to the foot: `How.svelte` found that
    a drawing pinned to the bottom edge makes the page measure full, so `fit.ts` stops growing the
    text and the gap opens in the middle instead. Shrinkable, with a floor, for the same reason
    its sketch is: somebody with half a page left draws it half the size.
  */
  .opener__doodles {
    display: flex;
    flex: 0 1 auto;
    min-block-size: 0;
    justify-content: space-around;
    align-items: flex-end;
    gap: var(--gap-wide);
    margin: 0;
    padding: var(--gap-wide) var(--gap) 0;
  }

  .doodle {
    display: flex;
    flex: 0 1 auto;
    min-block-size: 0;
    flex-direction: column;
    align-items: center;
    gap: var(--gap-tight);
    max-width: 12rem;
    transform: rotate(var(--lean)) translateY(var(--drop));
  }

  .doodle :global(.instrument) {
    flex: 0 1 auto;
    min-block-size: 2.5rem;
    block-size: clamp(3.5rem, calc(var(--book-h, 40rem) / 6.5), 9rem);
    inline-size: auto;
    aspect-ratio: 1;
  }

  .doodle figcaption {
    font-family: var(--font-hand);
    font-size: var(--size-margin);
    line-height: var(--leading-hand);
    color: var(--pencil);
    text-align: center;
  }
</style>
