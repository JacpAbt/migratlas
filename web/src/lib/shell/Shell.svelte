<script lang="ts">
  import Globe from "../globe/Globe.svelte";
  import Claim from "../claim/Claim.svelte";
  import Arrival from "./Arrival.svelte";
  import Index from "./Index.svelte";
  import { loadLedger, type Finding, type Ledger } from "../ledger";
  import { arrivalOf, exploreView, viewFor, type View } from "../story";

  let { base }: { base: string } = $props();

  /**
   * Three states, and the third is not a lesser version of the second.
   *
   * `arriving` is the landing claim. `reading` is one claim with its audit. `exploring` is the globe
   * with the panels and no claim in the way -- the reader who pressed "just let me explore" asked
   * for the map, so they get the map, not the map with an argument still on it.
   */
  type Mode = "arriving" | "reading" | "exploring";

  let ledger = $state<Ledger | null>(null);
  let failure = $state<string | null>(null);
  let mode = $state<Mode>("arriving");
  let current = $state<Finding | null>(null);
  /** What the globe actually loaded, so explore mode can show all of it without a second list. */
  let available = $state<string[]>([]);

  $effect(() => {
    loadLedger(base)
      .then((loaded) => {
        ledger = loaded;
        current = arrivalOf(loaded.findings) ?? null;
      })
      .catch((error: unknown) => (failure = String(error)));
  });

  // The camera follows whichever claim is in hand. While arriving it is already on the evidence
  // behind the card, which is the point of the card sitting on a live globe rather than on a picture
  // of one. Exploring is the exception: no claim is in hand, so no claim frames the view.
  const view = $derived<View | null>(
    mode === "exploring" ? exploreView(available) : current ? viewFor(current) : null,
  );

  function choose(finding: Finding): void {
    current = finding;
    mode = "reading";
  }
</script>

<div class="shell">
  <Globe {base} {view} onready={(report) => (available = report.layers)} />

  {#if failure}
    <!-- The ledger is the whole page here, so its failure is not survivable the way a layer's is.
         Say what happened rather than showing an empty globe. -->
    <div class="shell__failure" role="alert">
      <p>The claim ledger could not be read, so there is nothing to show.</p>
      <p class="shell__detail">{failure}</p>
    </div>
  {:else if ledger && current}
    {#if mode === "arriving"}
      <Arrival
        finding={current}
        onshow={() => (mode = "reading")}
        onexplore={() => (mode = "exploring")}
      />
    {:else if mode === "reading"}
      <article class="shell__reading" aria-live="polite">
        <div class="shell__sheet">
          {#key current.key}
            <Claim finding={current} />
          {/key}
        </div>
        <p class="shell__because">{view?.because}</p>
      </article>
    {/if}

    {#if mode !== "arriving"}
      <Index
        findings={ledger.findings}
        selected={mode === "reading" ? current.key : null}
        onchoose={choose}
        onclear={() => (mode = "exploring")}
      />
    {/if}
  {/if}
</div>

<style>
  .shell {
    position: relative;
    height: 100%;
    overflow: hidden;
  }

  .shell__reading {
    position: absolute;
    inset: 0;
    z-index: 2;
    display: flex;
    flex-direction: column;
    gap: var(--gap-tight);
    /* Room at the bottom for the index, and at the right for the globe to stay visible. A claim
       that covered the sphere would make the flight pointless. */
    padding: var(--gap-wide) var(--gap-wide) 6.5rem;
    pointer-events: none;
  }

  .shell__sheet {
    pointer-events: auto;
    /* Narrow enough that the globe it is read against stays visible. At 56rem the sheet covered the
       sphere on a 1360px laptop, which makes both the camera flight and the caption beneath it
       pointless. The claim card's own two-column breakpoint is set to match. */
    max-width: min(52rem, 68vw);
    max-height: 100%;
    padding: var(--gap-wide);
    overflow-y: auto;
    background-color: var(--paper);
    background-image: var(--grain);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    box-shadow: 0 2px 24px rgb(47 61 79 / 14%);
    animation: settle var(--draw) var(--ease-pen) both;
  }

  @keyframes settle {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: none;
    }
  }

  /* Why the camera is where it is. Outside the sheet, over the globe, because it is a caption on the
     globe rather than part of the claim. */
  .shell__because {
    pointer-events: auto;
    align-self: start;
    max-width: 26rem;
    margin: 0;
    padding: var(--gap-hair) var(--gap-tight);
    background: var(--paper);
    border-left: 2px solid var(--rust-ink);
    font-family: var(--font-mono);
    font-size: var(--size-margin);
    line-height: 1.5;
    color: var(--ink-soft);
  }

  .shell__failure {
    position: absolute;
    inset: 0;
    z-index: 3;
    display: grid;
    place-content: center;
    padding: var(--gap-wide);
    text-align: center;
  }

  .shell__failure p {
    margin: 0;
    font-size: var(--size-body);
  }

  .shell__detail {
    margin-top: var(--gap-tight);
    font-family: var(--font-mono);
    font-size: var(--size-margin);
    color: var(--rust);
  }

  @media (max-width: 52rem) {
    .shell__reading {
      padding: var(--gap) var(--gap) 8rem;
    }

    .shell__sheet {
      padding: var(--gap);
    }

    /* The globe has no room to be seen beside a full-width sheet on a phone, so the caption about
       where the camera is would be describing something invisible. */
    .shell__because {
      display: none;
    }
  }
</style>
