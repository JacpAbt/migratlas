<script lang="ts">
  import Book from "./Book.svelte";
  import Figure from "./Figure.svelte";
  import Introduction from "./Introduction.svelte";
  import Leaves from "./Leaves.svelte";
  import Settings from "./Settings.svelte";
  import World from "./World.svelte";
  import Claim from "../claim/Claim.svelte";
  import Margin from "../claim/Margin.svelte";
  import Response from "../sandbox/Response.svelte";
  import Sandbox from "../sandbox/Sandbox.svelte";
  import { openingOf, spreadsOf, type Panel } from "./pages";
  import { world as pocket } from "./pocket.svelte";
  import type { IntroductionDocument } from "./introduction";
  import type { ResponseDocument } from "../sandbox/response";
  import type { SandboxDocument } from "../sandbox/sandbox";
  import { CHAPTERS, chapterAt, chapterOf } from "../story";
  import type { Finding } from "../ledger";

  let {
    findings,
    base,
    opening,
    safeguards,
    dial,
  }: {
    findings: Finding[];
    base: string;
    /*
      The three documents the pagination is computed from, loaded in `main.ts` before this mounts.

      They used to be fetched here, on the argument that the book should open on a claim without
      waiting for a document only the introduction needs. That argument died with pagination: the
      number of pages depends on how many passages the introduction has and on which claims carry an
      audit or a dial, so a folio printed before they arrive is a folio that changes under the
      reader, and a deep link to a page lands somewhere else. A book cannot count its own pages
      later. All three together are 18 KB.
    */
    opening: IntroductionDocument | null;
    safeguards: SandboxDocument | null;
    dial: ResponseDocument | null;
  } = $props();

  const spreads = $derived(
    spreadsOf({ findings, introduction: opening, safeguards, dial }, CHAPTERS),
  );

  const of = (key: string): Finding | undefined => findings.find((f) => f.key === key);

  /**
   * Plate numbers, counted in reading order over the whole book.
   *
   * "Plate 3" has to be the third plate a reader passes or the caption cannot be cited, which the
   * old number could not promise -- it was the chapter's index, so two claims in one chapter shared
   * a number and a chapter with no plate consumed one.
   */
  const PLATES: readonly string[] = CHAPTERS.flatMap((chapter) => chapter.keys);
  const figureNumber = (key: string): number => PLATES.indexOf(key) + 1;

  const CHAPTER_PARAM = "ch";

  /** Which spread within the chapter, so a page has an address and not just a chapter. */
  const PAGE_PARAM = "p";

  /**
   * The old shell's claim address, still understood.
   *
   * `#c=marine-null` is what `state/route.ts` wrote and what `species/Study.svelte` still links to
   * from every study page -- "read the claim this evidence feeds". It is also the address the
   * deployed site has been handing out, so those links exist outside this repository. Ignoring it
   * would have landed all of them on whatever chapter happens to be the default.
   *
   * Read rather than rewritten, and resolved to the claim's own first page.
   */
  const CLAIM_PARAM = "c";

  /** The spread carrying a claim's plain register, which is where a link to that claim should land. */
  function pageOf(key: string): number {
    return spreads.findIndex((spread) =>
      [spread.verso, spread.recto].some(
        (panel) => panel.kind === "finding" && panel.key === key,
      ),
    );
  }

  /*
    The width below which a spread is not a spread.

    62rem is the same figure as `Page.svelte`'s narrow block, and it is the one number in the book
    written twice: a media query cannot read a custom property, so CSS and this cannot share it.
    Getting them out of step is loud rather than silent -- it shows as a two-page spread squeezed
    onto a phone -- which is why this is a comment and not machinery.
  */
  const NARROW = "(width < 62rem)";

  let narrow = $state(matchMedia(NARROW).matches);
  $effect(() => {
    const query = matchMedia(NARROW);
    const watch = () => (narrow = query.matches);
    query.addEventListener("change", watch);
    return () => query.removeEventListener("change", watch);
  });

  /**
   * The spread in the URL: a chapter, and how far into it.
   *
   * `ch` is kept and `p` is added rather than replacing both with one page id, because a chapter is
   * the durable address -- it survives a claim being added ahead of it, where an absolute page number
   * would silently point at a different page. `p` defaults to 0, so every link written before
   * pagination existed still opens the chapter it named.
   */
  function fromUrl(): number {
    const params = new URLSearchParams(location.hash.slice(1));

    // A claim address wins where there is no chapter one, because it is more specific: it names a
    // page rather than a chapter, and nothing that writes it also writes `ch`.
    const claim = params.get(CLAIM_PARAM);
    if (claim && !params.get(CHAPTER_PARAM)) {
      const at = pageOf(claim);
      if (at >= 0) return at;
    }

    const slug = chapterAt(params.get(CHAPTER_PARAM))?.slug ?? CHAPTERS[1]!.slug;
    const first = openingOf(spreads, slug);
    const into = Number.parseInt(params.get(PAGE_PARAM) ?? "0", 10);
    if (!Number.isFinite(into) || into <= 0) return first;
    // Clamped to the chapter it names, so `p=9` on a two-spread chapter lands on its last page
    // rather than in the middle of the next chapter.
    const last = spreads.findLastIndex((spread) => spread.chapter.slug === slug);
    return Math.min(first + into, last < 0 ? first : last);
  }

  let open = $state(0);

  /*
    Set once the spreads exist, and once only.

    The page count depends on the documents, so on the very first run `spreads` may be a shorter book
    than the one the reader asked for -- and re-deriving `open` on every change would drag a reader
    who had turned three pages back to wherever the URL still said. `settled` is a plain let for the
    same reason `Leaves` keeps one: it must not make this effect re-run.
  */
  let settled = false;
  $effect(() => {
    if (settled || spreads.length === 0) return;
    settled = true;
    open = fromUrl();
  });

  /*
    The page goes in the URL for the reason `state/route.ts` gives about claims: a page you cannot
    link to is a page nobody cites. `pushState` rather than `replaceState`, because going back to the
    page you were reading is exactly what a reader means by back -- the same split that module
    already makes between the clock and the claim.
  */
  function show(at: number): void {
    open = at;
    const spread = spreads[at];
    if (!spread) return;
    const params = new URLSearchParams(location.hash.slice(1));
    const into = String(at - openingOf(spreads, spread.chapter.slug));
    if (params.get(CHAPTER_PARAM) === spread.chapter.slug && params.get(PAGE_PARAM) === into) return;
    params.set(CHAPTER_PARAM, spread.chapter.slug);
    params.set(PAGE_PARAM, into);
    // Dropped once the page is written in the address it is written in: leaving `c` behind would
    // make it win over `ch` on the next read and pin the reader to one claim.
    params.delete(CLAIM_PARAM);
    history.pushState(null, "", `#${params.toString()}`);
  }

  /**
   * The other half of the road: a claim's own specimen, in the world chapter.
   *
   * `Claim` renders the invitation only when it is given somewhere to go, so without this the
   * button did not exist -- which is how the road went missing when the book replaced the shell
   * rather than being reported as broken. The species waits in `pocket.svelte.ts` because the panel
   * that shows it is on a page this one is about to turn to.
   */
  function toSpecimen(key: number): void {
    pocket.preselect = key;
    show(openingOf(spreads, CHAPTERS[CHAPTERS.length - 1]!.slug));
  }

  $effect(() => {
    const back = () => (open = fromUrl());
    addEventListener("popstate", back);
    return () => removeEventListener("popstate", back);
  });
