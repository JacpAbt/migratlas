<script lang="ts">
  import type { GeoJSONSource, Map as MapLibreMap } from "maplibre-gl";

  import { addDrawnCoast, createGlobe, setHatch, styleReady } from "../../globe/map";
  import { addContour } from "../../layers/contour";
  import { addSeasonal } from "../../layers/seasonal";
  import { addSeries } from "../../layers/series";
  import { addTracks } from "../../layers/tracks";
  import { addSurface } from "../../layers/surface";
  import { loadManifest, type LoadedLayer } from "../../layers/types";
  import { still } from "../../state/turn";
  import { nightPolygon } from "../../layers/terminator";
  import { addDetectability, type DetectabilityDocument } from "../../layers/detectability";
  import { SpeciesSelection } from "../../layers/selection";
  import type { View } from "../story";

  let {
    base,
    view,
    week = 0,
    instant,
    onready,
  }: {
    base: string;
    /** Where to point. Reassigning it flies the camera; it is never read back. */
    view: View | null;
    week?: number;
    /** Drives the night terminator. Not decoration on a page about nocturnal passage. */
    instant: Date;
    onready?: (report: {
      layers: LoadedLayer[];
      detectability: DetectabilityDocument | null;
      selection: SpeciesSelection;
      map: MapLibreMap;
    }) => void;
  } = $props();

  let container: HTMLDivElement;
  let map: MapLibreMap | undefined;
  let loaded = $state<LoadedLayer[]>([]);
  let failures = $state<string[]>([]);

  // MapLibre owns its own lifecycle and does not want to be re-created, so this runs once and
  // everything after it is an imperative call rather than a re-render. That is the whole reason
  // Svelte was chosen over a virtual DOM here: nothing tries to reconcile the canvas.
  $effect(() => {
    const instance = createGlobe(container, base);
    map = instance;

    // Startup phases, marked so the perf budget can say *where* the time went. It was one number
    // -- "ready in N ms" -- which doubled on CI and named nothing. `performance.measure` costs a
    // timestamp and turns the next regression into a reading rather than a bisect.
    const since = performance.now();
    const phases: Record<string, number> = {};
    let last = since;
    const mark = (name: string) => {
      const now = performance.now();
      phases[name] = Math.round(now - last);
      last = now;
    };

    void (async () => {
      await styleReady(instance);
      mark("style");
      // Before the data layers, and it has to be after the style: `addImage` needs somewhere to put
      // the image. Until this runs the land draws as a flat fill, which is why the layer keeps a
      // `fill-color` under its pattern.
      setHatch(instance);
      mark("hatch");
      // Survivable, and deliberately so: `addDrawnCoast` only dims the surveyed coastline once the
      // drawn one is in the style, so losing this costs the hand rather than the shoreline.
      try {
        await addDrawnCoast(instance, base);
      } catch (error) {
        failures = [...failures, `coastline: ${String(error)}`];
      }
      mark("coastline");
      addNightShade(instance);
      const manifest = await loadManifest(base);
      mark("manifest");
      // At once, not one after another. This was a `for` loop awaiting each layer in turn, which
      // made the globe's load time the *sum* of four round trips instead of the longest one --
      // invisible on a fast connection and worth seven seconds on CI, where latency dominates.
      //
      // `Promise.all` keeps `added` in manifest order, so the panel still lists layers in the order
      // the manifest declares. What it does not preserve is the order `addLayer` is called in, so
      // the style's own z-order is now completion order. That is acceptable here and is not an
      // accident: the four layers cover different oceans and continents, each has its own toggle,
      // and the one thing that genuinely depends on being underneath -- the detectability wash --
      // is added after this block and searches the style for what to sit beneath.
      const settled = await Promise.all(
        manifest.map(async (meta) => {
          try {
            if (meta.kind === "series") return await addSeries(instance, meta, base, week);
            if (meta.kind === "tracks") return await addTracks(instance, meta, base);
            if (meta.kind === "contour") return await addContour(instance, meta, base, week);
            if (meta.kind === "seasonal") {
              const siblings = manifest.filter((m) => m.name !== meta.name).map((m) => m.name);
              return await addSeasonal(instance, meta, base, week, siblings);
            }
            return await addSurface(instance, meta, base);
          } catch (error) {
            failures = [...failures, `${meta.name}: ${String(error)}`];
            return null;
          }
        }),
      );
      const added: LoadedLayer[] = settled.filter((one) => one !== null);
      mark("layers");
      // Added after the manifest layers so it can find them in the style and insert itself
      // beneath. A missing assessment costs the layer, not the globe.
      let assessment: DetectabilityDocument | null = null;
      try {
        const [layer, document_] = await addDetectability(instance, base);
        added.push(layer);
        assessment = document_;
      } catch (error) {
        failures = [...failures, `detectability: ${String(error)}`];
      }
      mark("detectability");

      loaded = added;

      // Behind ?debug, matching the old shell, so a browser test can read camera and layer state
      // from MapLibre rather than inferring it from pixels -- and so nothing is exposed to a
      // visitor who did not ask for it.
      if (new URLSearchParams(location.search).has("debug")) {
        (window as unknown as { migratlas: unknown }).migratlas = {
          map: instance,
          loaded: added,
          phases,
          totalMs: Math.round(performance.now() - since),
        };
      }

      onready?.({
        layers: added,
        detectability: assessment,
        selection: new SpeciesSelection(instance),
        map: instance,
      });
    })();

    return () => {
      instance.remove();
      map = undefined;
    };
  });

  // Camera and visibility follow the view. Split from the setup effect so a claim change costs a
  // flyTo and a few visibility properties rather than tearing the map down.
  $effect(() => {
    if (!map || !view || loaded.length === 0) return;

    for (const layer of loaded) {
      layer.setVisible(view.layers.includes(layer.meta.name));
    }

    map.flyTo({
      center: view.center,
      zoom: view.zoom,
      // Long and eased: the flight is meant to be followed, not endured. Read from the motion token
      // so `prefers-reduced-motion` zeroes it in one place along with everything else.
      duration: reducedMotion() ? 0 : 2200,
      essential: true,
    });
  });

  $effect(() => {
    for (const layer of loaded) layer.showWeek?.(week);
  });

  $effect(() => {
    const source = map?.getSource("night") as GeoJSONSource | undefined;
    source?.setData(nightPolygon(instant));
  });

  /**
   * The dusk veil.
   *
   * Kept from the old shell rather than dropped with it: this globe's headline layer is *nocturnal*
   * passage, so where night currently is says something about when the animals fly. A cool veil and
   * not a blackout -- on parchment a dark fill reads as a hole in the sphere, and the night side
   * still has to show its coastlines and its data.
   */
  function addNightShade(instance: MapLibreMap): void {
    instance.addSource("night", { type: "geojson", data: nightPolygon(instant) });
    const firstSymbol = instance.getStyle().layers.find((l) => l.type === "symbol")?.id;
    instance.addLayer(
      {
        id: "night-shade",
        type: "fill",
        source: "night",
        paint: { "fill-color": nightShade(), "fill-opacity": 0.17 },
      },
      firstSymbol,
    );
  }

  /**
   * The dusk veil's colour, from the token.
   *
   * It has to invert with the surface and not merely shift. On parchment the unlit side is a cool
   * darkening; on black paper a darkening is invisible, so the token holds a pale blue there and
   * the same 17% fill reads as moonlight instead of as a hole.
   */
  function nightShade(): string {
    return (
      getComputedStyle(document.documentElement).getPropertyValue("--night-shade").trim() ||
      "#41566b"
    );
  }

  /** Read from the token rather than from `matchMedia` twice, so one block controls all motion. */
  function reducedMotion(): boolean {
    return still();
  }
