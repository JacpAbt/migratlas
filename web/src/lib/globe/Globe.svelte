<script lang="ts">
  import type { Map as MapLibreMap } from "maplibre-gl";

  import { createGlobe, styleReady } from "../../globe/map";
  import { addSeries } from "../../layers/series";
  import { addSurface } from "../../layers/surface";
  import { loadManifest, type LoadedLayer } from "../../layers/types";
  import { addDetectability, type DetectabilityDocument } from "../../layers/detectability";
  import { SpeciesSelection } from "../../layers/selection";
  import type { View } from "../story";

  let {
    base,
    view,
    week = 0,
    onready,
  }: {
    base: string;
    /** Where to point. Reassigning it flies the camera; it is never read back. */
    view: View | null;
    week?: number;
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

    void (async () => {
      await styleReady(instance);
      const manifest = await loadManifest(base);
      const added: LoadedLayer[] = [];
      for (const meta of manifest) {
        try {
          added.push(
            meta.kind === "series"
              ? await addSeries(instance, meta, base, week)
              : await addSurface(instance, meta, base),
          );
        } catch (error) {
          failures = [...failures, `${meta.name}: ${String(error)}`];
        }
      }
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

      loaded = added;

      // Behind ?debug, matching the old shell, so a browser test can read camera and layer state
      // from MapLibre rather than inferring it from pixels -- and so nothing is exposed to a
      // visitor who did not ask for it.
      if (new URLSearchParams(location.search).has("debug")) {
        (window as unknown as { migratlas: unknown }).migratlas = { map: instance, loaded: added };
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
