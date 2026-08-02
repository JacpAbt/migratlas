<script lang="ts">
  import { tick } from "svelte";
  import type { Map as MapLibreMap } from "maplibre-gl";

  import Globe from "../globe/Globe.svelte";
  import Claim from "../claim/Claim.svelte";
  import Evidence from "../claim/Evidence.svelte";
  import Arrival from "./Arrival.svelte";
  import Explore from "./Explore.svelte";
  import Index from "./Index.svelte";
  import { loadLedger, type Finding, type Ledger } from "../ledger";
  import { arrivalOf, exploreView, viewFor, type View } from "../story";
  import { loadSandbox, type SandboxDocument } from "../sandbox/sandbox";
  import type { DetectabilityDocument } from "../../layers/detectability";
  import type { LoadedLayer } from "../../layers/types";
  import type { SpeciesSelection } from "../../layers/selection";
  import { SpeciesSurfaces } from "../../search/taxon";
  import { Clock } from "../../state/time";
  import { turnPage } from "../../state/turn";
  import { readClaim, watchHistory, writeClaim } from "../../state/route";
  import Surface from "../notebook/Surface.svelte";
  import TypeChoice from "../notebook/TypeChoice.svelte";
  import Sheet from "../notebook/Sheet.svelte";
  import { drawFurniture } from "../notebook/furniture";
  import {
    applySurface,
    isNight,
    storedSurface,
    watchSystem,
    type Surface as SurfaceChoice,
  } from "../../state/surface";
  import { applyType, storedType, type TypeChoice as TypeName } from "../../state/type";
  import { setPalette } from "../../globe/flavor";
  import { repaintBasemap } from "../../globe/map";

  let { base }: { base: string } = $props();

  // One clock, outside the reactive graph because it owns the URL and a timer. `day` mirrors it into
  // state, since a class with its own listeners is not reactive by itself.
  const clock = new Clock();
  let day = $state(clock.state.day);
  let minute = $state(clock.state.minute);

  // Derived, not constructed once: a value captured at init is a value that cannot change, and the
  // Svelte compiler is right to say so even where this particular prop never does.
  const surfaces = $derived(new SpeciesSurfaces(base));

  $effect(() =>
    clock.subscribe((state) => {
      day = state.day;
      minute = state.minute;
    }),
  );

  // Rebuilt from the mirrored parts rather than read off the clock, so the terminator is downstream
  // of reactive state instead of a value the effect graph cannot see change.
  const instant = $derived(new Date(Date.UTC(clock.state.year, 0, 1 + day, 0, minute)));

  /**
   * Which paper this is read on.
   *
   * Applied on mount rather than initialised from it: the stored choice has to reach
   * `document.documentElement` before anything reads a token off it, and the globe's palette is
   * set from the same value so the sphere and the page can never disagree about what surface it is.
   */
  let surface = $state<SurfaceChoice>("system");

  /** Which type the page is set in. Independent of the surface: black paper and a legible face is
      a combination someone will want, and neither setting reads the other. */
  let typeChoice = $state<TypeName>("hand");

  $effect(() => {
    surface = applySurface(storedSurface());
    typeChoice = applyType(storedType());
  });

  // The globe's colours are JavaScript, not CSS, so nothing repaints them on its own, and neither
  // the scrollbar nor MapLibre's buttons can hold a `var()` -- their ink is baked into a data URI.
  // Runs on the stored choice too, not only on a click, otherwise a reader who chose night last
  // week gets a black page around a parchment globe with a parchment scrollbar down the side.
  function follow(): void {
    setPalette(isNight(surface));
    drawFurniture();
    if (!map) return;
    repaintBasemap(map);
    for (const layer of layers) layer.repaint?.();
  }

  $effect(follow);

  // And when the machine changes its mind while the choice is "system".
  $effect(() =>
    watchSystem(() => {
      if (surface === "system") follow();
    }),
  );

  let shell: HTMLDivElement;

  /**
   * Reserve the attribution's real height, measured.
   *
   * It was a token, and a token cannot be right: the bar lists one credit per visible source and
   * wraps, so it is two lines on a laptop and four on a phone with every layer drawn. The fixed
   * 3.25rem held until the assessment added a fourth credit, and then the licence notice printed
   * across the bottom of the claim's own text again -- the exact failure the reservation existed to
   * prevent, returning through the one thing about it that was a guess.
   */
  $effect(() => {
    // Depends on `layers` so it re-runs once the map exists. MapLibre creates the attribution when
    // it adds its controls, which is after this component mounts -- the first version read `null`,
    // returned early, and never looked again, so the measurement silently stayed a guess.
    if (layers.length === 0) return;
    const attrib = shell.querySelector(".maplibregl-ctrl-attrib");
    if (!attrib) return;
    const observer = new ResizeObserver(([entry]) => {
      const height = entry?.borderBoxSize?.[0]?.blockSize ?? entry?.contentRect.height ?? 0;
      shell.style.setProperty("--attrib", `${Math.ceil(height) + 8}px`);
    });
    observer.observe(attrib);
    return () => observer.disconnect();
  });

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
  let layers = $state<LoadedLayer[]>([]);
  let detectability = $state<DetectabilityDocument | null>(null);
  let sandbox = $state<SandboxDocument | null>(null);
  let selection = $state<SpeciesSelection | null>(null);
  let map: MapLibreMap | undefined;

  const available = $derived(layers.map((layer) => layer.meta.name));

  // Fetched alongside the ledger rather than lazily per claim: 8 KB, and every claim card that has
  // knobs needs it the moment it opens.
  $effect(() => {
    loadSandbox(base)
      .then((loaded) => (sandbox = loaded))
      // Not fatal. The claims are the page; the sandbox is a way to interrogate them, and losing it
      // should cost the knobs rather than the argument.
      .catch(() => (sandbox = null));
  });

  $effect(() => {
    loadLedger(base)
      .then((loaded) => {
        ledger = loaded;
        // A claim named in the URL opens straight into its evidence, skipping the arrival card.
        // Someone who follows a link to a specific finding has already been told what it is; the
        // card would be an interstitial between them and the thing they clicked for.
        const asked = loaded.findings.find((finding) => finding.key === readClaim());
        current = asked ?? arrivalOf(loaded.findings) ?? null;
        if (asked) mode = "reading";
      })
      .catch((error: unknown) => (failure = String(error)));
  });

  // Back and forward. `writeClaim` pushes an entry per claim, so this is what makes the button do
  // what a reader means by it -- an unhandled popstate would change the URL and leave the page on
  // whatever it was showing, which is worse than not being linkable at all.
  $effect(() =>
    watchHistory(() => {
      const asked = ledger?.findings.find((finding) => finding.key === readClaim());
      if (asked) {
        current = asked;
        mode = "reading";
      } else if (ledger) {
        mode = "exploring";
      }
    }),
  );

  // The camera follows whichever claim is in hand. While arriving it is already on the evidence
  // behind the card, which is the point of the card sitting on a live globe rather than on a picture
  // of one. Exploring is the exception: no claim is in hand, so no claim frames the view.
  const view = $derived<View | null>(
    mode === "exploring" ? exploreView(available) : current ? viewFor(current) : null,
  );

  function choose(finding: Finding): void {
    // `await tick()` inside, not around: the transition has to capture the *new* sheet, and one
    // that resolves before Svelte has rendered it captures the old one twice and cross-fades
    // nothing. Everything about whether this animates at all is `turnPage`'s decision.
    turnPage(async () => {
      current = finding;
      mode = "reading";
      writeClaim(finding.key);
      await tick();
    });
  }
