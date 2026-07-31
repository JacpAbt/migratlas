/**
 * The rebuilt shell.
 *
 * The three modes are the design, so most of what is asserted here is that they stay distinct: a
 * reader who asks for the evidence gets the evidence, and a reader who asks for the map gets the map
 * rather than the map with an argument still filtered onto it. That last one shipped broken on the
 * first attempt and looked like a rendering fault rather than a decision.
 */

import { expect, test, type Page } from "@playwright/test";

/**
 * How long to keep asking whether the camera has arrived.
 *
 * Polled, never slept. The flight is 2.2s and the layers load asynchronously before it starts, so a
 * one-shot read after a fixed wait passes alone and fails under the whole suite -- which is the flake
 * that gets re-run rather than fixed. Two of these tests did exactly that.
 */
const SETTLE_MS = 15_000;

async function arrive(page: Page): Promise<void> {
  // Relative, and with ?debug so the map is readable. A leading slash would replace the whole
  // path of baseURL and land on the origin root rather than the project subpath -- the trap the
  // globe suite already documents.
  await page.goto("shell.html?debug=1");
  await expect(page.locator(".arrival__card")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  await expect(page.locator(".globe canvas")).toBeVisible();
}

/**
 * Wait until the camera stops moving, then answer where it is.
 *
 * Two consecutive identical readings, because `flyTo` has no "arrived" event worth trusting and a
 * single sample mid-flight is indistinguishable from a camera that never left.
 */
async function settled(page: Page): Promise<Camera> {
  let previous = "";
  await expect
    .poll(
      async () => {
        // Tolerates the hook not existing yet. It is published only once every layer has loaded,
        // and the arrival card is visible long before the 50,000-feature assessment finishes -- so a
        // poll that threw on a missing map reported "the shell must expose one" for a shell that
        // simply had not got there.
        const at = await camera(page);
        if (!at) return false;
        const now = `${at.lon.toFixed(2)},${at.lat.toFixed(2)},${at.zoom.toFixed(2)}`;
        const still = now === previous;
        previous = now;
        return still;
      },
      { timeout: SETTLE_MS, intervals: [250] },
    )
    .toBe(true);

  const at = await camera(page);
  expect(at, "the shell never exposed a map under ?debug").not.toBeNull();
  return at!;
}

interface Camera {
  lon: number;
  lat: number;
  zoom: number;
}

/** Camera state, read from MapLibre rather than inferred from pixels. Null until the hook exists. */
async function camera(page: Page): Promise<Camera | null> {
  return page.evaluate(() => {
    const globe = (window as unknown as { migratlas?: { map?: unknown } }).migratlas?.map as
      | { getCenter: () => { lng: number; lat: number }; getZoom: () => number }
      | undefined;
    if (!globe) return null;
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
  const at = await settled(page);
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
  const before = await settled(page);

  await page.locator(".tab", { hasText: /poleward/i }).click();
  await expect(page.locator(".claim__title")).toHaveText(/poleward/i);

  const after = await settled(page);
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
  await settled(page);

  await page.getByRole("button", { name: /just the map/i }).click();
  const wide = await settled(page);

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
  expect(wide.zoom).toBeLessThan(2);
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

    // Nothing the map owns may be printed *over* the claim, and that is the requirement -- not that
    // the boxes never touch. The first version compared bounding boxes, which is stricter than what
    // matters and failed on CI over a few pixels of harmless overlap while the notice was perfectly
    // readable. Occlusion is the real test: ask the browser what is actually on top at the centre of
    // each control, and require it to be that control.
    const buried = await page.evaluate(() => {
      const hits: string[] = [];
      for (const selector of [
        ".maplibregl-ctrl-attrib",
        ".maplibregl-ctrl-group",
        ".maplibregl-ctrl-scale",
      ]) {
        for (const node of document.querySelectorAll(selector)) {
          const box = node.getBoundingClientRect();
          if (box.width === 0 || box.height === 0) continue;
          const at = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
          if (!at || !(node.contains(at) || at.contains(node))) {
            hits.push(`${selector} is under ${at?.className || at?.tagName || "nothing"}`);
          }
        }
      }
      return hits;
    });
    expect(buried, buried.join("; ")).toEqual([]);
  });
}

/**
 * The panels the old page carried, rebuilt where they belong.
 *
 * The structural change worth asserting: a figure belongs to the *claim* it is evidence for, not to a
 * panel of its own. The counterfactual is the attribution's argument and the detectability
 * assessment is the coverage limit's number, so each appears with its claim and nowhere else.
 */

test("the counterfactual is the attribution claim's own evidence", async ({ page }) => {
  await arrive(page);
  await page.getByRole("button", { name: /show me how you know/i }).click();

  // Not on the first claim: a chart on every claim would be decoration.
  await expect(page.locator(".chart__svg")).toHaveCount(0);

  await page.locator(".tab", { hasText: /Human forcing/i }).click();
  const charts = page.locator(".chart__svg");
  await expect(charts.first()).toBeVisible();

  // Two charts, not one with four lines. Two of four lines would nearly coincide and two would sit
  // far apart, which invites averaging -- and an average of two different quantities is nothing.
  await expect(charts).toHaveCount(2);
  await expect(page.locator(".chart__line")).toHaveCount(4);

  // One frame for both, which is the assertion the whole design rests on. Each chart drawn to its
  // own extents would make a 0.89-day gap and a 0.29-day gap look the same size, and would stretch
  // the shorter window's slope. Compared on the rendered geometry rather than the source numbers,
  // because it is the pixels that would lie.
  const geometry = await charts.evaluateAll((nodes) =>
    nodes.map((node) => {
      const ticks = [...node.querySelectorAll(".chart__tick")].map((t) => t.textContent?.trim());
      return ticks.join("|");
    }),
  );
  expect(new Set(geometry).size, "the two charts share one frame").toBe(1);

  // The observed line draws before the counterfactual: the drawing order is the argument, because a
  // reader watches the gap fail to open rather than hunting for it.
  const delays = await page
    .locator(".chart__line")
    .evaluateAll((nodes) => nodes.map((n) => getComputedStyle(n).transitionDelay));
  expect(new Set(delays).size, "the lines all draw at once").toBeGreaterThan(1);

  // Both charts say where their own attribution stops, not only in the caveat -- and they say
  // different things, because ATTRICI's counterfactual series ran out where DAMIP's share is a ratio
  // carried past the window that fitted it. globe.spec.ts checks the geometry; this checks the words.
  const limits = await page.locator(".chart__beyond-label").allTextContents();
  expect(limits).toHaveLength(2);
  expect(limits.join(" ")).toMatch(/no counterfactual after 2019/);
  expect(limits.join(" ")).toMatch(/share fitted only to 2014/);

  // Each size stated in words, which is what stops a chart being "improved" into a diverging wedge.
  await expect(page.locator(".chart__size").first()).toContainText(/part by \d+\.\d+ days/);

  // And the disagreement explained, at body size rather than as a footnote. Two numbers that differ
  // by a factor of two with no explanation would be worse than publishing one of them.
  const gap = page.locator(".pair__gap");
  await expect(gap).toContainText(/differ/i);
  await expect(gap.locator("p")).toContainText("not two estimates of one number");
  const size = await gap.locator("p").evaluate((n) => parseFloat(getComputedStyle(n).fontSize));
  const footnote = await page
    .locator(".pair__caveat")
    .evaluate((n) => parseFloat(getComputedStyle(n).fontSize));
  expect(size, "the explanation is not set at footnote size").toBeGreaterThan(footnote);
});

test("the detectability assessment is the coverage claim's own number", async ({ page }) => {
  await arrive(page);
  await page.getByRole("button", { name: /show me how you know/i }).click();
  await page.locator(".tab", { hasText: /northern-hemis/i }).click();

  const coverage = page.locator(".coverage");
  await expect(coverage).toBeVisible();
  // The headline, as a share rather than a count: "1,997 cells" means nothing without a denominator.
  await expect(coverage.locator(".coverage__lead")).toContainText(/%/);
  // A key, because four unlabelled greys are not a map of anything.
  await expect(coverage.locator(".coverage__legend li")).toHaveCount(4);
  // And every source, with the best it can do -- the point being that most of them can do nothing.
  await expect(coverage.locator("tbody tr")).not.toHaveCount(0);
  await expect(coverage.locator(".coverage__ceiling").first()).not.toBeEmpty();
});

test("explore carries the tools, with the terms every drawn layer was published under", async ({
  page,
}) => {
  await arrive(page);
  await page.getByRole("button", { name: /just let me explore/i }).click();

  const explore = page.locator(".explore");
  await expect(explore).toBeVisible();

  // One toggle per layer, including the assessment, which starts off.
  const toggles = explore.locator(".layers input");
  await expect(toggles).toHaveCount(4);

  // Required, not decorative: published data must never be separable from the terms it was
  // published under. This is the assertion the old page had and the shell has to keep.
  await expect(explore.locator(".terms")).not.toBeEmpty();

  // The clock reads as a date rather than as a day number, and without the stray punctuation a
  // trimmed shared formatter left behind.
  const clockface = await explore.locator(".clockface").textContent();
  expect(clockface).toMatch(/^\d{1,2} \w{3} · week \d{1,2}$/);

  // Moving the slider moves the label, so the control is wired to the clock and not decorative.
  await explore.locator(".time input").fill("120");
  await expect(explore.locator(".clockface")).not.toHaveText(clockface!);

  // Search is loaded and knows how many animals it holds.
  await expect(explore.locator("#taxon-search")).toHaveAttribute("placeholder", /Search [\d,]+ animals/);
});

test("switching on the assessment brings its key with it", async ({ page }) => {
  await arrive(page);
  await page.getByRole("button", { name: /just let me explore/i }).click();

  const explore = page.locator(".explore");
  // The regression: the legend was on the claim and missing here, which is the worse way round --
  // the layer can be switched on from this panel and could not be read once it was.
  await expect(explore.locator(".key li")).toHaveCount(0);

  await explore.locator(".layers input").last().check();
  await expect(explore.locator(".key li")).toHaveCount(4);
  await expect(explore.locator(".key li").first()).toContainText("%");
});

test("searching an animal draws it and says which one is shown", async ({ page }) => {
  await arrive(page);
  await page.getByRole("button", { name: /just let me explore/i }).click();

  // A species the index actually holds. It is built from the *published* layers, so FISHGLOB's
  // fish are absent -- that source is a survey index with no per-species surface, and searching for
  // a cod found nothing while looking exactly like a broken search.
  await page.locator("#taxon-search").fill("Physeter");
  const hits = page.locator(".hits button");
  await expect(hits.first()).toBeVisible();
  await hits.first().click();

  // Named back to the reader, with a way out. A selection with no label is a map that changed for
  // no stated reason.
  await expect(page.locator(".chosen")).toContainText(/Showing/);
  await page.locator(".chosen__clear").click();
  await expect(page.locator(".chosen")).toHaveCount(0);
});

/**
 * The confound sandbox.
 *
 * Its whole claim is that switching a safeguard off shows what the published number owes to that
 * safeguard, and the claim collapses if the default does not reproduce what the ledger says. That
 * invariant is already asserted in `tests/test_sandbox.py` against the computed values; here it is
 * asserted against what a reader actually sees, which is a different failure mode.
 */

test("the sandbox default reproduces the number on the claim it sits under", async ({ page }) => {
  await arrive(page);
  await page.getByRole("button", { name: /show me how you know/i }).click();

  const published = await page.locator(".claim__value").first().textContent();
  const match = published?.match(/-?\d+\.\d+/);
  expect(match, `no number in the claim value "${published}"`).toBeTruthy();

  // Every knob on this claim, at its published setting, must show the claim's own figure. A panel
  // that disagreed with the card above it would undermine both.
  const knobs = page.locator(".knob");
  await expect(knobs.first()).toBeVisible();
  const count = await knobs.count();
  expect(count).toBeGreaterThan(1);

  for (let index = 0; index < count; index += 1) {
    const knob = knobs.nth(index);
    await expect(knob.locator(".option--on em")).toHaveText("published");
    await expect(knob.locator(".knob__value")).toContainText(match![0].replace("-", "−"));
    await expect(knob.locator(".knob__delta--published")).toBeVisible();
  }
});

test("switching a safeguard off moves the number and says which way", async ({ page }) => {
  await arrive(page);
  await page.getByRole("button", { name: /show me how you know/i }).click();

  const knob = page.locator(".knob").filter({ hasText: /hardware upgrade/i });
  const before = await knob.locator(".knob__value").textContent();

  await knob.locator(".option", { hasText: "break at detected outage" }).click();
  const after = await knob.locator(".knob__value").textContent();
  expect(after).not.toBe(before);

  // The direction is the point, and this project's answer is the unusual one: fitting a break makes
  // the advance *larger*, so the published number is the conservative choice. A panel that only said
  // "the number moved" would waste that.
  await expect(knob.locator(".knob__delta")).toContainText(/larger effect than the number we publish/);
  await expect(knob.locator(".knob__value--alternative")).toBeVisible();
  await expect(knob.locator(".option--on em")).toHaveCount(0);
});

test("the shuffled-years control collapses the trend to nothing", async ({ page }) => {
  await arrive(page);
  await page.getByRole("button", { name: /show me how you know/i }).click();

  // The strongest single thing in the panel: destroy the order of the years and the trend goes with
  // it, which is what shows the result is order and not arithmetic.
  const knob = page.locator(".knob").filter({ hasText: /years were shuffled/i });
  await knob.locator(".option", { hasText: "years shuffled" }).click();
  const shuffled = await knob.locator(".knob__value").textContent();
  const value = Number.parseFloat(shuffled!.replace("−", "-"));
  expect(Math.abs(value), `shuffling left ${shuffled}`).toBeLessThan(0.05);
});

test("the refusal is on the claim it refutes, and its wrong answer takes a click", async ({
  page,
}) => {
  await arrive(page);
  await page.getByRole("button", { name: /show me how you know/i }).click();

  // Not on the autumn advance: it is the marine null's counter-analysis.
  await expect(page.locator(".refusal")).toHaveCount(0);
  await page.locator(".tab", { hasText: /poleward/i }).click();

  const refusal = page.locator(".refusal");
  await expect(refusal).toBeVisible();
  await expect(refusal.locator(".refusal__question")).not.toBeEmpty();

  // The one place in this project where something is behind a control, and deliberately: the figure
  // is a number we say is unsupported, so a reader chooses to see the mistake rather than meeting it
  // as a result. The button has to say what it will show.
  await expect(refusal.locator(".refusal__rows")).toHaveCount(0);
  const reveal = refusal.getByRole("button");
  await expect(reveal).toContainText(/wrong answer/i);
  await reveal.click();

  await expect(refusal.locator(".refusal__rows dt")).toHaveCount(4);
  // +4.42 degrees of apparent poleward movement, against an audited -0.011 per decade.
  await expect(refusal.locator(".refusal__rows")).toContainText("4.42");
  // Years are counted, not measured to two decimals.
  await expect(refusal.locator(".refusal__rows")).toContainText("1985 year");
  await expect(refusal.locator(".refusal__rows")).not.toContainText("1985.00");

  // And the verdict is present whether or not the figure was revealed.
  await expect(refusal.locator(".refusal__verdict")).toContainText(/not runnable/i);
});
