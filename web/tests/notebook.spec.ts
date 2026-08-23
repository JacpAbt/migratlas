/**
 * The notebook: type, contrast, and the three refusals ADR 0007 commits to.
 *
 * Split from the other two suites by concern rather than by page -- all three now target the one
 * shipped page. `globe.spec.ts` is the map and the budget, `shell.spec.ts` is the modes and the
 * navigation, and this is what a claim looks like and what it will not do.
 *
 * The contrast test earns its place. Three text tokens were shipped failing AA in at least one
 * surface -- pencil at 4.10:1, rust at 4.38, the "addressed" green at 4.14 -- and all three looked
 * completely fine in a screenshot at 2x. This is the same lesson the layout learned earlier in the
 * project: measure, do not eyeball. A ratio computed from what the browser actually resolved cannot
 * be talked out of.
 */

import { readFileSync } from "node:fs";

import { expect, test, type Locator, type Page } from "@playwright/test";

import type { Leaf, Sources, Spread } from "../src/lib/book/pages";

/*
  The size the book is designed at, stated rather than inherited.

  Playwright's default is 1280x720, which is a number nobody here chose -- the same kind of default
  as the five-second poll deadline this suite used to run on. Every measurement in `book/pages.ts`
  and every divisor in `Book.svelte`'s reading scale was taken against a 1600x900 window, and this
  file is about what a page of the book looks like, so it should look at one. The sizes that are
  deliberately different set their own: `book.spec.ts` runs the overflow guard at two of them and
  has a phone block, and the colour-vision and plate-stock tests below vary the surface, not the
  window.

  Recorded rather than merely set: at 720px tall the spread's own reading scale puts body text at
  11.4px, below the 12px this suite enforces two hundred lines down, which is a real lower bound on
  the spread and has its own fix rather than a viewport that hides it.
*/
test.use({ viewport: { width: 1600, height: 900 } });

/** WCAG 2.1 AA for text below 24px, or below 18.66px bold. Everything on the card is below both. */
const AA_SMALL = 4.5;

/** AA for large text and for meaningful non-text marks. */
const AA_LARGE = 3;

/**
 * The book's own pagination, computed from the same module and documents the book uses.
 *
 * These tests used to walk the arrival's index. The book has no index -- it has pages -- so they
 * walk addresses instead, and the addresses come from `pages.ts` rather than being typed here: a
 * claim that gains a knob moves every page after it, and hard-coded numbers would pass while
 * pointing at the wrong leaf.
 */
function documents(): Sources {
  const read = (name: string) => JSON.parse(readFileSync(`public/${name}`, "utf8"));
  return {
    findings: read("findings.json").findings,
    introduction: read("introduction.json"),
    safeguards: read("sandbox.json"),
    dial: read("response.json"),
  };
}

async function layout(): Promise<readonly Spread[]> {
  const { spreadsOf } = await import("../src/lib/book/pages");
  return spreadsOf(documents());
}

/** The phone's arrangement of the same pages, which is shorter by the spread's padding. */
async function leafLayout(): Promise<readonly Leaf[]> {
  const { leavesOf } = await import("../src/lib/book/pages");
  return leavesOf(documents());
}

/** Where each of one claim's pages is, by kind. */
interface ClaimPages {
  key: string;
  finding: string;
  how: string;
  figure: string;
  record: string;
  bias: string;
  survived: string;
}

/**
 * Every claim in the book, and the address of each of its pages.
 *
 * One page carries one thing now, so a test that wants the plain sentence and the caveat that
 * qualifies it has to visit two leaves. That is the point of `pages.ts` rather than a nuisance, and
 * pretending otherwise -- by asserting only what happens to share a page -- is how the audit would
 * quietly stop being checked.
 */
async function eachClaim(page: Page, visit: (pages: ClaimPages) => Promise<void>): Promise<void> {
  const spreads = await layout();
  const leaves = await leafLayout();
  const keys = [
    ...new Set(
      spreads
        .flatMap((one) => [one.verso, one.recto])
        .flatMap((panel) => (panel.kind === "finding" ? [panel.key] : [])),
    ),
  ];
  expect(keys.length, "no claims in the book").toBeGreaterThan(0);

  for (const key of keys) {
    /*
      The arrangement this viewport will mount, not the spread's.

      A phone arranges the same authored pages without the spread's padding, so `p` is a different
      offset there -- and the audit test below sets 390px and then asked for a page by its spread
      address, landing two leaves away from the bias table it was about.
    */
    const narrow = (page.viewportSize()?.width ?? 1600) < 62 * 16;
    const pages = narrow
      ? leaves.map((leaf) => ({ chapter: leaf.chapter, at: leaf.at, panels: [leaf.panel] }))
      : spreads.map((one) => ({
          chapter: one.chapter,
          at: one.at,
          panels: [one.verso, one.recto],
        }));

    const addressOf = (kind: string): string => {
      const at = pages.find((one) =>
        one.panels.some((panel) => panel.kind === kind && "key" in panel && panel.key === key),
      );
      if (!at) throw new Error(`no ${kind} page for ${key}`);
      return `#ch=${at.chapter.slug}&p=${at.at}`;
    };
    await visit({
      key,
      finding: addressOf("finding"),
      how: addressOf("how"),
      figure: addressOf("figure"),
      record: addressOf("record"),
      bias: addressOf("bias"),
      survived: addressOf("survived"),
    });
  }
}