</script>

<!--
  The book, reading the ledger.

  What goes on a page is one snippet handed to the container, which calls it for the open chapter and
  again for the outgoing one during a turn. That is the whole of ADR 0015 decision 5: the turning
  leaf is another call with different arguments rather than a copy of the DOM, so none of the five
  defects that decision lists can occur.

  The claims are rendered by the app's own `Claim` component. ADR 0013 said the rebuild is structural
  and not stylistic, and frontend prose is authored in Python and rendered verbatim -- a book that
  re-wrote the claims would be presenting sentences the build cannot produce. What the book *does*
  decide is which register goes on which page, which is `part` and not new prose.

  One page carries one thing, and which things there are is `pages.ts`. The order across a claim is
  the order the owner asked for: what we found in plain language, then the figure, then the number
  with its scope and its caveat, then how it could be wrong.

  One snippet, two containers, and exactly one of them mounted. A phone gets `Leaves` -- the same
  pages, swiped rather than turned -- because the spread's every measurement was chosen against a
  shape a 390px screen does not have. Declaring the pages here and passing them as a prop is what
  keeps that a choice of *container* rather than a second authored version of the book: there is
  nowhere for the two to drift apart, because there is only one of them.
-->
{#snippet leaf(panel: Panel, _side: "verso" | "recto")}
  {#if panel.kind === "opening"}
    <Introduction document_={opening} opening />
  {:else if panel.kind === "intro"}
    <Introduction document_={opening} from={panel.from} to={panel.to} />
  {:else if panel.kind === "world"}
    <World {base} side={panel.part === "map" ? "recto" : "verso"} />
  {:else if panel.kind === "blank"}
    <p class="aside aside--quiet">Nothing is recorded on this leaf.</p>
  {:else}
    {@const finding = of(panel.key)}
    {#if !finding}
      <p class="aside aside--quiet">This claim is not in the ledger.</p>
    {:else if panel.kind === "finding"}
      <p class="chapter">{chapterOf(panel.key)?.title ?? ""}</p>
      <Claim {finding} part="finding" />
    {:else if panel.kind === "figure"}
      <Figure {finding} number={figureNumber(panel.key)} {base} at={panel.at} />
    {:else if panel.kind === "record"}
      <Claim {finding} part="record" onspecimen={toSpecimen} />
    {:else if panel.kind === "bias"}
      <Margin {finding} part="bias" />
    {:else if panel.kind === "survived"}
      <Margin {finding} part="survived" />
    {:else if panel.kind === "panel" && panel.doc === "safeguards"}
      <Sandbox
        doc={safeguards}
        claim={panel.key}
        part={panel.part}
        slice={{ kind: panel.part === "knobs" ? "knob" : "refusal", at: panel.at }}
      />
    {:else if panel.kind === "panel"}
      <Response
        doc={dial}
        claim={panel.key}
        part={panel.part}
        slice={{ kind: panel.part === "knobs" ? "knob" : "refusal", at: panel.at }}
      />
    {/if}
  {/if}
{/snippet}

<!-- On the desk rather than in the book: a book does not carry a switch for what paper it is
     printed on. Inherited from the shell it replaced, along with the repaint they drive. -->
<Settings />

{#if narrow}
  <Leaves chapters={CHAPTERS} {spreads} {open} onopen={show} page={leaf} />
{:else}
  <Book chapters={CHAPTERS} {spreads} {open} onopen={show} page={leaf} />
{/if}

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
