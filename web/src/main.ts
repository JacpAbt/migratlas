import type { GeoJSONSource } from "maplibre-gl";

import { createGlobe } from "./globe/map";
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

function notice(message: string): void {
  noticeEl.textContent = message;
  noticeEl.hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => (noticeEl.hidden = true), 6000);
}

map.on("error", (event) => {
  const message = event.error?.message ?? "unknown map error";
  notice(`Basemap: ${message}`);
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
