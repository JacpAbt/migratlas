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
      // Stamped directly. The shell has no surface switch yet -- ADR 0007 scopes night as a week of
      // work -- but the token set is written for both, and an unrendered palette is a guess. This is
      // exactly what a switch will do when there is one.
      await page.evaluate(() => document.documentElement.setAttribute("data-surface", "night"));
      await expect(page.locator(":root")).toHaveAttribute("data-surface", "night");
    }

    // One per token that carries text, chosen as the smallest instance of each: if the 0.66rem
    // label passes, the 1.35rem value using the same token does too.
    const samples: [string, string, number][] = [
      ["the claim title", ".claim__title", AA_SMALL],
      ["the measurement", ".claim__value", AA_SMALL],
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
  await ready(page);
  await eachClaim(page, async () => {
    const claim = page.locator(".claim").first();

    // Visible, and with no ancestor that could be closed. `findings.py` refuses to publish a claim
    // with no caveat; a `<details>` around the audit would satisfy that and break its point.
    await expect(claim.locator(".margin")).toBeVisible();
    await expect(claim.locator(".bias__domain").first()).toBeVisible();
    await expect(claim.locator(".margin details, .margin [hidden]")).toHaveCount(0);
    await expect(claim.locator(".claim__caveat")).not.toBeEmpty();
  });

  // And at least one domain reading "open" across the set: every domain "addressed" would mean
  // either that nothing is unresolved -- false, the 2012 step is -- or that the audit is written to
  // reassure rather than to inform.
  let open = 0;
  await eachClaim(page, async () => {
    open += await page.locator(".bias__status--open").count();
  });
  expect(open, "nothing is marked open, which would mean the audit is decorative").toBeGreaterThan(0);
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
