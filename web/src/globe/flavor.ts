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

/**
 * The same globe at night, and it is a different object rather than the day one dimmed.
 *
 * The reference is a globe seen by lamplight, not a satellite photograph of the dark side: land
 * stays the lighter of the two masses because that is what a paper globe does, and the ocean drops
 * to near-black. Inverting -- pale water, dark land -- was tried on the ramps and read as a
 * negative rather than as night.
 *
 * ADR 0007 scoped this at "roughly fifteen keys and a week", and the fifteen keys were right.
 */
export const NIGHT_FLAVOR = {
  ...namedFlavor("dark"),

  background: "#0b0a08",
  earth: "#2a251d",

  water: "#10161c",
  ocean_label: "#5c6a76",

  park_a: "#232a20",
  park_b: "#2b3427",
  wood_a: "#212a1f",
  wood_b: "#293325",
  scrub_a: "#272a1f",
  scrub_b: "#2f3325",
  zoo: "#272c22",
  sand: "#31291d",
  beach: "#342b1d",
  glacier: "#3a3a38",

  city_label: "#d8cdb8",
  city_label_halo: "#100e0b",
  state_label: "#8e836f",
  state_label_halo: "#100e0b",
  country_label: "#a3947c",
  subplace_label: "#8a7f6c",
  subplace_label_halo: "#100e0b",

  landcover: {
    grassland: "rgba(37, 43, 31, 1)",
    barren: "rgba(45, 39, 28, 1)",
    urban_area: "rgba(41, 38, 33, 1)",
    farmland: "rgba(41, 45, 30, 1)",
    glacier: "rgba(58, 58, 56, 1)",
    scrub: "rgba(41, 41, 30, 1)",
    forest: "rgba(31, 41, 30, 1)",
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

export const DAY: Palette = {
  ocean: "#c3dbe6",
  land: "#f3ece0",
  coast: "#c0ab93",
  border: "#cdbba6",
  warm: ["#dfe6e6", "#e8d9bb", "#d9ab7c", "#b9743f", "#8d4a2c"],
  cool: ["#e6e0d4", "#b9d2de", "#7fadc4", "#4c7f9c", "#2e5a73"],
  flavor: EARTH_FLAVOR,
};

export const NIGHT: Palette = {
  ocean: "#10161c",
  land: "#2a251d",
  coast: "#5a5040",
  border: "#443c30",
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
