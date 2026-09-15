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
   *
   * **It has exactly one reader, and that reader is the plate's caption.** So it describes the
   * *ground*: where in the world this claim is made, and nothing about how any measurement is
   * marked. Four of these used to describe the `layers` beside them instead -- "ringed where the
   * count fell, solid where it rose", "as weekly presence on the clock", "the two layers here" --
   * which was true of the globe and false of the sheet it was printed under, and sent a reader
   * looking for marks that are not on the paper. What the plate does draw is keyed in
   * `Plate.svelte`; what the layers draw belongs beside the layers.
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
    because:
      "The band the claim is made in: the middle of the United States, between 37 and 50 degrees " +
      "north, where the radar stations sit.",
  },
  "marine-null": {
    // The North Atlantic shelf. FISHGLOB's 29 surveys are North America and Europe by
    // construction, so this frames both sides of the ocean they share rather than one coast.
    center: [-35, 50],
    zoom: 2.2,
    layers: ["marine-taxa-recorded"],
    because:
      "Both shores of the North Atlantic, which is where the bottom-trawl surveys are: North " +
      "America and Europe, by construction.",
  },
  "composition-stable": {
    center: [-96, 42],
    zoom: 3.1,
    layers: ["aerial-passage"],
    because: "The same band as the timing claim, asked what was flying rather than when.",
  },
  "anthropogenic-share": {
    center: [-96, 42],
    zoom: 2.6,
    layers: ["aerial-passage"],
    because: "The same band, pulled back, because the forcing behind it is global.",
  },
  "atlas-no-net-change": {
    // Southern Africa, framed on the atlas footprint itself: South Africa, Lesotho and Eswatini.
    center: [25, -29],
    zoom: 3.6,
    // The 496 cells the comparison ran on, and only those: the gaps are places nobody atlassed
    // twice rather than places with nothing in them, which is why the surface is not interpolated.
    // What is drawn is the *uncorrected* count of taxa recorded, not the detection-corrected one --
    // `docs/methods/phase1f-atlas-surface.md` §5 registered in advance that a disagreement between
    // the two impeaches the model rather than the count, and the two disagreed.
    layers: ["atlas-taxa-change"],
    because:
      "The southern African atlas footprint: South Africa, Lesotho and Eswatini, and inside it " +
      "the squares that were atlassed in both epochs.",
  },
  "transfer-fails": {
    // All three legs at once, which is only possible because they ring one ocean: the radar band
    // over North America, the trawl surveys across the North Atlantic, and the atlas footprint in
    // southern Africa. Pulled back far enough that the two that agreed are visibly the two
    // furthest apart -- the frame is the argument here, so it is chosen rather than inherited.
    //
    // Centred on the point that minimises the worst-case distance to the three, which puts the
    // radar band and the atlas footprint at 65.6° and 65.7° from the middle rather than 59.7° and
    // 72.6°. Eyeballing it had southern Africa sitting near the limb, where the globe's curvature
    // squashes it into a sliver and the claim's own southern half is the part that reads worst.
    center: [-29, 11],
    zoom: 1.35,
    layers: ["aerial-passage", "marine-taxa-recorded", "atlas-taxa-change"],
    because:
      "All three records at once, which is the point: the two that turned out to agree are the " +
      "two on opposite sides of the equator.",
  },
  "skill-sparse": {
    // The same band as the headline claim, because the two are the same instrument asked
    // opposite questions: the trend is real, and the year-to-year forecast mostly is not.
    center: [-96, 42],
    zoom: 3.1,
    layers: ["aerial-passage"],
    because:
      "The same band as the headline claim, asked the opposite question: not whether timing " +
      "drifted over decades, but whether any single year can be predicted.",
  },
  "displacement-flat": {
    // Both herds at once: Ya Ha Tinda in the Canadian Rockies and the Svalbard archipelago sit
    // 4,700 km apart, and their great-circle midpoint is in the Canadian high Arctic -- so the
    // camera stands there, pulled back until both surfaces are on the near side of the sphere.
    center: [-99, 74],
    zoom: 2.0,
    layers: ["yahatinda-herd", "svalbard-herd"],
    because:
      "The two herds the claim is measured from, a continent apart: elk in the Canadian " +
      "Rockies, reindeer on Svalbard.",
  },
  "flight-advance": {
    // Britain, and no layer: the transects are a series in the lake with no tile behind them, so
    // the plate carries this claim's evidence and the globe carries only the place.
    center: [-2.4, 54.2],
    zoom: 4.4,
    layers: [],
    because:
      "Britain, where the same fixed transects are walked every year by volunteers who count " +
      "what crosses them.",
  },
  "protocol-disagreement": {
    // Sweden, which is the whole claim: one country counted twice, by two programmes, at once.
    center: [16.5, 62.5],
    zoom: 3.8,
    layers: [],
    because:
      "Sweden, counted twice over: two national bird-counting programmes have run side by side " +
      "across the same country for decades.",
  },
  "projection-mask": {
    // The claim band, pulled back the way the attribution's view is, because the forcing behind a
    // scenario is global even where the response is 78 stations wide.
    center: [-96, 42],
    zoom: 2.6,
    layers: ["aerial-passage"],
    because:
      "The same band the response was fitted in, which is the only band any of it may be " +
      "projected into.",
  },
  "seas-disagree": {
    // Pulled back much further than `marine-null`, and that is the claim rather than a framing
    // preference: this one says the seas differ *from each other*, so a camera on one of them would
    // contradict the sentence it illustrates. North America with an ocean on each side puts the
    // Bering Sea, the two Gulf of Mexico series, the Scotian shelf and the European surveys in one
    // frame, which is the comparison.
    center: [-70, 45],
    zoom: 1.6,
    // The same survey-footprint layer `marine-null` draws, because it is the same 2.8 million rows
    // and it shows where the eighteen segments are. It does not draw the heterogeneity: no tile
    // does, and the plate carries that.
    layers: ["marine-taxa-recorded"],
    because:
      "North America with an ocean on each side, because the finding is that these seas disagree " +
      "with one another -- framing one of them would argue against the sentence.",
  },
  "coverage-bias": {
    // Deliberately the southern hemisphere, and deliberately far out. This claim is about what the
    // project cannot see, so the camera points at the emptiness rather than at the data.
    center: [20, -30],
    zoom: 1.5,
    layers: ["marine-space-use", "marine-taxa-recorded"],
    because: "The hemisphere this project can measure almost nothing in.",
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
/**
 * The zoom at which the sphere just fills a box.
 *
 * MapLibre's globe draws the world `512 * 2 ** zoom` pixels around, so the sphere's diameter is that
 * over pi -- which inverts to this. Written as arithmetic rather than chosen, because the number that
 * was chosen has been wrong everywhere since it was written: `zoom: 1.4` is a 430px sphere at every
 * window size, which was small in the shell's 1600x900 and is small again in a 677px page. The owner
 * called the globe badly implemented and this is the half of that which is measurable.
 *
 * The margin leaves the sphere off the page edges, where the map's own controls and its licence
 * notice sit.
 */
export function sphereZoom(width: number, height: number, margin = 0.92): number {
  const diameter = Math.min(width, height) * margin;
  if (!Number.isFinite(diameter) || diameter <= 0) return 1.4;
  return Math.log2((diameter * Math.PI) / 512);
}

export function exploreView(available: string[], zoom = 1.4): View {
  return {
    center: [-45, 25],
    zoom,
    layers: available,
    because: "Every published layer, and no argument on top of it.",
  };
}

/**
 * The chapters, and which claims each one carries.
 *
 * ADR 0013 made the chapters the argument rather than a menu, and asked for this table to live
 * beside `VIEWS` with the guards extended to it: a published claim with no chapter fails the build.
 *
 * **The owner chose this order on 2026-09-15, from three mocked directions**, and it is a story
 * rather than a taxonomy: every migrating animal keeps a calendar and a map; over thirty years the
 * calendar moved and the map did not; chasing that mismatch finds something stranger than the
 * moving calendar, which is that *which animal you are* matters more than where in the world you
 * live. Each chapter is one step of that, and the chapter after it exists because of what the one
 * before found.
 *
 * What it replaced sorted claims by their *direction* -- what changed, what did not, what cannot be
 * seen -- which is a property of a result rather than a question any reader arrives with, and is
 * why the book read as a list of points with nothing between them.
 *
 * **Every slug is kept**, because they are in links this site has already handed out and a chapter
 * changing its question is not a reason to break them. So `what-changed` opens *The calendar moved*
 * and `why-it-changed` opens *Whose hand is on the clock*, which is what its old title was asking.
 * One slug is new, for the chapter the old table had nowhere to put.
 *
 * `tab` is deliberately not `title`. A thumb tab carries a word and the page carries the sentence;
 * seven full titles set vertically ran past the foot of the book in the mock ADR 0015 records.
 *
 * **Two claims moved house and the move is the argument.** `anthropogenic-share` leaves the timing
 * chapter for the one that asks what moved the clock, because attribution is the answer to *why*.
 * `seas-disagree` and `transfer-fails` come out of the limits and make a chapter of their own: that
 * the seas disagree, and that a response measured in one realm does not predict another, are not
 * caveats on the null before them -- they are the reason that null is an average of animals pulling
 * in opposite directions, which is the book's turn.
 */
export interface Chapter {
  /** Stable identity, and what goes in the URL. Never changed, even when the question is. */
  slug: string;
  /** The heading on the page this opens. */
  title: string;
  /** The word on the thumb tab. */
  tab: string;
  /** Ledger keys, in the order the argument makes them. Empty for the two chapters that carry no
      claim of their own -- the way in, and the way out. */
  keys: string[];
}

export const CHAPTERS: readonly Chapter[] = [
  /*
    The way in, and it answers a reader's first question before any epistemic one: what a migration
    actually is. `introduction.py` carries its passages.

    The slug is unchanged. It is in every link this site has handed out, and renaming a chapter is
    not a reason to break them.
  */
  {
    slug: "how-to-read",
    title: "An animal's year",
    tab: "The year",
    keys: [],
  },
  {
    slug: "what-changed",
    title: "The calendar moved",
    tab: "The calendar",
    keys: ["autumn-advance", "flight-advance", "composition-stable"],
  },
  {
    slug: "why-it-changed",
    title: "Whose hand is on the clock",
    tab: "The clock",
    keys: ["anthropogenic-share"],
  },
  {
    slug: "what-did-not",
    title: "But the map stayed put",
    tab: "The map",
    keys: ["marine-null", "atlas-no-net-change", "displacement-flat"],
  },
  {
    slug: "no-average-animal",
    title: "There is no average animal",
    tab: "No average",
    keys: ["seas-disagree", "transfer-fails"],
  },
  {
    slug: "can-be-predicted",
    title: "What about next year?",
    tab: "Next year",
    keys: ["skill-sparse", "projection-mask"],
  },
  {
    slug: "cannot-see",
    title: "What we cannot see",
    tab: "Cannot see",
    keys: ["coverage-bias", "protocol-disagreement"],
  },
  { slug: "the-world", title: "The world", tab: "The world", keys: [] },
];

/** The chapter carrying a claim, or undefined -- which the build guard turns into a failure. */
export function chapterOf(key: string): Chapter | undefined {
  return CHAPTERS.find((chapter) => chapter.keys.includes(key));
}

/**
 * The realms, and the words the tabs show for them.
 *
 * **Why realm and not taxon.** `realm` is required on every source and every schema in this project
 * -- it is the structural half of "this is not a bird project" -- so it is the one axis the book can
 * filter on that every claim already answers. A taxon filter would promise what the evidence cannot
 * deliver: the aerial record is reflectivity, it cannot tell a bird from a bat, and a "birds" tab
 * over it would be a label the measurement does not support. Where an animal is -- air, sea, land --
 * every source states, and states before it is admitted.
 *
 * The tabs carry the plain word rather than the field's. `aerial` is what the schema calls it and
 * "Air" is what it means, and these are the smallest type in the book.
 */
export interface Realm {
  /** The `realm` field's own value, and what goes in the URL. Empty for the unfiltered tab. */
  slug: string;
  /** The word on the tab. */
  tab: string;
  /** The same realm inside a sentence, for the page a filter empties: "nothing measured in the sea". */
  the: string;
}

export const REALMS: readonly Realm[] = [
  { slug: "", tab: "All", the: "any realm" },
  { slug: "aerial", tab: "Air", the: "the air" },
  { slug: "marine", tab: "Sea", the: "the sea" },
  { slug: "terrestrial", tab: "Land", the: "the land" },
];

/** The realm a cross-realm finding carries, which is every realm rather than a fourth one. */
export const EVERYWHERE = "all";

/**
 * Whether a finding belongs under a realm tab.
 *
 * A cross-realm finding appears under every one of them, because `realm: "all"` means the claim is
 * true of each realm rather than of none. Both findings that carry it are limits on the whole
 * project -- the coverage bias and the failure to transfer -- and filtering to the sea and being
 * told that nothing limits what we know about the sea would be the one reading that is false.
 */
export function inRealm(finding: Finding, realm: string): boolean {
  return realm === "" || finding.realm === realm || finding.realm === EVERYWHERE;
}

/** A realm by its slug, for reading one out of the URL. Anything unknown reads as unfiltered. */
export function realmAt(slug: string | null): Realm {
  return REALMS.find((realm) => realm.slug === slug) ?? REALMS[0]!;
}

/** A chapter by its slug, for reading one out of the URL. */
export function chapterAt(slug: string | null): Chapter | undefined {
  return CHAPTERS.find((chapter) => chapter.slug === slug);
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
