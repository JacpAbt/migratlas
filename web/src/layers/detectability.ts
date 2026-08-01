/**
 * Where change could ever be measured, drawn under everything else.
 *
 * Not a quantity, so not on a ramp. The four statuses are different *kinds* of problem — no time
 * axis, effort not measured, series too short, and none of those — and putting them on a sequential
 * scale would invent an ordering they only partly have. The three that fail get greys close enough
 * in lightness that the map reads as "mostly grey" at a glance; the one that passes gets the
 * project's accent, which is the only thing that survives at globe zoom against them.
 *
 * It ships from `detectability.json` rather than through the layer manifest, because it is a report
 * about the lake rather than a slice of it: there is no upstream licence to attach and no
 * generalisation to declare, since the finest thing it states about anywhere is a one-degree cell.
 */

import type { ExpressionSpecification, Map as MapLibreMap } from "maplibre-gl";

import { gridToFeatures, type GridPayload, type LayerMeta, type LoadedLayer } from "./types";

interface Coverage {
  source_id: string;
  realm: string;
  ceiling: string;
  reason: string;
  effort_note: string;
  cells: number;
  detectable_cells: number;
  years: [number, number];
}

/** A source the gate holds and never draws. Rendered as a list, never as an absence. */
export interface Withheld {
  source_id: string;
  realm: string;
  taxon: string;
  sensitivity: string;
  reason: string;
  span: [number, number];
  individuals: number;
}

interface DetectabilityDocument {
  schema_version: number;
  min_years: number;
  grid: GridPayload & { categories: string[] };
  coverage: Coverage[];
  withheld: Withheld[];
  summary: Record<string, number>;
  caveat: string;
  method: string;
  supporting: string[];
}

const SUPPORTED_SCHEMA = 2;

const LAYER_ID = "detectability";

/**
 * One token per status, keyed by name so a reordering upstream cannot silently recolour the map.
 *
 * Read from CSS rather than written here, because the night surface has to reach them and these four
 * were picked to read as "mostly grey" against parchment -- they do not transfer to slate. The
 * accent for `detectable` is the same one the ledger uses for "change detected": against the greys
 * it is the only colour that survives at globe zoom. The first attempt drew it in the layer blue at
 * 55% opacity and the whole map vanished into the basemap, turning "grey is the finding" into
 * "there is nothing here".
 */
const TOKENS: Record<string, string> = {
  "no-time-axis": "--detect-none",
  "effort-not-measured": "--detect-no-effort",
  "too-short": "--detect-short",
  detectable: "--detect-yes",
};

const FALLBACK = "#b5afa3";

/** Resolve a token against the live surface. MapLibre paint takes colours, not custom properties. */
export function colourFor(status: string): string {
  const token = TOKENS[status];
  if (!token) return FALLBACK;
  const value = getComputedStyle(document.documentElement).getPropertyValue(token).trim();
  return value || FALLBACK;
}

/** Plain-language legend text. The status slug is precise and says nothing to a first-time reader. */
const MEANS: Record<string, string> = {
  "no-time-axis": "one pooled epoch — nothing to trend",
  "effort-not-measured": "records, but no measure of how hard anyone looked",
  "too-short": "a repeated protocol, not yet long enough",
  detectable: "a long enough series with effort accounted for",
};

function paint(categories: string[]): ExpressionSpecification {
  // `v` is an index into the shipped categories, so the match is built from that array. A
  // hard-coded index list here would break the moment a status was inserted.
  const colours = categories.map((status) => colourFor(status));
  const [first = FALLBACK, ...rest] = colours;
  return [
    "match",
    ["get", "value"],
    0,
    first,
    ...rest.flatMap((colour, index) => [index + 1, colour]),
    FALLBACK,
  ] as ExpressionSpecification;
}

/**
 * A synthetic manifest entry, so the layer toggle and terms list need no special case.
 *
 * The attribution names the project rather than a source, which is accurate: the map is this
 * project's assessment of other people's data, and misattributing it to them would put words in
 * their mouths.
 */
