import type { GeoJSONSource, Map as MapLibreMap } from "maplibre-gl";

import { palette } from "../globe/flavor";

/** The paper the dot sits on, so the stroke reads as a gap rather than as a second colour. */
function halo(): string {
  return (
    getComputedStyle(document.documentElement).getPropertyValue("--selection-halo").trim() ||
    "#fdf8f0"
  );
}
import type { SpeciesGrid, TaxonEntry } from "../search/taxon";

const SOURCE = "selected-species";

/**
 * The surface of one chosen species, drawn over the pooled layers.
 *
 * A separate source rather than a filter on an existing layer, because the published layers are
 * pooled — one surface across 121 species, one count of taxa per cell — and carry no per-species
 * geometry to filter on. Selecting a species genuinely needs different data, which is why the
 * exporter publishes per-taxon grids.
 */
export class SpeciesSelection {
  #added = false;

  constructor(private readonly map: MapLibreMap) {}

  show(entry: TaxonEntry, grid: SpeciesGrid): { center: [number, number]; cells: number } {
    const size = grid.cell_size_deg;
    const features: GeoJSON.Feature[] = [];
    let lon = 0;
    let lat = 0;

    for (let i = 0; i < grid.v.length; i++) {
      const x = grid.x[i];
      const y = grid.y[i];
      const value = grid.v[i];
      if (x === undefined || y === undefined || value === undefined) continue;
      const coordinates: [number, number] = [(x + 0.5) * size - 180, (y + 0.5) * size - 90];
      lon += coordinates[0];
      lat += coordinates[1];
      features.push({
        type: "Feature",
        geometry: { type: "Point", coordinates },
        properties: { value },
      });
    }

    const data: GeoJSON.FeatureCollection = { type: "FeatureCollection", features };
    if (this.#added) {
      (this.map.getSource(SOURCE) as GeoJSONSource).setData(data);
    } else {
      this.map.addSource(SOURCE, { type: "geojson", data });
      this.map.addLayer({
        id: SOURCE,
        type: "circle",
        source: SOURCE,
        paint: {
          // Deliberately louder than the pooled layers underneath: this is the answer to a
          // question the viewer just asked, and it has to be findable at a glance.
          "circle-color": palette().warm[4],
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 1, 2.5, 6, 9],
          "circle-opacity": 0.9,
          "circle-stroke-width": 0.6,
          "circle-stroke-color": halo(),
        },
      });
      this.#added = true;
    }

    const count = features.length || 1;
    return { center: [lon / count, lat / count], cells: features.length };
  }

  clear(): void {
    if (!this.#added) return;
    (this.map.getSource(SOURCE) as GeoJSONSource).setData({
      type: "FeatureCollection",
      features: [],
    });
  }
}
