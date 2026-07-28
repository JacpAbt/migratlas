import type { GeoJSONSource } from "maplibre-gl";

import { createGlobe } from "./globe/map";
import { addSurface, loadManifest, setSurfaceVisible, type LoadedLayer } from "./layers/surface";
import { nightPolygon } from "./layers/terminator";
import { TaxonIndex, type TaxonHit } from "./search/taxon";
import { Clock, formatInstant } from "./state/time";

import "./styles.css";

const el = <T extends HTMLElement>(id: string): T => {
  const node = document.getElementById(id);
  if (!node) throw new Error(`missing #${id}`);
  return node as T;
};

const map = createGlobe(el("globe"));
const clock = new Clock();

map.once("style.load", () => {
  map.addSource("night", { type: "geojson", data: nightPolygon(clock.instant) });

  // Under the labels, so place names stay legible on the dark side.
  const firstSymbol = map.getStyle().layers.find((l) => l.type === "symbol")?.id;
  map.addLayer(
    {
      id: "night-shade",
      type: "fill",
      source: "night",
      paint: { "fill-color": "#04070f", "fill-opacity": 0.45 },
    },
    firstSymbol,
  );

  clock.subscribe((_, instant) => {
    const source = map.getSource("night") as GeoJSONSource | undefined;
    source?.setData(nightPolygon(instant));
  });
});

// Exposed only under ?debug=1, so the map can be inspected from a console or a test
// harness. MapLibre creates its GL context without preserveDrawingBuffer, which makes pixel
// readback useless -- queryRenderedFeatures is the only reliable way to assert a layer draws.
if (new URLSearchParams(location.search).has("debug")) {
  (window as unknown as { migratlas: unknown }).migratlas = { map, clock };
}

// --- Published layers -------------------------------------------------------
// Each layer carries the generalisation the ethics gate applied. Showing it is required, so
// it lives next to the toggle rather than buried in an about page.
const layerList = el<HTMLUListElement>("layer-list");
const layerTerms = el("layer-terms");
const visibleLayers = new Set<string>();

map.once("style.load", () => {
  void (async () => {
    const manifest = await loadManifest(import.meta.env.BASE_URL);
    if (manifest.length === 0) {
      layerList.innerHTML = "<li class=\"empty\">No layers built yet — run make build-layers</li>";
      return;
    }

    const loaded: LoadedLayer[] = [];
    for (const meta of manifest) {
      try {
        loaded.push(await addSurface(map, meta, import.meta.env.BASE_URL));
      } catch (error) {
        notice(`Layer ${meta.name}: ${String(error)}`);
      }
    }
    renderLayerList(loaded);
  })();
});

function renderLayerList(loaded: LoadedLayer[]): void {
  layerList.replaceChildren(
    ...loaded.map(({ meta, terms }) => {
      const item = document.createElement("li");
      const label = document.createElement("label");
      const toggle = document.createElement("input");
      toggle.type = "checkbox";
      toggle.checked = true;
      visibleLayers.add(meta.name);
      toggle.addEventListener("change", () => {
        setSurfaceVisible(map, meta.name, toggle.checked);
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
const searchInput = el<HTMLInputElement>("taxon-search");
const resultList = el<HTMLUListElement>("taxon-results");

TaxonIndex.load(`${import.meta.env.BASE_URL}taxon-index.json`)
  .then((index) => {
    searchInput.placeholder = `Search ${index.size} animals…`;
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
      item.querySelector("strong")!.textContent = hit.vernacular;
      item.querySelector("em")!.textContent = hit.scientific;
      item.querySelector("span")!.textContent = hit.group;
      item.addEventListener("click", () => select(hit));
      return item;
    }),
  );
  resultList.hidden = hits.length === 0;
}

function select(hit: TaxonHit): void {
  searchInput.value = hit.vernacular;
  resultList.hidden = true;
  // Phase 0 has nothing to show yet. Saying so beats a silent no-op.
  notice(
    `${hit.vernacular} (GBIF ${hit.key}) — no published layer yet. ` +
      `Data layers arrive in Phase 1.`,
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
// after a few seconds, and it must be distinguishable from the app being broken. The data
// layers stay usable on the plain ocean background underneath.
let basemapFailed = false;
map.on("error", (event) => {
  const message = event.error?.message ?? "unknown map error";
  // sourceId is present on source-related error events but absent from the base ErrorEvent
  // type, so it is read defensively rather than asserted.
  const sourceId = (event as { sourceId?: string }).sourceId ?? "";
  const isBasemap = /pmtiles|protomaps|tile/i.test(message) || sourceId === "protomaps";
  if (isBasemap && !basemapFailed) {
    basemapFailed = true;
    persistentNotice(
      "Basemap tiles unavailable — the demo tileset could not be reached. Data layers " +
        "still work; set VITE_BASEMAP_PMTILES to a self-hosted tileset for coastlines.",
    );
    return;
  }
  if (!isBasemap) notice(message);
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
