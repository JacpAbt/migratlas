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

import { readFileSync } from "node:fs";

import { expect, test, type Page } from "@playwright/test";

import type { Leaf, Panel, Spread } from "../src/lib/book/pages";

/**
 * The book's own pagination, computed in the test from the same module and the same documents.
 *
 * Hard-coded page numbers would have to be re-typed every time a claim gains a knob, and the first
 * one that was missed would pass while pointing at the wrong page. This asks `pages.ts` instead.
 */
async function layout(realm = ""): Promise<readonly Spread[]> {
  const { spreadsOf } = await import("../src/lib/book/pages");
  const { CHAPTERS: chapters } = await import("../src/lib/story");
  const read = (name: string) => JSON.parse(readFileSync(`public/${name}`, "utf8"));
  return spreadsOf(
    {
      findings: read("findings.json").findings,
      introduction: read("introduction.json"),
      safeguards: read("sandbox.json"),
      dial: read("response.json"),
    },
    chapters,
    realm,
  );
}

/**
 * The phone's arrangement of the same pages, which is not this list doubled.
 *
 * It was, and these tests indexed leaves as `spread * 2` on that basis. The spread pads each
 * argument to an even page count so a leaf ending one never faces a leaf starting the next; a phone
 * shows one page at a time and has nothing to pad against, so its list is shorter by exactly that
 * padding and the doubling is off by however much of it came before.
 */
async function leafLayout(realm = ""): Promise<readonly Leaf[]> {
  const { leavesOf } = await import("../src/lib/book/pages");
  const { CHAPTERS: chapters } = await import("../src/lib/story");
  const read = (name: string) => JSON.parse(readFileSync(`public/${name}`, "utf8"));
  return leavesOf(
    {
      findings: read("findings.json").findings,
      introduction: read("introduction.json"),
      safeguards: read("sandbox.json"),
      dial: read("response.json"),
    },
    chapters,
    realm,
  );
}

/** The first leaf of a chapter, which is where a tab or a deep link lands on a phone. */
function leafOpening(leaves: readonly Leaf[], slug: string): number {
  const at = leaves.findIndex((leaf) => leaf.chapter.slug === slug);
  if (at < 0) throw new Error(`no leaf in ${slug}`);
  return at;
}

/** The address of the first spread carrying a panel that matches. */
function addressOf(spreads: readonly Spread[], match: (panel: Panel) => boolean): string {
  const spread = spreads.find((one) => match(one.verso) || match(one.recto));
  if (!spread) throw new Error("no spread carries that panel");
  return `#ch=${spread.chapter.slug}&p=${spread.at}`;
}

/**
 * The spread carrying a panel, *and which side of it the panel is on*.
 *
 * Which side a panel lands on is `pages.ts`'s business and it moves: inserting the plain-method page
 * flipped the parity of every claim, so the figure went from the recto of the opening spread to the
 * verso of the next one. Seven tests here addressed a page as "the chapter's first spread, on the
 * right" and all seven failed at once -- correctly, because that was never the fact they were about.
 * Ask for the panel and be told where it is.
 */
function pageAt(
  spreads: readonly Spread[],
  match: (panel: Panel) => boolean,
): { at: string; side: "verso" | "recto" } {
  for (const spread of spreads) {
    for (const side of ["verso", "recto"] as const) {
      if (match(spread[side])) return { at: `#ch=${spread.chapter.slug}&p=${spread.at}`, side };
    }
  }
  throw new Error("no spread carries that panel");
}

