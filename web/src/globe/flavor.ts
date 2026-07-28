import { namedFlavor } from "@protomaps/basemaps";

/**
 * An earthy pastel basemap: parchment land, soft blue water, muted sage vegetation.
 *
 * Built by overriding Protomaps' `light` flavour rather than authoring 80 colours, so an
 * upstream addition inherits a sensible default instead of rendering as a hole. Only the keys
 * a globe of animal movement actually shows at low zoom are changed: land, water, vegetation
 * and label contrast. Roads and buildings keep the upstream light greys, which read as quiet
 * detail against the parchment when zoomed in.
 */
export const EARTH_FLAVOR = {
  ...namedFlavor("light"),

  // Off-globe void and the sphere itself.
  background: "#e8eef0",
  earth: "#f3ece0",

  // Water is the second-largest area on the globe, so it sets the mood more than anything
  // else. Upstream's #80deea is a saturated cyan that fights every data ramp drawn on top.
  water: "#c3dbe6",
  ocean_label: "#7f9aad",

  // Vegetation as muted sage rather than the mint upstream uses. Kept close in lightness to
  // the parchment so continents read as one warm mass at globe zoom.
  park_a: "#e2e6d3",
  park_b: "#c8d4b4",
  wood_a: "#dfe4d0",
  wood_b: "#c2d0af",
  scrub_a: "#e4e5d4",
  scrub_b: "#cdd3b6",
  zoo: "#dfe4d5",
  sand: "#efe6d1",
  beach: "#f0e6cd",
  glacier: "#f4f2ee",

  // Labels in warm brown, since grey text over parchment reads as faded.
  city_label: "#5f4d3f",
  city_label_halo: "#f7f2e8",
  state_label: "#9c8a79",
  state_label_halo: "#f7f2e8",
  country_label: "#8c7864",
  subplace_label: "#7d6a59",
  subplace_label_halo: "#f7f2e8",

  landcover: {
    grassland: "rgba(224, 232, 205, 1)",
    barren: "rgba(240, 232, 212, 1)",
    urban_area: "rgba(232, 226, 216, 1)",
    farmland: "rgba(230, 234, 205, 1)",
    glacier: "rgba(246, 244, 240, 1)",
    scrub: "rgba(232, 232, 208, 1)",
    forest: "rgba(206, 220, 196, 1)",
  },
};

// The bundled outline basemap. Kept in the same file as the detailed flavour so the two cannot
// drift into looking like different maps.
/** Ocean, and the sphere wherever there is no land. */
export const OCEAN_COLOUR = "#c3dbe6";
/** Land, matching the detailed flavour's `earth` so the two are interchangeable. */
export const LAND = "#f3ece0";
/** Coastline. Warm and thin: it should delineate, not draw attention. */
export const COAST = "#c0ab93";
/** National borders, dashed and fainter still than the coast. */
export const BORDER = "#cdbba6";

/**
 * Shared data-layer ramps, warm-to-cool so a value reads the same way on any layer.
 *
 * Ordered pale sand → clay → terracotta. Sequential and roughly monotonic in lightness, which
 * is what makes a quantity readable; a rainbow would look livelier and mislead.
 */
export const WARM_RAMP = ["#dfe6e6", "#e8d9bb", "#d9ab7c", "#b9743f", "#8d4a2c"] as const;

/** The same idea in blue for water-realm layers, so realm is legible at a glance. */
export const COOL_RAMP = ["#e6e0d4", "#b9d2de", "#7fadc4", "#4c7f9c", "#2e5a73"] as const;
