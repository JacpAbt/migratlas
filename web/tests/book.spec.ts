/**
 * The book: the spread, the tabs, the turn, and the URL.
 *
 * Its own file because it is its own subsystem and because it boots no globe -- ADR 0013's shell
 * replaces the arrival rather than sitting beside it, so none of these tests wait on WebGL. That is
 * why they are fast, and it is also why they must not be folded into `shell.spec.ts`, which
 * measures a page with a live map on it.
 *
 * Two tests that belong to the book live in `globe.spec.ts` instead: the ones that open the world
 * chapter and therefore boot a map. `playwright.config.ts` records that this machine drives two
 * WebGL contexts and no more, and files run in parallel while tests inside one file do not -- so a
 * fourth globe-booting *file* is a fourth context competing for the same GPU. Adding one here pushed
 * globe.spec.ts's layer-draw test, which takes 3.6 minutes alone, past the ten-minute hang detector.
 * Keeping the count at three files is the cheap fix; raising a timeout would have been the other
 * kind.
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
  /*
    The parameter, not its position. Once the world chapter mounts a `Clock` the hash also carries
    `d` and `t`, and `state/route.ts` says why that is right: the clock and the chapter share the
    hash and each reads the existing parameters before writing, so neither can evict the other. An
    assertion anchored to `#ch=` was demanding an ordering nothing promises.
  */
  await expect(page).toHaveURL(/[#&]ch=cannot-see/);
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

test("the book opens on an introduction, carried across the spread", async ({ page }) => {
  await openBook(page, "#ch=how-to-read");

  await expect(page.locator(".intro__kicker")).toHaveText("How to read this");
  // Quoted, because frontend prose is authored in Python and rendered verbatim -- changing this
  // sentence means editing `reports/introduction.py` and then editing this line.
  await expect(page.locator(".intro__standfirst")).toContainText(
    "a record of what this project has actually measured",
  );

  // Both pages, not one page and a blank: a book's opening spread uses both.
  const versoHeadings = await page.locator(".page--verso .intro__passage h2").count();
  const rectoHeadings = await page.locator(".page--recto .intro__passage h2").count();
  expect(versoHeadings, "the verso carries no passage").toBeGreaterThan(0);
  expect(rectoHeadings, "the facing page is blank").toBeGreaterThan(0);

  // The opening chapter has no plate, because it makes no claim.
  await expect(page.locator(".plate")).toHaveCount(0);
});

test("the introduction's figures are the ledger's, in the rendered page", async ({ page }) => {
  /*
    The sentence a visitor reads first is the one most worth holding to the data. `reports/` counts
    the ledger and this asserts the count survived the trip: the rendered text, the published
    document and `findings.json` all have to agree, so a stale rebuild shows up here rather than in
    a screenshot somebody notices months later.
  */
  await openBook(page, "#ch=how-to-read");

  const published = await page.evaluate(async () => {
    const [ledger, intro] = await Promise.all([
      fetch("findings.json").then((r) => r.json() as Promise<{ findings: { direction: string }[] }>),
      fetch("introduction.json").then(
        (r) => r.json() as Promise<{ counted: string; passages: { body: string }[] }>,
      ),
    ]);
    return {
      findings: ledger.findings.length,
      nulls: ledger.findings.filter((f) => f.direction === "null").length,
      limits: ledger.findings.filter((f) => f.direction === "limit").length,
      counted: intro.counted,
      nullsPassage: intro.passages.find((p) => p.body.includes("no change"))?.body ?? "",
    };
  });

  expect(published.counted).toContain(`${published.findings} findings`);
  expect(published.nullsPassage).toContain(`${published.nulls} of the findings report no change`);
  expect(published.nullsPassage).toContain(`${published.limits} report a limit`);

  // And the page is showing that document rather than a copy of it.
  await expect(page.locator(".intro__counted")).toHaveText(published.counted);
});

test("each chapter's facing page carries the figure its claim actually has", async ({ page }) => {
  /*
    The routing that decides this is a handful of conditions, and a condition with no test is a
    condition that flips. Two claims have a figure of their own -- the counterfactual ribbon and the
    coverage assessment -- and `claim/Evidence.svelte` explains why only two: a chart per claim
    would be decoration, since the nulls are all "indistinguishable from zero" and a flat line drawn
    three times teaches nothing the value already said. Everything else gets the drawn plate, which
    answers a different question.
  */
  await openBook(page, "#ch=why-it-changed");
  await expect(page.locator(".page--recto .figure h2")).toHaveText("The world without us");
  await expect(page.locator(".page--recto .response")).toHaveCount(1);
  await expect(page.locator(".page--recto .plate")).toHaveCount(0);

  await openBook(page, "#ch=cannot-see");
  await expect(page.locator(".page--recto .figure h2")).toHaveText(
    "Where change could be measured",
  );
  await expect(page.locator(".page--recto .plate")).toHaveCount(0);

  await openBook(page, "#ch=what-changed");
  await expect(page.locator(".page--recto .plate")).toHaveCount(1);
  await expect(page.locator(".page--recto .figure")).toHaveCount(0);
  await expect(page.locator(".page--recto .response")).toHaveCount(0);
});

test("the safeguards sit beside the claim they qualify", async ({ page }) => {
  /*
    The gap this closes: the book showed each claim's headline, number and caveat and none of its
    evidence, while the old shell showed both. `sandbox.json` carries knobs for two claims, and they
    belong on the argument page under the claim rather than on the facing page with the figures --
    `Evidence` fixes that order and the reason carries over: the safeguards say how much to trust
    the number, and only then is it worth asking what a different world would do to it.
  */
  await openBook(page, "#ch=what-changed");
  await expect(page.locator(".page--verso .knob").first()).toBeVisible();

  await openBook(page, "#ch=what-did-not");
  await expect(page.locator(".page--verso .knob").first()).toBeVisible();
});

test("a 460 KB assessment is not fetched by a chapter that does not show it", async ({ page }) => {
  /*
    `detectability.json` is about 460 KB, nearly all of it the fifty thousand grid cells the map
    wash draws, and the coverage figure wants four percentages out of it. Loading it at boot would
    be paying that on every chapter mostly for nothing, so the figure fetches it and the figure only
    exists while its own chapter is open.
  */
  const asked: string[] = [];
  page.on("request", (request) => {
    if (request.url().endsWith(".json")) asked.push(request.url().split("/").pop() ?? "");
  });

  await openBook(page, "#ch=what-changed");
  await expect(page.locator(".page--recto .plate")).toHaveCount(1);
  expect(asked, "the assessment was fetched by a chapter that does not show it").not.toContain(
    "detectability.json",
  );

  await page.locator(".tab", { hasText: "Cannot see" }).click();
  await expect(page.locator(".page--recto .figure h2")).toHaveText(
    "Where change could be measured",
  );
  expect(asked, "the chapter that shows it never asked for it").toContain("detectability.json");
});

test("turning the dial changes what the fit says", async ({ page }) => {
  /*
    The owner's founding ask, and the thing that makes this a mechanism panel rather than a figure:
    change an input and see what the response function answers. Every reading comes from
    `response.json`, so this asserts the control is wired to the published numbers rather than that
    any particular number is right.
  */
  await openBook(page, "#ch=why-it-changed");
  const knob = page.locator(".page--recto .knob").first();
  await expect(knob).toBeVisible();

  const before = await knob.locator(".knob__value").textContent();
  // The setting that is not currently chosen, so the click is a real change.
  await knob.locator(".option:not(.option--on) input[type=radio]").first().click();
  await expect(knob.locator(".knob__value")).not.toHaveText(before ?? "");

  // And it still says what it is: a reading off a fit, not a forecast.
  await expect(page.locator(".page--recto")).toContainText("not predictions");
});

test("no chapter but the world boots a map", async ({ page }) => {
  /*
    A globe is the most expensive thing this site can mount, and the plates exist so the claim
    chapters do not need one. If a map turns up on a claim chapter it means the drawn plate has been
    replaced by the thing it was drawn to avoid.
  */
  await openBook(page, "#ch=what-changed");
  await expect(page.locator(".page--recto .plate")).toHaveCount(1);
  await expect(page.locator(".maplibregl-canvas")).toHaveCount(0);
});

test("a monitor gets the spread and only the spread", async ({ page }) => {
  // The two containers are a choice, not a fallback: mounting both would run the world chapter's
  // map twice and put two of every page in the accessibility tree.
  await openBook(page);
  await expect(page.locator(".leaves")).toHaveCount(0);
});

/*
  The phone, which is a different object rather than the spread squeezed. ADR 0015's measurements --
  the crease, the tab stack, the page padding -- were chosen against a shape 375px does not have, so
  `Reader` mounts `Leaves` instead and the swipe is the page turn.

  Nothing here opens the world chapter, and that is deliberate rather than incidental: the mounted
  window reaches one leaf either side, so a test that landed on the world's verso would boot a
  MapLibre context in the one spec file whose header promises it does not. The file's reason still
  holds -- a fourth globe-booting file is a fourth context on a machine that drives two.
*/
test.describe("on a phone", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  /** Opens the book at phone width. */
  async function openLeaves(page: Page, hash = ""): Promise<void> {
    await page.goto(`?book${hash}`);
    await expect(page.locator(".leaves")).toBeVisible();
  }

  /** Where the leaves are, and what is written on them. */
  function survey(page: Page) {
    return page.evaluate(() => {
      const rail = document.querySelector<HTMLElement>(".rail")!;
      const sheets = [...rail.querySelectorAll<HTMLElement>("[data-leaf]")];
      return {
        scrollLeft: rail.scrollLeft,
        railWidth: rail.clientWidth,
        leafWidth: sheets[0]!.getBoundingClientRect().width,
        offsets: sheets.map((sheet) => sheet.offsetLeft),
        leaves: sheets.map((sheet) => `${sheet.dataset.chapter}:${sheet.dataset.side}`),
        /* Which leaves hold anything. The window is the rule that keeps a live map from running two
           chapters away, so it is asserted by what is on the paper rather than by a variable. */
        written: sheets.flatMap((sheet, index) =>
          sheet.querySelector(".page__inner")!.childElementCount > 0 ? [index] : [],
        ),
      };
    });
  }

  /**
   * Puts a leaf at the rail's left edge.
   *
   * The gesture is the browser's and not ours: what this exercises is the handler that reads where
   * the rail came to rest, which is the whole of what this component does with a swipe.
   */
  async function swipeTo(page: Page, index: number): Promise<void> {
    await page.evaluate((leaf) => {
      const rail = document.querySelector<HTMLElement>(".rail")!;
      const sheets = rail.querySelectorAll<HTMLElement>("[data-leaf]");
      rail.scrollLeft = sheets[leaf]!.offsetLeft;
    }, index);
  }

  test("a phone gets leaves it can swipe, not a spread it cannot read", async ({ page }) => {
    await openLeaves(page);

    await expect(page.locator(".book")).toHaveCount(0);

    const { CHAPTERS } = await import("../src/lib/story");
    const state = await survey(page);
    expect(state.leaves).toHaveLength(CHAPTERS.length * 2);
    expect(state.leaves[0]).toBe(`${CHAPTERS[0]!.slug}:verso`);

    // The next leaf's edge shows past this one, because otherwise nothing on screen says there is
    // another page. It is the one affordance a swipe container has.
    expect(state.leafWidth).toBeLessThan(state.railWidth);
    expect(state.railWidth - state.leafWidth).toBeGreaterThan(8);
  });

  test("a leaf got the measurements a page needs", async ({ page }) => {
    /*
      `Page` reads `--page-pad` from whatever it is mounted in, and `Book` is where that used to be
      declared -- so the first leaf outside the book resolved `padding: var(--page-pad)` to an
      invalid declaration the browser drops, and a hand-written lede ran off both edges. Nothing in
      tsc or the build can see that. This can.
    */
    await openLeaves(page, "#ch=what-changed");
    const pad = await page.locator(".leaf .page__inner").first().evaluate((node) => {
      const style = getComputedStyle(node);
      return {
        left: Number.parseFloat(style.paddingLeft),
        right: Number.parseFloat(style.paddingRight),
        bottom: Number.parseFloat(style.paddingBottom),
      };
    });
    expect(pad.left).toBeGreaterThan(12);
    expect(pad.right).toBeGreaterThan(12);

    // And the foot clears the fore-edge tab, because text under it is text nobody can read.
    const thumb = await page.locator(".thumb").evaluate((node) => node.getBoundingClientRect().height);
    expect(pad.bottom).toBeGreaterThan(thumb);
  });

  test("the swipe is the page turn, and where it stops goes in the URL", async ({ page }) => {
    await openLeaves(page);
    await expect(page.locator(".thumb__word")).toHaveText("Changed");

    await swipeTo(page, 6);
    await expect(page).toHaveURL(/[#&]ch=cannot-see/);
    await expect(page.locator(".thumb__word")).toHaveText("Cannot see");

    // Back is the reading and not the gesture: the rail follows the chapter out of the history.
    await page.goBack();
    await expect(page.locator(".thumb__word")).toHaveText("Changed");
    const state = await survey(page);
    expect(state.scrollLeft).toBe(state.offsets[2]);
  });

  test("a flick through chapters leaves one history entry per stop", async ({ page }) => {
    await openLeaves(page);
    const before = await page.evaluate(() => history.length);

    /*
      Three leaves crossed inside the settle window, with real gaps so each one is a scroll event the
      browser actually dispatches. Reported per leaf this would push three entries and make the back
      button a rewind of the gesture; the URL waits for the rail to stop instead.
    */
    await page.evaluate(async () => {
      const rail = document.querySelector<HTMLElement>(".rail")!;
      const sheets = rail.querySelectorAll<HTMLElement>("[data-leaf]");
      for (const leaf of [4, 6, 8]) {
        rail.scrollLeft = sheets[leaf]!.offsetLeft;
        await new Promise((settle) => setTimeout(settle, 40));
      }
    });

    await expect(page).toHaveURL(/[#&]ch=can-be-predicted/);
    expect(await page.evaluate(() => history.length)).toBe(before + 1);

    // And the paper kept up with the flick, which is the other cadence: mounted at once, so a fling
    // never lands on blank paper.
    expect((await survey(page)).written).toEqual([7, 8, 9]);
  });

  test("only the leaf in view and its neighbours carry anything", async ({ page }) => {
    await openLeaves(page, "#ch=what-changed");
    const state = await survey(page);

    expect(state.written).toEqual([1, 2, 3]);
    // Named rather than counted, because this is the assertion that keeps a phone from running a
    // MapLibre context five chapters away from the reader.
    expect(state.leaves.slice(12)).toEqual(["the-world:verso", "the-world:recto"]);
    expect(state.written).not.toContain(12);
    expect(state.written).not.toContain(13);
  });

  test("a deep link opens on its chapter rather than scrolling to it", async ({ page }) => {
    await openLeaves(page, "#ch=what-did-not");
    const state = await survey(page);
    expect(state.scrollLeft).toBe(state.offsets[4]);
    expect(state.written).toEqual([3, 4, 5]);
  });

  test("the last leaf can be reached, flush", async ({ page }) => {
    await openLeaves(page);
    // The peek costs the last leaf its snap point unless the rail carries a peek's worth of stop
    // after it. Off by that much and the final page can never be read.
    await page.evaluate(() => {
      const rail = document.querySelector<HTMLElement>(".rail")!;
      rail.scrollLeft = rail.scrollWidth;
    });
    const state = await survey(page);
    expect(state.scrollLeft).toBe(state.offsets[state.offsets.length - 1]);
  });

  test("the fore-edge fans out into the seven tabs, and takes you to one", async ({ page }) => {
    await openLeaves(page);
    const { CHAPTERS } = await import("../src/lib/story");

    const thumb = page.locator(".thumb");
    await expect(thumb).toHaveAttribute("aria-expanded", "false");
    await expect(page.locator(".fan")).toHaveCount(0);

    await thumb.click();
    await expect(thumb).toHaveAttribute("aria-expanded", "true");
    const tabs = page.locator(".fan__tab");
    expect((await tabs.allTextContents()).map((label) => label.trim())).toEqual(
      CHAPTERS.map((chapter) => chapter.tab),
    );

    /*
      A thumb, not a cursor. 44px is the smallest thing one hits reliably and these seven are the
      whole of this container's navigation -- the first pass came out at 38.
    */
    for (const box of await tabs.evaluateAll((nodes) =>
      nodes.map((node) => node.getBoundingClientRect().height),
    )) {
      expect(box).toBeGreaterThanOrEqual(44);
    }
    expect(
      await thumb.evaluate((node) => node.getBoundingClientRect().height),
    ).toBeGreaterThanOrEqual(44);

    await tabs.filter({ hasText: "Did not" }).click();
    await expect(page).toHaveURL(/[#&]ch=what-did-not/);
    await expect(page.locator(".fan")).toHaveCount(0);
    const state = await survey(page);
    expect(state.scrollLeft).toBe(state.offsets[4]);
  });

  test("the fan shuts without picking anything", async ({ page }) => {
    await openLeaves(page);
    await page.locator(".thumb").click();
    await expect(page.locator(".fan")).toHaveCount(1);

    await page.keyboard.press("Escape");
    await expect(page.locator(".fan")).toHaveCount(0);
    await expect(page).not.toHaveURL(/[#&]ch=/);

    // And the shade over the leaves, which is the tap most readers will use to dismiss it.
    await page.locator(".thumb").click();
    await page.locator(".shade").click();
    await expect(page.locator(".fan")).toHaveCount(0);
  });
});
