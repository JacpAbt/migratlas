<script lang="ts">
  import Rule from "../notebook/Rule.svelte";
  import { CHAPTERS, REALMS } from "../story";

  let { chapter, realm }: { chapter: string; realm: string } = $props();

  const where = $derived(REALMS.find((r) => r.slug === realm)?.the ?? realm);

  /* Named from the chapter table rather than typed here, so renaming that chapter does not strand a
     sentence pointing at a title the book no longer has. */
  const limits = CHAPTERS.find((c) => c.slug === "cannot-see")?.title ?? "what we cannot see";
</script>

<!--
  The page a chapter shows when the realm filter empties it.

  Not the blank leaf, and the distinction is the point. A blank means the ledger is missing what this
  chapter names; this means the claims exist and every one of them was measured somewhere else. Those
  are different facts and printing the same page for both would hide the more interesting one.

  This states where the measurements are. It states no result and quotes no number, so it is prose
  the build cannot get wrong -- which is the line `CLAUDE.md` draws when it says frontend prose is
  authored in Python: what is authored there is anything the analysis could contradict.
-->
<div class="absent">
  <p class="absent__kicker">{chapter}</p>
  <h2 class="absent__line">Nothing measured in {where}.</h2>
  <Rule seed="absent-{realm}" />
  <p class="absent__body">
    This chapter has claims. None of them is in {where} — so the page is empty because of where the
    instruments are, not because of where the animals are. That difference has a chapter of its own:
    {limits}.
  </p>
</div>

<style>
  /*
    Hatched, so it reads as paper left empty on purpose.

    Three lines on an otherwise white page looks like a page that failed to load, and the hatch is
    the mark this notebook already uses for ground it is holding back. It goes *under* the text, in
    the part of the leaf that is actually empty -- laid over the words it would be decoration
    fighting the sentence, and the first attempt put it there and was invisible for its trouble.

    The page's own column is a flex column at full height, so filling it is `flex: 1` rather than a
    height: the hatch has to reach the foot of the leaf and the text does not.
  */
  .absent {
    position: relative;
    flex: 1;
    isolation: isolate;
  }

  .absent::before {
    content: "";
    position: absolute;
    inset: 10.5rem -0.5rem 0;
    z-index: -1;
    background: repeating-linear-gradient(
      -38deg,
      color-mix(in srgb, var(--rule) 85%, transparent) 0 1px,
      transparent 1px 10px
    );
    /* Fading in downwards rather than out: it should start where the words stop, and the hardest
       hatch belongs at the foot where there is most nothing. */
    mask-image: linear-gradient(to bottom, transparent, rgb(0 0 0 / 90%) 22%);
  }

  .absent__kicker {
    margin: 0 0 var(--gap-hair);
    font-size: var(--size-label);
    letter-spacing: var(--tracking-label);
    text-transform: uppercase;
    color: var(--ink-soft);
  }

  .absent__line {
    margin: 0;
    font-family: var(--font-hand);
    font-size: var(--size-claim);
    line-height: var(--leading-hand);
    font-weight: 400;
  }

  .absent__body {
    margin: var(--gap) 0 0;
    font-size: var(--size-body);
    color: var(--ink-soft);
  }
</style>