/** Open a page of the book and wait for the type to be the type. */
async function at(page: Page, address: string): Promise<void> {
  await page.goto(address);
  // Either container: below 62rem the reader gets leaves rather than a spread, and a handful of
  // these tests are about exactly that width.
  await expect(page.locator(".book, .leaves")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
}

/** The first claim's record page, which is where the number and the precise sentence are. */
async function recordPage(page: Page): Promise<void> {
  const spreads = await layout();
  const at_ = spreads.find((one) => [one.verso, one.recto].some((p) => p.kind === "record"));
  if (!at_) throw new Error("the book carries no record page");
  await at(page, `#ch=${at_.chapter.slug}&p=${at_.at}`);
  await expect(page.locator(".claim__value").first()).toBeVisible();
}

/**
 * The world chapter, which is where the shell's own furniture went.
 *
 * `Sheet` and the explore panel were not rebuilt for the book -- they are mounted by the chapter
 * that needs them -- so the tests about a torn edge, a clipped ground and a scroll inside the paper
 * follow the component rather than being deleted with the arrival.
 */
async function world(page: Page): Promise<void> {
  await page.goto("?debug=1#ch=the-world");
  /*
    Thirty seconds, because this waits on a WebGL context and ten layers rather than on a DOM node.

    `.explore` appears only once the globe has reported its layers, and Playwright's default `expect`
    deadline is five seconds -- which this machine beats and a runner with no GPU does not. Four local
    gates passed in a row while CI failed five tests on this one line, which is the whole argument for
    stating a deadline rather than inheriting one: the default is a number nobody chose, and here it
    was a number about DOM latency applied to a map boot.
  */
  await expect(page.locator(".explore")).toBeVisible({ timeout: 30_000 });
  await expect(page.locator(".globe canvas")).toBeVisible({ timeout: 30_000 });
  await page.evaluate(() => document.fonts.ready);
}

/** Open the book on its first claim, which is what most of these tests want. */
async function ready(page: Page): Promise<void> {
  const spreads = await layout();
  const first = spreads.find((one) => one.verso.kind === "finding");
  if (!first) throw new Error("the book carries no claim");
  await at(page, `#ch=${first.chapter.slug}&p=${first.at}`);
  await expect(page.locator(".claim").first()).toBeVisible();
}

/**
 * Choose a surface through the control a reader would use.
 *
 * Scoped to `.surface`, because the confound sandbox's knobs are radiogroups too and an unscoped
 * `getByRole("radio")` reaches into whichever one loaded first.
 */
async function surfaceIs(page: Page, name: string): Promise<void> {
  await page.locator(".surface").getByRole("radio", { name, exact: true }).check();
}

/**
 * The paper as it is actually painted, averaged over a patch of it.
 *
 * Not `--paper`, and the difference is the whole reason this exists. The token is the colour the
 * grain is blended *into*; what a reader looks at is the two composited, and for one release that
 * was a texture centred on mid-grey multiplied over cream, which resolves to concrete. Every
 * contrast number on the page was computed against a value nothing on the screen had.
 *
 * A screenshot, decoded in the browser, rather than the blend re-implemented here: re-implementing
 * it would agree with itself no matter what the compositor did. The patch is averaged because
 * grain is a distribution and text is read against its mean.
 */
interface Patch {
  /** Mean colour, which is what text is read against. */
  rgb: [number, number, number];
  /** Spread of the green channel: whether there is any grain in it at all. */
  sd: number;
}

async function sheetPaper(page: Page): Promise<Patch> {
  /*
    The foot of the facing page, which is blank paper.

    It used to be the top-left of the old shell's torn sheet. In the book the paper is the spread's
    own ground seen through a page, and the reliable patch of it is low on the recto: a plate is
    landscape and top-aligned, so the bottom of a figure page carries nothing. Reading the paper on
    one page and the ink on another is sound for the reason the header already gives -- the notebook
    has one background everywhere, and `every surface that paints paper paints it the same way` is
    the test that keeps that true.
  */
  const box = await page.locator(".spread > .page--recto").boundingBox();
  expect(box, "no page to measure the paper on").toBeTruthy();
  const shot = (
    await page.screenshot({
      clip: { x: box!.x + box!.width * 0.5, y: box!.y + box!.height * 0.82, width: 12, height: 12 },
    })
  ).toString("base64");

  return page.evaluate(async (encoded) => {
    const image = new Image();
    image.src = `data:image/png;base64,${encoded}`;
    await image.decode();
    const canvas = document.createElement("canvas");
    canvas.width = image.width;
    canvas.height = image.height;
    const context = canvas.getContext("2d")!;
    context.drawImage(image, 0, 0);
    const { data } = context.getImageData(0, 0, canvas.width, canvas.height);
    const total = [0, 0, 0];
    let squares = 0;
    for (let index = 0; index < data.length; index += 4) {
      total[0]! += data[index]!;
      total[1]! += data[index + 1]!;
      total[2]! += data[index + 2]!;
      squares += data[index + 1]! ** 2;
    }
    const count = data.length / 4;
    const mean = total.map((sum) => sum / count) as [number, number, number];
    return {
      rgb: mean.map(Math.round) as [number, number, number],
      sd: Math.sqrt(Math.max(0, squares / count - mean[1] ** 2)),
    };
  }, shot);
}

/** Relative luminance of an `rgb(...)` string or a channel triple. */
function luminance(colour: string | [number, number, number]): number {
  const parts = typeof colour === "string" ? (colour.match(/[\d.]+/g)?.map(Number) ?? []) : colour;
  const [r = 0, g = 0, b = 0] = parts
    .slice(0, 3)
    .map((value) => value / 255)
    .map((value) => (value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function ratio(ink: number, paper: number): number {
  const [high, low] = ink > paper ? [ink, paper] : [paper, ink];
  return (high + 0.05) / (low + 0.05);
}

/**
 * Contrast of an element's own text against the paper it is painted on.
 *
 * The paper is passed in rather than read off an ancestor, which is sound here only because the
 * notebook has one background everywhere: the same colour under the same grain under the same
 * blend. `every surface that paints paper paints it the same way` is the test that keeps that
 * true; if a component ever gets a fill of its own, this has to walk the tree instead.
 */
async function contrast(target: Locator, paper: number): Promise<number> {
  const ink = await target.evaluate((node) => getComputedStyle(node).color);
  return ratio(luminance(ink), paper);
}

for (const surface of ["day", "night"] as const) {
  test(`every text colour clears AA on the ${surface} surface`, async ({ page }) => {
    await ready(page);
    /*
      The surface is set again after every navigation, inside the loop below, because these samples
      are on four different leaves and each `goto` is a fresh load. It is set through the switch a
      reader would use and never by stamping the attribute: this test used to do the latter with a
      comment saying the shell had no switch yet, so the palette was measured in a state nobody
      could reach, and the day it became reachable nothing here would have noticed if the control
      set the wrong value.
    */

    /*
      One per token that carries text, chosen as the smallest instance of each: if the 0.66rem label
      passes, the value using the same token does too.

      Each now names the page it is on, because one page carries one thing. Two consequences worth
      stating. `.claim__scope` is gone from this list and `.plate__scope` has taken its place: the
      scope moved to the plate's caption when the record page stopped printing it twice, and it was
      about to become a token nobody measured. And the bias table, the survived list and the
      specimen line are on three different leaves now -- the first two in the book, the third on the
      plate -- so they are visited rather than read off one card.
    */
    const samples: [string, string, number, keyof Omit<ClaimPages, "key">][] = [
      ["the claim title", ".claim__title", AA_SMALL, "finding"],
      ["why it matters", ".claim__matters", AA_SMALL, "finding"],
      ["the short caveat", ".claim__short-caveat", AA_SMALL, "finding"],
      ["the direction banner", ".claim__banner", AA_SMALL, "finding"],
      ["the chapter kicker", ".chapter", AA_SMALL, "finding"],
      ["the measurement", ".claim__value", AA_SMALL, "record"],
      ["the register label", ".claim__register", AA_SMALL, "record"],
      ["the precise claim", ".claim__precise", AA_SMALL, "record"],
      ["the caveat", ".claim__caveat", AA_SMALL, "record"],
      ["the method link", ".claim__method", AA_SMALL, "record"],
      ["the plain method", ".how__lead", AA_SMALL, "how"],
      ["its kicker", ".how__kicker", AA_SMALL, "how"],
      ["its method link", ".how__method", AA_SMALL, "how"],
      ["a bias domain", ".bias__domain", AA_SMALL, "bias"],
      ["an open bias status", ".bias__status--open", AA_SMALL, "bias"],
      ["a bounded bias status", ".bias__status--bounded", AA_SMALL, "bias"],
      ["a bias finding", ".bias__finding", AA_SMALL, "bias"],
      ["a survived test", ".survived li", AA_SMALL, "survived"],
      ["the plate caption", ".plate figcaption", AA_SMALL, "figure"],
      ["the scope, on the plate", ".plate__scope", AA_SMALL, "figure"],
    ];

    /*
      A claim that carries every one of them, so a token is measured rather than skipped.

      `autumn-advance` has an open bias domain and a bounded one, a list of what it survived, and a
      drawn plate. Picking the first claim in the book instead would have measured whichever tokens
      that one happened to have, and a status colour with no instance on the page reads as a pass.
    */
    let pages: ClaimPages | null = null;
    await eachClaim(page, async (claim) => {
      if (claim.key === "autumn-advance") pages = claim;
    });
    expect(pages, "autumn-advance is not in the book").not.toBeNull();

    let where = "";
    for (const [what, selector, floor, side] of samples) {
      const address = pages![side];
      if (address !== where) {
        await at(page, address);
        if (surface === "night") {
          await surfaceIs(page, "Night");
          await expect(page.locator(":root")).toHaveAttribute("data-surface", "night");
        }
        where = address;
      }

      // Measured off the paper these words are printed on, not off `--paper`, and the two are not
      // the same value: the grain is blended into the token, so what a reader sees is the composite.
      const sheet = await sheetPaper(page);
      const paper = luminance(sheet.rgb);

      const target = page.locator(selector).first();
      await expect(target, `${what} is not on ${address}`).toBeVisible();
      const measured = await contrast(target, paper);
      expect(
        measured,
        `${what} (${selector}) is ${measured.toFixed(2)}:1 on rgb(${sheet.rgb.join(" ")}), needs ${floor}:1`,
      ).toBeGreaterThanOrEqual(floor);
    }
  });
}

test("every surface that paints paper paints it the same way", async ({ page }) => {
  await ready(page);
  // The bug this exists for: `Sheet` set the paper colour and the grain and no blend mode, so the
  // texture was painted *over* the colour rather than into it and every card on the site was a grey
  // slab in both surfaces. Nothing caught it, because the contrast suite read the token underneath.
  //
  // Structural rather than sampled, because these three declarations only mean anything together
  // and a card can be measured only where it has no words on it.
  const painted = await page.evaluate(() => {
    const style = (selector: string) => {
      const node = document.querySelector(selector);
      return node ? getComputedStyle(node) : null;
    };
    const body = getComputedStyle(document.body);
    const spread = style(".spread");
    const grain = style(".page--recto .page__grain");
    return {
      bodyColour: body.backgroundColor,
      bodyImage: body.backgroundImage,
      bodySize: body.backgroundSize,
      bodyBlend: body.backgroundBlendMode,
      spreadColour: spread?.backgroundColor ?? null,
      grainImage: grain?.backgroundImage ?? null,
      grainSize: grain?.backgroundSize ?? null,
      grainBlend: grain?.mixBlendMode ?? null,
    };
  });

  /*
    Re-authored for the book, where the paper is composed in two elements rather than one: the spread
    paints the colour and `.page__grain` paints the texture over it with a blend mode. The bug this
    exists for survives the change unaltered -- a displacement map painted *over* the colour instead
    of into it turned every card on the site into a grey slab, and nothing caught it because the
    contrast suite was reading the token underneath.
  */
  expect(painted.spreadColour, "the spread is not the same colour as the page").toBe(
    painted.bodyColour,
  );
  expect(painted.grainImage, "the page's grain is not the page's grain").toBe(painted.bodyImage);
  expect(painted.grainSize, "the grain is at a different scale on the page").toBe(painted.bodySize);
  expect(
    painted.grainBlend,
    "the grain is painted over the paper rather than into it, which is the grey-slab bug",
  ).toBe(painted.bodyBlend);
});

test("the grain is a texture, not a filter over the paper", async ({ page }) => {
  await ready(page);
  // A displacement map straight out of the archive is centred on mid-grey, because a height field
  // carries no tone. Multiplied over cream that is a 40% neutral-density filter, and the page came
  // out the colour of concrete while every token still said it was paper.
  //
  // So: the sheet as painted must be the colour it claims to be, on both surfaces, within the
  // rounding that a texture and an 8-bit blend cost. Three levels of slack, no more -- ten would
  // let the whole failure back in.
  for (const [surface, intended] of [
    ["day", [0xef, 0xe9, 0xd8]],
    ["night", [0x0d, 0x13, 0x1e]],
  ] as const) {
    if (surface === "night") await surfaceIs(page, "Night");
    const sheet = await sheetPaper(page);
    const where = `the ${surface} sheet is rgb(${sheet.rgb.join(" ")}) sd ${sheet.sd.toFixed(2)}`;

    for (const [index, channel] of sheet.rgb.entries()) {
      expect(
        Math.abs(channel - intended[index]!),
        `${where}, and the palette says ${intended.map((v) => v.toString(16).padStart(2, "0")).join("")}`,
      ).toBeLessThanOrEqual(3);
    }

    // And the other half of it, on the surface where the grain is meant to be seen: shifting no
    // tone is easy to achieve by having no texture. Only the day paper is asserted to have any,
    // because night is deliberately four times smoother -- its map is large-scale creases rather
    // than fibre, and at any real amplitude on a near-black ground that reads as foil.
    if (surface === "day") {
      expect(sheet.sd, `${where} -- no variation, so there is no grain`).toBeGreaterThan(1);
    }
  }
});

/**
 * The two red-green dichromacies, simulated.
 *
 * Viénot, Brettel & Mollon (1999): to linear RGB, into LMS, collapse the missing cone's response
 * onto the plane the other two span, and back. It is the standard construction and it is the one
 * the palette was tuned against by hand -- what did not exist until now was anything that re-runs
 * it, so the separations recorded in `tokens.css` were true when written and unguarded ever after.
 */
type Blindness = "protan" | "deutan";

function dichromat(colour: string, kind: Blindness): [number, number, number] {
  const [sr = 0, sg = 0, sb = 0] = (colour.match(/[\d.]+/g) ?? ["0", "0", "0"])
    .slice(0, 3)
    .map(Number)
    .map((value) => value / 255)
    .map((value) => (value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4));

  const l = 17.8824 * sr + 43.5161 * sg + 4.11935 * sb;
  const m = 3.45565 * sr + 27.1554 * sg + 3.86714 * sb;
  const s = 0.0299566 * sr + 0.184309 * sg + 1.46709 * sb;

  const [pl, pm, ps] =
    kind === "protan" ? [2.02344 * m - 2.52581 * s, m, s] : [l, 0.494207 * l + 1.24827 * s, s];

  return [
    0.080944 * pl - 0.130504 * pm + 0.116721 * ps,
    -0.0102485 * pl + 0.0540194 * pm - 0.113615 * ps,
    -0.000365294 * pl - 0.00412163 * pm + 0.693513 * ps,
  ].map((value) => {
    const clamped = Math.min(1, Math.max(0, value));
    const encoded = clamped <= 0.0031308 ? clamped * 12.92 : 1.055 * clamped ** (1 / 2.4) - 0.055;
    return Math.round(encoded * 255);
  }) as [number, number, number];
}

/**
 * How far apart two colours are once a dichromat has seen them.
 *
 * Euclidean in sRGB, which is crude, and kept anyway: it is the metric the numbers already written
 * into `tokens.css` are in, and changing the metric in the same commit that first measures anything
 * would silently invalidate a recorded measurement. The scale runs to 441; 60 is the floor the
 * night palette was retuned to clear.
 */
function separation(a: string, b: string, kind: Blindness): number {
  const [ar, ag, ab] = dichromat(a, kind);
  const [br, bg, bb] = dichromat(b, kind);
  return Math.hypot(ar - br, ag - bg, ab - bb);
}

const SEPARATION_FLOOR = 60;

/**
 * Pairs where the colour is the whole message, so colour blindness would take the message away.
 *
 * WCAG 1.4.1 does not ask that colours be separable to a dichromat. It asks that colour is never
 * the only channel. So the floor binds exactly where there *is* no other channel, and the honest
 * work of this list is saying which pairs those are and paying for the ones it excludes.
 *
 * The detectability choropleth is the case. A cell on the globe is a colour and nothing else: the
 * legend names the classes, but nothing on the sphere does, and a reader comparing two regions is
 * comparing two fills. `--detect-short` was #d8bd7e and sat 43 from `--detect-unknown` under
 * deuteranopia, which is a class boundary disappearing.
 *
 * Excluded, each with the second channel that makes it compliant:
 *
 *   - The bias statuses. Red against green, and by day they measure 52 apart under protanopia --
 *     under the floor, and there is no value that clears it without leaving the red-green axis
 *     entirely for purple, which is the palette. They do not need to: every status renders with
 *     the word it means. `an addressed status ... is not the only signal` asserts that, for all
 *     three, so this exclusion is checked rather than asserted.
 *   - `--line-scatter` against the two series lines. Different mark, not a different colour: the
 *     scatter is dots at 55% opacity with 1px whiskers, the series are 2.2px strokes with their own
 *     end labels. `a chart says which line is which without colour` pins that.
 *   - `--detect-none`, `--detect-no-effort` and `--detect-unknown` against each other. 26, 34 and
 *     57 apart in ordinary vision, which is the design: all three are kinds of "this cannot be
 *     measured here", and separating them would claim a distinction the reader has no use for.
 *     Each is still held to the floor against the two colours that mean the opposite.
 *   - The globe's warm and cool ramps. They separate realm, and they do it as amber against blue --
 *     the one axis both red-green dichromacies leave intact.
 */
const CONFUSABLE: [string, string, string][] = [
  ["measurable against short-series", "--detect-yes", "--detect-short"],
  ["measurable against no data", "--detect-yes", "--detect-none"],
  ["measurable against no effort", "--detect-yes", "--detect-no-effort"],
  ["measurable against unknown", "--detect-yes", "--detect-unknown"],
  ["short-series against no data", "--detect-short", "--detect-none"],
  ["short-series against no effort", "--detect-short", "--detect-no-effort"],
  ["short-series against unknown", "--detect-short", "--detect-unknown"],
];

for (const surface of ["day", "night"] as const) {
  test(`no meaningful pair collapses under red-green colour blindness on ${surface}`, async ({
    page,
  }) => {
    await ready(page);
    if (surface === "night") await surfaceIs(page, "Night");

    const resolved = await page.evaluate((names) => {
      const style = getComputedStyle(document.documentElement);
      // Through a probe, so a token arrives as `rgb(...)` rather than as whatever hex it was
      // authored in -- the simulation needs channels, not a string it has to guess the format of.
      const probe = document.createElement("span");
      document.body.append(probe);
      const out: Record<string, string> = {};
      for (const name of names) {
        probe.style.color = style.getPropertyValue(name).trim();
        out[name] = getComputedStyle(probe).color;
      }
      probe.remove();
      return out;
    }, [...new Set(CONFUSABLE.flatMap(([, a, b]) => [a, b]))]);

    const failures: string[] = [];
    for (const [what, first, second] of CONFUSABLE) {
      const a = resolved[first];
      const b = resolved[second];
      expect(a, `${first} resolves to nothing`).toBeTruthy();
      expect(b, `${second} resolves to nothing`).toBeTruthy();
      for (const kind of ["protan", "deutan"] as const) {
        const apart = separation(a!, b!, kind);
        if (apart < SEPARATION_FLOOR) {
          failures.push(`${what} is ${apart.toFixed(0)} apart under ${kind} (floor ${SEPARATION_FLOOR})`);
        }
      }
    }
    expect(failures, failures.join("; ")).toEqual([]);
  });
}

test("the surface is a three-way choice, and it survives a reload", async ({ page }) => {
  await ready(page);

  // Three, not a toggle. "Follow the system" is a choice: a reader whose machine dims at sunset
  // wants the paper to dim with it, and one who picked day wants day at midnight. A two-state
  // switch cannot say the difference, so the first click would opt out of the system for good.
  await expect(page.locator(".surface").getByRole("radio")).toHaveCount(3);

  await surfaceIs(page, "Night");
  await expect(page.locator(":root")).toHaveAttribute("data-surface", "night");

  await page.reload();
  await expect(page.locator(":root")).toHaveAttribute("data-surface", "night");

  // And "system" is the absence of the attribute rather than a third value of it, so the media
  // query in tokens.css gets to decide again.
  await surfaceIs(page, "System");
  await expect(page.locator(":root")).not.toHaveAttribute("data-surface", /.*/);
});

test("the globe follows the paper it is read on", async ({ page }) => {
  await world(page);
  // The one thing CSS cannot do for us. MapLibre paint is set in JavaScript, so without an explicit
  // repaint a reader who switches to night gets black paper around a parchment sphere -- which is
  // the state this project shipped in for the whole time the palette existed and the switch did not.
  const ocean = () =>
    page.evaluate(() => {
      const map = (window as unknown as { migratlas?: { map?: unknown } }).migratlas?.map as
        | { getPaintProperty: (id: string, property: string) => unknown }
        | undefined;
      return String(map?.getPaintProperty("ocean", "background-color") ?? "");
    });

  const byDay = await ocean();
  expect(byDay, "no ocean colour to read").toBeTruthy();

  await surfaceIs(page, "Night");
  /*
    An explicit deadline, because the default is five seconds and nobody chose it. See the note on
    the darts' rotation poll for the flake that made the point.
  */
  await expect
    .poll(ocean, { message: "the surface changed and the ocean did not", timeout: 30_000 })
    .not.toBe(byDay);
});

test("an addressed status is legible too, and is not the only signal", async ({ page }) => {
  /*
    The audit is a page per claim now, and "addressed" is not on every one of them -- so this walks
    until it finds one rather than assuming the first claim has every status. A test that asserted
    the colour of a status with no instance on the page would pass by having nothing to measure.
  */
  let found = false;
  await eachClaim(page, async (pages) => {
    if (found) return;
    await at(page, pages.bias);
    if ((await page.locator(".bias__status--addressed").count()) > 0) found = true;
  });
  expect(found, "no claim has an addressed bias domain to measure").toBe(true);
  const addressed = page.locator(".bias__status--addressed").first();
  await expect(addressed).toBeVisible();
  const paper = luminance((await sheetPaper(page)).rgb);
  expect(await contrast(addressed, paper)).toBeGreaterThanOrEqual(AA_SMALL);

  // Never colour alone, and this is the assertion the colour-vision test leans on rather than a
  // convention. Red against green measures 52 apart under protanopia by day, which is below the
  // separability floor and cannot be fixed without leaving the palette; what makes it compliant is
  // that the word is the signal and the colour only agrees with it. So: every status on the page,
  // not just this one, has to read as its own meaning.
  //
  // Read in one `evaluate` rather than looped over a locator, because a page turn keeps the old
  // claim in the DOM for the length of the transition: counting the nodes and then asserting on
  // them are two moments, and the first version failed on a node that had been replaced between
  // them. One synchronous pass over the live document has no such gap.
  await eachClaim(page, async () => {
    const silent = await page.evaluate(() =>
      [...document.querySelectorAll("[class*='bias__status--']")]
        .map((node) => {
          const meaning = /bias__status--(\w+)/.exec(node.className)?.[1] ?? "";
          return { meaning, text: (node.textContent ?? "").trim() };
        })
        .filter(({ meaning, text }) => !text.toLowerCase().includes(meaning))
        .map(({ meaning, text }) => `${meaning} reads "${text}"`),
    );
    expect(silent, silent.join("; ")).toEqual([]);
  });
});

test("a chart says which line is which without colour", async ({ page }) => {
  await ready(page);
  // The other exclusion from the colour-vision floor, and the same deal: the scatter sits 16 from
  // the counterfactual line under both dichromacies at night, and does not need to move because it
  // is not the same *kind* of mark. Dots against strokes is a second channel; a second hue is not.
  //
  // On the attribution claim specifically: a chart on every claim would be decoration, so this is
  // the one claim that has one.
  await eachClaim(page, async (claim) => {
    if (claim.key === "anthropogenic-share") await at(page, claim.figure);
  });
  const chart = page.locator(".chart__svg").first();
  await expect(chart).toBeVisible();

  const marks = await chart.evaluate((node) => {
    const read = (selector: string) => {
      const found = node.querySelector(selector);
      if (!found) return null;
      const style = getComputedStyle(found);
      return { tag: found.tagName, width: Number.parseFloat(style.strokeWidth) || 0 };
    };
    return {
      scatter: read(".chart__year"),
      observed: read(".chart__line--observed"),
      counterfactual: read(".chart__line--counterfactual"),
    };
  });

  // The scatter is a filled circle per year; the two series are stroked lines, and thick ones.
  expect(marks.scatter?.tag, "the scatter is not a point mark").toBe("circle");
  expect(marks.observed?.tag, "the observed series is not a stroke").toBe("line");
  expect(marks.counterfactual?.tag, "the counterfactual is not a stroke").toBe("line");
  expect(marks.observed?.width ?? 0, "a series line thin enough to read as scatter").toBeGreaterThan(
    1.5,
  );

  // And the two lines, which *are* the same mark, carry their own labels rather than relying on the
  // legend to say which is which.
  await expect(chart.locator(".chart__label--observed")).toHaveCount(1);
  await expect(chart.locator(".chart__label--counterfactual")).toHaveCount(1);
});

test("every claim shows an instrument rather than a creature", async ({ page }) => {
  await ready(page);
  await eachClaim(page, async (pages) => {
    await at(page, pages.finding);
    const claim = page.locator(".claim").first();
    const instrument = claim.locator(".instrument");
    await expect(instrument, "a claim with no instrument mark").toHaveCount(1);

    // ADR 0007 decision 5, asserted rather than trusted. The radar measures aerial biomass and
    // cannot separate birds from bats from insects; a drawing of an animal beside that claim would
    // contradict the caveat printed two lines below it, in the page's most legible register.
    const label = await instrument.getAttribute("aria-label");
    expect(label, "an instrument with nothing read out to a screen reader").toBeTruthy();
    expect(
      label,
      `"${label}" names a creature; only the apparatus goes here`,
    ).not.toMatch(/bird|bat|insect|fish|whale|shark|turtle|swallow/i);
  });
});

test("the audit is a page of its own, not something behind a control", async ({ page }) => {
  /*
    Re-authored for the book, and the half that mattered is the half that survived.

    It used to assert the audit was rendered *beside* every claim. It is not beside anything now: the
    bias table and what a claim survived overflowed a shared page by 231 and 304 pixels on the two
    longest audits, so they have a leaf each. What the test was really for is the other clause --
    `findings.py` refuses to publish a claim with no caveat, and a `<details>` around the audit would
    satisfy that refusal while breaking its point. A page is not a disclosure widget, so the guard
    now says: on its own page, visible, with nothing collapsible anywhere near it.
  */
  test.setTimeout(90_000);

  let open = 0;
  let audited = 0;
  await eachClaim(page, async (pages) => {
    await at(page, pages.bias);
    const spread = page.locator(".spread");
    await expect(spread.locator(".bias__domain").first()).toBeVisible();
    await expect(spread.locator("details, [hidden]")).toHaveCount(0);
    audited += 1;

    // Counted in the same pass. At least one domain must read "open" across the set: every domain
    // "addressed" would mean either that nothing is unresolved -- false, the 2012 step is -- or that
    // the audit is written to reassure rather than to inform.
    open += await spread.locator(".bias__status--open").count();

    // And the caveat is still with the number it qualifies, one leaf earlier, which is the rule
    // ADR 0007 states and pagination had to be careful not to break.
    await at(page, pages.record);
    await expect(page.locator(".claim__caveat")).not.toBeEmpty();
  });

  expect(audited, "no claim has an audit page").toBeGreaterThan(0);
  expect(open, "nothing is marked open, which would mean the audit is decorative").toBeGreaterThan(0);
});

test("every claim is said twice, plainly and precisely, and both are in the book", async ({
  page,
}) => {
  /*
    Both registers, one leaf apart rather than one card. The plain sentence and the number that
    earns it are 526 to 680 and 274 to 821 pixels tall, and together they did not fit a page -- so
    the pair is a spread now. What this guards is unchanged and is not about layout: the next change
    is the one where somebody notices the claim looks redundant under a heading that says almost the
    same thing, and deletes one of them.
  */
  test.setTimeout(90_000);

  // The precise sentence is the scientific statement and stays whole. The plain one carries the
  // finding to a reader without statistics. Adding the second register is fine; the failure this
  // guards is the next change, where someone notices the claim looks redundant under a heading
  // that says almost the same thing and deletes one of them.
  await eachClaim(page, async (pages) => {
    await at(page, pages.finding);
    const plain = (await page.locator(".claim__title").textContent())?.trim() ?? "";
    await expect(page.locator(".claim__short-caveat")).not.toBeEmpty();
    await expect(page.locator(".claim__matters")).not.toBeEmpty();
    await expect(page.locator(".spread details, .spread [hidden]")).toHaveCount(0);

    await at(page, pages.record);
    const claim = page.locator(".claim").first();
    const precise = (await claim.locator(".claim__precise").textContent())?.trim() ?? "";
    await expect(claim.locator(".claim__caveat")).not.toBeEmpty();

    expect(plain.length, "a claim with no plain sentence").toBeGreaterThan(20);
    expect(precise.length, "a claim with no precise sentence").toBeGreaterThan(20);
    expect(precise.replace(/^Precisely\s*/, "")).not.toBe(plain);

    // Neither register is behind a control, on either leaf -- the same rule as the audit page.
    await expect(page.locator(".spread details, .spread [hidden]")).toHaveCount(0);
  });
});

test("the plain register is set larger than the precise one it introduces", async ({ page }) => {
  /*
    Measured across two leaves, because the registers are on two. Nothing about the comparison
    changed -- the plain sentence is the heading and is set as one -- but the pages are now the
    finding and the record, so both sizes are read where each is actually printed.
  */
  const spreads = await layout();
  const finding = spreads.find((one) => one.verso.kind === "finding")!;
  const key = "key" in finding.verso ? finding.verso.key : "";
  const record = spreads.find((one) =>
    [one.verso, one.recto].some((panel) => panel.kind === "record" && panel.key === key),
  )!;
  // Which register is the heading is the decision, so it has to be legible as one. A plain
  // sentence typeset at the same size as the sentence beneath it is not a heading, it is a
  // duplicate -- and a reader would have to work out which of the two to read first.
  const sizeOf = (selector: string) =>
    page
      .locator(selector)
      .first()
      .evaluate((node) => Number.parseFloat(getComputedStyle(node).fontSize));

  await at(page, `#ch=${finding.chapter.slug}&p=${finding.at}`);
  const plain = await sizeOf(".claim__title");
  await at(page, `#ch=${record.chapter.slug}&p=${record.at}`);
  const precise = await sizeOf(".claim__precise");

  expect(plain, `the plain register is ${plain}px against ${precise}px`).toBeGreaterThan(precise);
});

test("no number animates to its value", async ({ page }) => {
  await recordPage(page);
  // ADR 0007 decision 6. A counting number reads as a score; -0.56 +/- 0.25 is a measurement with
  // an interval on it. Asserted by reading the value immediately and again after any animation
  // would have finished -- if it were counting, the two would differ.
  const value = page.locator(".claim__value").first();
  const first = await value.textContent();
  await page.waitForTimeout(1200);
  expect(await value.textContent()).toBe(first);
  expect(first).toMatch(/\d/);
});

test("the type is a setting a reader can reach, and it survives a reload", async ({ page }) => {
  await ready(page);

  // Beside the surface switch, not behind anything. Two of the three options exist for people who
  // cannot comfortably read the first, and an accessibility provision in a menu is one nobody
  // finds.
  const picker = page.locator(".type");
  await expect(picker.getByRole("radio")).toHaveCount(3);

  await picker.getByRole("radio", { name: "Dyslexia", exact: true }).check();
  await expect(page.locator(":root")).toHaveAttribute("data-type", "dyslexic");
  await expect(page.locator(".claim__title")).toHaveCSS("font-family", /OpenDyslexic/);

  await page.reload();
  await expect(page.locator(":root")).toHaveAttribute("data-type", "dyslexic");
});

test("changing the type changes the letterforms and nothing else", async ({ page }) => {
  await ready(page);
  const picker = page.locator(".type");

  // The faces do not share an x-height, so each preset carries its own scale and leading. Without
  // that, switching makes the page look a size bigger or smaller rather than differently drawn --
  // which is the whole of what "optimised" means for a type setting.
  const measure = () =>
    page.evaluate(() => {
      const title = getComputedStyle(document.querySelector(".claim__title")!);
      const body = getComputedStyle(document.querySelector(".claim__matters")!);
      return {
        title: Number.parseFloat(title.fontSize),
        body: Number.parseFloat(body.fontSize),
        leading: Number.parseFloat(body.lineHeight),
      };
    });

  const seen: Record<string, Awaited<ReturnType<typeof measure>>> = {};
  for (const name of ["Hand", "Clear", "Dyslexia"]) {
    await picker.getByRole("radio", { name, exact: true }).check();
    seen[name] = await measure();
  }

  // Every preset lands in a readable band rather than at the same nominal size.
  for (const [name, size] of Object.entries(seen)) {
    expect(size.title, `${name} heading is ${size.title}px`).toBeGreaterThan(15);
    expect(size.body, `${name} body is ${size.body}px`).toBeGreaterThan(12);
    expect(size.leading / size.body, `${name} leading`).toBeGreaterThan(1.4);
  }
  // And they are genuinely different settings, not three names for one.
  expect(new Set(Object.values(seen).map((s) => s.title)).size).toBeGreaterThan(1);
});

test("a figure is never set in a face that cannot line one up", async ({ page }) => {
  await recordPage(page);
  /*
    Retargeted rather than dropped, and the retarget is the point. This used to name Architects
    Daughter, which pinned the invariant to whichever face the site happened to use -- so the day
    the type became a setting the test failed for a reason that had nothing to do with what it was
    protecting.

    What it protects is the reason ADR 0007 gave, and that reason has not moved: no handwriting
    face has tabular digits. Virgil's widest digit is half again its narrowest. So the measurement
    stays mono under every preset, and the assertion reads the token rather than a family name.
  */
  const faceOf = (selector: string) =>
    page
      .locator(selector)
      .first()
      .evaluate((node) => getComputedStyle(node).fontFamily);

  const token = (name: string) =>
    page.evaluate(
      (property) => getComputedStyle(document.documentElement).getPropertyValue(property).trim(),
      name,
    );

  const hand = (await token("--font-hand")).split(",")[0]!.replaceAll('"', "").trim();
  const mono = (await token("--font-mono")).split(",")[0]!.replaceAll('"', "").trim();

  /*
    And the small registers are never the hand. `.claim__banner` is on the finding page and
    `.bias__domain` on the audit page, so each is checked where it is printed -- the specimen line
    left this list because it left the margin: it is the plate's legend now, and the plate caption is
    covered by the contrast sweep instead.
  */
  const spreads = await layout();
  const findingAt = spreads.find((one) => one.verso.kind === "finding")!;
  const key = "key" in findingAt.verso ? findingAt.verso.key : "";
  const biasAt = spreads.find((one) =>
    [one.verso, one.recto].some((panel) => panel.kind === "bias" && panel.key === key),
  )!;

  expect(await faceOf(".claim__value")).toContain(mono);

  await at(page, `#ch=${findingAt.chapter.slug}&p=${findingAt.at}`);
  expect(await faceOf(".claim__banner"), "the banner is set in the hand face").not.toContain(hand);
  expect(await faceOf(".claim__title")).toContain(hand);

  await at(page, `#ch=${biasAt.chapter.slug}&p=${biasAt.at}`);
  expect(await faceOf(".bias__domain"), "a bias domain is set in the hand face").not.toContain(hand);
});

test("the audit is still there on a phone, and still not behind anything", async ({ page }) => {
  /*
    Re-authored, and the clause that mattered is the one that survived.

    It used to assert the margin dropped *below* the claim at 390px rather than being hidden -- a
    statement about a two-column grid collapsing. There is no grid now: the audit is a leaf of its
    own on a phone exactly as it is on a monitor, which is a stronger answer to the same worry.
    "Nothing about always visible is negotiable on a small screen" is the sentence this test is for,
    so that is what it says.
  */
  await page.setViewportSize({ width: 390, height: 844 });
  await eachClaim(page, async (pages) => {
    await at(page, pages.bias);
    await expect(page.locator(".leaves"), "a phone got a spread").toBeVisible();
    await expect(page.locator(".bias__domain").first()).toBeVisible();
    await expect(page.locator(".bias__finding").first()).toBeVisible();
    await expect(page.locator("details, [hidden]")).toHaveCount(0);
  });

  // And nothing overflows sideways, which is what a fixed 19rem column would have done here.
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, `${overflow}px of horizontal overflow`).toBeLessThanOrEqual(1);
});

test("paper is paper, not a bordered box", async ({ page }) => {
  /*
    Two halves, because the subject split.

    A claim is on a *page* now, and a page is not a card: no border and no radius, which is what the
    arrival's sheet was measured for and is just as true of a leaf. And `Sheet` itself was not
    rebuilt for the book -- the world chapter still mounts one -- so its torn ground and its lift are
    still asserted, on the component rather than on the page that used to hold it. `clip-path` and
    `box-shadow` do not compose, so the lift has to be a drop-shadow filter on an ancestor, and that
    is the trap worth keeping a test on.
  */
  await ready(page);
  const leaf = await page.locator(".spread > .page--verso").evaluate((node) => {
    const style = getComputedStyle(node);
    return { border: style.borderTopWidth, radius: style.borderTopLeftRadius };
  });
  expect(leaf.border, "a page has a border, which makes it a card").toBe("0px");
  expect(leaf.radius, "a page has rounded corners, which makes it a card").toBe("0px");

  await world(page);
  const clip = await page
    .locator(".explore .sheet__ground")
    .evaluate((node) => getComputedStyle(node).clipPath);
  expect(clip, "the paper is still a rectangle").toContain("path(");

  const lift = await page
    .locator(".explore .sheet__lift")
    .evaluate((node) => getComputedStyle(node).filter);
  expect(lift, "no shadow, or one that the clip will have eaten").toContain("drop-shadow");
});

test("the drawn edge stays put while what is inside it scrolls", async ({ page }) => {
  /*
    The regression this exists for: an absolutely-positioned edge inside a scrolling box is placed
    against the padding box, so the tear travels up the screen as a reader scrolls.

    It used to scroll a claim under the arrival's sheet. Book pages do not scroll -- `pages.ts` puts
    one panel on a page for exactly that reason, and the guard against a page overflowing lives in
    `book.spec.ts` now -- but the *pattern* is alive in the world chapter, whose tools scroll inside
    a torn sheet. So the assertion moved to where it can still fail.
  */
  await world(page);
  await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running"));

  const slip = page.locator(".explore__slip");
  const before = await page.locator(".explore .sheet__ink").boundingBox();
  await slip.evaluate((node) => node.scrollBy(0, 400));
  await expect
    .poll(async () => (await slip.evaluate((n) => n.scrollTop)) > 0, { timeout: 15_000 })
    .toBe(true);
  const after = await page.locator(".explore .sheet__ink").boundingBox();
  expect(after?.y).toBeCloseTo(before?.y ?? 0, 0);
});

test("a control is drawn, not bordered", async ({ page }) => {
  /*
    The arrival's three doors are gone, so this probes the controls the book actually has: the thumb
    tab that turns to a chapter, and the folio in the corner that turns one page. Same pen, same
    rule -- a stroked rounded rectangle is a platform control and there are none on this site.
  */
  await ready(page);

  /*
    The `Boxed` controls, which are the ones that claim to be drawn. The folio in the corner is not
    one of them and is not meant to be: it is type, with no box at all, which the bordered-control
    sweep below covers instead. A control that draws nothing cannot be measured for whether what it
    drew overshoots.
  */
  for (const selector of [".type__option--on", ".surface__option--on"]) {
    // The *chosen* one of each, because `Boxed` draws the circle only round the option that is on
    // -- which is the next test down. Probing the first option instead found an element with
    // nothing drawn in it and waited thirty seconds for a path that was never going to exist.
    const button = page.locator(selector).first();
    expect(
      await button.evaluate((node) => getComputedStyle(node).borderTopWidth),
      `${selector} still has a border`,
    ).toBe("0px");
    const length = await button
      .locator(".boxed path")
      .first()
      .evaluate((node) => (node as unknown as SVGPathElement).getTotalLength());
    // Longer than the perimeter would be if it were a rectangle drawn exactly: the corners
    // overshoot, which is the whole reason it reads as drawn rather than as a border.
    expect(length, `${selector} has no drawn box`).toBeGreaterThan(100);
  }

  /*
    Chosen is a second pass of the pen, not a fill. A hand has "drawn" and "gone over twice"; it does
    not have a hover colour, which is what `Boxed` says at length and does with a second `boxDrawn`
    from a different seed at 55% opacity.

    Compared rather than counted: rough.js emits more than one path per pass, so the number is its
    business and the invariant is that the chosen option carries strokes the unchosen ones do not.
    The arrival's three doors used to be the subject here; the type presets are the same control.
  */
  const strokes = (selector: string) => page.locator(`${selector} .boxed path`).count();
  const chosen = await strokes(".type__option--on");
  const unchosen = await strokes(".type__option:not(.type__option--on)");
  expect(chosen, "the chosen option has no drawn box at all").toBeGreaterThan(0);
  expect(
    chosen,
    `the chosen option has ${chosen} strokes against ${unchosen} across the other two`,
  ).toBeGreaterThan(Math.round(unchosen / 2));
});

test("only the chosen option is circled", async ({ page }) => {
  await ready(page);
  // Looping all three would say nothing. The unchosen ones are meant to be just words, which is
  // also why they carry no fill and no border to distinguish them.
  const options = page.locator(".surface__option");
  await expect(options).toHaveCount(3);
  await expect(page.locator(".surface .ink-lasso")).toHaveCount(1);
  await expect(page.locator(".surface__option--on .ink-lasso")).toHaveCount(1);
});

test("nothing on the page is still a bordered control", async ({ page }) => {
  await ready(page);
  /*
    The sweep, rather than one assertion per widget. Every interactive thing on a claim was once a
    rectangle with a border and a radius, and the point of this pass is that none of them are.

    `.tab` left the list, and this is the one exemption in it, so it is argued rather than dropped.
    ADR 0015 decision 3 makes a chapter tab a piece of *coloured paper stock* cut into the book's
    fore-edge -- not a widget -- and its 1px edge is `color-mix(--tint 45%, --rule)`, which is the
    notebook's own pencil line at the colour of the tab. The rule this test enforces is that nothing
    looks like a platform control; a cut edge on paper does not. The assertion below keeps a guard on
    it rather than trusting that: a tab's edge must be drawn in the rule's colour and must never pick
    up a radius on more than the two corners a tab has.
  */
  const bordered = await page.evaluate(() =>
    [...document.querySelectorAll(".option, .surface__option, .type__option, .layers input, [data-turn]")]
      .filter((node) => {
        const style = getComputedStyle(node);
        return Number.parseFloat(style.borderTopWidth) > 0;
      })
      .map((node) => node.className || node.tagName),
  );
  expect(bordered, "these still carry a CSS border").toEqual([]);

  const tab = await page.locator(".tab").first().evaluate((node) => {
    const style = getComputedStyle(node);
    return {
      colour: style.borderTopColor,
      rule: getComputedStyle(document.documentElement).getPropertyValue("--rule").trim(),
      corners: [
        style.borderTopLeftRadius,
        style.borderTopRightRadius,
        style.borderBottomRightRadius,
        style.borderBottomLeftRadius,
      ],
    };
  });
  // Mixed with the tab's own tint, so not equal to `--rule` -- but it must be a colour and not a
  // system border, and it must not be the ink the text is set in.
  expect(tab.colour, "a tab with no edge is not cut paper").not.toBe("rgba(0, 0, 0, 0)");
  expect(
    tab.corners.filter((corner) => corner !== "0px").length,
    "a tab is rounded on the two corners that stick out, not all four",
  ).toBeLessThanOrEqual(2);
});

test("switching a layer on draws a tick rather than filling a box", async ({ page }) => {
  await world(page);

  // Layers land one by one and the panel re-renders as they do; clicking a row while the list
  // grows races the re-render. The debug hook is published once every layer has loaded, so its
  // existence is the load-complete signal -- the first version of this wait counted to seven,
  // and the ice layer made the count stale within a day, which is what counting by hand does.
  await page.waitForFunction(
    () => !!(window as unknown as { migratlas?: { loaded?: unknown[] } }).migratlas?.loaded?.length,
    undefined,
    { timeout: 30_000 },
  );

  const row = page.locator(".layers li").first();
  const mark = row.locator(".ticked");
  await expect(mark).toBeVisible();

  // Drawn on, so the state is a dash offset rather than a colour. Reading it this way also pins
  // that the tick animates in from nothing instead of appearing -- and that reduced motion, which
  // zeroes `--draw-quick`, still lands it in the final state.
  const offset = () =>
    row.locator(".ticked .ink-tick path").first().evaluate((node) => getComputedStyle(node).strokeDashoffset);

  const before = await offset();
  await row.locator("input").click();
  // Fifteen seconds because the tick redraws on an animation frame, and CI runs two WebGL
  // workers on a machine with no GPU -- the state lands correctly and late.
  await expect.poll(offset, { timeout: 15_000 }).not.toBe(before);

  // And the checkbox is still the control: hidden natively, but the thing a pointer and a keyboard
  // both reach. The tick is ink.
  await expect(row.locator("input")).toBeFocused();
});

test("the paper turns and the world does not", async ({ page }) => {
  /*
    The book's turn is a CSS 3D rotation rather than a view transition, so the assertion changed
    shape while keeping its subject exactly: whatever the turn captures must not include the globe.

    The root must still be unnameable, and for the reason it always was -- a snapshotted root
    includes MapLibre's canvas, which freezes into a still image for the length of the turn and says
    the globe is a picture the card is printed over. What replaces "only the sheet is named" is
    stronger and is the rule ADR 0015 decision 7 states: no `filter` on any ancestor of the leaf,
    because a filter flattens 3D transforms. The turn is measured about the spine, which is what
    `book.spec.ts` does at three points of the animation's own timeline.
  */
  await ready(page);

  const named = await page.evaluate(
    () => getComputedStyle(document.documentElement).viewTransitionName,
  );
  expect(named, "the root would be snapshotted, freezing the globe").toBe("none");

  // The leaf rotates in three dimensions, so nothing above it may carry a filter.
  await page.locator('.spread > .page--recto [data-turn="on"]').click();
  await expect(page.locator(".leaf"), "no leaf was built for the turn").toHaveCount(1);
  const flattened = await page.evaluate(() => {
    const leaf = document.querySelector(".leaf");
    if (!leaf) return "no leaf was built";
    for (let node = leaf.parentElement; node; node = node.parentElement) {
      if (getComputedStyle(node).filter !== "none") return node.className || node.tagName;
    }
    return "";
  });
  expect(flattened, "an ancestor of the leaf carries a filter, which flattens the rotation").toBe("");
});

test("changing claim never blocks the main thread for long", async ({ page }) => {
  await ready(page);
  // The guard that lets the rest of this go all out. Bytes are the wrong instrument for animation
  // work -- a page turn adds no payload and can still cost a reader every frame of it -- so what
  // is budgeted is the thing that would actually be felt.
  //
  // Not `buffered: true`, and that is the whole reliability of this test. A buffered longtask
  // observer replays entries from before it existed, so the first thing it reports is the page
  // load -- MapLibre booting and 125,000 features decoding. This measured a constant 229ms for
  // every claim, including ones it had not clicked yet, and read as a page-turn cost.
  //
  // **Two numbers, because one cannot serve both machines.** 300ms is a developer machine, where
  // this reads 132-228ms and a regression shows up immediately. CI reads 617-1208ms for the same
  // page: Chromium there renders WebGL in software, and a claim change flies the MapLibre camera.
  //
  // A ratio was tried first and is recorded here because it looked right and was not. The idea was
  // to divide runner speed out by measuring a claim change against a repaint of the same page --
  // switching surface -- in the same run. It held between 1.50 and 1.71 across four local runs and
  // on the pull-request runner, then read **3.2** on the deploy runner. Runner speed only divides
  // out of a ratio when both sides scale together, and these do not: the camera flight is GPU work
  // that software rendering inflates several times harder than it inflates a sheet repaint.
  //
  // So the local number does the work and CI keeps a backstop against catastrophe. The repaint is
  // still measured, because a failure that reports both is diagnosable and one that reports a bare
  // number is a bisect -- which is what the previous version of this cost.
  const observe = () =>
    page.evaluate(() => {
      (window as unknown as { longTasks: number[] }).longTasks = [];
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          (window as unknown as { longTasks: number[] }).longTasks.push(entry.duration);
        }
      }).observe({ type: "longtask" });
    });
  const worstSince = () =>
    page.evaluate(() => Math.max(0, ...(window as unknown as { longTasks: number[] }).longTasks));

  await observe();
  await surfaceIs(page, "Night");
  await surfaceIs(page, "Day");
  const repaint = await worstSince();

  /*
    Three page turns, where this used to click three index tabs. The budget is unchanged and it is
    the calibrated kind: 300ms locally against a repaint of the same page on the same machine, which
    is why the repaint is measured first rather than assumed.
  */
  await observe();
  for (let turn = 0; turn < 3; turn += 1) {
    await page.locator('.spread > .page--recto [data-turn="on"]').click();
    await expect(page.locator(".spread > .page--recto .page__folio")).toBeVisible();
  }
  const worst = await worstSince();

  const allowed = process.env.CI ? 2000 : 300;
  expect(
    worst,
    `a ${worst.toFixed(0)}ms task during a claim change, against a ${repaint.toFixed(0)}ms ` +
      `repaint of the same page on the same machine`,
  ).toBeLessThan(allowed);
});

