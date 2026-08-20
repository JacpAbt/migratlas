/**
 * The book: the spread, the tabs, the turn, and the URL.
 *
 * Its own file because it is its own subsystem and because it boots no globe -- ADR 0013's shell
 * replaces the arrival rather than sitting beside it, so none of these tests wait on WebGL. That is
 * why they are fast, and it is also why they must not be folded into `shell.spec.ts`, which
 * measures a page with a live map on it.
 *
 * The turn is asserted by driving the animation's own timeline rather than by watching it. That is
 * not a workaround: a browser that is not compositing never fires `animationend`, so a test that
 * waited for the motion would hang in exactly the environment CI runs in. Sampling the timeline
 * measures the geometry, which is what the five defects in ADR 0015 decision 5 were about.
 */

import { expect, test, type Page } from "@playwright/test";

/** Opens the book. The flag goes when the book becomes the default; so does this helper. */
async function openBook(page: Page, hash = ""): Promise<void> {
  await page.goto(`?book${hash}`);
  await expect(page.locator(".book")).toBeVisible();
}

test("the book opens as a spread of two pages with a tab per chapter", async ({ page }) => {
  await openBook(page);

  await expect(page.locator(".page--verso")).toHaveCount(1);
  await expect(page.locator(".page--recto")).toHaveCount(1);

  const { CHAPTERS } = await import("../src/lib/story");
  const tabs = await page.locator(".tab").allTextContents();
  expect(tabs.map((t) => t.trim())).toEqual(CHAPTERS.map((c) => c.tab));

  // The claims are the app's own, not prose written for the book.
  await expect(page.locator(".page--verso")).toContainText("Whatever flies over the middle");
});

test("the default is still the arrival, so the book cannot ship by accident", async ({ page }) => {
  await page.goto("");
  await expect(page.locator(".shell")).toBeVisible();
  await expect(page.locator(".book")).toHaveCount(0);
});

