import type { GeoJSONSource } from "maplibre-gl";

import { createGlobe, styleReady, type BasemapState } from "./globe/map";
import { addSeries } from "./layers/series";
import { addSurface } from "./layers/surface";
import { nightPolygon } from "./layers/terminator";
import { loadManifest, type LoadedLayer } from "./layers/types";
import { mountFindings } from "./panels/findings";
import { SpeciesSelection } from "./layers/selection";
import { SpeciesSurfaces, TaxonIndex, type TaxonHit } from "./search/taxon";
import { Clock, formatInstant } from "./state/time";

import "./styles.css";

const el = <T extends HTMLElement>(id: string): T => {
  const node = document.getElementById(id);
  if (!node) throw new Error(`missing #${id}`);
  return node as T;
};

const map = createGlobe(el("globe"), import.meta.env.BASE_URL);
const clock = new Clock();

// Exposed only under ?debug=1, so the map can be inspected from a console or a test harness.
// MapLibre creates its GL context without preserveDrawingBuffer, which makes pixel readback
// useless -- queryRenderedFeatures is the only reliable way to assert a layer draws.
//
// `ready` is the important part: a test that polls isStyleLoaded cannot tell "still fetching"
// from "gave up and rendered nothing", which is how a blank globe shipped once already.
let announceReady: (report: ReadyReport) => void = () => {};
const ready = new Promise<ReadyReport>((resolve) => (announceReady = resolve));

interface ReadyReport {
  basemap: BasemapState;
  layers: string[];
  /** Features per layer, so a test can check a decode against the sidecar's cell count. */
  cells: Record<string, number>;
  /** Where each layer's data actually is, so a camera can be pointed at it. */
  centers: Record<string, [number, number]>;
}

if (new URLSearchParams(location.search).has("debug")) {
  (window as unknown as { migratlas: unknown }).migratlas = { map, clock, ready };
}

// --- Layers, once the style is usable ---------------------------------------
// Each layer carries the generalisation the ethics gate applied. Showing it is required, so
// it lives next to the toggle rather than buried in an about page.
const layerList = el<HTMLUListElement>("layer-list");
const layerTerms = el("layer-terms");
const visibleLayers = new Set<string>();

// Independent of the map: the findings are text and should appear even if the globe is still
// fetching tiles, or fails to.
void mountFindings(el("findings-body"), import.meta.env.BASE_URL);

void (async () => {
  const basemap = await styleReady(map);
  addNightShade();
  const loaded = await addDataLayers();
  announceReady({
    basemap,
    layers: loaded.map(({ meta }) => meta.name),
    cells: Object.fromEntries(loaded.map(({ meta, cells }) => [meta.name, cells])),
    centers: Object.fromEntries(loaded.map(({ meta, center }) => [meta.name, center])),
  });
})();

function addNightShade(): void {
  map.addSource("night", { type: "geojson", data: nightPolygon(clock.instant) });

  // Under the labels, so place names stay legible on the dark side.
  const firstSymbol = map.getStyle().layers.find((l) => l.type === "symbol")?.id;
  map.addLayer(
    {
      id: "night-shade",
      type: "fill",
      source: "night",
      // A cool dusk veil, not a blackout: on a parchment basemap a dark fill reads as a hole,
      // and the night side still has to show its coastlines and its data.
      paint: { "fill-color": "#41566b", "fill-opacity": 0.17 },
    },
    firstSymbol,
  );

  clock.subscribe((_, instant) => {
    const source = map.getSource("night") as GeoJSONSource | undefined;
    source?.setData(nightPolygon(instant));
  });
}

async function addDataLayers(): Promise<LoadedLayer[]> {
  const manifest = await loadManifest(import.meta.env.BASE_URL);
  if (manifest.length === 0) {
    layerList.replaceChildren(emptyItem("No layers built yet — run make build-layers"));
    return [];
  }

  const loaded: LoadedLayer[] = [];
  for (const meta of manifest) {
    try {
      loaded.push(
        meta.kind === "series"
          ? await addSeries(map, meta, import.meta.env.BASE_URL, clock.week)
          : await addSurface(map, meta, import.meta.env.BASE_URL),
      );
    } catch (error) {
      notice(`Layer ${meta.name}: ${String(error)}`);
    }
  }
  renderLayerList(loaded);

  // One subscription for every time-indexed layer. Each ignores a repeat of its current
  // week, so a playing clock at 60 fps costs nothing between week boundaries.
  const timed = loaded.filter((layer) => layer.showWeek);
  if (timed.length > 0) {
    clock.subscribe(() => {
      for (const layer of timed) layer.showWeek?.(clock.week);
    });
  }
  return loaded;
}