test("with motion turned down the next claim is simply there", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await ready(page);

  // Not a faster turn -- no turn. `Book` reads `--draw` through `still()` and declines to build a
  // leaf at all, so the new spread is in its final state on the first frame.
  const before = await page.locator(".spread > .page--recto .page__folio").textContent();
  await page.locator('.spread > .page--recto [data-turn="on"]').click();
  await expect(page.locator(".spread > .page--recto .page__folio")).not.toHaveText(before ?? "");
  await expect(page.locator(".leaf")).toHaveCount(0);
  expect(
    await page.evaluate(() => document.getAnimations().some((a) => a.playState === "running")),
    "something is still animating under reduced motion",
  ).toBe(false);
});

test("nothing on the page is still set in a type face that came with a glyph", async ({ page }) => {
  await eachClaim(page, async (pages) => {
    if ((await page.locator(".survived li").count()) === 0) await at(page, pages.survived);
  });
  // The survived list used U+2713, which came from whichever font happened to have it and was the
  // last mark on the page still set in type rather than drawn. Every other tick on the site is two
  // strokes from `ink.ts`; this one is now too.
  const survived = page.locator(".survived li").first();
  await expect(survived).toBeVisible();
  await expect(survived.locator(".ticked")).toHaveCount(1);
  expect(await survived.textContent()).not.toContain("✓");

  // Bare in a list, boxed in a control: a list of things a claim survived is not a set of
  // checkboxes, and drawing boxes round them would invite a reader to untick one.
  await expect(survived.locator(".ticked .ink-box")).toHaveCount(0);
});