test("the chapter is in the URL, and a deep link opens it", async ({ page }) => {
  await openBook(page);
  await page.locator(".tab", { hasText: "Cannot see" }).click();
  await expect(page).toHaveURL(/#ch=cannot-see/);
  await expect(page.locator(".page--verso")).toContainText("What we cannot see");

  // A chapter nobody can link to is a chapter nobody cites, which is `state/route.ts`'s own reason.
  await openBook(page, "#ch=what-did-not");
  await expect(page.locator(".page--verso")).toContainText("What did not");
});

test("the turning page is a page, hinged on the crease", async ({ page }) => {
  await openBook(page);

  const measured = await page.evaluate(async () => {
    const creaseCentre = () => {
      const box = document.querySelector(".gutter__line")!.getBoundingClientRect();
      return box.left + box.width / 2;
    };
    const crease = creaseCentre();
    const outgoing = document.querySelector(".spread > .page--verso")!.textContent ?? "";

    // Forward, so the recto lifts and the verso is the page being covered.
    const tabs = [...document.querySelectorAll<HTMLButtonElement>(".tab")];
    tabs[4]!.click();
    await new Promise((resolve) => requestAnimationFrame(() => resolve(null)));

    const leaf = document.querySelector(".leaf");
    const stale = document.querySelector(".stale");
    if (!leaf || !stale) return { built: false };

    /*
      Every face holds a real `Page`, which is the whole of ADR 0015 decision 5. The mock cloned DOM
      and the clone lost the class carrying its padding, the paper its grain needed, and its place
      on the crease -- five defects with one cause.
    */
    const faces = [...leaf.querySelectorAll(".leaf__face > .page")].map((node) =>
      node.className.includes("page--recto") ? "recto" : "verso",
    );

    const edges: { pct: number; onCrease: boolean; is3d: boolean }[] = [];
    const animation = leaf.getAnimations()[0];
    if (animation) {
      animation.pause();
      const duration = Number(animation.effect?.getTiming().duration ?? 0);
      for (const pct of [0, 50, 100]) {
        animation.currentTime = (duration * pct) / 100;
        const box = leaf.getBoundingClientRect();
        edges.push({
          pct,
          // One edge stays on the hinge for the whole turn. Measured against the crease's *centre*:
          // comparing to its left edge is half a pixel out and fails for no reason.
          onCrease:
            Math.abs(box.left - crease) < 1.5 || Math.abs(box.right - crease) < 1.5,
          is3d: getComputedStyle(leaf).transform.startsWith("matrix3d"),
        });
      }
      animation.cancel();
    }

    return {
      built: true,
      faces,
      // The covered half keeps the outgoing chapter until the leaf lands on it.
      staleKeepsOutgoing: (stale.textContent ?? "").slice(0, 40) === outgoing.slice(0, 40),
      staleSide: stale.className.includes("stale--verso"),
      edges,
    };
  });

  expect(measured.built, "no leaf was built for the turn").toBe(true);
  expect(measured.faces, "a leaf face is not a Page").toEqual(["recto", "verso"]);
  expect(measured.staleSide, "the outgoing page is parked on the wrong half").toBe(true);
  expect(
    measured.staleKeepsOutgoing,
    "the covered page changed into the page about to cover it",
  ).toBe(true);
  for (const edge of measured.edges ?? []) {
    expect(edge.onCrease, `at ${edge.pct}% the leaf has left the crease`).toBe(true);
  }
  // Flattened 3D was what turned the rotation into a horizontal squash; rotateY(0) is legitimately
  // 2D, so only the sampled middle and end carry the assertion.
  expect(
    (measured.edges ?? []).filter((e) => e.pct > 0).every((e) => e.is3d),
    "the turn is not a 3D rotation -- a filter on an ancestor flattens it",
  ).toBe(true);
});

test("the turn clears itself even where the animation never fires", async ({ page }) => {
  /*
    `animationend` does not arrive in a tab that is not compositing, and without a fallback the leaf
    stays parked over half the spread for the rest of the session with no way back. Found exactly
    that way in the mock, so it is asserted rather than assumed.
  */
  await openBook(page);
  await page.locator(".tab", { hasText: "Predicted" }).click();
  await expect(page.locator(".leaf")).toHaveCount(0, { timeout: 4000 });
  await expect(page.locator(".stale")).toHaveCount(0);
  await expect(page.locator(".tab.is-on")).toHaveText("Predicted");
});

test("the plate is drawn, and its marks are named", async ({ page }) => {
  await openBook(page, "#ch=what-did-not");
  const svg = page.locator(".plate__sheet svg");
  await expect(svg).toBeVisible();

  // Named, because `ink.ts` says an anonymous `<g>` of paths is useless to select and the suite has
  // to reach for these by name rather than by "the second path inside the third svg".
  for (const name of ["ink-graticule", "ink-land", "ink-here"]) {
    await expect(page.locator(`.plate__sheet svg .${name}`)).toHaveCount(1);
  }
  // The caption cites the camera line `story.ts` already records and a test already guards.
  await expect(page.locator("figcaption")).toContainText("bottom-trawl surveys");
});

test("the plate's pen is the same weight at any window size", async ({ page }) => {
  /*
    The rule `notebook/ink.ts` states and the mock in `web/mocks/` breaks: geometry generated in a
    fixed viewBox and scaled to fit keeps its coordinates in user units while the stroke is applied
    in screen units, so the same 1.3px pen renders at 0.6px on a laptop and 1.7px on a monitor. The
    plate takes the measured box instead, so this asserts the weights do not move when the box does.
  */
  const read = async () => {
    await expect(page.locator(".plate__sheet svg")).toBeVisible();
    return page.evaluate(() => {
      const svg = document.querySelector(".plate__sheet svg")!;
      const widths = [...svg.querySelectorAll("path")].map((path) =>
        Number(path.getAttribute("stroke-width") ?? 0),
      );
      return {
        size: `${svg.getAttribute("width")}x${svg.getAttribute("height")}`,
        weights: [...new Set(widths)].sort((first, second) => first - second),
        scaled: svg.hasAttribute("viewBox"),
      };
    });
  };

  await page.setViewportSize({ width: 1600, height: 900 });
  await openBook(page, "#ch=what-did-not");
  const wide = await read();

  await page.setViewportSize({ width: 1100, height: 700 });
  await page.reload();
  await expect(page.locator(".book")).toBeVisible();
  const narrow = await read();

  expect(narrow.size, "the plate did not resize, so this proves nothing").not.toBe(wide.size);
  expect(narrow.weights, "the pen changed weight with the window").toEqual(wide.weights);
  expect(wide.scaled, "a viewBox means the drawing is being scaled after the fact").toBe(false);
  expect(narrow.scaled).toBe(false);
});

test("the plate's geometry resamples by length and projects into its box", async () => {
  const { projection, resample, TOP_LAT, BOTTOM_LAT } = await import("../src/lib/book/plate");

  // Resampling by arc length rather than by index: a ring whose vertices bunch at one end must come
  // back evenly spaced, or the whole point budget is spent on Norway's fjords.
  const lopsided: number[][] = [
    [0, 0],
    [0.1, 0],
    [0.2, 0],
    [10, 0],
    [0, 0],
  ];
  const even = resample(lopsided, 8);
  expect(even).toHaveLength(8);
  const gaps = even
    .slice(1)
    .map((point, index) => Math.hypot(point[0] - even[index]![0], point[1] - even[index]![1]));
  const spread = Math.max(...gaps) / Math.min(...gaps);
  expect(spread, `resampled gaps vary by ${spread.toFixed(1)}x`).toBeLessThan(2);

  const { x, y } = projection(1000, 500);
  expect(x(-180)).toBeCloseTo(0);
  expect(x(180)).toBeCloseTo(1000);
  expect(x(0)).toBeCloseTo(500);
  expect(y(TOP_LAT)).toBeCloseTo(0);
  expect(y(BOTTOM_LAT)).toBeCloseTo(500);
  // Clamped rather than sent to infinity, which is what Mercator does with a pole.
  expect(Number.isFinite(y(90))).toBe(true);
  expect(y(90)).toBeCloseTo(y(TOP_LAT));
});

