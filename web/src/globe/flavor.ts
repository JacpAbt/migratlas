import { type Flavor, namedFlavor } from "@protomaps/basemaps";

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

  // Off-globe void and the sphere itself. The void is the page's own paper as composited, because
  // with the detail basemap on this layer paints the whole canvas: anything else puts a slab of a
  // different colour behind a globe that is lying on a notebook.
  background: "#efe9d8",
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

/**
 * The same globe at night, and it is a different object rather than the day one dimmed.
 *
 * The reference is a globe seen by lamplight, not a satellite photograph of the dark side: land
 * stays the lighter of the two masses because that is what a paper globe does, and the ocean drops
 * to near-black. Inverting -- pale water, dark land -- was tried on the ramps and read as a
 * negative rather than as night.
 *
 * Every value here was warm before this commit, and the warmth was chosen when night was a warm
 * near-black page. It is a night *sky* now -- `--paper` is #0d131e -- and a brown sphere on a blue
 * page reads as two unrelated pictures rather than as one object on a surface. So the whole set
 * moved into the page's own slate-blue family, which is a hue change and not a lightness one: the
 * land-over-ocean order and the label weights are exactly as they were.
 *
 * ADR 0007 scoped this at "roughly fifteen keys and a week", and the fifteen keys were right.
 */
export const NIGHT_FLAVOR = {
  ...namedFlavor("dark"),

  background: "#0d131e",
  earth: "#223046",

  water: "#141d2e",
  ocean_label: "#7f93ab",

  // Vegetation as a blue-green rather than an olive, and only just lighter than the land: at globe
  // zoom a continent should read as one mass, and at street zoom a park should read as a park.
  park_a: "#24393f",
  park_b: "#2b4348",
  wood_a: "#223a3c",
  wood_b: "#2a4547",
  scrub_a: "#253842",
  scrub_b: "#2d434c",
  zoo: "#26383e",
  sand: "#2c3852",
  beach: "#2f3d58",
  glacier: "#3c4a5e",

  // Moonlight, from the same tokens the page sets its own ink in, so a label on the globe and a
  // word on the paper are the same colour of writing.
  city_label: "#cfd9ea",
  city_label_halo: "#0d131e",
  state_label: "#8496ad",
  state_label_halo: "#0d131e",
  country_label: "#9fb0c6",
  subplace_label: "#8496ad",
  subplace_label_halo: "#0d131e",

  landcover: {
    grassland: "rgba(37, 56, 62, 1)",
    barren: "rgba(43, 54, 76, 1)",
    urban_area: "rgba(43, 50, 63, 1)",
    farmland: "rgba(38, 58, 60, 1)",
    glacier: "rgba(60, 74, 94, 1)",
    scrub: "rgba(40, 55, 66, 1)",
    forest: "rgba(32, 54, 56, 1)",
  },
};

/**
 * Every colour the bundled outline basemap and the data ramps use, per surface.
 *
 * One object rather than eight exports, because the globe now has to swap all of them together the
 * moment the surface changes -- and because a palette half-swapped is worse than either surface.
 *
 * The ramps are re-picked rather than reused. Day's pale-sand-to-terracotta is monotonic in
 * lightness *upwards from a light paper*; on black the pale end vanishes into the ocean and the
 * ramp loses its low half. Night's runs the other way, from a dim ember to a bright one.
 */
export type Ramp = readonly [string, string, string, string, string];

export interface Palette {
  /** Ocean, and the sphere wherever there is no land. */
  ocean: string;
  /** Land, matching the detailed flavour's `earth` so the two are interchangeable. */
  land: string;
  /** Coastline. Thin: it should delineate, not draw attention. */
  coast: string;
  /** National borders, dashed and fainter still than the coast. */
  border: string;
  /**
   * Sequential, roughly monotonic in lightness. A rainbow would look livelier and mislead.
   *
   * A fixed-length tuple rather than an array, because the layer modules index into it -- `ramp[2]`
   * for a resting colour, `ramp[4]` for the loudest one -- and `noUncheckedIndexedAccess` is right
   * that an arbitrary-length array cannot promise those exist.
   */
  warm: Ramp;
  /** The same idea in blue for water-realm layers, so realm is legible at a glance. */
  cool: Ramp;
  /** The detailed opt-in Protomaps flavour that goes with this surface. */
  flavor: Flavor;
}

/**
 * The bundled outline basemap by day.
 *
 * The coast was #c0ab93, which is 1.54:1 against this ocean. A coastline is the mark that says
 * where the boundary is -- with no coast there is no globe, only two fields of colour -- so it is a
 * graphical object required to understand the picture and 3:1 is the floor for one. It was found by
 * writing the night value to clear that floor and then checking whether the day value did.
 */
export const DAY: Palette = {
  ocean: "#c3dbe6",
  land: "#f3ece0",
  coast: "#8a7358",
  border: "#cdbba6",
  warm: ["#dfe6e6", "#e8d9bb", "#d9ab7c", "#b9743f", "#8d4a2c"],
  cool: ["#e6e0d4", "#b9d2de", "#7fadc4", "#4c7f9c", "#2e5a73"],
  flavor: EARTH_FLAVOR,
};

/**
 * The bundled outline basemap at night, which is what actually ships: the detail flavour above is
 * behind an environment variable, so these five values are the night globe for every visitor.
 *
 * The two masses sit 1.27:1 apart, which is deliberately the same near-nothing as day's 1.23:1 --
 * land and ocean are the two largest areas on the screen, and a step you can measure between them
 * is a step that competes with the data drawn on top. The coastline is what carries the boundary
 * and what therefore has to clear 3:1, at 3.60:1 over this ocean against day's 3.12:1 over its own.
 *
 * The border is not held to that and is not meant to be: it is dashed, it is fainter than the coast
 * on purpose, and no reading of a claim about animal movement depends on seeing a national line.
 */
export const NIGHT: Palette = {
  ocean: "#141d2e",
  land: "#223046",
  coast: "#5c7695",
  border: "#364a66",
  warm: ["#3a3428", "#6b4f30", "#a3703c", "#cf9450", "#f0c07a"],
  cool: ["#26313a", "#33566a", "#3f7f9c", "#5aa6c4", "#8fcbe4"],
  flavor: NIGHT_FLAVOR,
};

export function paletteFor(night: boolean): Palette {
  return night ? NIGHT : DAY;
}

/**
 * The palette in force, as module state.
 *
 * Deliberately mutable and deliberately global, which is the unusual choice here. The alternative
 * is threading a palette through `addSeries`, `addSurface`, `addDetectability`, `SpeciesSelection`
 * and every paint expression each of them builds -- and every one of those would then need the
 * same value at *two* times, once at construction and again on every repaint. One module-level
 * value read at call time is what makes a repaint "set it and redraw" rather than a parameter
 * change in nine signatures.
 *
 * It is safe because there is exactly one globe on the page and exactly one surface at a time.
 */
let active: Palette = DAY;

export function setPalette(night: boolean): Palette {
  active = paletteFor(night);
  return active;
}

export function palette(): Palette {
  return active;
}

// Kept as the day names the existing layer modules import, so the surface swap did not have to
// touch every call site in the same change.
export const OCEAN_COLOUR = DAY.ocean;
export const LAND = DAY.land;
export const COAST = DAY.coast;
export const BORDER = DAY.border;
export const WARM_RAMP = DAY.warm;
export const COOL_RAMP = DAY.cool;
