/**
 * Identified journeys, drawn as lines.
 *
 * Static geometry, deliberately: the movement is legible in the shape itself -- winter loops out
 * onto the sea ice and back -- and animating a line would claim to know the pace along it, which
 * daily medians a kilometre coarse do not support. The clock does not touch this layer.
 */

import { Popup, type Map as MapLibreMap } from "maplibre-gl";

import { palette } from "../globe/flavor";

import { attributionFor, fetchLayer, type LayerMeta, type LoadedLayer } from "./types";

const SOURCE_PREFIX = "tracks-";

interface TrackProperties {
  individual: string;
  days: number;
}

export async function addTracks(
  map: MapLibreMap,
  meta: LayerMeta,
  baseUrl: string,
): Promise<LoadedLayer> {
  const [data, terms] = await fetchLayer<GeoJSON.FeatureCollection>(baseUrl, meta.name);

  const id = `${SOURCE_PREFIX}${meta.name}`;
  map.addSource(id, { type: "geojson", data, attribution: attributionFor(meta, terms) });
  map.addLayer({
    id,
    type: "line",
    source: id,
    layout: { "line-cap": "round", "line-join": "round" },
    paint: {
      "line-color": palette().warm[3],
      "line-width": ["interpolate", ["linear"], ["zoom"], 2, 0.4, 6, 1.2, 10, 2.2],
      // Translucent so a hundred journeys pile into density where they overlap, which is the
      // honest way for lines to show where the animals actually spend their year.
      "line-opacity": 0.45,
    },
  });

  // Measured, not styled: below z3 the tiler's per-tile simplification eats every journey
  // whole, so a locator says the study is here and hands over -- the coastline's pattern.
  const HANDOVER = 3;
  const locatorId = `${id}-locator`;
  map.addSource(locatorId, {
    type: "geojson",
    data: {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: { type: "Point", coordinates: lineMean(data) },
          properties: { title: meta.title },
        },
      ],
    },
  });
  map.addLayer({
    id: locatorId,
    type: "circle",
    source: locatorId,
    maxzoom: HANDOVER,
    paint: {
      "circle-color": palette().warm[3],
      "circle-radius": 4,
      "circle-opacity": 0.85,
      "circle-blur": 0.4,
    },
  });

  const popup = new Popup({ closeButton: true, maxWidth: "320px" });
  map.on("click", id, (event) => {
    const feature = event.features?.[0];
    if (!feature) return;
    const properties = feature.properties as unknown as TrackProperties;
    const caveat = meta.popup_caveat ? `<p class="caveat">${meta.popup_caveat}</p>` : "";
    popup
      .setLngLat(event.lngLat)
      .setHTML(
        `<strong>${properties.individual}</strong>
         <table><tr><th>Days on this journey</th><td>${properties.days}</td></tr></table>
         ${caveat}`,
      )
      .addTo(map);
  });
  map.on("mouseenter", id, () => (map.getCanvas().style.cursor = "pointer"));
  map.on("mouseleave", id, () => (map.getCanvas().style.cursor = ""));

  return {
    meta,
    terms,
    cells: data.features.length,
    center: lineMean(data),
    // Where the journeys become visible, for any camera that means to show them.
    zoom: 4.5,
    setVisible: (visible) => {
      for (const layerId of [id, locatorId]) {
        if (map.getLayer(layerId)) {
          map.setLayoutProperty(layerId, "visibility", visible ? "visible" : "none");
        }
      }
    },
    repaint: () => {
      map.setPaintProperty(id, "line-color", palette().warm[3]);
      map.setPaintProperty(locatorId, "circle-color", palette().warm[3]);
    },
  };
}

/** Mean of every vertex: `meanPosition` counts points, and these features are lines. */
function lineMean(collection: GeoJSON.FeatureCollection): [number, number] {
  let lon = 0;
  let lat = 0;
  let count = 0;
  for (const feature of collection.features) {
    if (feature.geometry.type !== "LineString") continue;
    for (const [x, y] of feature.geometry.coordinates) {
      if (x === undefined || y === undefined) continue;
      lon += x;
      lat += y;
      count++;
    }
  }
  return count === 0 ? [0, 0] : [lon / count, lat / count];
}
