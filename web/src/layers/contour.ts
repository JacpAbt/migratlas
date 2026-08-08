/**
 * A driver drawn on the animals' clock.
 *
 * The ice edge is the first environmental layer to ride the week index: the clock that brightens
 * the passage and moves the herds now also walks the ice through its year, which is the point --
 * the environment is the cause, not a backdrop. The product is monthly, so the weekly clock steps
 * it twelve times a year rather than pretending to interpolate ice.
 */

import { Popup, type Map as MapLibreMap } from "maplibre-gl";

import { palette } from "../globe/flavor";

import { attributionFor, fetchLayer, type LayerMeta, type LoadedLayer } from "./types";

const SOURCE_PREFIX = "contour-";

/** The month the clock's week falls in, read off the week's midpoint day. */
const monthOf = (week: number): number =>
  new Date(Date.UTC(2001, 0, 1 + week * 7 + 3)).getUTCMonth() + 1;

export async function addContour(
  map: MapLibreMap,
  meta: LayerMeta,
  baseUrl: string,
  initialWeek: number,
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
      "line-color": palette().cool[3],
      "line-width": ["interpolate", ["linear"], ["zoom"], 1, 0.8, 6, 2.0],
      "line-opacity": 0.7,
    },
  });

  let current = -1;
  const showWeek = (week: number): void => {
    const month = monthOf(week);
    if (month === current) return;
    current = month;
    map.setFilter(id, ["==", ["get", "month"], month]);
  };
  showWeek(initialWeek);

  const popup = new Popup({ closeButton: true, maxWidth: "320px" });
  map.on("click", id, (event) => {
    const caveat = meta.popup_caveat ? `<p class="caveat">${meta.popup_caveat}</p>` : "";
    popup
      .setLngLat(event.lngLat)
      .setHTML(`<strong>${meta.title}</strong>${caveat}`)
      .addTo(map);
  });
  map.on("mouseenter", id, () => (map.getCanvas().style.cursor = "pointer"));
  map.on("mouseleave", id, () => (map.getCanvas().style.cursor = ""));

  return {
    meta,
    terms,
    cells: data.features.length,
    // A two-pole layer has no honest single centre; the camera hint points at the Arctic edge.
    // The zoom is for the query instrument, which reports nothing for these lines at globe
    // zooms while the canvas draws them -- measured in pixels, like the journeys.
    center: [-45, 75],
    zoom: 3.5,
    showWeek,
    setVisible: (visible) => {
      if (map.getLayer(id)) {
        map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
      }
    },
    repaint: () => {
      map.setPaintProperty(id, "line-color", palette().cool[3]);
    },
  };
}
