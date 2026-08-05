/**
 * Where the camera goes for each claim, and which layers back it up.
 *
 * This is presentation, so it lives here and not in `reports/findings.py`. A camera position is not
 * a finding: putting one in the ledger would mean the science file carried a decision about framing,
 * and the next person to change the framing would be editing a file whose tests are about numbers.
 *
 * Keyed by the ledger's own `key`, with a fallback. `tests/notebook.spec.ts` asserts every published
 * claim has an entry and that every layer named here exists in the manifest -- the same shape as
 * `detectability.RULES`. Both guards earn their place: a claim with no view lands the reader on a
 * default globe with no sign anything is missing, and two of the layer names below were wrong on
 * the first attempt, which shows up as a claim whose evidence simply never appears.
 */

import type { Finding } from "./ledger";

export interface View {
  /** Longitude, latitude. */
  center: [number, number];
  zoom: number;
  /**
   * Layer names to show while this claim is on screen, by their manifest `name`. Everything else is
   * hidden: a claim about mid-latitude US radar is not helped by a global marine grid drawn over it.
   */
  layers: string[];
  /**
   * Why the camera is here, in one line. Shown to the reader, because a globe that flies somewhere
   * without saying why is a slideshow -- and because writing it down is what caught two of these
   * pointing at the wrong hemisphere.
   */
  because: string;
}

const FALLBACK: View = {
  // The Atlantic, so the Americas and western Europe and Africa are all on the near side.
  center: [-45, 25],
  zoom: 1.4,
  layers: [],
  because: "No view is recorded for this claim, so the globe stays where it started.",
};

export const VIEWS: Record<string, View> = {
  "autumn-advance": {
    // The claim band itself: 37-50°N, centred on the continental US where the 78 stations are.
    center: [-96, 42],
    zoom: 3.1,
    layers: ["aerial-passage"],
    because: "The 78 radar stations the claim is made from, between 37°N and 50°N.",
  },
  "marine-null": {
    // The North Atlantic shelf. FISHGLOB's 29 surveys are North America and Europe by
    // construction, so this frames both sides of the ocean they share rather than one coast.
    center: [-35, 50],
    zoom: 2.2,
    layers: ["marine-taxa-recorded"],
    because: "The bottom-trawl surveys, on both sides of the North Atlantic.",
  },
  "composition-stable": {
    center: [-96, 42],
    zoom: 3.1,
    layers: ["aerial-passage"],
    because: "The same stations, asked a different question: what was flying, not when.",
  },
  "anthropogenic-share": {
    center: [-96, 42],
    zoom: 2.6,
    layers: ["aerial-passage"],
    because: "The claim band again, pulled back: the forcing behind it is global.",
  },
  "atlas-no-net-change": {
    // Southern Africa, framed on the atlas footprint itself: South Africa, Lesotho and Eswatini.
    center: [25, -29],
    zoom: 3.6,
    // No layer, and that is the honest state rather than an omission. This claim rests on 496
    // quarter-degree cells of occupancy change, and no such surface has been exported yet -- the
    // manifest holds four layers and none of them is this one. Borrowing another claim's evidence
    // to fill the frame would be worse than flying there and saying nothing is drawn.
    layers: [],
    because:
      "The southern African atlas footprint: South Africa, Lesotho and Eswatini. Nothing is " +
      "drawn on it yet — the occupancy surface behind this claim has not been exported.",
  },
  "coverage-bias": {
    // Deliberately the southern hemisphere, and deliberately far out. This claim is about what the
    // project cannot see, so the camera points at the emptiness rather than at the data.
    center: [20, -30],
    zoom: 1.5,
    layers: ["marine-space-use", "marine-taxa-recorded"],
    because:
      "The hemisphere this project has almost no measurable change in. The two layers here " +
      "cover it and neither can support a trend.",
  },
};

export function viewFor(finding: Finding): View {
  return VIEWS[finding.key] ?? FALLBACK;
}

/**
 * The view for "just let me explore": every layer, pulled back to the whole sphere.
 *
 * Both halves are the point. Keeping the last claim's layer subset would mean a reader who asked for
 * the map got the map with one claim's evidence still filtered onto it -- which is what shipped on
 * the first attempt, and it reads as a bug rather than as a choice. Pulling back to the world is the
 * other half: the reader asked to stop being led somewhere.
 *
 * `layers` comes from what the globe actually loaded rather than from a list here, so a layer added
 * to the manifest appears in explore mode without anyone remembering to add it.
 */
export function exploreView(available: string[]): View {
  return {
    center: [-45, 25],
    zoom: 1.4,
    layers: available,
    because: "Every published layer, and no argument on top of it.",
  };
}

/**
 * The claim a visitor arrives on.
 *
 * The autumn advance, because it is the only claim in the ledger with a complete audited chain
 * behind it -- detected, four confounds killed, a response function fitted, and the warming
 * attributed. Landing on a null result would be honest and would also give a first-time reader
 * nothing to hold. `tests/notebook.spec.ts` asserts it exists and is a `change`.
 */
export const ARRIVAL_KEY = "autumn-advance";

export function arrivalOf(findings: Finding[]): Finding | undefined {
  return findings.find((finding) => finding.key === ARRIVAL_KEY) ?? findings[0];
}
