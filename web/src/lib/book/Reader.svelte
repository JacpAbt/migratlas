<script lang="ts">
  import Book from "./Book.svelte";
  import Plate from "./Plate.svelte";
  import Claim from "../claim/Claim.svelte";
  import { CHAPTERS, chapterAt, type Chapter } from "../story";
  import type { Finding } from "../ledger";

  let { findings, base }: { findings: Finding[]; base: string } = $props();

  const CHAPTER_PARAM = "ch";

  /** The chapter in the URL, defaulting to the first one that carries a claim. */
  function fromUrl(): string {
    const slug = new URLSearchParams(location.hash.slice(1)).get(CHAPTER_PARAM);
    return chapterAt(slug)?.slug ?? CHAPTERS[1]!.slug;
  }

  let open = $state(fromUrl());

  /*
    The chapter goes in the URL for the reason `state/route.ts` gives about claims: a chapter you
    cannot link to is a chapter nobody cites. `pushState` rather than `replaceState`, because going
    back to the chapter you were reading is exactly what a reader means by back -- the same split
    that module already makes between the clock and the claim.
  */
  function show(slug: string): void {
    open = slug;
    const params = new URLSearchParams(location.hash.slice(1));
    if (params.get(CHAPTER_PARAM) === slug) return;
    params.set(CHAPTER_PARAM, slug);
    history.pushState(null, "", `#${params.toString()}`);
  }

  $effect(() => {
    const back = () => (open = fromUrl());
    addEventListener("popstate", back);
    return () => removeEventListener("popstate", back);
  });

  const held = (chapter: Chapter): Finding[] =>
    chapter.keys
      .map((key) => findings.find((finding) => finding.key === key))
      .filter((finding): finding is Finding => Boolean(finding));
</script>

<!--
  The book, reading the ledger.

  What goes on a page is one snippet handed to `Book`, which calls it for the open chapter and again
  for the outgoing one during a turn. That is the whole of ADR 0015 decision 5: the turning leaf is
  another call with different arguments rather than a copy of the DOM, so none of the five defects
  that decision lists can occur.

  The claims are rendered by the app's own `Claim` component, unchanged. ADR 0013 said the rebuild
  is structural and not stylistic, and frontend prose is authored in Python and rendered verbatim --
  a book that re-wrote the claims would be presenting sentences the build cannot produce.

  Two chapters carry no claim of their own: the way in and the way out. They get their own line
  rather than an empty page, and the introduction and the world both land in later changes.
-->
<Book chapters={CHAPTERS} {open} onopen={show}>
  {#snippet page(chapter: Chapter, side: "verso" | "recto")}
    {@const claims = held(chapter)}
    {#if side === "verso"}
      <p class="chapter">{chapter.title}</p>
      {#if claims.length}
        <!-- Every claim the chapter carries, not just the first: "What did not" holds three, and a
             page showing one of them would drop two results on the floor. The argument is the left
             page and the plate is the right one. -->
        {#each claims as finding (finding.key)}
          <Claim {finding} />
        {/each}
      {:else}
        <p class="aside">
          No claim of its own. This chapter says how to read the ones that follow.
        </p>
      {/if}
    {:else if claims[0]}
      <!-- The plate is a figure: where on Earth this chapter's first claim is. The map itself is
           the world chapter, per ADR 0013, which is why a still is right here. -->
      <Plate finding={claims[0]} number={CHAPTERS.indexOf(chapter)} {base} />
    {:else}
      <p class="aside aside--quiet">
        No plate: this chapter is the way in, or the way out.
      </p>
    {/if}
  {/snippet}
</Book>

<style>
  .chapter {
    margin: 0 0 var(--gap);
    font-size: var(--size-label);
    letter-spacing: var(--tracking-label);
    text-transform: uppercase;
    color: var(--moss);
  }

  .aside {
    margin: 0;
    font-family: var(--font-hand);
    font-size: var(--size-lede);
    line-height: var(--leading-hand);
    color: var(--ink-soft);
  }

  .aside--quiet {
    margin-top: auto;
    font-size: var(--size-margin);
    color: var(--pencil);
  }
</style>
