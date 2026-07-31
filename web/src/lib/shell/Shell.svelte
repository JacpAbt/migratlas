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

<div class="shell" class:shell--reading={mode === "reading"}>
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

  /* Lifted clear of the index strip. MapLibre owns these nodes so they cannot be scoped, and they
     defaulted into the same corner the strip occupies: on a phone the zoom buttons landed on top of
     the claim's own text, and the attribution was underneath the strip entirely -- which is a
     licence notice that a visitor cannot read. */
  .shell :global(.maplibregl-ctrl-bottom-right),
  .shell :global(.maplibregl-ctrl-bottom-left) {
    bottom: var(--strip);
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
    padding: var(--gap-wide) var(--gap-wide) calc(var(--strip) + var(--gap-wide));
    pointer-events: none;
  }

  .shell__sheet {
    pointer-events: auto;
    /* Full width by default. The `68vw` cap that keeps the globe visible beside it is only sane
       once there is a globe worth seeing: at 390px it left a useless 32% strip of sphere and shrank
       the claim to a column of two-word lines. */
    max-width: 52rem;
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

  /* Wide enough for the sphere to be worth leaving room for. */
  @media (min-width: 60rem) {
    .shell__sheet {
      max-width: min(52rem, 68vw);
    }
  }

  /* Below the width where the sheet leaves room beside itself, it runs the full width and so
     reaches the corner MapLibre keeps its controls in. Two different answers for two different
     kinds of control, and the difference is not cosmetic:
       - The attribution is a licence notice, so space is reserved for it and it stays put.
       - Zoom, projection and scale are for driving a globe that is, at this width, entirely behind
         an opaque sheet. They are 200px of buttons printed over the claim's own text, controlling
         something the reader cannot see. They come back the moment the sheet does not cover it. */
  @media (max-width: 60rem) {
    .shell__reading {
      padding-bottom: calc(var(--strip) + var(--attrib) + var(--gap-tight));
    }

    .shell--reading :global(.maplibregl-ctrl-group),
    .shell--reading :global(.maplibregl-ctrl-scale) {
      display: none;
    }
  }

  @media (max-width: 52rem) {
    .shell__reading {
      padding: var(--gap) var(--gap) calc(var(--strip) + var(--attrib) + var(--gap-tight));
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
