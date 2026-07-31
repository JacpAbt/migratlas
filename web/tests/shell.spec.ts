/**
 * The rebuilt shell.
 *
 * The three modes are the design, so most of what is asserted here is that they stay distinct: a
 * reader who asks for the evidence gets the evidence, and a reader who asks for the map gets the map
 * rather than the map with an argument still filtered onto it. That last one shipped broken on the
 * first attempt and looked like a rendering fault rather than a decision.
 */

import { expect, test, type Page } from "@playwright/test";

/** The camera flight is 2.2s, plus tile settling. Generous: a flaky wait is worse than a slow test. */
const FLIGHT_MS = 4000;

async function arrive(page: Page): Promise<void> {
  // Relative, and with ?debug so the map is readable. A leading slash would replace the whole
  // path of baseURL and land on the origin root rather than the project subpath -- the trap the
  // globe suite already documents.
  await page.goto("shell.html?debug=1");
  await expect(page.locator(".arrival__card")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  await expect(page.locator(".globe canvas")).toBeVisible();
}

/** Camera state, read from MapLibre rather than inferred from pixels. */
async function camera(page: Page): Promise<{ lon: number; lat: number; zoom: number }> {
  return page.evaluate(() => {
    const globe = (window as unknown as { migratlas?: { map?: unknown } }).migratlas?.map as
      | { getCenter: () => { lng: number; lat: number }; getZoom: () => number }
      | undefined;
    if (!globe) throw new Error("no map on window; the shell must expose one for this test");
    const centre = globe.getCenter();
    return { lon: centre.lng, lat: centre.lat, zoom: globe.getZoom() };
  });
}

test("a visitor lands on a claim, with its number and its caveat", async ({ page }) => {
  await arrive(page);

  // The number in full, on the first screen, with its interval. An arrival that said "something is
  // changing" and made you click for the figure would invert what this project is for.
  await expect(page.locator(".arrival__value")).toHaveText(/[−-]?\d+\.\d+/);
  await expect(page.locator(".arrival__scope")).not.toBeEmpty();
  await expect(page.locator(".arrival__caveat")).not.toBeEmpty();

  // Both ways out, offered together rather than one after the other.
  await expect(page.getByRole("button", { name: /show me how you know/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /just let me explore/i })).toBeVisible();

  // And the globe is live behind it, already pointed at the claim's own evidence -- which is the
  // only reason to put a card on a globe rather than on a picture of one.
  const at = await camera(page);
  expect(Math.abs(at.lat - 42), `arrived at ${at.lat.toFixed(1)}N`).toBeLessThan(12);
  expect(at.zoom).toBeGreaterThan(2);
});

test("asking how we know opens the claim with its audit beside it", async ({ page }) => {
  await arrive(page);
  await page.getByRole("button", { name: /show me how you know/i }).click();

  await expect(page.locator(".shell__sheet")).toBeVisible();
  await expect(page.locator(".claim__title")).toBeVisible();
  await expect(page.locator(".margin")).toBeVisible();
  await expect(page.locator(".bias__domain").first()).toBeVisible();
  await expect(page.locator(".arrival__card")).toHaveCount(0);
});

test("the sheet leaves the globe it is read against visible", async ({ page }) => {
  await arrive(page);
  await page.getByRole("button", { name: /show me how you know/i }).click();

  // The regression this replaces: at 56rem the sheet covered the sphere on a laptop, which makes
  // both the camera flight and the caption explaining it pointless.
  const sheet = await page.locator(".shell__sheet").boundingBox();
  const width = page.viewportSize()?.width ?? 0;
  expect(sheet).toBeTruthy();
  expect(
    sheet!.width / width,
    `the sheet takes ${((sheet!.width / width) * 100).toFixed(0)}% of the viewport`,
  ).toBeLessThan(0.75);

  // And it says why the camera is where it is. A globe that flies somewhere without explaining
  // itself is a slideshow.
  await expect(page.locator(".shell__because")).not.toBeEmpty();
});

test("choosing another claim flies the camera and swaps the evidence", async ({ page }) => {
  await arrive(page);
  await page.getByRole("button", { name: /show me how you know/i }).click();
  const before = await camera(page);

  await page.locator(".tab", { hasText: /poleward/i }).click();
  await expect(page.locator(".claim__title")).toHaveText(/poleward/i);
  await page.waitForTimeout(FLIGHT_MS);

  const after = await camera(page);
  const moved = Math.abs(after.lon - before.lon) + Math.abs(after.lat - before.lat);
  expect(moved, "the camera did not move between two claims on different continents").toBeGreaterThan(
    10,
  );

  // The layers follow the claim, not the other way round: this is what makes the globe an index to
  // the arguments rather than a layer switcher with prose attached.
  const visible = await page.evaluate(() => {
    const map = (window as unknown as { migratlas?: { map?: unknown } }).migratlas?.map as
      | { getStyle: () => { layers: { id: string; layout?: { visibility?: string } }[] } }
      | undefined;
    return (map?.getStyle().layers ?? [])
      .filter((layer) => /^(series|surface)-/.test(layer.id))
      .filter((layer) => layer.layout?.visibility !== "none")
      .map((layer) => layer.id);
  });
  expect(visible.join(","), "the aerial series is still drawn on a marine claim").not.toContain(
    "aerial-passage",
  );
});

test("just the map means the whole map, not the last claim's filter", async ({ page }) => {
  await arrive(page);
  await page.getByRole("button", { name: /show me how you know/i }).click();
  await page.locator(".tab", { hasText: /poleward/i }).click();
  await page.waitForTimeout(FLIGHT_MS);

  await page.getByRole("button", { name: /just the map/i }).click();
  await page.waitForTimeout(FLIGHT_MS);

  // No claim in the way.
  await expect(page.locator(".shell__sheet")).toHaveCount(0);

  // The regression. Explore mode inherited the last claim's layer subset, so a reader who asked for
  // the map got one claim's evidence still filtered onto it -- which reads as a bug, not a choice.
  const visible = await page.evaluate(() => {
    const map = (window as unknown as { migratlas?: { map?: unknown } }).migratlas?.map as
      | { getStyle: () => { layers: { id: string; layout?: { visibility?: string } }[] } }
      | undefined;
    return (map?.getStyle().layers ?? [])
      .filter((layer) => /^(series|surface)-/.test(layer.id))
      .filter((layer) => layer.layout?.visibility !== "none").length;
  });
  expect(visible, "explore mode is still hiding layers").toBeGreaterThanOrEqual(3);

  // And pulled back: the reader asked to stop being led somewhere.
  expect((await camera(page)).zoom).toBeLessThan(2);
});

test("the index names every claim and says what each one found", async ({ page }) => {
  await arrive(page);
  await page.getByRole("button", { name: /just let me explore/i }).click();

  const tabs = page.locator(".tab");
  // One per claim, plus the way back to the bare globe.
  await expect(tabs).toHaveCount(6);

  // Whether each found a change, a null or a limit, in words, before anyone clicks. An index of
  // only the positives would be lying by selection.
  const kinds = await page.locator(".tab__what").allTextContents();
  expect(kinds.join(" ")).toContain("change detected");
  expect(kinds.join(" ")).toContain("no change detected");
  expect(kinds.join(" ")).toContain("limit of this work");
});

test("every published claim has a view, and every view names a real layer", async ({ page }) => {
  await arrive(page);
  const problems = await page.evaluate(async () => {
    const [ledger, manifest] = await Promise.all([
      fetch("findings.json").then((r) => r.json() as Promise<{ findings: { key: string }[] }>),
      fetch("layers/manifest.json").then((r) => r.json() as Promise<{ name: string }[]>),
    ]);
    return { keys: ledger.findings.map((f) => f.key), names: manifest.map((m) => m.name) };
  });

  // Imported rather than re-listed, so the assertion is about the module the app actually uses.
  const { VIEWS, ARRIVAL_KEY } = await import("../src/lib/story");

  for (const key of problems.keys) {
    expect(VIEWS[key], `no view recorded for the claim "${key}"`).toBeTruthy();
  }
  // The guard that caught two wrong layer names, which show up as a claim whose evidence never
  // appears -- indistinguishable from a claim that has no evidence.
  for (const [key, view] of Object.entries(VIEWS)) {
    for (const layer of view.layers) {
      expect(problems.names, `${key} names a layer "${layer}" that is not in the manifest`).toContain(
        layer,
      );
    }
    expect(view.because, `${key} does not say why the camera is there`).toBeTruthy();
  }
  expect(problems.keys, "the arrival claim is not in the ledger").toContain(ARRIVAL_KEY);
});

/**
 * Small screens.
 *
 * "At least decent" is the bar, and these are the four ways it was not: a claim column two words
 * wide on a tablet, zoom buttons printed over the claim's own text, a licence notice printed across
 * it, and the arrival's measurement broken so that "decade" sat alone on a line.
 */
for (const [device, width, height] of [
  ["phone", 390, 844],
  ["tablet", 768, 1024],
] as const) {
  test(`the shell is readable on a ${device}`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await arrive(page);

    // Nothing runs off the side, in any mode. The one failure a visitor cannot work around.
    const overflow = () =>
      page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
    expect(await overflow(), `${await overflow()}px of horizontal overflow on arrival`).toBeLessThanOrEqual(1);

    // The arrival's measurement stays on one line. Broken after "days", it read as two facts
    // rather than as one number with an interval.
    const value = page.locator(".arrival__value");
    const lines = await value.evaluate((node) => {
      const style = getComputedStyle(node);
      return node.getBoundingClientRect().height / Number.parseFloat(style.lineHeight || "0");
    });
    expect(lines, "the arrival value wraps").toBeLessThan(1.8);

    // Both ways out reachable without scrolling past the fold.
    for (const name of [/show me how you know/i, /just let me explore/i]) {
      await expect(page.getByRole("button", { name })).toBeInViewport();
    }

    await page.getByRole("button", { name: /show me how you know/i }).click();
    expect(await overflow()).toBeLessThanOrEqual(1);

    // The claim card responds to the sheet it is in, not to the viewport. On a 768px tablet the
    // sheet is narrower than any sensible media-query breakpoint, and the two-column layout
    // squeezed the claim body to 230px and wrapped the hand heading over nine lines.
    const claim = page.locator(".claim").first();
    const body = await claim.locator(".claim__body").boundingBox();
    expect(body, "no claim body").toBeTruthy();
    expect(
      body!.width,
      `the claim body is ${Math.round(body!.width)}px wide, which is a column of two-word lines`,
    ).toBeGreaterThan(300);

    // The audit is still there, still not behind a control -- only its position changed.
    await expect(claim.locator(".margin")).toBeVisible();
    await expect(claim.locator(".bias__finding").first()).toBeVisible();

    // And nothing the map owns is printed over the claim: the zoom buttons landed on the text, and
    // the attribution -- a licence notice -- printed across the bottom of it.
    const collisions = await page.evaluate(() => {
      const sheet = document.querySelector(".shell__sheet")?.getBoundingClientRect();
      if (!sheet) return ["no sheet"];
      const hits: string[] = [];
      for (const selector of [".maplibregl-ctrl-attrib", ".maplibregl-ctrl-group", ".maplibregl-ctrl-scale"]) {
        for (const node of document.querySelectorAll(selector)) {
          const box = node.getBoundingClientRect();
          if (box.width === 0 || box.height === 0) continue;
          const clear =
            box.right < sheet.left ||
            box.left > sheet.right ||
            box.bottom < sheet.top ||
            box.top > sheet.bottom;
          if (!clear) hits.push(selector);
        }
      }
      return hits;
    });
    expect(collisions, `${collisions.join(", ")} overlaps the reading sheet`).toEqual([]);
  });
}