</script>

<div class="globe" bind:this={container} role="application" aria-label="Interactive globe"></div>

{#if failures.length > 0}
  <!-- A layer that fails must not take the globe with it, and must not fail silently either: a
       blank sphere and a broken fetch look identical to whoever has to debug it. -->
  <p class="globe__failures" role="status">
    {failures.length} layer{failures.length > 1 ? "s" : ""} could not be drawn: {failures.join("; ")}
  </p>
{/if}

<style>
  .globe {
    position: absolute;
    inset: 0;
    /* Behind everything the shell draws. The globe is the index to the arguments, not the subject,
       so it never competes with the claim in front of it. */
    z-index: 0;
  }

  .globe__failures {
    position: absolute;
    bottom: 0.5rem;
    left: 50%;
    z-index: 3;
    transform: translateX(-50%);
    margin: 0;
    padding: var(--gap-hair) var(--gap-tight);
    background: var(--paper);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    font-family: var(--font-mono);
    font-size: var(--size-margin);
    color: var(--rust);
  }

  /*
    Moved here from `shell/Shell.svelte` on 2026-08-21, which is why that file no longer exists to
    look at -- and it was a regression for as long as it lived there.

    Every rule below was scoped to `.shell`, so the moment the book became the front door the map in
    the world chapter lost all of it -- MapLibre's own white rounded boxes, grey drop shadows and
    fixed near-black icons came back, on paper, which is the exact thing these rules exist to
    prevent. `notebook.spec.ts` caught it the day those tests moved to the book, which is a fair
    argument for moving tests rather than deleting them.

    The component that mounts MapLibre is the honest owner: `.globe` rather than `.shell`, so the
    furniture follows the map wherever it is mounted instead of following one page.
  */
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
  .globe :global(.maplibregl-ctrl-group:not(:empty)) {
    background: none;
    border-radius: 0;
    box-shadow: none;
  }

  .globe :global(.maplibregl-ctrl-group button) {
    /* The separator line between stacked buttons: each has its own drawn box now, so a border
       between them draws a straight line across two wobbling ones. */
    border: 0;
    margin-bottom: 3px;
    background-repeat: no-repeat;
    background-position: center;
  }

  /* The icons are MapLibre's own SVG data URIs on an inner span, in a fixed near-black that follows
     no surface. Cleared, and both the mark and the box drawn on the button itself. */
  .globe :global(.maplibregl-ctrl-group .maplibregl-ctrl-icon) {
    background-image: none;
  }

  .globe :global(.maplibregl-ctrl-zoom-in) {
    background-image: var(--ctrl-zoom-in);
  }

  .globe :global(.maplibregl-ctrl-zoom-out) {
    background-image: var(--ctrl-zoom-out);
  }

  .globe :global(.maplibregl-ctrl-globe) {
    background-image: var(--ctrl-globe);
  }

  .globe :global(.maplibregl-ctrl-globe-enabled) {
    background-image: var(--ctrl-globe-enabled);
  }

  .globe :global(.maplibregl-ctrl-group button:hover) {
    background-color: transparent;
    filter: contrast(1.4);
  }

  /* MapLibre paints its own blue glow on focus, including for a mouse click. Rust, and only for a
     keyboard, which is the same rule `base.css` applies to everything else. */
  .globe :global(.maplibregl-ctrl-group button:focus) {
    box-shadow: none;
  }

  .globe :global(.maplibregl-ctrl-group button:focus-visible) {
    outline: 2px solid var(--rust);
    outline-offset: -2px;
  }

  /*
    The scale bar: a measure, drawn.

    Three images and only one of them stretches. MapLibre sets this element's width in pixels to
    whatever the current zoom makes a round distance, so the rule has to follow that width exactly
    -- it is the measurement. The end ticks are pinned to each end at their drawn size.
  */
  .globe :global(.maplibregl-ctrl-scale) {
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
  .globe :global(.maplibregl-ctrl.maplibregl-ctrl-attrib) {
    padding: 0.2rem 0.5rem;
    border-radius: 0;
    background-color: var(--paper);
    color: var(--ink-soft);
    font-family: var(--font-mono);
    font-size: var(--size-margin);
    line-height: 1.5;
    /* Opened, it is a readable column, not a banner: seven citations at full map width once
       covered the middle third of the sphere and every radar station with it. */
    max-width: min(56ch, 70vw);
  }

  .globe :global(.maplibregl-ctrl-attrib a) {
    color: var(--rust);
  }

  /* The (i) that opens it. MapLibre's is a blue disc with a glyph in it; this is the same drawn box
     the zoom buttons wear, with the mark left as a letter because a hand-drawn "i" at nine pixels
     is a smudge rather than a character. */
  .globe :global(.maplibregl-ctrl-attrib summary.maplibregl-ctrl-attrib-button) {
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

  .globe :global(.maplibregl-ctrl-attrib summary.maplibregl-ctrl-attrib-button)::before {
    content: "i";
  }

  .globe :global(.maplibregl-ctrl-attrib.maplibregl-compact-show .maplibregl-ctrl-attrib-button) {
    background-color: var(--paper-sunken);
  }

  /*
    The station popup: a specimen label, not a dialog.

    MapLibre ships it as a white rounded card with its own sans stack, and the fill does not
    follow the surface -- so on night the page's tokens turned the text chalk while the card
    stayed white, and the label all but vanished. Paper, ink and mono, like the attribution:
    it reports measurements, it is not pressed, so it gets no drawn box.
  */
  .globe :global(.maplibregl-popup-content) {
    padding: 0.6rem 0.9rem 0.7rem;
    border-radius: 0;
    background: var(--paper);
    box-shadow: var(--shadow-sheet);
    color: var(--ink);
    font-family: var(--font-body);
    font-size: var(--size-margin);
    letter-spacing: var(--tracking-body);
    line-height: 1.5;
  }

  /* The pointer is a border-triangle MapLibre colours white, one border per anchor; every
     anchor has to follow the paper or the tip gives the old card away. */
  .globe :global(.maplibregl-popup-anchor-bottom .maplibregl-popup-tip),
  .globe :global(.maplibregl-popup-anchor-bottom-left .maplibregl-popup-tip),
  .globe :global(.maplibregl-popup-anchor-bottom-right .maplibregl-popup-tip) {
    border-top-color: var(--paper);
  }

  .globe :global(.maplibregl-popup-anchor-top .maplibregl-popup-tip),
  .globe :global(.maplibregl-popup-anchor-top-left .maplibregl-popup-tip),
  .globe :global(.maplibregl-popup-anchor-top-right .maplibregl-popup-tip) {
    border-bottom-color: var(--paper);
  }

  .globe :global(.maplibregl-popup-anchor-left .maplibregl-popup-tip) {
    border-right-color: var(--paper);
  }

  .globe :global(.maplibregl-popup-anchor-right .maplibregl-popup-tip) {
    border-left-color: var(--paper);
  }

  /* A station id is an identifier, so it is set as one. */
  .globe :global(.maplibregl-popup-content strong) {
    font-family: var(--font-mono);
    font-size: var(--size-body);
    font-weight: 500;
    letter-spacing: var(--tracking-label);
  }

  .globe :global(.maplibregl-popup-content table) {
    margin: 0.3rem 0;
    border-collapse: collapse;
  }

  .globe :global(.maplibregl-popup-content th) {
    padding: 0.1rem 0.6rem 0.1rem 0;
    color: var(--ink-soft);
    font-weight: 400;
    text-align: left;
  }

  .globe :global(.maplibregl-popup-content td) {
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
  }

  .globe :global(.maplibregl-popup-content .caveat) {
    margin: 0.2rem 0 0;
    color: var(--pencil);
    font-size: var(--size-label);
    line-height: 1.55;
  }

  /* MapLibre's close button, kept bare: ink instead of its fixed near-black, a wash on hover
     like every other control, and no white disc behind either state. */
  .globe :global(.maplibregl-popup-close-button) {
    padding: 0 0.4rem;
    border-radius: 0;
    color: var(--ink-soft);
    font-size: 1rem;
  }

  .globe :global(.maplibregl-popup-close-button:hover) {
    background-color: var(--paper-sunken);
    color: var(--ink);
  }
</style>
