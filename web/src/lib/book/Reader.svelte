<script lang="ts">
  import Book from "./Book.svelte";
  import Figure from "./Figure.svelte";
  import Introduction from "./Introduction.svelte";
  import World from "./World.svelte";
  import Claim from "../claim/Claim.svelte";
  import Response from "../sandbox/Response.svelte";
  import Sandbox from "../sandbox/Sandbox.svelte";
  import { loadIntroduction, type IntroductionDocument } from "./introduction";
  import { loadResponse, type ResponseDocument } from "../sandbox/response";
  import { loadSandbox, type SandboxDocument } from "../sandbox/sandbox";
  import { CHAPTERS, chapterAt, type Chapter } from "../story";
  import type { Finding } from "../ledger";

  let { findings, base }: { findings: Finding[]; base: string } = $props();

  /*
    Fetched here rather than in `main.ts`, so the book opens on a claim chapter without waiting for
    a document only the introduction needs. A failure leaves `opening` null and the component says
    so, which is the same treatment `Plate` gives a basemap that will not load.
  */
  let opening = $state<IntroductionDocument | null>(null);
  $effect(() => {
    loadIntroduction(base)
      .then((loaded) => (opening = loaded))
      .catch(() => (opening = null));
  });

  /*
    The dial, on the one chapter it answers.

    `response.json` keys its dials to `anthropogenic-share`, which is the claim "Why it changed"
    carries -- so the chapter that asks why is the chapter that gets to turn the input and see what
    the fit says. Loaded here beside the introduction, and a failure leaves it null so the panel
    renders nothing rather than a broken control.
  */
  let dial = $state<ResponseDocument | null>(null);
  $effect(() => {
    loadResponse(base)
      .then((loaded) => (dial = loaded))
      .catch(() => (dial = null));
  });

  /*
    The safeguards, which belong beside the claim rather than beside the figure.

    `claim/Evidence.svelte` orders these deliberately and the order carries over: the sandbox says
    how much to trust the number, and only then is it worth asking what a different world would do
    to it. So the sandbox sits under the claim on the argument page, and the dial sits on the facing
    page with the figures.
  */
  let safeguards = $state<SandboxDocument | null>(null);
  $effect(() => {
    loadSandbox(base)
      .then((loaded) => (safeguards = loaded))
      .catch(() => (safeguards = null));
  });

  /** The chapter that opens the book, which is the only one the introduction belongs on. */
  const OPENING_SLUG = CHAPTERS[0]!.slug;

  /** The chapter in the back pocket, which is the only one that gets a live map. */
  const WORLD_SLUG = CHAPTERS[CHAPTERS.length - 1]!.slug;

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

  Two chapters carry no claim of their own, and each gets a page of its own kind rather than an
  empty one: the introduction opens the book, and the world is the live map in the back pocket.
-->
<Book chapters={CHAPTERS} {open} onopen={show}>
  {#snippet page(chapter: Chapter, side: "verso" | "recto")}
    {@const claims = held(chapter)}
    {#if chapter.slug === OPENING_SLUG}
      <Introduction document_={opening} {side} />
    {:else if chapter.slug === WORLD_SLUG}
      <World {base} {side} />
    {:else if side === "verso"}
      <p class="chapter">{chapter.title}</p>
      {#if claims.length}
        <!-- Every claim the chapter carries, not just the first: "What did not" holds three, and a
             page showing one of them would drop two results on the floor. The argument is the left
             page and the plate is the right one. -->
        {#each claims as finding (finding.key)}
          <Claim {finding} />
          <Sandbox doc={safeguards} claim={finding.key} />
        {/each}
      {/if}
    {:else if claims[0]}
      <!--
        The facing page: the claim's own figure where it has one, and the drawn plate where it does
        not. The dial follows on the chapter whose claim has one, after the figure, in the order
        `Evidence` fixed -- how much to trust the number, then what a different world would do to it.
      -->
      <Figure finding={claims[0]} number={CHAPTERS.indexOf(chapter)} {base} />
      <Response doc={dial} claim={claims[0].key} />
    {:else}
      <p class="aside aside--quiet">No plate: this chapter is the way out, not a claim.</p>
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
