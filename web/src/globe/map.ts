import { layers, namedFlavor } from "@protomaps/basemaps";
import {
  GlobeControl,
  Map as MapLibreMap,
  NavigationControl,
  ScaleControl,
  addProtocol,
} from "maplibre-gl";
import { Protocol } from "pmtiles";

import "maplibre-gl/dist/maplibre-gl.css";

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
      layers: layers("protomaps", namedFlavor("dark"), { lang: "en" }),
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
