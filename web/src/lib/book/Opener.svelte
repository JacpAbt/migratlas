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
-->
<script lang="ts">
  import type { ChapterOpener } from "./chapters";

  const {
    chapter,
    opener,
    from,
    to,
  }: { chapter: string; opener: ChapterOpener; from: number; to: number } = $props();

  const shown = $derived(opener.paragraphs.slice(from, to));
  /* The question heads the account, so it belongs on the leaf the account starts on. */
  const opens = $derived(from === 0);
</script>

<article class="opener">
  <p class="opener__chapter">{chapter}</p>
  {#if opens}
    <h2 class="opener__question">{opener.question}</h2>
  {/if}
  {#each shown as paragraph (paragraph)}
    <p class="opener__body">{paragraph}</p>
  {/each}
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

  .opener__chapter {
    color: var(--ink-faint);
    font-size: 0.78rem;
    letter-spacing: 0.09em;
    margin: 0;
    text-transform: uppercase;
  }

  .opener__question {
    font-size: 1.35rem;
    font-weight: 600;
    line-height: 1.25;
    margin: 0;
    text-wrap: balance;
  }

  /*
    Wider measure and a larger size than a record page, because this is the one leaf meant to be
    read straight through rather than consulted. The first line is not indented -- nothing precedes
    it -- and the paragraph carries its own leading rather than the book's tighter default.
  */
  .opener__body {
    font-size: 0.98rem;
    line-height: 1.6;
    margin: 0;
    text-align: justify;
    hyphens: auto;
  }
</style>
