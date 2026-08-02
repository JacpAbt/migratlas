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
 * Contrast of an element's own text against the page background, computed in the browser from
 * resolved values.
 *
 * Reads the *page* background rather than walking up for the nearest painted ancestor, which is
 * sound here only because the notebook has one background: paper, with the grain over it. If a
 * component ever gets its own fill, this has to walk the tree instead of being trusted.
 */
async function contrast(target: Locator): Promise<number> {
  return target.evaluate((node) => {
    const channel = (value: number) =>
      value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;

    const luminance = (colour: string): number => {
      const parts = colour.match(/[\d.]+/g)?.map(Number) ?? [0, 0, 0];
      const [r = 0, g = 0, b = 0] = parts.map((value) => channel(value / 255));
      return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    };

    const ink = luminance(getComputedStyle(node).color);
    const paper = luminance(getComputedStyle(document.body).backgroundColor);
    const [high, low] = ink > paper ? [ink, paper] : [paper, ink];
    return (high + 0.05) / (low + 0.05);
  });
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

    for (const [what, selector, floor] of samples) {
      const target = page.locator(selector).first();
      await expect(target, `${what} is not on the page`).toBeVisible();
      const ratio = await contrast(target);
      expect(ratio, `${what} (${selector}) is ${ratio.toFixed(2)}:1, needs ${floor}:1`).toBeGreaterThanOrEqual(
        floor,
      );
    }
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
  expect(await contrast(addressed)).toBeGreaterThanOrEqual(AA_SMALL);

  // Never colour alone. The status word is the signal; the colour only reinforces it, because a
  // red-green distinction is not available to every reader.
  await expect(addressed).toHaveText(/addressed/);
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

test("the hand face is never used for a number or a label", async ({ page }) => {
  await ready(page);
  // The constraint is the decision, not a caveat on it: the hand face has no tabular figures, so a
  // measurement set in it stops reading as a measurement.
  const faceOf = (selector: string) =>
    page
      .locator(selector)
      .first()
      .evaluate((node) => getComputedStyle(node).fontFamily);

  expect(await faceOf(".claim__title")).toContain("Architects Daughter");
  for (const selector of [".claim__value", ".claim__banner", ".bias__domain", ".specimen p"]) {
    expect(await faceOf(selector), `${selector} is set in the hand face`).not.toContain(
      "Architects Daughter",
    );
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
      .locator(".boxed__stroke")
      .first()
      .evaluate((node) => (node as unknown as SVGPathElement).getTotalLength());
    // Longer than the perimeter would be if it were a rectangle drawn exactly: the corners
    // overshoot, which is the whole reason it reads as drawn rather than as a border.
    expect(length, `${selector} has no drawn box`).toBeGreaterThan(100);
  }

  // Pressed and chosen are a second pass of the pen, not a fill. A hand has "drawn" and "gone over
  // twice"; it does not have a hover colour.
  await expect(page.locator(".way--primary .boxed__stroke")).toHaveCount(2);
  await expect(page.locator(".way:not(.way--primary) .boxed__stroke")).toHaveCount(1);
});

test("only the chosen option is circled", async ({ page }) => {
  await ready(page);
  // Looping all three would say nothing. The unchosen ones are meant to be just words, which is
  // also why they carry no fill and no border to distinguish them.
  const options = page.locator(".surface__option");
  await expect(options).toHaveCount(3);
  await expect(page.locator(".surface .boxed__stroke")).toHaveCount(2);
  await expect(page.locator(".surface__option--on .boxed__stroke")).toHaveCount(2);
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
    row.locator(".ticked__tick").evaluate((node) => getComputedStyle(node).strokeDashoffset);

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
  // every claim, including ones it had not clicked yet, and read as a page-turn cost. Unbuffered,
  // a claim change is 52 to 90ms and the turn adds nothing measurable to it.
  await page.evaluate(() => {
    (window as unknown as { longTasks: number[] }).longTasks = [];
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        (window as unknown as { longTasks: number[] }).longTasks.push(entry.duration);
      }
    }).observe({ type: "longtask" });
  });

  for (const key of ["marine-null", "anthropogenic-share", "coverage-bias"]) {
    await page.locator(`.tab[data-claim="${key}"]`).click();
    await expect(page.locator(".claim__title")).toBeVisible();
  }

  const worst = await page.evaluate(() =>
    Math.max(0, ...(window as unknown as { longTasks: number[] }).longTasks),
  );
  expect(worst, `a ${worst.toFixed(0)}ms task during a claim change`).toBeLessThan(200);
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