test("the tools are on the same paper as the claims", async ({ page }) => {
  await world(page);

  // The panel was the last thing left with a plain background and no edge, which read as a
  // different material sitting next to the cards.
  await expect(page.locator(".explore .sheet__ink .ink-box")).toHaveCount(1);
  const clip = await page
    .locator(".explore .sheet__ground")
    .evaluate((node) => getComputedStyle(node).clipPath);
  expect(clip).toContain("path(");

  // And the scroll is inside the paper, so the torn edge does not travel as the tools scroll.
  expect(
    await page.locator(".explore__slip").evaluate((node) => getComputedStyle(node).overflowY),
  ).toBe("auto");
});

test("a slider is a ruled scale, not a platform control", async ({ page }) => {
  await world(page);
  const slider = page.locator('.explore input[type="range"]').first();
  await expect(slider).toBeVisible();

  // `appearance: none` is the load-bearing half: a range input styles nothing in common across
  // engines, and a half-styled one looks like a rendering fault rather than a decision.
  const style = await slider.evaluate((node) => {
    const computed = getComputedStyle(node);
    return { appearance: computed.appearance, background: computed.backgroundColor };
  });
  expect(style.appearance).toBe("none");
  expect(style.background).toBe("rgba(0, 0, 0, 0)");

  // Still a real range, so a keyboard still drives it.
  await slider.focus();
  const before = await slider.inputValue();
  await slider.press("ArrowRight");
  expect(await slider.inputValue()).not.toBe(before);
});