function meta(document_: DetectabilityDocument): LayerMeta {
  const sources = document_.coverage.length;
  return {
    name: LAYER_ID,
    title: "Could change be measured here?",
    description:
      `An assessment of ${sources} sources: a cell is coloured by the best any of them can do. ` +
      `Detectable means some source there has ${document_.min_years} years or more with effort ` +
      "accounted for — not that a change has been found.",
    realm: "all",
    evidence_type: "assessment",
    kind: "surface",
    format: "grid",
    value_kind: "detectability",
    attribution: "Migratlas",
    licence: "CC-BY-4.0",
    landing_page: "https://github.com/JacpAbt/migratlas",
    caveats: document_.caveat,
  };
}

/**
 * Legend rows, best first.
 *
 * Data rather than DOM: the shell renders these in a component, and the old page built the elements
 * here. Best first so the eye starts at the colour that matters and works down into the grey.
 */
export function legendRows(
  document_: DetectabilityDocument,
): { status: string; means: string; colour: string; share: number }[] {
  const total = Object.values(document_.summary).reduce((sum, n) => sum + n, 0);
  return [...document_.grid.categories].reverse().map((status) => ({
    status,
    means: MEANS[status] ?? status,
    colour: colourFor(status),
    share: total > 0 ? ((document_.summary[status] ?? 0) / total) * 100 : 0,
  }));
}

export type { Coverage, DetectabilityDocument };

export async function addDetectability(
  map: MapLibreMap,
  base: string,
): Promise<[LoadedLayer, DetectabilityDocument]> {
  const response = await fetch(`${base}detectability.json`);
  if (!response.ok) throw new Error(`detectability.json: ${response.status}`);
  const document_ = (await response.json()) as DetectabilityDocument;
  if (document_.schema_version !== SUPPORTED_SCHEMA) {
    throw new Error(`detectability.json schema ${document_.schema_version}`);
  }

  const data = gridToFeatures(document_.grid);
  map.addSource(LAYER_ID, {
    type: "geojson",
    data,
    attribution: `<a href="https://github.com/JacpAbt/migratlas">Migratlas</a> — ` +
      "an assessment of what the sources can support, not of where animals are",
  });

  // Under the data layers: this is the ground the results stand on, and a fifty-thousand-cell
  // wash drawn over a radar series would bury it. Insertion is by the first existing data layer
  // rather than by name, so adding a layer upstream cannot push this on top.
  const above = map.getStyle().layers.find((entry) => entry.id.startsWith("surface-"))?.id;
  map.addLayer(
    {
      id: LAYER_ID,
      type: "circle",
      source: LAYER_ID,
      paint: {
        "circle-color": paint(document_.grid.categories),
        // Flat by status: a cell's size would be a second encoding of a nominal value, which is
        // to say a decoration that looks like information.
        "circle-radius": [
          "interpolate",
          ["linear"],
          ["zoom"],
          1,
          2,
          6,
          8,
        ] as ExpressionSpecification,
        // Opaque enough to read as a veil rather than a haze, and only lightly blurred: at 0.5 the
        // fifty thousand cells merged into a smear with no cell edges to judge coverage by.
        "circle-opacity": 0.72,
        "circle-blur": 0.2,
      },
    },
    above,
  );

  // Off by default. It is the most important layer in the project and the least interesting to
  // arrive to: a first-time visitor should meet the animals, then find out what is knowable.
  map.setLayoutProperty(LAYER_ID, "visibility", "none");

  return [
    {
      meta: meta(document_),
      terms: {
        "dwc:dataGeneralizations": "One-degree cells; no record is identifiable from this layer.",
        sensitivity: "none",
      },
      cells: data.features.length,
      center: [0, 20],
      visible: false,
      setVisible: (visible) => {
        if (map.getLayer(LAYER_ID)) {
          map.setLayoutProperty(LAYER_ID, "visibility", visible ? "visible" : "none");
        }
      },
    },
    document_,
  ];
}