</script>

<div class="shell" class:shell--reading={mode === "reading"} bind:this={shell}>
  <Globe
    {base}
    {view}
    week={Math.floor(day / 7)}
    {instant}
    onready={(report) => {
      layers = report.layers;
      detectability = report.detectability;
      selection = report.selection;
      map = report.map;
    }}
  />

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
        onexplore={() => {
          mode = "exploring";
          writeClaim(null);
        }}
      />
    {:else if mode === "reading"}
      <article class="shell__reading" aria-live="polite">
        <div class="shell__sheet">
          <Sheet seed={current.key}>
            <!-- The scroll is inside the paper, not on it. A drawn edge inside a scrolling box is
                 positioned against the padding box and slides away with the content, so the tear
                 would travel up the screen as a reader scrolls. -->
            <div class="shell__leaf">
              {#key current.key}
                <Claim finding={current} />
                <!-- The figure belongs to the claim, not to a panel of its own: for the attribution
                     it IS the argument, and for the coverage limit it is the number. -->
                <Evidence finding={current} {base} {detectability} {sandbox} />
              {/key}
            </div>
          </Sheet>
        </div>
        <p class="shell__because">{view?.because}</p>
      </article>
    {/if}

    {#if mode === "exploring"}
      <Explore
        {layers}
        {clock}
        {day}
        {minute}
        {selection}
        {surfaces}
        {detectability}
        onfocus={(at) => map?.flyTo({ center: at, zoom: 3, essential: true })}
      />
    {/if}

    <div class="shell__settings">
      <TypeChoice choice={typeChoice} onchoose={(next) => (typeChoice = applyType(next))} />
      <Surface {surface} onchoose={(next) => (surface = applySurface(next))} />
    </div>

    {#if mode !== "arriving"}
      <Index
        findings={ledger.findings}
        selected={mode === "reading" ? current.key : null}
        onchoose={choose}
        onclear={() => {
          mode = "exploring";
          writeClaim(null);
        }}
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

  /* Top right, out of the reading path and above the sheet. Small on purpose: it is a preference,
     not a claim, and ADR 0007 gives the page's emphasis to the argument. */
  .shell__settings {
    position: absolute;
    top: var(--gap-tight);
    right: var(--gap-tight);
    z-index: 4;
    display: flex;
    align-items: center;
    gap: var(--gap);
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  /* Lifted clear of the index strip. MapLibre owns these nodes so they cannot be scoped, and they
     defaulted into the same corner the strip occupies: on a phone the zoom buttons landed on top of
     the claim's own text, and the attribution was underneath the strip entirely -- which is a
     licence notice that a visitor cannot read. */
  .shell :global(.maplibregl-ctrl-bottom-right),
  .shell :global(.maplibregl-ctrl-bottom-left) {
    bottom: var(--strip);
  }

  /*
    The map's own furniture, in the same hand as the rest.

    These were the last white rounded boxes on the page: a 4px radius, a white fill and a grey
    drop shadow, sitting on paper. Everything here is an override of MapLibre's stylesheet, so
    every rule has to undo something before it sets anything -- and `:global` because these are
    nodes MapLibre creates, which Svelte's scoping never sees.

    Some selectors carry a clause they do not need to match -- `:not(:empty)` here,
    `.maplibregl-ctrl` on the attribution below -- purely to reach the specificity of the rule they
    override. Without it they tie, and a tie is settled by whichever stylesheet the bundler emitted
    last, which is not a thing to leave to a build.

    The drawings come from `notebook/furniture.ts` as data URIs, redrawn on a surface change.
  */
  .shell :global(.maplibregl-ctrl-group:not(:empty)) {
    background: none;
    border-radius: 0;
    box-shadow: none;
  }

  .shell :global(.maplibregl-ctrl-group button) {
    /* The separator line between stacked buttons: each has its own drawn box now, so a border
       between them draws a straight line across two wobbling ones. */
    border: 0;
    margin-bottom: 3px;
    background-repeat: no-repeat;
    background-position: center;
  }

  /* The icons are MapLibre's own SVG data URIs on an inner span, in a fixed near-black that follows
     no surface. Cleared, and both the mark and the box drawn on the button itself. */
  .shell :global(.maplibregl-ctrl-group .maplibregl-ctrl-icon) {
    background-image: none;
  }

  .shell :global(.maplibregl-ctrl-zoom-in) {
    background-image: var(--ctrl-zoom-in);
  }

  .shell :global(.maplibregl-ctrl-zoom-out) {
    background-image: var(--ctrl-zoom-out);
  }

  .shell :global(.maplibregl-ctrl-globe) {
    background-image: var(--ctrl-globe);
  }

  .shell :global(.maplibregl-ctrl-globe-enabled) {
    background-image: var(--ctrl-globe-enabled);
  }

  .shell :global(.maplibregl-ctrl-group button:hover) {
    background-color: transparent;
    filter: contrast(1.4);
  }

  /* MapLibre paints its own blue glow on focus, including for a mouse click. Rust, and only for a
     keyboard, which is the same rule `base.css` applies to everything else. */
  .shell :global(.maplibregl-ctrl-group button:focus) {
    box-shadow: none;
  }

  .shell :global(.maplibregl-ctrl-group button:focus-visible) {
    outline: 2px solid var(--rust);
    outline-offset: -2px;
  }

  /*
    The scale bar: a measure, drawn.

    Three images and only one of them stretches. MapLibre sets this element's width in pixels to
    whatever the current zoom makes a round distance, so the rule has to follow that width exactly
    -- it is the measurement. The end ticks are pinned to each end at their drawn size.
  */
  .shell :global(.maplibregl-ctrl-scale) {
    border: 0;
    padding: 0 2px 6px;
    background-color: transparent;
    background-image: var(--scale-rule), var(--scale-left), var(--scale-right);
    background-repeat: no-repeat;
    background-position:
      center bottom,
      left bottom,
      right bottom;
    background-size:
      100% 6px,
      auto,
      auto;
    font-family: var(--font-mono);
    font-size: var(--size-label);
    font-variant-numeric: tabular-nums;
    letter-spacing: var(--tracking-label);
    color: var(--ink-soft);
    /* A halo rather than a panel. This is the one label on the page that can end up over open
       ocean, coastline or a data surface depending on where the camera is, and a box of paper
       under it would be a box of paper in the middle of the map. */
    text-shadow:
      0 0 3px var(--paper),
      0 0 6px var(--paper);
  }

  /*
    The attribution, which is a licence notice before it is furniture.

    Restyled, never shrunk: it keeps the body's own reading size rather than MapLibre's 10px, and
    it sits on opaque paper rather than a half-transparent white so it stays readable over an ocean
    at any zoom. The radius goes, the fill becomes paper, and the links take the page's rust.
  */
  .shell :global(.maplibregl-ctrl.maplibregl-ctrl-attrib) {
    padding: 0.2rem 0.5rem;
    border-radius: 0;
    background-color: var(--paper);
    color: var(--ink-soft);
    font-family: var(--font-mono);
    font-size: var(--size-margin);
    line-height: 1.5;
  }

  .shell :global(.maplibregl-ctrl-attrib a) {
    color: var(--rust);
  }

  /* The (i) that opens it. MapLibre's is a blue disc with a glyph in it; this is the same drawn box
     the zoom buttons wear, with the mark left as a letter because a hand-drawn "i" at nine pixels
     is a smudge rather than a character. */
  .shell :global(.maplibregl-ctrl-attrib summary.maplibregl-ctrl-attrib-button) {
    border-radius: 0;
    background-color: transparent;
    background-image: var(--ctrl-info);
    color: var(--ink-soft);
    font-family: var(--font-mono);
    font-size: var(--size-label);
    font-style: italic;
    text-align: center;
    line-height: 24px;
  }

  .shell :global(.maplibregl-ctrl-attrib summary.maplibregl-ctrl-attrib-button)::before {
    content: "i";
  }

  .shell :global(.maplibregl-ctrl-attrib.maplibregl-compact-show .maplibregl-ctrl-attrib-button) {
    background-color: var(--paper-sunken);
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

  /*
    The leaf that turns.

    Named so the View Transitions API captures this and nothing else -- `base.css` switches the
    root snapshot off, so MapLibre's canvas is never frozen and the globe keeps rendering while the
    paper turns over it. The paper turns, the world does not.
  */
  .shell__sheet {
    view-transition-name: leaf;
    pointer-events: auto;
    /* Full width by default. The `68vw` cap that keeps the globe visible beside it is only sane
       once there is a globe worth seeing: at 390px it left a useless 32% strip of sphere and shrank
       the claim to a column of two-word lines. */
    max-width: 52rem;
    max-height: 100%;
    /* The paper is `Sheet`'s: ground, grain, torn edge, shadow. This is only where it sits. */
    display: flex;
    animation: settle var(--draw) var(--ease-pen) both;
  }

  /* Column, and every link in the chain needs `min-height: 0`. Without the direction the leaf is a
     row item with `overflow-y: auto` and collapses to a zero-height box -- the claim is still in the
     DOM, still has its text, and is not visible, which is how the suite found it. */
  .shell__sheet :global(.sheet) {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }

  .shell__leaf {
    flex: 1;
    min-height: 0;
    padding: var(--gap-wide) var(--gap-wide) var(--gap-wide) calc(var(--gap-wide) + 0.4rem);
    overflow-y: auto;
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
