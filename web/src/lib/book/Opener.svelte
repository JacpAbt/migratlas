<!--
  The leaf a chapter opens on: its question, and the argument that answers it before any claim does.

  Set as a question and a paragraph rather than as a heading and body text, because the question is
  the thing a reader is holding when they arrive and the chapter title is only its subject. The
  fore-edge tab says "Where"; this leaf says "Are the places changing, and do they follow the
  warming?" and then answers it in a voice, with the ledger's own numbers inside the sentences.

  No figure and no claim on this leaf on purpose. It is the one page in each chapter that is
  argument rather than evidence, and putting a number's picture beside it would invite a reader to
  check the argument against one claim instead of against the chapter.
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
  /* The question heads the account, so it belongs on the leaf the account starts on. The
     figures close it, so they belong on the leaf it ends on. */
  const opens = $derived(from === 0);
  const closes = $derived(to >= opener.paragraphs.length);
</script>

<article class="opener">
  <p class="opener__chapter">{chapter}</p>
  {#if opens}
    <h2 class="opener__question">{opener.question}</h2>
  {/if}
  {#each shown as paragraph (paragraph)}
    <p class="opener__body">{paragraph}</p>
  {/each}
  <!--
    Every digit on this leaf, and the reason the account above has none.

    The prose says "about half a day" so that it can be read by somebody who does not want a
    number; this says -0.56 so that the somebody who does is not fobbed off. The Python that
    authors both refuses to put a digit in the first, which is what makes the plain register safe:
    there is nothing up there that can quietly stop being true.
  -->
  {#if closes}
    <dl class="opener__figures">
      {#each opener.figures as figure (figure)}
        <div>
          <dt>{figure.split(" — ")[0]}</dt>
          <dd>{figure.split(" — ").slice(1).join(" — ")}</dd>
        </div>
      {/each}
    </dl>
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

  /* Subordinate to the account and never competing with it: this is the apparatus, set small,
     ruled off, and in the mono face because a column of figures has to line up. */
  .opener__figures {
    border-top: 1px solid var(--rule);
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    margin: 0;
    padding-top: 0.7rem;
  }

  .opener__figures div {
    display: flex;
    flex-wrap: wrap;
    gap: 0.15rem 0.5rem;
  }

  .opener__figures dt {
    color: var(--ink-soft);
    font-family: var(--font-mono);
    font-size: 0.72rem;
  }

  .opener__figures dd {
    color: var(--ink);
    font-family: var(--font-mono);
    font-size: 0.72rem;
    font-variant-numeric: tabular-nums;
    margin: 0;
  }
</style>