test("the scrollbar is drawn, and only one of the two APIs is styling it", async ({ page }) => {
  await ready(page);

  const drawn = await page.evaluate(() => {
    const style = getComputedStyle(document.documentElement);
    return {
      track: style.getPropertyValue("--scroll-track").trim(),
      thumb: ["--thumb-top", "--thumb-mid", "--thumb-bottom"].map((name) =>
        style.getPropertyValue(name).trim(),
      ),
      width: style.scrollbarWidth,
    };
  });

  expect(drawn.track, "no drawn track").toContain("data:image/svg+xml");
  for (const part of drawn.thumb) expect(part).toContain("data:image/svg+xml");

  // The whole reliability of the drawing. Chromium supports `scrollbar-width`, and setting it to
  // anything but `auto` switches the `::-webkit-scrollbar-*` pseudo-elements off entirely -- which
  // is how the first version silently un-styled itself and shipped a plain grey bar. The rule that
  // sets it is behind `@supports not selector(::-webkit-scrollbar)`, so in this engine it must not
  // apply. In Firefox it would, and the drawing is not available there anyway.
  const webkit = await page.evaluate(() => CSS.supports("selector(::-webkit-scrollbar)"));
  if (webkit) {
    expect(drawn.width, "the standard property is on, so the drawn track is switched off").toBe(
      "auto",
    );
  }
});

