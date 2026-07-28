import { layers, namedFlavor } from "@protomaps/basemaps";
import {
  GlobeControl,
  Map as MapLibreMap,
  NavigationControl,
  ScaleControl,
  addProtocol,
  setWorkerUrl,
} from "maplibre-gl";
// MapLibre computes its own worker URL at runtime from a template string --
// `new URL(`./${name}`, import.meta.url)` -- which no bundler can statically analyse, so the
// worker is never emitted and 404s. MapLibre then fails *silently*: sources never finish
// loading, no tiles are requested, and the canvas stays empty at a healthy 60 fps with no
// console error. setWorkerUrl is the sanctioned way to take over.
//
// `?worker&url` and not `?url`: the worker imports maplibre-gl-shared.mjs, which a plain
// file copy leaves dangling. A dev server's SPA fallback then answers that import with
// index.html and a 200, so the worker parses HTML as JavaScript and dies. ?worker bundles
// the dependency in.
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { Protocol } from "pmtiles";

import "maplibre-gl/dist/maplibre-gl.css";

setWorkerUrl(workerUrl);

const ASSETS = "https://protomaps.github.io/basemaps-assets";

/**
 * Protomaps' public demo tileset by default. Production self-hosts on object storage;
 * see ADR 0001 for why not on a Pages product.
 */
const BASEMAP =
  import.meta.env.VITE_BASEMAP_PMTILES ?? "https://demo-bucket.protomaps.com/v4.pmtiles";

let protocolRegistered = false;

export function createGlobe(container: HTMLElement): MapLibreMap {
  // The protocol is global to maplibre, so registering twice throws under HMR.
  if (!protocolRegistered) {
    addProtocol("pmtiles", new Protocol().tile);
    protocolRegistered = true;
  }

  const map = new MapLibreMap({
    container,
    style: {
      version: 8,
      glyphs: `${ASSETS}/fonts/{fontstack}/{range}.pbf`,
      sprite: `${ASSETS}/sprites/v4/dark`,
      sources: {
        protomaps: {
          type: "vector",
          url: `pmtiles://${BASEMAP}`,
          attribution:
            '<a href="https://protomaps.com">Protomaps</a> © <a href="https://openstreetmap.org">OpenStreetMap</a>',
        },
      },
      layers: [
        // Drawn beneath everything, so the globe still reads as a globe when the basemap
        // tiles are unavailable -- a self-hosted tileset may not be configured yet, and the
        // data layers are useful without it. Without this the sphere is invisible and the
        // failure looks like the whole app being broken.
        { id: "ocean", type: "background", paint: { "background-color": "#0b1a2b" } },
        ...layers("protomaps", namedFlavor("dark"), { lang: "en" }),
      ],
    },
    center: [10, 30],
    zoom: 1.4,
    // Nothing here needs sub-metre detail, and capping zoom bounds tile memory.
    maxZoom: 12,
    attributionControl: { compact: true },
    // Rendering at full devicePixelRatio on a 4K display triples fragment cost for no
    // visible gain on a globe.
    pixelRatio: Math.min(window.devicePixelRatio, 2),
  });

  map.addControl(new NavigationControl({ visualizePitch: false }), "bottom-right");
  map.addControl(new GlobeControl(), "bottom-right");
  map.addControl(new ScaleControl({ unit: "metric" }), "bottom-left");

  // setProjection before the style loads throws, so it has to wait for the event.
  map.once("style.load", () => {
    map.setProjection({ type: "globe" });
  });

  return map;
}
