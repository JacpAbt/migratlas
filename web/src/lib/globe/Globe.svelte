<script lang="ts">
  import type { GeoJSONSource, Map as MapLibreMap } from "maplibre-gl";

  import { addDrawnCoast, createGlobe, setHatch, styleReady } from "../../globe/map";
  import { addSeries } from "../../layers/series";
  import { addSurface } from "../../layers/surface";
  import { loadManifest, type LoadedLayer } from "../../layers/types";
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
            return meta.kind === "series"
              ? await addSeries(instance, meta, base, week)
              : await addSurface(instance, meta, base);
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
    const draw = getComputedStyle(document.documentElement).getPropertyValue("--draw").trim();
    return draw === "0ms" || draw === "0s";
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
</style>
