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

import { expect, test, type Locator, type Page } from "@playwright/test";

/** WCAG 2.1 AA for text below 24px, or below 18.66px bold. Everything on the card is below both. */
const AA_SMALL = 4.5;

/** AA for large text and for meaningful non-text marks. */
const AA_LARGE = 3;

/**
 * Open the shipped page and get to a claim.
 *
 * The shell shows one claim at a time, so a suite that used to read five cards off a preview page now
 * walks the index. That is the right trade: these assertions are worth more against what actually
 * ships than against a page built to make them convenient.
 */
async function ready(page: Page): Promise<void> {
  await page.goto("?debug=1");
  await page.getByRole("button", { name: /show me how you know/i }).click();
  await expect(page.locator(".claim").first()).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
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

/** Every claim in turn, by clicking the index. */
async function eachClaim(page: Page, visit: (index: number) => Promise<void>): Promise<void> {
  const tabs = page.locator(".tab").filter({ hasNotText: "Just the map" });
  const count = await tabs.count();
  expect(count, "no claims in the index").toBeGreaterThan(0);
  for (let index = 0; index < count; index += 1) {
    await tabs.nth(index).click();
    await expect(page.locator(".claim__title")).toBeVisible();
    await visit(index);
  }
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
  const sheet = await page.locator(".sheet").first().boundingBox();
  expect(sheet, "no sheet to measure the paper on").toBeTruthy();
  // The top-left of the ground, inside the torn edge and above the first line of the claim: the
  // leaf's own top padding is 25.6px, and the drawn edge wanders no further in than about 6.
  const shot = (
    await page.screenshot({
      clip: { x: sheet!.x + 12, y: sheet!.y + 11, width: 12, height: 12 },
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
    if (surface === "night") {
      // Through the switch a reader would use, not by stamping the attribute. This test used to do
      // the latter with a comment saying the shell had no switch yet -- so the palette was measured
      // in a state nobody could reach, and the day it became reachable nothing here would have
      // noticed if the control set the wrong value.
      await surfaceIs(page, "Night");
      await expect(page.locator(":root")).toHaveAttribute("data-surface", "night");
    }

    // One per token that carries text, chosen as the smallest instance of each: if the 0.66rem
    // label passes, the 1.35rem value using the same token does too.
    const samples: [string, string, number][] = [
      ["the claim title", ".claim__title", AA_SMALL],
      ["why it matters", ".claim__matters", AA_SMALL],
      ["the measurement", ".claim__value", AA_SMALL],
      ["the short caveat", ".claim__short-caveat", AA_SMALL],
      ["the register label", ".claim__register", AA_SMALL],
      ["the precise claim", ".claim__precise", AA_SMALL],
      ["the scope", ".claim__scope", AA_SMALL],
      ["the caveat", ".claim__caveat", AA_SMALL],
      ["the direction banner", ".claim__banner", AA_SMALL],
      ["the method link", ".claim__method", AA_SMALL],
      ["a bias domain", ".bias__domain", AA_SMALL],
      ["an open bias status", ".bias__status--open", AA_SMALL],
      ["a bounded bias status", ".bias__status--bounded", AA_SMALL],
      ["a bias finding", ".bias__finding", AA_SMALL],
      ["a survived test", ".survived li", AA_SMALL],
      ["the specimen line", ".specimen p", AA_SMALL],
    ];

    // Measured off the sheet these words are printed on, not off `--paper`, and the two are not
    // the same value: the grain is blended into the token, so what a reader sees is the composite.
    const sheet = await sheetPaper(page);
    const paper = luminance(sheet.rgb);

    for (const [what, selector, floor] of samples) {
      const target = page.locator(selector).first();
      await expect(target, `${what} is not on the page`).toBeVisible();
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
  const surfaces = await page.evaluate(() => {
    const of = (node: Element | null) => {
      if (!node) return null;
      const style = getComputedStyle(node);
      return [style.backgroundColor, style.backgroundImage, style.backgroundSize, style.backgroundBlendMode].join(
        " | ",
      );
    };
    return {
      body: of(document.body),
      sheet: of(document.querySelector(".sheet__ground")),
      index: of(document.querySelector(".index")),
    };
  });

  expect(surfaces.sheet, "the claim sheet is not the same paper as the page").toBe(surfaces.body);
  expect(surfaces.index, "the index strip is not the same paper as the page").toBe(surfaces.body);
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
  await ready(page);
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
  await expect.poll(ocean).not.toBe(byDay);
});

test("an addressed status is legible too, and is not the only signal", async ({ page }) => {
  await ready(page);
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
  await page.locator('.tab[data-claim="anthropogenic-share"]').click();
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
  await eachClaim(page, async () => {
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

test("the audit is rendered beside every claim, not behind a control", async ({ page }) => {
  // Walks every claim, and each walk is a camera flight. Budgeted rather than left on the 30s
  // default, which it exceeded on CI -- and the second walk this test used to make was pure waste.
  test.setTimeout(90_000);
  await ready(page);

  let open = 0;
  await eachClaim(page, async () => {
    const claim = page.locator(".claim").first();

    // Visible, and with no ancestor that could be closed. `findings.py` refuses to publish a claim
    // with no caveat; a `<details>` around the audit would satisfy that and break its point.
    await expect(claim.locator(".margin")).toBeVisible();
    await expect(claim.locator(".bias__domain").first()).toBeVisible();
    await expect(claim.locator(".margin details, .margin [hidden]")).toHaveCount(0);
    await expect(claim.locator(".claim__caveat")).not.toBeEmpty();

    // Counted in the same pass. At least one domain must read "open" across the set: every domain
    // "addressed" would mean either that nothing is unresolved -- false, the 2012 step is -- or that
    // the audit is written to reassure rather than to inform.
    open += await claim.locator(".bias__status--open").count();
  });

  expect(open, "nothing is marked open, which would mean the audit is decorative").toBeGreaterThan(0);
});

test("every claim is said twice, plainly and precisely, and both are on the page", async ({
  page,
}) => {
  test.setTimeout(90_000);
  await ready(page);

  // The precise sentence is the scientific statement and stays whole. The plain one carries the
  // finding to a reader without statistics. Adding the second register is fine; the failure this
  // guards is the next change, where someone notices the claim looks redundant under a heading
  // that says almost the same thing and deletes one of them.
  await eachClaim(page, async () => {
    const claim = page.locator(".claim").first();
    const plain = (await claim.locator(".claim__title").textContent())?.trim() ?? "";
    const precise = (await claim.locator(".claim__precise").textContent())?.trim() ?? "";

    expect(plain.length, "a claim with no plain sentence").toBeGreaterThan(20);
    expect(precise.length, "a claim with no precise sentence").toBeGreaterThan(20);
    expect(precise.replace(/^Precisely\s*/, "")).not.toBe(plain);

    // Both caveats, and neither behind a control -- same rule as the audit margin.
    await expect(claim.locator(".claim__short-caveat")).not.toBeEmpty();
    await expect(claim.locator(".claim__caveat")).not.toBeEmpty();
    await expect(claim.locator(".claim__matters")).not.toBeEmpty();
    await expect(claim.locator(".claim details, .claim [hidden]")).toHaveCount(0);
  });
});

test("the plain register is set larger than the precise one it introduces", async ({ page }) => {
  await ready(page);
  // Which register is the heading is the decision, so it has to be legible as one. A plain
  // sentence typeset at the same size as the sentence beneath it is not a heading, it is a
  // duplicate -- and a reader would have to work out which of the two to read first.
  const sizeOf = (selector: string) =>
    page
      .locator(selector)
      .first()
      .evaluate((node) => Number.parseFloat(getComputedStyle(node).fontSize));

  expect(await sizeOf(".claim__title")).toBeGreaterThan(await sizeOf(".claim__precise"));
});

test("no number animates to its value", async ({ page }) => {
  await ready(page);
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
  await ready(page);
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

  // The heading is the hand, whichever hand the reader has chosen.
  expect(await faceOf(".claim__title")).toContain(hand);

  // And every figure is mono, which is the half that is not negotiable.
  expect(await faceOf(".claim__value")).toContain(mono);
  for (const selector of [".claim__banner", ".bias__domain", ".specimen p"]) {
    expect(await faceOf(selector), `${selector} is set in the hand face`).not.toContain(hand);
  }
});

test("the margin moves below the claim on a phone rather than disappearing", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await ready(page);

  const claim = page.locator(".claim").first();
  const body = await claim.locator(".claim__body").boundingBox();
  const margin = await claim.locator(".margin").boundingBox();
  expect(body && margin).toBeTruthy();

  // Below, not beside, and still on the page: the only thing that changes at this width is where
  // it sits. Nothing about "always visible" is negotiable on a small screen.
  expect(margin!.y).toBeGreaterThanOrEqual(body!.y + body!.height - 1);
  expect(margin!.width).toBeGreaterThan(200);
  await expect(claim.locator(".bias__finding").first()).toBeVisible();

  // And nothing overflows sideways, which is what a fixed 19rem column would have done here.
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, `${overflow}px of horizontal overflow`).toBeLessThanOrEqual(1);
});

test("a claim is on a sheet of paper, not in a bordered box", async ({ page }) => {
  await ready(page);
  const sheet = page.locator(".shell__sheet .sheet");
  await expect(sheet).toBeVisible();

  // No border and no radius: a stroked rounded rectangle is a UI card, and it was the single most
  // un-notebook-like thing on the page. The edge is drawn instead, and it overshoots its corners.
  const box = await sheet.evaluate((node) => {
    const style = getComputedStyle(node);
    return { border: style.borderTopWidth, radius: style.borderTopLeftRadius };
  });
  expect(box.border).toBe("0px");
  expect(box.radius).toBe("0px");

  // The ground is clipped to a torn path rather than filling the rectangle.
  const clip = await page
    .locator(".shell__sheet .sheet__ground")
    .evaluate((node) => getComputedStyle(node).clipPath);
  expect(clip, "the paper is still a rectangle").toContain("path(");

  // And the shadow follows the tear. `clip-path` and `box-shadow` do not compose -- the shadow is
  // painted and then clipped away -- so this has to be a drop-shadow filter on an ancestor.
  const lift = await page
    .locator(".shell__sheet .sheet__lift")
    .evaluate((node) => getComputedStyle(node).filter);
  expect(lift, "no shadow, or one that the clip will have eaten").toContain("drop-shadow");
});

test("the drawn edge stays put while the claim scrolls under it", async ({ page }) => {
  await ready(page);
  const leaf = page.locator(".shell__leaf");
  // The regression this exists for: an absolutely-positioned edge inside a scrolling box is placed
  // against the padding box, so the tear travels up the screen as a reader scrolls.
  //
  // Measured only once the sheet has stopped arriving. The card lands with an 8px `settle`, and a
  // first reading taken mid-animation put this 1.7px out -- reported as the edge having moved,
  // which is the one thing the test is meant to detect. Fonts finishing later made it likelier
  // rather than causing it, so the wait belongs here rather than a longer one in `ready`.
  await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running"));

  const before = await page.locator(".shell__sheet .sheet__ink").boundingBox();
  await leaf.evaluate((node) => node.scrollBy(0, 400));
  await expect.poll(async () => (await leaf.evaluate((n) => n.scrollTop)) > 0).toBe(true);
  const after = await page.locator(".shell__sheet .sheet__ink").boundingBox();
  expect(after?.y).toBeCloseTo(before?.y ?? 0, 0);
});

test("a control is drawn, not bordered", async ({ page }) => {
  await page.goto("?debug=1");
  await expect(page.locator(".arrival__card")).toBeVisible();

  for (const selector of [".way--primary", ".way:not(.way--primary)"]) {
    const button = page.locator(selector);
    expect(
      await button.evaluate((node) => getComputedStyle(node).borderTopWidth),
      `${selector} still has a border`,
    ).toBe("0px");
    const length = await button
      .locator(".ink-box path")
      .first()
      .evaluate((node) => (node as unknown as SVGPathElement).getTotalLength());
    // Longer than the perimeter would be if it were a rectangle drawn exactly: the corners
    // overshoot, which is the whole reason it reads as drawn rather than as a border.
    expect(length, `${selector} has no drawn box`).toBeGreaterThan(100);
  }

  // Pressed and chosen are a second pass of the pen, not a fill. A hand has "drawn" and "gone over
  // twice"; it does not have a hover colour.
  await expect(page.locator(".way--primary .ink-box")).toHaveCount(2);
  await expect(page.locator(".way:not(.way--primary) .ink-box")).toHaveCount(1);
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
  // The sweep, rather than one assertion per widget. Every interactive thing on a claim was a
  // rectangle with a border and a radius, and the point of this pass is that none of them are.
  const bordered = await page.evaluate(() =>
    [...document.querySelectorAll(".way, .option, .surface__option, .tab, .layers input")]
      .filter((node) => {
        const style = getComputedStyle(node);
        return Number.parseFloat(style.borderTopWidth) > 0;
      })
      .map((node) => node.className || node.tagName),
  );
  expect(bordered, "these still carry a CSS border").toEqual([]);
});

test("switching a layer on draws a tick rather than filling a box", async ({ page }) => {
  await page.goto("?debug=1");
  await page.getByRole("button", { name: /just let me explore/i }).click();
  await expect(page.locator(".explore")).toBeVisible();

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
  await expect.poll(offset).not.toBe(before);

  // And the checkbox is still the control: hidden natively, but the thing a pointer and a keyboard
  // both reach. The tick is ink.
  await expect(row.locator("input")).toBeFocused();
});

test("the paper turns and the world does not", async ({ page }) => {
  await ready(page);

  // Only the sheet is named, so only the sheet is captured. If the root were nameable the whole
  // page would be snapshotted -- including MapLibre's canvas, which would freeze into a still
  // image for the length of the turn and say the globe is a picture the card is printed over.
  const named = await page.evaluate(() => ({
    root: getComputedStyle(document.documentElement).viewTransitionName,
    sheet: getComputedStyle(document.querySelector(".shell__sheet")!).viewTransitionName,
  }));
  expect(named.root, "the root would be snapshotted, freezing the globe").toBe("none");
  expect(named.sheet).toBe("leaf");

  // And it turns about the spine -- the left edge, the same one `sheetEdge` tears.
  const origin = await page.evaluate(() => {
    for (const sheet of [...document.styleSheets]) {
      for (const rule of [...sheet.cssRules]) {
        if (rule.cssText.includes("view-transition-old(leaf)")) return rule.cssText;
      }
    }
    return "";
  });
  // `0px center` is how the CSSOM serialises `left center`, so match either rather than the text
  // that happens to be authored.
  expect(origin).toMatch(/transform-origin: (left|0px) center/);
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

  await observe();
  for (const key of ["marine-null", "anthropogenic-share", "coverage-bias"]) {
    await page.locator(`.tab[data-claim="${key}"]`).click();
    await expect(page.locator(".claim__title")).toBeVisible();
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

  // Not a faster turn -- no turn. `state/turn.ts` reads `--draw` and declines to start a
  // transition at all, so the new claim is in its final state on the first frame.
  await page.locator('.tab[data-claim="marine-null"]').click();
  await expect(page.locator(".claim__title")).toHaveText(/fish/i);
  expect(
    await page.evaluate(() => document.getAnimations().some((a) => a.playState === "running")),
    "something is still animating under reduced motion",
  ).toBe(false);
});

test("nothing on the page is still set in a type face that came with a glyph", async ({ page }) => {
  await ready(page);
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
  await page.goto("?debug=1");
  await page.getByRole("button", { name: /just let me explore/i }).click();
  await expect(page.locator(".explore")).toBeVisible();

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
  await page.goto("?debug=1");
  await page.getByRole("button", { name: /just let me explore/i }).click();
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
  await ready(page);

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
  await ready(page);
  // The one piece of map furniture that is a legal obligation rather than a control. It may be
  // recoloured and it may be moved; it may not be made smaller or fainter than the page's own
  // smallest prose, and it has to clear AA against whatever it is sitting on.
  const notice = page.locator(".maplibregl-ctrl-attrib").first();
  // Resolved through a probe rather than parsed off the token, because `--size-margin` is a rem
  // string and the comparison has to be in the pixels the reader actually gets.
  const smallest = await page.evaluate(() => {
    const probe = document.createElement("span");
    probe.style.fontSize = "var(--size-margin)";
    document.body.append(probe);
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
  await expect.poll(async () => (await read())[0]).not.toBe(day[0]);

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