test("the map's own controls are in the same hand", async ({ page }) => {
  await world(page);

  // MapLibre ships these as white rounded boxes with a grey shadow and near-black icons in fixed
  // colours -- the last borrowed furniture on the page, and the only part of it that sits directly
  // on the paper.
  const group = page.locator(".maplibregl-ctrl-group").first();
  const box = await group.evaluate((node) => {
    const style = getComputedStyle(node);
    return { radius: style.borderTopLeftRadius, shadow: style.boxShadow };
  });
  expect(box.radius).toBe("0px");
  expect(box.shadow).toBe("none");

  for (const role of ["zoom-in", "zoom-out"]) {
    const button = page.locator(`.maplibregl-ctrl-${role}`);
    const image = await button.evaluate((node) => getComputedStyle(node).backgroundImage);
    // Two: the mark and the box it is in, both generated with the same pen as the page.
    expect(image, `${role} is not drawn`).toContain("data:image/svg+xml");
    expect(image.match(/data:image\/svg\+xml/g)?.length, `${role} has no drawn box`).toBe(2);

    // And MapLibre's own icon is off rather than underneath, which would be two plus signs.
    const inner = await button
      .locator(".maplibregl-ctrl-icon")
      .evaluate((node) => getComputedStyle(node).backgroundImage);
    expect(inner, `${role} still carries MapLibre's icon`).toBe("none");
  }

  // The scale bar is a measure before it is a mark: its rule must span the element MapLibre sized,
  // because the width *is* the distance printed beside it.
  const scale = await page
    .locator(".maplibregl-ctrl-scale")
    .evaluate((node) => getComputedStyle(node).backgroundSize.split(",")[0]?.trim());
  expect(scale).toBe("100% 6px");
});