function emptyItem(text: string): HTMLLIElement {
  const item = document.createElement("li");
  item.className = "empty";
  item.textContent = text;
  return item;
}

/** Kept so a species selection can name the layer and terms its surface came from. */
let loadedLayers: LoadedLayer[] = [];

function renderLayerList(loaded: LoadedLayer[]): void {
  loadedLayers = loaded;
  layerList.replaceChildren(
    ...loaded.map(({ meta, setVisible }) => {
      const item = document.createElement("li");
      const label = document.createElement("label");
      const toggle = document.createElement("input");
      toggle.type = "checkbox";
      toggle.checked = true;
      visibleLayers.add(meta.name);
      toggle.addEventListener("change", () => {
        setVisible(toggle.checked);
        if (toggle.checked) visibleLayers.add(meta.name);
        else visibleLayers.delete(meta.name);
        showTerms(loaded.filter((entry) => visibleLayers.has(entry.meta.name)));
      });

      const text = document.createElement("span");
      text.textContent = meta.title;
      text.title = `${meta.description}

${meta.caveats}`;

      const kind = document.createElement("em");
      kind.textContent = meta.value_kind.replace(/_/g, " ");

      label.append(toggle, text, kind);
      item.append(label);
      return item;
    }),
  );
  showTerms(loaded);
}

function showTerms(loaded: LoadedLayer[]): void {
  layerTerms.textContent = loaded
    .map(({ terms }) => terms["dwc:dataGeneralizations"])
    .filter((value, index, all) => all.indexOf(value) === index)
    .join(" ");
}

// --- Time controls ----------------------------------------------------------
const daySlider = el<HTMLInputElement>("time-slider");
const utcSlider = el<HTMLInputElement>("utc-slider");
const timeLabel = el<HTMLOutputElement>("time-label");
const playButton = el<HTMLButtonElement>("play");

clock.subscribe((state, instant) => {
  timeLabel.textContent = `${formatInstant(instant)} UTC · week ${clock.week + 1}`;
  if (daySlider.valueAsNumber !== state.day) daySlider.value = String(state.day);
  if (utcSlider.valueAsNumber !== state.minute) utcSlider.value = String(state.minute);
});

daySlider.addEventListener("input", () => clock.set({ day: daySlider.valueAsNumber }));
utcSlider.addEventListener("input", () => clock.set({ minute: utcSlider.valueAsNumber }));

playButton.addEventListener("click", () => {
  clock.toggle();
  playButton.textContent = clock.playing ? "Pause" : "Play";
  playButton.setAttribute("aria-pressed", String(clock.playing));
});

// --- Species search ---------------------------------------------------------
// Every entry in the index has a published surface behind it, so a hit is never a dead end.
const searchInput = el<HTMLInputElement>("taxon-search");
const resultList = el<HTMLUListElement>("taxon-results");
const surfaces = new SpeciesSurfaces(import.meta.env.BASE_URL);
const selection = new SpeciesSelection(map);

TaxonIndex.load(`${import.meta.env.BASE_URL}taxon-index.json`)
  .then((index) => {
    searchInput.placeholder = `Search ${index.size.toLocaleString()} animals…`;
    searchInput.addEventListener("input", () => render(index.search(searchInput.value)));
  })
  .catch(() => {
    searchInput.disabled = true;
    searchInput.placeholder = "Species index unavailable";
  });