/** Opens the book, which is now simply the site. */
async function openBook(page: Page, hash = ""): Promise<void> {
  await page.goto(hash || "?");
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

test("the book is the front door, and the shell is the one behind a flag now", async ({ page }) => {
  /*
    Inverted on 2026-08-21. This test used to assert the opposite -- that the default was the
    arrival, so an unfinished book could not ship by accident -- and it earned its place then. The
    book now carries the introduction, the plates, the evidence, the world and a container of its
    own for phones, so the guard it provided is spent and the assertion is the other way round.
  */
  await page.goto("");
  await expect(page.locator(".book")).toBeVisible();
  await expect(page.locator(".shell")).toHaveCount(0);

  // And the settings the shell used to carry came with it, rather than being lost in the move.
  await expect(page.locator(".settings .surface")).toBeVisible();
  await expect(page.locator(".settings .type")).toBeVisible();
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
  /*
    The spread's own left page, not any page. Mid-turn the leaf and the parked page are `Page`
    instances too -- which is ADR 0015 decision 5 working as designed -- so a bare `.page--verso`
    matches three elements and the assertion is ambiguous rather than false.
  */
  await expect(page.locator(".spread > .page--verso")).toContainText("What we cannot see");

  // A chapter nobody can link to is a chapter nobody cites, which is `state/route.ts`'s own reason.
  await openBook(page, "#ch=what-did-not");
  await expect(page.locator(".spread > .page--verso")).toContainText("What did not");
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
  // The plate's own page, by kind: it is no longer the leaf facing the claim it belongs to.
  const plate = pageAt(
    await layout(),
    (panel) => panel.kind === "figure" && panel.key === "marine-null",
  );
  await openBook(page, plate.at);
  const svg = page.locator(".plate__sheet svg");
  await expect(svg).toBeVisible();

  // Named, because `ink.ts` says an anonymous `<g>` of paths is useless to select and the suite has
  // to reach for these by name rather than by "the second path inside the third svg".
  const marks = ["ink-graticule", "ink-land", "ink-here"];
  for (const name of marks) {
    await expect(page.locator(`.plate__sheet svg .${name}`)).toHaveCount(1);
  }
  // The caption cites the camera line `story.ts` already records and a test already guards.
  await expect(page.locator("figcaption")).toContainText("bottom-trawl surveys");

  /*
    And every mark is in the key, which is the assertion the key exists for.

    The caption used to describe the *layer* rather than the sheet -- "ringed where the count fell,
    solid where it rose" printed under a drawing with no cells on it -- so a reader was hunting for
    marks that were never there. The fix is only a fix while the two lists stay the same length: a
    mark with no entry is a mark nobody can read, and an entry with no mark is the same lie again in
    a new place.
  */
  await expect(page.locator(".plate__key li")).toHaveCount(marks.length);
  // The measurement is not on this sheet, and the plate says where it is instead of implying it is.
  await expect(page.locator(".plate__elsewhere")).toContainText("world chapter");
});

test("the plate's pen is the same weight at any window size", async ({ page }) => {
  /*
    The rule `notebook/ink.ts` states and the deleted mock broke: geometry generated in a
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

  const plate = pageAt(
    await layout(),
    (panel) => panel.kind === "figure" && panel.key === "marine-null",
  );

  await page.setViewportSize({ width: 1600, height: 900 });
  await openBook(page, plate.at);
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

  const { height, x, y } = projection(1000);
  expect(x(-180)).toBeCloseTo(0);
  expect(x(180)).toBeCloseTo(1000);
  expect(x(0)).toBeCloseTo(500);
  expect(y(TOP_LAT)).toBeCloseTo(0);
  expect(y(BOTTOM_LAT)).toBeCloseTo(height);
  // Clamped rather than sent to infinity, which is what Mercator does with a pole.
  expect(Number.isFinite(y(90))).toBe(true);
  expect(y(90)).toBeCloseTo(y(TOP_LAT));
});

test("the plate is conformal: one scale in both axes, at any size", async () => {
  const { PLATE_RATIO, projection, TOP_LAT } = await import("../src/lib/book/plate");

  /*
    The assertion that would have caught the stretch, and it is a property rather than a number: a
    degree of longitude at the equator and a degree of latitude at the equator must come out the same
    length in pixels. They did not -- the sheet was `flex: 1`, so the map got the page column's
    leftover height and every plate was 1.9 to 2.1 times too tall.
  */
  for (const width of [320, 531, 1000, 1783]) {
    const { height, x, y } = projection(width);
    expect(height).toBeCloseTo(width / PLATE_RATIO);
    const perDegreeLon = x(1) - x(0);
    const perDegreeLat = y(0) - y(1);
    expect(
      perDegreeLat / perDegreeLon,
      `at width ${width} a degree of latitude is ${(perDegreeLat / perDegreeLon).toFixed(3)} of a degree of longitude`,
    ).toBeCloseTo(1, 2);

    // And the box is landscape, which is the shape 80°N to 58°S actually is.
    expect(height).toBeLessThan(width);
  }

  // The ratio itself, so a change to the latitude band has to be a deliberate one.
  expect(PLATE_RATIO).toBeCloseTo(1.705, 3);
  expect(TOP_LAT).toBe(80);
});

test("the book opens on an introduction, carried across the spread", async ({ page }) => {
  await openBook(page, "#ch=how-to-read");

  await expect(page.locator(".intro__kicker")).toHaveText("What this is");
  // Quoted, because frontend prose is authored in Python and rendered verbatim -- changing this
  // sentence means editing `reports/introduction.py` and then editing this line.
  await expect(page.locator(".intro__standfirst")).toContainText(
    "a record of what this project has actually measured",
  );

  /*
    The opening chapter answers what, why and how before it answers anything else, and it does so
    with no result in it.

    Quoted for the reason above, and asserted at all because the ordering is the decision: the four
    passages that were here first are about how to read a claim, which is a question a reader only
    has once they have been handed one. What is being studied and why it is worth measuring come
    before that, and a future edit that files them behind the epistemics should fail here.
  */
  const headings = await page.locator(".page--recto .intro__passage h2").allInnerTexts();
  expect(headings.slice(0, 2)).toEqual(["What we are studying", "Why it is worth measuring"]);

  /*
    The opening leaf is the standfirst and the counted line, and the passages start on the facing
    page. That is not the arrangement it had before pagination, and it is the arrangement a book
    has: a chapter opening is not a page of body text with a title on it.
  */
  await expect(page.locator(".page--verso .intro__passage")).toHaveCount(0);
  expect(
    await page.locator(".page--recto .intro__passage h2").count(),
    "the facing page carries no passage",
  ).toBeGreaterThan(0);

  // And every passage is on some page: the chapter runs across as many spreads as it needs, and a
  // fifth passage added upstream must not fall off the end.
  const doc = JSON.parse(readFileSync("public/introduction.json", "utf8")) as {
    passages: { heading: string }[];
  };
  const carried = (await layout())
    .filter((one) => one.chapter.slug === "how-to-read")
    .flatMap((one) => [one.verso, one.recto])
    .filter((panel) => panel.kind === "intro");
  const covered = new Set(
    carried.flatMap((panel) =>
      Array.from({ length: panel.to - panel.from }, (_, step) => panel.from + step),
    ),
  );
  for (const [index, passage] of doc.passages.entries()) {
    expect(covered.has(index), `"${passage.heading}" is on no page`).toBe(true);
  }

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

test("each claim's figure page carries the figure that claim actually has", async ({ page }) => {
  /*
    The routing that decides this is a handful of conditions, and a condition with no test is a
    condition that flips. Two claims have a figure of their own -- the counterfactual ribbon and the
    coverage assessment -- and `claim/Evidence.svelte` explains why only two: a chart per claim
    would be decoration, since the nulls are all "indistinguishable from zero" and a flat line drawn
    three times teaches nothing the value already said. Everything else gets the drawn plate, which
    answers a different question.
  */
  const spreads = await layout();
  const figureOf = (key: string) =>
    pageAt(spreads, (panel) => panel.kind === "figure" && panel.key === key);

  for (const [key, heading] of [
    ["anthropogenic-share", "The world without us"],
    ["coverage-bias", "Where change could be measured"],
  ] as const) {
    const { at, side } = figureOf(key);
    await openBook(page, at);
    await expect(page.locator(`.page--${side} .figure h2`)).toHaveText(heading);
    await expect(page.locator(`.page--${side} .plate`)).toHaveCount(0);
    // One page, one thing: the dial is several leaves on, not stacked under the chart.
    await expect(page.locator(`.page--${side} .response`)).toHaveCount(0);
  }

  const drawn = figureOf("autumn-advance");
  await openBook(page, drawn.at);
  await expect(page.locator(`.page--${drawn.side} .plate`)).toHaveCount(1);
  await expect(page.locator(`.page--${drawn.side} .figure`)).toHaveCount(0);
  await expect(page.locator(`.page--${drawn.side} .response`)).toHaveCount(0);
});

test("a figure that needs more than a page gets more, and its document agrees", async ({
  page,
}) => {
  /*
    `figures.ts` declares the page count because the ribbon's own document is fetched lazily by the
    component that draws it -- so the pagination cannot count its charts, and a count that arrives
    late is a folio that renumbers itself under the reader. The declaration is therefore a claim
    about a file, and this is what keeps it true: a third reconstruction added upstream fails here
    rather than falling off the end of the book.
  */
  const { RIBBON_CHARTS } = await import("../src/lib/book/figures");
  const doc = JSON.parse(readFileSync("public/counterfactual.json", "utf8")) as { ribbons: unknown[] };
  expect(doc.ribbons).toHaveLength(RIBBON_CHARTS);

  const pages = (await layout())
    .flatMap((one) => [one.verso, one.recto])
    .filter((panel) => panel.kind === "figure" && panel.key === "anthropogenic-share");
  expect(pages, "the ribbon's declared pages are not all allocated").toHaveLength(4);

  // And a chart page draws one chart, which is what made them fit: two came to 1,362px on an 826px
  // page.
  const first = pageAt(
    await layout(),
    (panel) => panel.kind === "figure" && panel.key === "anthropogenic-share",
  );
  await openBook(page, first.at);
  await expect(page.locator(`.page--${first.side} .pair__set li`)).toHaveCount(1);
});

test("the safeguards sit beside the claim they qualify", async ({ page }) => {
  /*
    The gap this closes: the book showed each claim's headline, number and caveat and none of its
    evidence, while the old shell showed both. `sandbox.json` carries knobs for two claims, and they
    belong on the argument page under the claim rather than on the facing page with the figures --
    `Evidence` fixes that order and the reason carries over: the safeguards say how much to trust
    the number, and only then is it worth asking what a different world would do to it.
  */
  const spreads = await layout();
  for (const key of ["autumn-advance", "marine-null"]) {
    const address = addressOf(
      spreads,
      (panel) => panel.kind === "panel" && panel.doc === "safeguards" && panel.key === key,
    );
    await openBook(page, address);
    await expect(page.locator(".knob").first(), `no knob at ${address}`).toBeVisible();
    /*
      One to a *page*, which is what three of them at about 435px each on an 826px page forced.

      Counted per leaf rather than per spread. Per spread held only while the knobs happened to land
      against something else: the plain-method page flipped the parity and two knobs now face each
      other, which is two pages carrying one knob each and exactly what the rule says.
    */
    for (const side of ["verso", "recto"] as const) {
      const knobs = await page.locator(`.spread > .page--${side} .knob`).count();
      expect(knobs, `${side} at ${address} carries ${knobs} knobs`).toBeLessThanOrEqual(1);
    }
  }
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

  const spreads = await layout();
  const drawn = pageAt(
    spreads,
    (panel) => panel.kind === "figure" && panel.key === "autumn-advance",
  );
  await openBook(page, drawn.at);
  await expect(page.locator(`.page--${drawn.side} .plate`)).toHaveCount(1);
  expect(asked, "the assessment was fetched by a chapter that does not show it").not.toContain(
    "detectability.json",
  );

  /*
    Then its own page rather than its own chapter.

    Opening the chapter used to mount the figure, because the figure was the leaf facing the claim.
    It is two leaves in now, so a chapter click alone proves nothing either way -- and the rule being
    tested was always about the page: the figure fetches this file, and the figure exists only while
    it is on screen.
  */
  const assessment = pageAt(
    spreads,
    (panel) => panel.kind === "figure" && panel.key === "coverage-bias",
  );
  await openBook(page, assessment.at);
  await expect(page.locator(`.page--${assessment.side} .figure h2`)).toHaveText(
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
  const spreads = await layout();
  await openBook(
    page,
    addressOf(spreads, (panel) => panel.kind === "panel" && panel.doc === "dial"),
  );
  const knob = page.locator(".knob").first();
  await expect(knob).toBeVisible();

  const before = await knob.locator(".knob__value").textContent();
  // The setting that is not currently chosen, so the click is a real change.
  await knob.locator(".option:not(.option--on) input[type=radio]").first().click();
  await expect(knob.locator(".knob__value")).not.toHaveText(before ?? "");

  // And it still says what it is: a reading off a fit, not a forecast.
  await expect(page.locator(".spread")).toContainText("not predictions");
});

test("no chapter but the world boots a map", async ({ page }) => {
  /*
    A globe is the most expensive thing this site can mount, and the plates exist so the claim
    chapters do not need one. If a map turns up on a claim chapter it means the drawn plate has been
    replaced by the thing it was drawn to avoid.
  */
  const drawn = pageAt(
    await layout(),
    (panel) => panel.kind === "figure" && panel.key === "autumn-advance",
  );
  await openBook(page, drawn.at);
  await expect(page.locator(`.page--${drawn.side} .plate`)).toHaveCount(1);
  await expect(page.locator(".maplibregl-canvas")).toHaveCount(0);
});

test("a claim reads what, then how, then the picture, then the numbers", async ({ page }) => {
  /*
    The owner's reading order, asserted as an order rather than as four pages that exist.

    Every one of these registers was already published; what was missing was the second, and what is
    easy to lose again is the sequence. A reader who meets the interval before the procedure has been
    handed a number to trust, which is the failure the plain registers exist against -- so this walks
    the panels of one claim in the order `pages.ts` emits them and names each one.
  */
  const claim = (await layout())
    .filter((spread) => spread.chapter.slug === "what-changed")
    .flatMap((spread) => [spread.verso, spread.recto])
    .filter((panel) => "key" in panel && panel.key === "autumn-advance")
    .map((panel) => panel.kind);

  expect(claim.slice(0, 4)).toEqual(["finding", "how", "figure", "record"]);

  // And the page renders the sentence the ledger holds, not a summary of it written in Svelte.
  const ledger = JSON.parse(readFileSync("public/findings.json", "utf8")) as {
    findings: { key: string; plain_how: string }[];
  };
  const how = ledger.findings.find((one) => one.key === "autumn-advance")!.plain_how;
  await openBook(page, addressOf(await layout(), (panel) => panel.kind === "how"));
  await expect(page.locator(".how__lead")).toHaveText(how);
  // The register above it, because a page of prose with no label is a page a reader has to guess at.
  await expect(page.locator(".how__kicker")).toHaveText("How we found it");
});

/*
  The realm filter, which is the book's second level of index tabs.

  Model first and browser after, because the two things most worth pinning are facts about the
  pagination rather than about the DOM: which claims a realm holds, and what a chapter does when the
  filter empties it.
*/
test("a cross-realm limit is in every realm, not in none of them", async () => {
  /*
    The one reading of `realm: "all"` that is false.

    Two findings carry it -- the coverage bias and the failure to transfer -- and both are limits on
    this whole project rather than on one realm. Filtered to the sea, a book that dropped them would
    be telling a reader that nothing limits what is known about the sea, which is the opposite of
    what those two findings say. So they appear under every tab, and this is the assertion that stops
    a future `finding.realm === realm` from looking correct.
  */
  const keys = async (realm: string) =>
    (await layout(realm))
      .flatMap((spread) => [spread.verso, spread.recto])
      .flatMap((panel) => (panel.kind === "finding" ? [panel.key] : []));

  for (const realm of ["aerial", "marine", "terrestrial"]) {
    expect(await keys(realm), `${realm} lost a cross-realm limit`).toEqual(
      expect.arrayContaining(["coverage-bias", "transfer-fails"]),
    );
  }

  // And the filter does filter: the marine book has the marine null and neither aerial claim.
  const sea = await keys("marine");
  expect(sea).toContain("marine-null");
  expect(sea).not.toContain("autumn-advance");
  expect(sea).not.toContain("atlas-no-net-change");
});

test("a chapter the filter empties says which silence it is", async () => {
  /*
    Two ways for a chapter to come out empty and they must not print the same page. Every chapter in
    the ledger has claims, so under a filter the only silence available is "measured elsewhere" --
    which is a fact about instruments and is worth a page of words. Blank paper is reserved for the
    other case, where the ledger does not hold what the chapter names and there is nothing true to
    say.
  */
  const empty = (await layout("marine")).find(
    (spread) => spread.chapter.slug === "what-changed",
  );
  expect(empty?.verso).toEqual({ kind: "absent", realm: "marine", chapter: "What changed" });
  expect(empty?.recto).toEqual({ kind: "blank" });

  // Unfiltered, that chapter is five spreads of claims and no absence anywhere in the book.
  const all = await layout();
  expect(all.filter((spread) => spread.chapter.slug === "what-changed").length).toBeGreaterThan(1);
  expect(all.flatMap((s) => [s.verso, s.recto]).filter((p) => p.kind === "absent")).toEqual([]);
});

test("turning a realm tab keeps the chapter, writes the URL, and back comes back", async ({
  page,
}) => {
  await openBook(page, "#ch=what-changed");
  await expect(page.locator(".page--verso .claim")).toHaveCount(1);

  await page.locator(".realms").getByRole("button", { name: "Sea", exact: true }).click();

  /*
    The chapter survives and the position does not, which is the choice `Reader.filter` records: a
    reader turning "Sea" is asking about the chapter they are in, and an offset carried across a
    filter is an offset into a book that no longer has those pages.
  */
  await expect(page.locator(".absent")).toBeVisible();
  await expect(page).toHaveURL(/ch=what-changed/);
  await expect(page).toHaveURL(/r=marine/);

  // Written with pushState, so the filter is a place a reader can leave and return to.
  await page.goBack();
  await expect(page.locator(".page--verso .claim")).toHaveCount(1);
  await expect(page).not.toHaveURL(/r=marine/);
});

test("the realm in the URL is the realm on the tab, and an unknown one is all of them", async ({
  page,
}) => {
  await openBook(page, "#ch=what-did-not&r=terrestrial");
  await expect(page.locator(".realms .is-on")).toHaveText("Land");
  // The claim on the page is the one that realm holds, so the filter applied before the first paint
  // rather than after it -- which is why `Reader` reads the parameter synchronously.
  await expect(page.locator(".page--verso .claim")).toHaveCount(1);
  await expect(page.locator(".page--verso")).toContainText("Southern African");

  await openBook(page, "#ch=what-did-not&r=nonsense");
  await expect(page.locator(".realms .is-on")).toHaveText("All");
});

for (const [width, height] of [
  [1600, 900],
  [1280, 800],
] as const) {
  test(`the page a filter empties fits its leaf at ${width}x${height}`, async ({ page }) => {
    /*
      The one page shape the full walk below cannot reach.

      Every other page in a filtered book is a page of the unfiltered one -- the filter drops claims,
      it does not reflow them -- so the corner-walk already measures them. The absent leaf exists
      only under a filter, and four realms times two widths times a forty-second walk to measure one
      new panel is the kind of coverage that gets deleted for being slow.
    */
    await page.setViewportSize({ width, height });
    await openBook(page, "#ch=what-changed&r=marine");
    await expect(page.locator(".absent")).toBeVisible();

    const over = await page.evaluate(() => {
      const inner = document.querySelector(".spread > .page--verso .page__inner");
      return inner ? inner.scrollHeight - inner.clientHeight : -1;
    });
    expect(over, "the absent page overflows its leaf").toBeLessThanOrEqual(2);
  });
}

/*
  The guard that makes declared panels worth declaring.

  Before pagination `.page__inner` scrolled, so every chapter fitted by definition and no test could
  tell: measured at 1600x900, "What did not" put 6,855px on an 826px page. Every split in `pages.ts`
  and every divisor in `Book.svelte`'s reading scale was chosen against this walk, and without it the
  next paragraph added to a claim silently puts the scrollbar back.

  It walks the whole book by the corner rather than by URL, so it also asserts the two things a book
  has to do: every page is reachable by turning, and the folios run without a gap.
*/
for (const [width, height] of [
  [1600, 900],
  [1280, 800],
] as const) {
  test(`no page in the book overflows itself at ${width}x${height}`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await openBook(page, "#ch=how-to-read&p=0");

    const spreads = (await layout()).length;
    const over: string[] = [];
    const folios: number[] = [];
    let turned = 0;

    for (;;) {
      const spread = await page.evaluate(() => {
        // The direct child of the spread, so the turn's own leaf and parked page are not measured.
        const read = (side: string) => {
          const inner = document.querySelector(`.spread > .page--${side} .page__inner`);
          if (!inner) return null;
          const folio = document
            .querySelector(`.spread > .page--${side} .page__folio`)
            ?.textContent?.trim()
            .split(" ")[0];
          return {
            over: inner.scrollHeight - inner.clientHeight,
            folio: folio ? Number.parseInt(folio, 10) : null,
            head: (inner.textContent ?? "").trim().slice(0, 40).replace(/\s+/g, " "),
          };
        };
        return {
          verso: read("verso"),
          recto: read("recto"),
          more: Boolean(document.querySelector('.spread > .page--recto [data-turn="on"]')),
        };
      });

      for (const [side, cell] of [
        ["verso", spread.verso],
        ["recto", spread.recto],
      ] as const) {
        if (!cell) continue;
        // Two pixels of slack for sub-pixel layout, and no more: this is a budget, not a target.
        if (cell.over > 2) over.push(`${cell.folio} (${side}) by ${cell.over}px: ${cell.head}`);
        if (cell.folio !== null) folios.push(cell.folio);
      }

      if (!spread.more) break;
      const was = spread.recto?.folio ?? spread.verso?.folio ?? null;
      await page.locator('.spread > .page--recto [data-turn="on"]').click();
      turned += 1;
      if (turned > spreads + 2) throw new Error("the corner never stopped offering a next page");
      /*
        Waiting for the folio to change rather than for an element to appear. During the turn the
        leaf and the parked page are `Page` instances too -- which is ADR 0015 decision 5 working --
        so `.page--recto` matches three elements mid-flight and a visibility assertion on it is
        ambiguous rather than wrong. The folio on the *settled* recto is unambiguous.
      */
      await expect
        .poll(() =>
          page.evaluate(() => {
            const text = document
              .querySelector(".spread > .page--recto .page__folio")
              ?.textContent?.trim()
              .split(" ")[0];
            return text ? Number.parseInt(text, 10) : null;
          }),
        )
        .not.toBe(was);
    }

    expect(over, `${over.length} of ${folios.length + 1} pages overflow`).toEqual([]);
    expect(turned + 1, "the corner did not reach every spread").toBe(spreads);
    // Folios in order and with no gap, which is the whole reason to print one.
    expect(folios).toEqual(Array.from({ length: folios.length }, (_, step) => step + 1));
  });
}

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
    await page.goto(hash || "?");
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
    // One page to a leaf, which is the whole of this container -- and its own list, so counted from
    // `leavesOf` rather than from the spreads doubled.
    expect(state.leaves).toHaveLength((await leafLayout()).length);
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
        top: Number.parseFloat(style.paddingTop),
        bottom: Number.parseFloat(style.paddingBottom),
      };
    });
    expect(pad.left).toBeGreaterThan(12);
    expect(pad.right).toBeGreaterThan(12);

    // And the foot clears the fore-edge tab, because text under it is text nobody can read.
    const thumb = await page.locator(".thumb").evaluate((node) => node.getBoundingClientRect().height);
    expect(pad.bottom).toBeGreaterThan(thumb);

    /*
      And the head clears the type controls, for the same reason at the other edge.

      They are `position: fixed` in the top-left corner. Over a spread they sit on the desk's own
      margin; a phone has no margin, so every leaf in the book printed its chapter kicker underneath
      "HAND CLEAR DYSLEXIA" -- on the claim pages, the introduction, all of them. Asserted against
      the bar's measured box rather than against the number, so moving the bar fails here.
    */
    const bar = await page
      .locator(".settings")
      .evaluate((node) => node.getBoundingClientRect().bottom);
    expect(pad.top, "the page's first line runs under the type controls").toBeGreaterThan(bar);
  });

  test("the swipe is the page turn, and where it stops goes in the URL", async ({ page }) => {
    await openLeaves(page);
    await expect(page.locator(".thumb__word")).toHaveText("Changed");

    // The first leaf of "What we cannot see", found from the phone's own pagination.
    const leaves = await leafLayout();
    const target = leafOpening(leaves, "cannot-see");

    await swipeTo(page, target);
    await expect(page).toHaveURL(/[#&]ch=cannot-see/);
    await expect(page.locator(".thumb__word")).toHaveText("Cannot see");

    // Back is the reading and not the gesture: the rail follows the chapter out of the history.
    await page.goBack();
    await expect(page.locator(".thumb__word")).toHaveText("Changed");
    const state = await survey(page);
    const opened = leafOpening(leaves, "what-changed");
    expect(state.scrollLeft).toBe(state.offsets[opened]);
  });

  test("a flick through chapters leaves one history entry per stop", async ({ page }) => {
    await openLeaves(page);
    const before = await page.evaluate(() => history.length);

    /*
      Three leaves crossed inside the settle window, with real gaps so each one is a scroll event the
      browser actually dispatches. Reported per leaf this would push three entries and make the back
      button a rewind of the gesture; the URL waits for the rail to stop instead.
    */
    const leaves = await leafLayout();
    const crossed = ["what-changed", "what-did-not", "cannot-see"].map((slug) =>
      leafOpening(leaves, slug),
    );
    await page.evaluate(async (leaves) => {
      const rail = document.querySelector<HTMLElement>(".rail")!;
      const sheets = rail.querySelectorAll<HTMLElement>("[data-leaf]");
      for (const leaf of leaves) {
        rail.scrollLeft = sheets[leaf]!.offsetLeft;
        await new Promise((settle) => setTimeout(settle, 40));
      }
    }, crossed);

    await expect(page).toHaveURL(/[#&]ch=cannot-see/);
    expect(await page.evaluate(() => history.length)).toBe(before + 1);

    // And the paper kept up with the flick, which is the other cadence: mounted at once, so a fling
    // never lands on blank paper.
    const landed = crossed[crossed.length - 1]!;
    expect((await survey(page)).written).toEqual([landed - 1, landed, landed + 1]);
  });

  test("only the leaf in view and its neighbours carry anything", async ({ page }) => {
    await openLeaves(page, "#ch=what-changed");
    const state = await survey(page);
    const opened = leafOpening(await leafLayout(), "what-changed");

    expect(state.written).toEqual([opened - 1, opened, opened + 1]);
    // Named rather than counted, because this is the assertion that keeps a phone from running a
    // MapLibre context most of a book away from the reader.
    expect(state.leaves.slice(-2)).toEqual(["the-world:verso", "the-world:recto"]);
    for (const leaf of [state.leaves.length - 2, state.leaves.length - 1]) {
      expect(state.written).not.toContain(leaf);
    }
  });

  test("a deep link opens on its chapter rather than scrolling to it", async ({ page }) => {
    await openLeaves(page, "#ch=what-did-not");
    const state = await survey(page);
    const opened = leafOpening(await leafLayout(), "what-did-not");
    expect(state.scrollLeft).toBe(state.offsets[opened]);
    expect(state.written).toEqual([opened - 1, opened, opened + 1]);
  });

  test("a phone numbers its own pages, in order and without a gap", async ({ page }) => {
    /*
      **This asserted the opposite until the owner decided otherwise, and the reason is recorded
      here rather than deleted.**

      It used to say a phone prints the same folio the spread does, on the argument that a page
      number which moved when you turned the device would not be a page number. What overturned it
      was a measurement: ten of the phone's leaves overflowed and scrolled, worst by 485 pixels, and
      the cause is geometry rather than type -- a 375px column reflows the same prose about 1.8 times
      taller than a 677px one, so no readable size makes a desktop page fit a phone leaf. Holding one
      pagination meant either unreadable type or splitting the spread's pages for a screen that does
      not need it. The owner's call: a phone and a spread can be different, because the logic is
      different and forcing one onto the other is worse.

      So the folio is per container, and what is asserted instead is what a folio is for: the numbers
      run in order, from one, with no gap, so a reader can tell where they are and how far in.
    */
    await openLeaves(page, "#ch=how-to-read");
    const printed = await page
      .locator("[data-leaf] .page__folio")
      .evaluateAll((nodes) =>
        nodes.map((node) => Number.parseInt((node.textContent ?? "").trim(), 10)),
      );

    // The first leaf is a title page and carries no number, as the spread's own first verso does.
    expect(printed.length, "no folios printed").toBeGreaterThan(1);
    expect(printed).toEqual(Array.from({ length: printed.length }, (_, step) => step + 1));
  });

  test("a phone carries no leaf the spread only needed to pad with", async ({ page }) => {
    /*
      The spread pads each argument to an even page count so a leaf ending one never faces a leaf
      starting the next. A phone shows one page at a time and has nothing to pad against, so those
      blanks are swipes onto nothing -- four of them, when this was the spread's list flattened.

      Counted against the spread rather than written down: the two lists come from one set of
      authored pages, so the phone's is shorter by exactly the padding and by nothing else.
    */
    const { leavesOf, spreadsOf } = await import("../src/lib/book/pages");
    const { CHAPTERS: chapters } = await import("../src/lib/story");
    const read = (name: string) => JSON.parse(readFileSync(`public/${name}`, "utf8"));
    const sources = {
      findings: read("findings.json").findings,
      introduction: read("introduction.json"),
      safeguards: read("sandbox.json"),
      dial: read("response.json"),
    };
    const leaves = leavesOf(sources, chapters);
    const spreads = spreadsOf(sources, chapters);

    expect(leaves.length, "the phone gained pages rather than losing padding").toBeLessThan(
      spreads.length * 2,
    );
    // And every page the spread carries, other than its padding, is a leaf: same book, arranged twice.
    const carried = spreads
      .flatMap((spread) => [spread.verso, spread.recto])
      .filter((panel) => panel.kind !== "blank").length;
    expect(leaves.filter((leaf) => leaf.panel.kind !== "blank").length).toBe(carried);

    await openLeaves(page, "#ch=how-to-read");
    await expect(page.locator("[data-leaf]")).toHaveCount(leaves.length);
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
    const opened = leafOpening(await leafLayout(), "what-did-not");
    expect(state.scrollLeft).toBe(state.offsets[opened]);
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