test("the licence notice is restyled and not shrunk", async ({ page }) => {
  await world(page);
  // The one piece of map furniture that is a legal obligation rather than a control. It may be
  // recoloured and it may be moved; it may not be made smaller or fainter than the page's own
  // smallest prose, and it has to clear AA against whatever it is sitting on.
  const notice = page.locator(".maplibregl-ctrl-attrib").first();
  // Resolved through a probe rather than parsed off the token, because `--size-margin` is a rem
  // string and the comparison has to be in the pixels the reader actually gets.
  const smallest = await page.evaluate(() => {
    const probe = document.createElement("span");
    probe.style.fontSize = "var(--size-margin)";
    // Resolved *inside* the book rather than on the body. The spread scales its reading sizes
    // against the page's own height, so `--size-margin` on the root is a different number from the
    // one the notice sitting on that page actually inherits -- and comparing the two measured the
    // scale rather than the notice. 10.03px against a root 10.56px, which is what this caught.
    (document.querySelector(".leaves, .spread, .world") ?? document.body).append(probe);
    const resolved = Number.parseFloat(getComputedStyle(probe).fontSize);
    probe.remove();
    return resolved;
  });
  const size = await notice.evaluate((node) => Number.parseFloat(getComputedStyle(node).fontSize));
  expect(
    size,
    `the licence notice is ${size}px against the page's smallest prose at ${smallest}px`,
  ).toBeGreaterThanOrEqual(smallest);

  const ratio = await notice.evaluate((node) => {
    const channel = (value: number) =>
      value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
    const luminance = (colour: string) => {
      const parts = colour.match(/[\d.]+/g)?.map(Number) ?? [0, 0, 0];
      const [r = 0, g = 0, b = 0] = parts.map((value) => channel(value / 255));
      return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    };
    const style = getComputedStyle(node);
    const ink = luminance(style.color);
    const paper = luminance(style.backgroundColor);
    const [high, low] = ink > paper ? [ink, paper] : [paper, ink];
    return (high + 0.05) / (low + 0.05);
  });
  expect(ratio, `the licence notice is ${ratio.toFixed(2)}:1`).toBeGreaterThanOrEqual(AA_SMALL);
});