function render(hits: TaxonHit[]): void {
  resultList.replaceChildren(
    ...hits.map((hit) => {
      const item = document.createElement("li");
      item.setAttribute("role", "option");
      item.innerHTML = `<strong></strong><em></em><span></span>`;
      // Scientific name as the heading when GBIF has no English name, rather than an empty row.
      item.querySelector("strong")!.textContent = hit.vernacular || hit.scientific;
      item.querySelector("em")!.textContent = hit.vernacular ? hit.scientific : "";
      // The layer, not just the count: 95 taxa are in both marine sources, and two rows reading
      // only "9,712 cells" and "1,312 cells" give the viewer no way to choose between them.
      item.querySelector("span")!.textContent =
        `${hit.cells.toLocaleString()} cells · ${hit.layer_title}`;
      item.addEventListener("click", () => void select(hit));
      return item;
    }),
  );
  resultList.hidden = hits.length === 0;
}

async function select(hit: TaxonHit): Promise<void> {
  searchInput.value = hit.vernacular || hit.scientific;
  resultList.hidden = true;

  let grid;
  try {
    grid = await surfaces.get(hit);
  } catch (error) {
    notice(`Could not load ${hit.scientific}: ${String(error)}`);
    return;
  }
  if (!grid) {
    // Should not happen -- the index is generated from the shards -- so say so plainly rather
    // than failing silently, because it would mean the two went out of step.
    notice(`No surface for ${hit.scientific} (GBIF ${hit.key}); the index and shards disagree.`);
    return;
  }

  const { center, cells } = selection.show(hit, grid);
  map.flyTo({ center, zoom: 1.9, speed: 0.9 });

  const layer = loadedLayers.find((entry) => entry.meta.name === grid.layer);
  const name = hit.vernacular ? `${hit.vernacular} (${hit.scientific})` : hit.scientific;
  notice(
    `${name} — ${cells.toLocaleString()} occupied cells from ${layer?.meta.title ?? grid.layer}. ` +
      `${layer?.terms["dwc:dataGeneralizations"] ?? ""}`.trim(),
  );
}

searchInput.addEventListener("blur", () => {
  // Deferred so a click on a result registers before the list is hidden.
  setTimeout(() => (resultList.hidden = true), 150);
});

// --- Notices ----------------------------------------------------------------
const noticeEl = el("notice");
// Not `number`: @types/node is in scope for vite.config.ts, so setTimeout resolves to
// the Node overload returning Timeout.
let noticeTimer: ReturnType<typeof setTimeout> | undefined;

function persistentNotice(message: string): void {
  noticeEl.textContent = message;
  noticeEl.hidden = false;
  clearTimeout(noticeTimer);
}

function notice(message: string): void {
  noticeEl.textContent = message;
  noticeEl.hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => (noticeEl.hidden = true), 6000);
}

// A failed basemap is a persistent condition, not a transient one: it must not scroll away
// after a few seconds, and it must be distinguishable from the app being broken. It is also
// reported once rather than per tile, because a dead tileset emits an error for every request.
let basemapFailed = false;
map.on("error", (event) => {
  const message = event.error?.message ?? "unknown map error";
  // sourceId is present on source-related error events but absent from the base ErrorEvent
  // type, so it is read defensively rather than asserted.
  const sourceId = (event as { sourceId?: string }).sourceId ?? "";
  if (/pmtiles|protomaps|sprite|glyph|tile/i.test(message) || sourceId === "protomaps") {
    if (basemapFailed) return;
    basemapFailed = true;
    persistentNotice(
      "Detailed basemap unavailable — the configured tileset could not be reached. " +
        "Coastlines and the data layers are served from this app and are unaffected.",
    );
    return;
  }
  notice(message);
});

// --- Performance budget -----------------------------------------------------
// The README commits to a heap ceiling, so it should be observable rather than
// aspirational. Enable with ?perf=1.
interface MemoryInfo {
  usedJSHeapSize: number;
}

if (new URLSearchParams(location.search).has("perf")) {
  const perfEl = el("perf");
  perfEl.hidden = false;
  let frames = 0;
  let last = performance.now();

  const sample = (now: number): void => {
    frames++;
    if (now - last >= 1000) {
      const memory = (performance as Performance & { memory?: MemoryInfo }).memory;
      const heap = memory ? `${(memory.usedJSHeapSize / 1_048_576).toFixed(0)} MB` : "n/a";
      perfEl.textContent = `${frames} fps · heap ${heap}`;
      frames = 0;
      last = now;
    }
    requestAnimationFrame(sample);
  };
  requestAnimationFrame(sample);
}
