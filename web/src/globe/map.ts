import { layers } from "@protomaps/basemaps";
import {
  GlobeControl,
  Map as MapLibreMap,
  NavigationControl,
  ScaleControl,
  addProtocol,
  setWorkerUrl,
  type LayerSpecification,
  type SourceSpecification,
  type StyleSpecification,
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

import { DRAWN_COAST, drawnCoast, drawnOpacity, trueOpacity } from "./coastline";
import { palette } from "./flavor";
import { GRATICULE, graticuleLayer, graticuleSource } from "./graticule";
import { HATCH, hatchTile } from "./hatch";

import "maplibre-gl/dist/maplibre-gl.css";

setWorkerUrl(workerUrl);

const ASSETS = "https://protomaps.github.io/basemaps-assets";

/**
 * Optional detailed basemap, self-hosted.
 *
 * There is deliberately no default. Protomaps' public demo bucket refuses the CORS preflight
 * for ranged requests -- a verified 403 `AccessForbidden` -- so it cannot load in any browser
 * from any origin, and shipping it as the default meant every visitor met a basemap error. Set
 * this to your own PMTiles URL on object storage; see ADR 0001.
 */
const DETAIL_PMTILES: string | undefined = import.meta.env.VITE_BASEMAP_PMTILES;

/** Whether the globe has street-level detail, or only its own coastlines. */
export type BasemapState = "detail" | "outline";

/**
 * Coastlines and borders, served from this app.
 *
 * Natural Earth 1:110m, ~210 KiB of geometry with every attribute stripped. It is the right
 * resolution for a globe, and it removes the entire class of failure where a third-party tile
 * host decides whether the map draws at all. Public domain, so it can simply be bundled.
 */
function outlineSources(baseUrl: string): Record<string, SourceSpecification> {
  const attribution = '<a href="https://www.naturalearthdata.com/">Natural Earth</a>';
  return {
    land: { type: "geojson", data: `${baseUrl}basemap/land.geojson`, attribution },
    borders: { type: "geojson", data: `${baseUrl}basemap/borders.geojson` },
    // Computed, not fetched. Seventeen lines of geometry are cheaper to generate than to request.
    [GRATICULE]: graticuleSource(),
  };
}

function outlineLayers(): LayerSpecification[] {
  const skin = palette();
  return [
    // Drawn beneath everything, so the sphere reads as a globe even before any data lands.
    { id: "ocean", type: "background", paint: { "background-color": skin.ocean } },
    // `fill-color` as well as the pattern, and it is not dead: MapLibre uses the colour whenever the
    // pattern image is missing, which is every frame between the style loading and `addImage`, and
    // any frame at all if the canvas that draws the tile is unavailable. Land the colour it hatches
    // to, so the fallback is the same land rather than a hole.
    {
      id: "land",
      type: "fill",
      source: "land",
      paint: { "fill-color": skin.land, "fill-pattern": HATCH },
    },
    // Between the land and its coastline, which is where a ruled grid sits on paper: over the fill,
    // under the ink.
    graticuleLayer(),
    {
      id: "coast",
      type: "line",
      source: "land",
      paint: { "line-color": skin.coast, "line-width": 0.7 },
    },
    {
      id: "borders",
      type: "line",
      source: "borders",
      paint: { "line-color": skin.border, "line-width": 0.5, "line-dasharray": [3, 2] },
    },
  ];
}

/**
 * Add the drawn coastline, and only then let the surveyed one step back.
 *
 * The order is the safety. The style ships with the true coast at full strength; the crossfade is
 * written here, after the drawn pass is actually in the style, so every way this can fail -- a fetch
 * that 404s, geometry that will not parse -- leaves an accurate coastline on screen rather than none.
 *
 * The fetch is the same URL the `land` source already pulled, so it is a cache hit and costs no
 * bytes. Building the strokes from the parsed data rather than shipping a second asset keeps the
 * payload where it was and keeps one geometry as the source of both.
 */
export async function addDrawnCoast(map: MapLibreMap, baseUrl: string): Promise<void> {
  const response = await fetch(`${baseUrl}basemap/land.geojson`);
  if (!response.ok) throw new Error(`land.geojson: ${response.status}`);
  const land = (await response.json()) as GeoJSON.FeatureCollection;

  map.addSource(DRAWN_COAST, { type: "geojson", data: drawnCoast(land) });
  map.addLayer(
    {
      id: DRAWN_COAST,
      type: "line",
      source: DRAWN_COAST,
      paint: {
        "line-color": palette().coast,
        "line-width": 0.9,
        "line-opacity": drawnOpacity() as never,
      },
    },
    "coast",
  );
  map.setPaintProperty("coast", "line-opacity", trueOpacity() as never);
}

/**
 * Put the hatch tile into the style, replacing any tile already there.
 *
 * `updateImage` rather than remove-and-add: removing an image a layer is currently using makes
 * MapLibre draw that fill as nothing until the replacement lands, which on a surface change is a
 * frame of continents that are not there.
 */
export function setHatch(map: MapLibreMap): void {
  const { data, pixelRatio } = hatchTile();
  if (map.hasImage(HATCH)) map.updateImage(HATCH, data);
  else map.addImage(HATCH, data, { pixelRatio });
}

/**
 * Recolour the sphere for the surface now in force.
 *
 * `setPaintProperty` rather than `setStyle`, which would drop every data source and re-fetch the
 * layers -- a second of blank globe and 450 KiB, to change four colours. The paint properties
 * survive a style that is already loaded, and the data layers repaint themselves.
 *
 * The hatch is redrawn rather than recoloured, for the reason every generated mark in this project
 * is: the palette is baked into the pixels.
 */
export function repaintBasemap(map: MapLibreMap): void {
  const skin = palette();
  if (map.getLayer("ocean")) map.setPaintProperty("ocean", "background-color", skin.ocean);
  if (map.getLayer("land")) map.setPaintProperty("land", "fill-color", skin.land);
  if (map.getLayer("coast")) map.setPaintProperty("coast", "line-color", skin.coast);
  if (map.getLayer("borders")) map.setPaintProperty("borders", "line-color", skin.border);
  if (map.getLayer(GRATICULE)) map.setPaintProperty(GRATICULE, "line-color", skin.coast);
  if (map.getLayer(DRAWN_COAST)) map.setPaintProperty(DRAWN_COAST, "line-color", skin.coast);
  if (map.hasImage(HATCH)) setHatch(map);
}

function style(baseUrl: string): StyleSpecification {
  const base: StyleSpecification = {
    version: 8,
    projection: { type: "globe" },
    sources: outlineSources(baseUrl),
    layers: outlineLayers(),
  };
  if (!DETAIL_PMTILES) return base;

  return {
    ...base,
    glyphs: `${ASSETS}/fonts/{fontstack}/{range}.pbf`,
    sprite: `${ASSETS}/sprites/v4/light`,
    sources: {
      ...base.sources,
      protomaps: { type: "vector", url: `pmtiles://${DETAIL_PMTILES}` },
    },
    // Above the outline, which then shows through only where detail tiles have not arrived.
    layers: [...base.layers, ...layers("protomaps", palette().flavor, { lang: "en" })],
  };
}

let protocolRegistered = false;

export function createGlobe(container: HTMLElement, baseUrl: string): MapLibreMap {
  // The protocol is global to maplibre, so registering twice throws under HMR.
  if (!protocolRegistered) {
    addProtocol("pmtiles", new Protocol().tile);
    protocolRegistered = true;
  }

  const map = new MapLibreMap({
    container,
    style: style(baseUrl),
    // Facing the Atlantic: the Americas and western Europe/Africa are both in view, so the
    // published layers are visible on the first frame rather than on the far side.
    center: [-45, 25],
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
  // With the others rather than in the opposite corner, which is MapLibre's default and where a
  // scale bar normally belongs. Here the bottom-left is the only part of the window contested by
  // three things at once: the index strip, the licence notice -- which is the full width of the
  // page, because it lists one credit per drawn layer -- and the claim sheet, which reaches the
  // left margin. Lifted clear of the notice it went under the sheet; left where it was it went
  // under the notice. The bottom-right corner is free at every width the scale is shown at.
  map.addControl(new ScaleControl({ unit: "metric" }), "bottom-right");

  return map;
}

/**
 * Resolve when the style is loaded, reporting how much basemap there is.
 *
 * Exists so the data layers wait in one place rather than in several `map.once` handlers, and
 * so a test can tell "still loading" from "loaded and drew nothing" -- the distinction a
 * blank-globe release once turned on.
 */
export function styleReady(map: MapLibreMap): Promise<BasemapState> {
  const state: BasemapState = DETAIL_PMTILES ? "detail" : "outline";
  if (map.isStyleLoaded()) return Promise.resolve(state);
  return new Promise((resolve) => map.once("style.load", () => resolve(state)));
}