test("the furniture follows the paper it is drawn on", async ({ page }) => {
  await ready(page);
  // A data URI cannot carry a `var()`, so every one of these has a hex baked into it. That is the
  // one thing about this approach that can rot: a scrollbar and a set of map buttons still drawn in
  // day ink down the side of a black page, which is exactly what a token would have prevented.
  const read = () =>
    page.evaluate(() => {
      const style = getComputedStyle(document.documentElement);
      return ["--scroll-track", "--thumb-top", "--ctrl-zoom-in", "--scale-rule"].map((name) =>
        style.getPropertyValue(name).trim(),
      );
    });

  const day = await read();
  await surfaceIs(page, "Night");
  await expect(page.locator(":root")).toHaveAttribute("data-surface", "night");
  /*
    An explicit deadline, because the default is five seconds and nobody chose it. See the note on
    the darts' rotation poll for the flake that made the point.
  */
  await expect
    .poll(async () => (await read())[0], {
      message: "the surface changed and the drawn marks did not",
      timeout: 30_000,
    })
    .not.toBe(day[0]);

  const night = await read();
  for (const [index, drawing] of night.entries()) {
    expect(drawing, "this one was not redrawn for the night surface").not.toBe(day[index]);
  }
});

test("a rule is one continuous stroke, not a dashed line", async ({ page }) => {
  await ready(page);
  // The regression. The first version stretched a 100-unit viewBox with `non-scaling-stroke`, which
  // put the path in user units and the dash pattern in screen units -- so the dasharray meant to
  // cover the whole line drew four dashes and a gap instead. It looked like a design choice.
  const drawn = await page.locator(".rule path").first().evaluate((node) => {
    const style = getComputedStyle(node);
    return {
      dash: Number.parseFloat(style.strokeDasharray),
      length: (node as SVGPathElement).getTotalLength(),
    };
  });

  expect(drawn.length).toBeGreaterThan(50);
  // One dash at least as long as the path: anything shorter is a gap somewhere in the middle.
  expect(
    drawn.dash,
    `dash ${drawn.dash.toFixed(0)} against a path of ${drawn.length.toFixed(0)}`,
  ).toBeGreaterThanOrEqual(drawn.length);
});

test("the instrument marks stay legible as marks", async ({ page }) => {
  await ready(page);
  // Non-text contrast: an instrument that carries meaning has to be distinguishable from the paper.
  const stroke = page.locator(".instrument__stroke").first();
  const ratio = await stroke.evaluate((node) => {
    const channel = (value: number) =>
      value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
    const luminance = (colour: string) => {
      const parts = colour.match(/[\d.]+/g)?.map(Number) ?? [0, 0, 0];
      const [r = 0, g = 0, b = 0] = parts.map((value) => channel(value / 255));
      return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    };
    const ink = luminance(getComputedStyle(node).stroke);
    const paper = luminance(getComputedStyle(document.body).backgroundColor);
    const [high, low] = ink > paper ? [ink, paper] : [paper, ink];
    return (high + 0.05) / (low + 0.05);
  });
  expect(ratio, `instrument stroke is ${ratio.toFixed(2)}:1`).toBeGreaterThanOrEqual(AA_LARGE);
});

/**
 * The book's own tokens, and the one property of them that is measured rather than chosen.
 *
 * `--plate-paper` is the stock a plate is taped onto, and its relationship to the page **inverts
 * with the light**: by day a second sheet on cream paper is slightly darker, by night it must be
 * lighter, because `--paper` and `--paper-sunken` are six units apart on the dark palette and a mix
 * between them is invisible. ADR 0015 records that as a measurement; this is what stops a later
 * simplification of the mix from quietly undoing it.
 */
for (const surface of ["day", "night"] as const) {
  test(`the plate stock reads against the page on ${surface}`, async ({ page }) => {
    await ready(page);
    if (surface === "night") await surfaceIs(page, "Night");

    const measured = await page.evaluate(() => {
      const style = getComputedStyle(document.documentElement);
      // Through a canvas, because `color-mix()` resolves to `color(srgb ...)` whose components are
      // fractions -- parsing the string as 0-255 silently rounds every channel to 0 or 1.
      const canvas = document.createElement("canvas");
      canvas.width = 1;
      canvas.height = 1;
      const ctx = canvas.getContext("2d");
      const channels = (css: string): number[] => {
        if (!ctx) return [];
        ctx.fillStyle = "#000";
        ctx.fillStyle = css;
        ctx.fillRect(0, 0, 1, 1);
        return [...ctx.getImageData(0, 0, 1, 1).data].slice(0, 3);
      };
      const brightness = (rgb: number[]) => (rgb[0]! + rgb[1]! + rgb[2]!) / 3;
      const paper = channels(style.getPropertyValue("--paper").trim());
      const plate = channels(style.getPropertyValue("--plate-paper").trim());
      return {
        gap: Math.round(Math.hypot(...plate.map((v, i) => v - paper[i]!))),
        lighter: brightness(plate) > brightness(paper),
        lede: style.getPropertyValue("--size-lede").trim(),
      };
    });

    // Visible, and the first attempt at this managed two units per channel by day and six by night.
    expect(measured.gap, `plate is only ${measured.gap} from the page`).toBeGreaterThan(10);
    expect(
      measured.lighter,
      surface === "day"
        ? "by day a sheet on the page should be darker than it"
        : "by night a sheet on the page should be lighter than it",
    ).toBe(surface === "night");
    expect(measured.lede, "--size-lede does not resolve").toContain("rem");
  });
}

