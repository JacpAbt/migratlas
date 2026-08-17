import { expect, test, type Page } from "@playwright/test";

import { readFile } from "node:fs/promises";

import { JITTER, MIN_EXTENT, drawnCoast } from "../src/globe/coastline";
import { graticuleSource } from "../src/globe/graticule";

/**
 * What this suite is for.
 *
 * A previous release shipped a globe that never drew anything: MapLibre's worker 404ed, and
 * MapLibre's response to that is silence — no console error, no map error event, a healthy
 * 60 fps and an empty canvas. `tsc` passed, `vite build` passed, CI was green, and the DOM
 * looked entirely correct. Nothing short of asking the map what it actually rendered would
 * have caught it, which is what these tests do.
 *
 * No test reaches the network. That is a property of the app, not of the harness: the default
 * basemap is bundled, so a run cannot be reddened by someone else's CDN.
 */

interface LoadedLayer {
  meta: { name: string; value_kind: string };
  cells: number;
  center: [number, number];
}

interface Hook {
  migratlas: {
    map: maplibregl.Map;
    loaded: LoadedLayer[];
  };
}

interface ReadyReport {
  layers: string[];
  cells: Record<string, number>;
  centers: Record<string, [number, number]>;
}

/**
 * Load the app and wait for the globe to declare its layers added.
 *
 * Relative, not "/?debug=1": a leading slash replaces the whole path of baseURL, which lands on
 * the origin root instead of the project subpath. `vite preview` happens to redirect the root to
 * its base, so an absolute path passes locally and would fetch somebody else's site on Pages.
 *
 * Polls for the hook rather than awaiting a promise on it: the shell publishes it once every layer
 * has loaded, and the arrival card is interactive well before the 50,000-feature assessment lands.
 */
async function ready(page: Page): Promise<ReadyReport> {
  await page.goto("?debug=1");
  await expect
    .poll(
      () => page.evaluate(() => (window as unknown as Hook).migratlas?.loaded?.length ?? 0),
      { timeout: 20_000 },
    )
    .toBeGreaterThan(0);

  return page.evaluate(() => {
    const { loaded } = (window as unknown as Hook).migratlas;
    return {
      layers: loaded.map((l) => l.meta.name),
      cells: Object.fromEntries(loaded.map((l) => [l.meta.name, l.cells])),
      centers: Object.fromEntries(loaded.map((l) => [l.meta.name, l.center])),
      zooms: Object.fromEntries(loaded.map((l) => [l.meta.name, l.zoom])),
    };
  });
}

/**
 * Get to the tools, which is where the layer toggles and the clock now live.
 *
 * Waits for the camera to stop before returning. Entering explore mode starts a 2.2s flight to the
 * whole sphere, and a test that then jumps the camera is fighting an animation that still owns it --
 * which showed up as a layer reporting zero rendered features while being visible, source-loaded,
 * and pointed at, i.e. as a bug in the app rather than in the test.
 */
async function explore(page: Page): Promise<void> {
  await page.getByRole("button", { name: /just let me explore/i }).click();
  await expect(page.locator(".explore")).toBeVisible();
  await settle(page);
}

/** Two consecutive identical camera readings. `flyTo` has no arrival event worth trusting. */
async function settle(page: Page): Promise<void> {
  let previous = "";
  await expect
    .poll(
      async () => {
        const now = await page.evaluate(() => {
          const { map } = (window as unknown as Hook).migratlas;
          const at = map.getCenter();
          return `${at.lng.toFixed(2)},${at.lat.toFixed(2)},${map.getZoom().toFixed(2)}`;
        });
        const still = now === previous;
        previous = now;
        return still;
      },
      { timeout: 15_000, intervals: [250] },
    )
    .toBe(true);
}

/** How many features the last frame actually drew for a layer. */
const rendered = (page: Page, layer: string): Promise<number> =>
  page.evaluate(
    (id) => (window as unknown as Hook).migratlas.map.queryRenderedFeatures({ layers: [id] }).length,
    layer,
  );

/** Camera and layer state, for a failure message that does not need a second CI run to read. */
async function diagnose(page: Page, layer: string): Promise<string> {
  return page.evaluate((id) => {
    const { map } = (window as unknown as Hook).migratlas;
    const spec = map.getStyle().layers.find((l) => l.id === id);
    const centre = map.getCenter();
    return JSON.stringify({
      centre: [Number(centre.lng.toFixed(2)), Number(centre.lat.toFixed(2))],
      zoom: Number(map.getZoom().toFixed(2)),
      visibility: spec?.layout?.visibility ?? "visible",
      filter: JSON.stringify(spec?.filter),
      sourceLoaded: map.isSourceLoaded(id),
      allLayers: map.queryRenderedFeatures().length,
    });
  }, layer);
}

/** Per-layer patience. Three of these must still fit inside a test's own timeout. */
const DRAW_TIMEOUT_MS = 8000;

/**
 * Assert a layer draws, polling rather than waiting on a single event.
 *
 * `queryRenderedFeatures` answers for the last completed frame, and MapLibre's `idle` does not
 * reliably fire on a map with no tile sources — so the honest primitive is to keep asking.
 */
async function expectDrawn(page: Page, layer: string): Promise<void> {
  try {
    await expect.poll(() => rendered(page, layer), { timeout: DRAW_TIMEOUT_MS }).toBeGreaterThan(0);
  } catch (error) {
    // Reports state, not a cause. An earlier version asserted "never drew a feature" for any
    // failure here, including Playwright's own test deadline -- which sent one investigation
    // through two wrong hypotheses before a screenshot showed the layer drawing perfectly.
    throw new Error(`${layer} had 0 rendered features. State: ${await diagnose(page, layer)}`, {
      cause: error,
    });
  }
}

const mapLayerFor = (page: Page, name: string): Promise<string> =>
  page.evaluate(
    (layer) =>
      (window as unknown as Hook).migratlas.map
        .getStyle()
        .layers.map((l) => l.id)
        .find((candidate) => candidate.endsWith(layer)) ?? "",
    name,
  );

/**
 * Point the camera at a layer's data.
 *
 * On a globe only the facing hemisphere renders, so a layer covering one continent is
 * legitimately invisible from the default view. The centre comes from the app's ready report
 * rather than from a second HTTP fetch of the layer file -- re-downloading what the page already
 * has cost six extra requests per run and reset the connection often enough to redden the suite.
 */
async function focusOn(page: Page, report: ReadyReport, name: string, layerId: string): Promise<void> {
  const center = report.centers[name];
  expect(center, `no centre reported for ${name}`).toBeDefined();
  // The layer's own camera hint, where it declares one: a compact layer's cells sit below the
  // tiler's hand-over zoom and are legitimately absent from the globe view.
  const zoom = report.zooms?.[name] ?? 2.2;
  await page.evaluate(
    (view) => (window as unknown as Hook).migratlas.map.jumpTo(view),
    { center: center as [number, number], zoom },
  );
  await settle(page);
  await expectDrawn(page, layerId);
}


test("the globe reaches a usable style with coastlines", async ({ page }) => {
  await ready(page);
  await expect(page.locator(".globe canvas")).toBeVisible();
  // Bundled land, so a globe always looks like a globe.
  await expectDrawn(page, "land");
});

/**
 * Every layer draws, in one test over one page load.
 *
 * Split into a test per layer once, for a better failure message, and reverted: each one reloads the
 * page and re-decodes 125,000 features across four layers, so the split cost four times the work to
 * buy a name that `expectDrawn` already reports.
 *
 * **This deadline is a hang detector and nothing else, and it took three tries to say so.**
 *
 * It began at 150s, from timing this alone -- 66s -- and doubling. It had been passing at 98% of
 * that for the life of the project and finally went over. Raising it to 240s bought one green run.
 * Dropping the suite from three workers to two (`playwright.config.ts`, and that change is right
 * on its own terms) did not bring it back under 150s either, because the other two spec files now
 * boot a full globe per test and decode 125,000 features each time.
 *
 * So the wall clock here is a fact about the machine and the rest of the suite, not about the map.
 * Trying to make it a performance assertion was the mistake; the performance assertion is
 * `DRAW_TIMEOUT_MS`, eight seconds per layer, which fails with a state dump and is what actually
 * catches a wedged map. This number exists so a hung run ends, and it is set where it will not
 * fire on a scheduler.
 */
test("every layer draws features once it is switched on", async ({ page }) => {
  // 240s was the contended number for a five-layer walk; the movement arc made it eight, each
  // with its own flight and settle, and CI ran past the ceiling mid-walk with every layer that
  // had been reached drawing fine. Same scaling, same reasoning: the ceiling ends a hung run,
  // DRAW_TIMEOUT_MS catches a wedged map.
  test.setTimeout(420_000);
  const report = await ready(page);
  expect(report.layers.length).toBeGreaterThan(0);
  await explore(page);

  for (const [index, name] of report.layers.entries()) {
    const id = await mapLayerFor(page, name);
    expect(id, `no map layer for entry ${name}`).not.toBe("");

    // Switched on first. Not every layer ships visible -- the assessment starts off deliberately --
    // and asserting on the arrival state would either fail on that layer or, if the loop simply
    // skipped hidden ones, let a broken layer pass by staying hidden.
    const toggle = page.locator(".explore .layers input").nth(index);
    if (!(await toggle.isChecked())) await toggle.check();

    // The assertion an earlier failure needed: not "the layer exists" but "it drew something".
    await focusOn(page, report, name, id);
  }
});

test("the layer panel publishes its generalisation statement", async ({ page }) => {
  await ready(page);
  await explore(page);
  // Required, not decorative: published data must never be separable from the terms it was
  // published under.
  await expect(page.locator(".explore .terms")).not.toBeEmpty();

  await page.locator(".maplibregl-ctrl-attrib-button").click();
  await expect(page.locator(".maplibregl-ctrl-attrib-inner")).toContainText("resolution");
});

test("advancing the clock re-times the series layer without rebuilding it", async ({ page }) => {
  test.setTimeout(90_000);
  const report = await ready(page);
  await explore(page);
  const id = "series-aerial-passage";
  await focusOn(page, report, "aerial-passage", id);

  // The week lives inside the filter expression, which is the whole point of the design: the
  // clock swaps which property the layer reads, it never touches the source.
  const weekIndex = (): Promise<string> =>
    page.evaluate((layer) => {
      const filter = (window as unknown as Hook).migratlas.map.getFilter(layer);
      return JSON.stringify(filter).match(/"w(\d+)"/)?.[1] ?? "";
    }, id);
  // Counting requests rather than inspecting MapLibre's internals: the requirement is that a
  // week change costs no fetch, and that is exactly what the network says.
  let fetches = 0;
  page.on("request", (request) => {
    if (request.url().includes("aerial-passage.geojson")) fetches += 1;
  });

  const before = await weekIndex();
  // Through the slider rather than a hook on `window`: the clock is internal to the shell
  // now, and driving it the way a visitor does tests the wiring as well as the filter.
  await page.locator(".explore .time input").fill("250");

  await expect.poll(weekIndex).toBe("35");
  expect(before).not.toBe("35");
  await expectDrawn(page, id);
  expect(fetches, "a week change must not refetch the layer").toBe(0);

  // The same clock walks the ice: day 250 sits in September, and the contour's filter is
  // month-keyed because monthly is the finest wheel its product turns on.
  const iceMonth = await page.evaluate(() => {
    const filter = (window as unknown as Hook).migratlas.map.getFilter("contour-sea-ice-edge");
    return JSON.stringify(filter);
  });
  expect(iceMonth).toContain("9");
});

test("the passage layer wears its measured direction, and the clock turns it", async ({ page }) => {
  test.setTimeout(90_000);
  const report = await ready(page);
  await explore(page);
  const id = "series-aerial-passage";
  const flow = `${id}-flow`;
  await focusOn(page, report, "aerial-passage", id);

  // The darts are the same source wearing a second mark: a symbol whose rotation reads the
  // week's measured bearing, geographic rather than screen-aligned. A station whose week has
  // passage but no velocity fit shows a circle and no dart -- filtered, not drawn at zero.
  const state = () =>
    page.evaluate((layer) => {
      const { map } = (window as unknown as Hook).migratlas;
      return {
        image: map.hasImage("flow-dart"),
        rotate: JSON.stringify(map.getLayoutProperty(layer, "icon-rotate")),
        alignment: map.getLayoutProperty(layer, "icon-rotation-alignment") as string,
        drawn: map.queryRenderedFeatures({ layers: [layer] }).length,
      };
    }, flow);

  const before = await state();
  expect(before.image, "the dart image is registered").toBe(true);
  expect(before.rotate).toContain("dw");
  expect(before.alignment, "a bearing is geographic, not a screen decoration").toBe("map");
  await expect
    .poll(async () => (await state()).drawn, { message: "no darts rendered" })
    .toBeGreaterThan(0);

  await page.locator(".explore .time input").fill("250");
  await expect.poll(async () => (await state()).rotate).toContain("dw35");
});

test("a station popup states the caveat with the number", async ({ page }) => {
  test.setTimeout(90_000);
  const report = await ready(page);
  // In explore mode: a claim sheet covers the sphere, so there would be nothing to click.
  await explore(page);
  await focusOn(page, report, "aerial-passage", "series-aerial-passage");

  // A station the panels are not sitting on. Clicking the *first* rendered feature put the click
  // under the tools panel on CI, where it opened nothing and reported an empty popup -- which reads
  // as a broken popup rather than as a click that never reached the map.
  const point = await page.evaluate(() => {
    const { map } = (window as unknown as Hook).migratlas;
    const panels = [...document.querySelectorAll(".explore, .index, .maplibregl-ctrl-bottom-right")]
      .map((node) => node.getBoundingClientRect())
      .filter((box) => box.width > 0);

    for (const feature of map.queryRenderedFeatures({ layers: ["series-aerial-passage"] })) {
      const at = (feature.geometry as GeoJSON.Point).coordinates as [number, number];
      const { x, y } = map.project(at);
      const covered = panels.some(
        (box) => x >= box.left && x <= box.right && y >= box.top && y <= box.bottom,
      );
      if (!covered) return { x: Math.round(x), y: Math.round(y) };
    }
    throw new Error("every rendered station is under a panel");
  });

  await page.locator(".globe canvas").click({ position: point });
  const popup = page.locator(".maplibregl-popup-content");
  await expect(popup).toContainText("Autumn passage shift");
  // The radar cannot tell a bird from a bat from an insect, so no reading of this layer may
  // omit that.
  await expect(popup).toContainText("aerial biomass, not birds");

  // The popup is MapLibre's node, so nothing re-renders it when the surface changes -- the
  // tokens have to reach it through CSS alone. It shipped broken once: night swapped the page's
  // ink to chalk while the card kept MapLibre's white, and the label all but vanished. Measured
  // against a probe painted with the tokens, because the tokens are hex and computed styles are
  // rgb().
  const rendered = () =>
    popup.evaluate((node) => {
      const probe = document.createElement("div");
      probe.style.background = "var(--paper)";
      probe.style.color = "var(--ink)";
      document.body.append(probe);
      const tokens = getComputedStyle(probe);
      const got = getComputedStyle(node);
      const seen = {
        background: got.backgroundColor,
        paper: tokens.backgroundColor,
        color: got.color,
        ink: tokens.color,
      };
      probe.remove();
      return seen;
    });

  const day = await rendered();
  expect(day.background).toBe(day.paper);
  expect(day.color).toBe(day.ink);

  await page.locator(".surface").getByRole("radio", { name: "Night", exact: true }).check();
  await expect(page.locator(":root")).toHaveAttribute("data-surface", "night");
  const night = await rendered();
  expect(night.background).toBe(night.paper);
  expect(night.color).toBe(night.ink);
  expect(night.background).not.toBe(day.background);
});

test("each counterfactual is drawn to the scatter, and both to one frame", async ({ page }) => {
  // The two geometric properties worth pinning, measured off the rendered SVG rather than the source
  // numbers, because it is the pixels that would lie.
  //
  // Scaled to the gap, the divergence would grow to fill the plot. And scaled *per chart*, DAMIP's
  // 0.89-day gap and ATTRICI's 0.29-day gap would render the same height -- so the reader would see
  // two counterfactuals agreeing where the whole finding is that they do not.
  await ready(page);
  await page.getByRole("button", { name: /show me how you know/i }).click();
  await page.locator('.tab[data-claim="anthropogenic-share"]').click();
  await expect(page.locator(".chart__svg").first()).toBeVisible();

  const charts = await page.locator(".chart__svg").evaluateAll((nodes) =>
    nodes.map((node) => {
      const y = (selector: string) => {
        const line = node.querySelector(selector) as SVGLineElement | null;
        return line ? Number(line.getAttribute("y2")) : NaN;
      };
      const dots = [...node.querySelectorAll(".chart__year")].map((dot) =>
        Number(dot.getAttribute("cy")),
      );
      const ticks = [...node.querySelectorAll(".chart__tick")].map((tick) =>
        Number(tick.getAttribute("y")),
      );
      return {
        gap: Math.abs(y(".chart__line--observed") - y(".chart__line--counterfactual")),
        scatter: Math.max(...dots) - Math.min(...dots),
        ticks: ticks.join(","),
      };
    }),
  );

  expect(charts.length).toBeGreaterThan(1);
  for (const chart of charts) {
    expect(chart.scatter).toBeGreaterThan(0);
    expect(
      chart.gap / chart.scatter,
      `the lines part by ${((chart.gap / chart.scatter) * 100).toFixed(0)}% of the observed ` +
        "scatter, which means the axis is scaled to the gap rather than to the data",
    ).toBeLessThan(0.35);
  }

  expect(
    new Set(charts.map((chart) => chart.ticks)).size,
    "the charts' rules sit at different heights, so each was scaled to itself",
  ).toBe(1);

  // And the gaps must render *differently*, because they are different sizes. Equal heights here
  // would mean the shared frame was defeated somewhere downstream of the ticks.
  const gaps = charts.map((chart) => Math.round(chart.gap));
  expect(new Set(gaps).size, `both gaps render at ${gaps[0]}px`).toBeGreaterThan(1);
});

test("no ribbon is drawn past its own frame, and each shades where its evidence stops", async ({
  page,
}) => {
  // Three things I found by looking at a screenshot rather than by a failing test, which is why they
  // are here: a label that printed past the SVG's right edge, a leader that crossed the shaded years
  // as a straight diagonal and read as the line continuing through them, and only one of the two
  // charts shading at all -- which told a reader DAMIP carried evidence to 2025 when `f` is fitted to
  // 2014. Eyes do not run in CI.
  await ready(page);
  await page.getByRole("button", { name: /show me how you know/i }).click();
  await page.locator('.tab[data-claim="anthropogenic-share"]').click();
  await expect(page.locator(".chart__svg").first()).toBeVisible();

  const measured = await page.locator(".chart__svg").evaluateAll((nodes) =>
    nodes.map((node) => {
      const box = node.viewBox.baseVal;
      const labels = [...node.querySelectorAll<SVGTextElement>(".chart__label, .chart__rate")];
      return {
        overflowing: labels
          .filter((label) => label.getBBox().x + label.getBBox().width > box.width)
          .map((label) => label.textContent?.trim()),
        // The plot's right edge, so a band can be told apart from no band at all.
        band: node.querySelector<SVGRectElement>(".chart__beyond")?.x.baseVal.value ?? null,
        lineEnds: [...node.querySelectorAll<SVGLineElement>(".chart__line")].map((line) =>
          Math.round(line.x2.baseVal.value),
        ),
      };
    }),
  );

  for (const chart of measured) {
    expect(chart.overflowing, "labels printing past the chart's own box").toEqual([]);
    // Both lines in a ribbon end at the same x -- its window's end. One reaching further would be a
    // counterfactual drawn over years its own method never saw.
    expect(new Set(chart.lineEnds).size).toBe(1);
  }

  // Every chart declares where its attribution stops, and they stop in different places: DAMIP's
  // share is fitted to 2014, ATTRICI's counterfactual series ends in 2019.
  const bands = measured.map((chart) => chart.band);
  expect(bands.every((band) => band !== null), "a chart with no limit drawn").toBe(true);
  expect(new Set(bands).size, "both charts shade from the same year").toBeGreaterThan(1);

  // And the two labels say different things, because they are different kinds of limit -- a series
  // that ran out against a ratio carried past what fitted it.
  const said = await page.locator(".chart__beyond-label").allTextContents();
  expect(new Set(said.map((text) => text.trim())).size).toBe(said.length);
});

test("the detectability layer draws, and most of it is not detectable", async ({ page }) => {
  test.setTimeout(90_000);
  const report = await ready(page);
  await explore(page);

  // Off on arrival: a first-time visitor should meet the animals before the epistemology.
  const toggle = page.locator(".explore .layers input").last();
  await expect(toggle).not.toBeChecked();
  await toggle.check();
  await focusOn(page, report, "detectability", "detectability");

  // The finding, asserted through the key the viewer actually reads. If "detectable" were ever
  // the largest share, either the lake changed profoundly or the assessment stopped assessing.
  await expect(page.locator(".explore .key li")).toHaveCount(4);
  const shares = await page.locator(".explore .key em").allTextContents();
  const detectable = Number.parseFloat(shares[0] ?? "0");
  expect(detectable, "nothing is detectable, so the layer is broken").toBeGreaterThan(0);
  expect(detectable, "most of the world is detectable, which is not true").toBeLessThan(50);
});

test("a missing ledger says so rather than showing an empty globe", async ({ page }) => {
  // The old page degraded to a globe with a broken panel, because the layers were the subject.
  // Here the claims are, so there is nothing to carry on with, and the honest failure is to say
  // what happened. Asserted because the alternative -- an unhandled rejection and a blank
  // sphere -- is invisible until it happens in production.
  await page.route("**/findings.json", (route) => route.fulfill({ status: 404, body: "" }));
  const report = await ready(page);
  expect(report.layers.length, "the globe should still have its layers").toBeGreaterThan(0);
  await expect(page.locator(".shell__failure")).toBeVisible();
  await expect(page.locator(".shell__detail")).toContainText("404");
});

/**
 * The README commits to a heap ceiling and a load time. Until this test existed they were
 * aspirations, and a task got opened on the belief that a 2.9 MB layer was blowing the budget
 * when it measured 33.5 MB against 150. Numbers with headroom over what is measured today: the
 * point is to catch a layer that changes the order of magnitude, not to freeze the current
 * figure.
 */
const BUDGET = {
  heapMb: 150,
  /**
   * A pathology guard, not a performance target.
   *
   * Measured at 1.6 s locally and 7.2 s on a shared CI runner with no GPU, against a 4 s ceiling
   * written for the old page -- so the number was mostly measuring the runner, and it failed a deploy
   * for it. The real budget is the heap and the payload bytes, both of which are properties of the
   * build rather than of the machine. This stays only to catch a page that has stopped becoming
   * usable at all.
   */
  readyMs: 20_000,
  /**
   * Compressed bytes of every data payload the page fetches on load, which is what a visitor
   * actually pays. Was measured at 172 KiB when it counted only `layers/`, and that filter let two
   * of the largest payloads through: `taxon-index.json` and `detectability.json` sit at the root,
   * so 978 KiB on disk never reached the gate the budget existed to be. Counting everything is the
   * point -- a ceiling that only watches one directory measures the directory, not the page.
   *
   * Raised from 900 KB when the movement arc landed three track layers (ADRs 0010/0011): measured
   * 1.8 MB with the fox journeys at 812 KiB after one-cell simplification. Two caveats on the
   * number: the preview server does not compress `.geojson`, so those payloads count raw here and
   * gzip to roughly a third in production -- and the ceiling still catches the mistake it exists
   * for, which is a layer arriving an order of magnitude heavier than intended.
   */
  payloadBytesGzipped: 2_500_000,
};

/** Data the page fetches for itself. The basemap is excluded: it is not ours and it is not built. */
const PAYLOAD = /\/(layers\/.*|[^/]+)\.(geojson|json)$/;

test("the published layers stay inside the performance budget", async ({ page }) => {
  // Must outlast its own readyMs ceiling by a clear margin, or the test dies before the assertion
  // it exists to make can fail. Raising that ceiling to 20s while leaving this on Playwright's 30s
  // default made the budget unfalsifiable and still red -- worst of both.
  test.setTimeout(90_000);

  // request.sizes(), not response.body() and not content-length. content-length is absent on
  // the chunked grid responses, so reading the header measured 94 KiB of an 858 KiB payload --
  // and reading the bodies instead made Chromium retain them, which pushed the measured heap
  // from 45 MB to 141 MB. An instrument that perturbs its subject is worse than none.
  const sizes: Promise<[string, number]>[] = [];
  page.on("response", (response) => {
    const url = new URL(response.url());
    if (url.origin !== new URL(page.url() || "http://localhost").origin) return;
    if (!PAYLOAD.test(url.pathname)) return;
    sizes.push(
      response
        .request()
        .sizes()
        .then(({ responseBodySize }): [string, number] => [url.pathname, responseBodySize])
        .catch((): [string, number] => [url.pathname, 0]),
    );
  });

  const started = Date.now();
  const report = await ready(page);
  const readyMs = Date.now() - started;
  await focusOn(page, report, "aerial-passage", "series-aerial-passage");

  // Collect first. usedJSHeapSize counts garbage that simply has not been swept yet, and the
  // same run measured 45 MB and 141 MB on consecutive attempts -- a gate that bimodal fails at
  // random, which is worse than no gate. What the README promises is steady-state retained heap,
  // and that is what a collection makes observable.
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("HeapProfiler.collectGarbage");
  const heapMb = await page.evaluate(() => {
    const memory = (performance as Performance & { memory?: { usedJSHeapSize: number } }).memory;
    return memory ? memory.usedJSHeapSize / 1_048_576 : 0;
  });
  await cdp.detach();

  const measured = await Promise.all(sizes);
  const payloadBytes = measured.reduce((sum, [, bytes]) => sum + bytes, 0);

  expect(report.layers.length, "no layers means the budget proves nothing").toBeGreaterThan(0);
  expect(payloadBytes, "measured no payload bytes, so the budget proves nothing").toBeGreaterThan(
    100_000,
  );
  expect(heapMb, `heap ${heapMb.toFixed(1)} MB`).toBeLessThan(BUDGET.heapMb);
  expect(readyMs, `ready in ${readyMs} ms`).toBeLessThan(BUDGET.readyMs);
  expect(
    payloadBytes,
    `payloads total ${(payloadBytes / 1024).toFixed(0)} KiB compressed:\n` +
      measured
        .sort((a, b) => b[1] - a[1])
        .map(([path, bytes]) => `  ${(bytes / 1024).toFixed(0)} KiB  ${path}`)
        .join("\n"),
  ).toBeLessThan(BUDGET.payloadBytesGzipped);
  // The phase breakdown, not only the total. "ready in N ms" doubled on CI once and named nothing,
  // which cost a bisect to find out that the hatch was 7 ms and the layers were loading one after
  // another. A number you cannot decompose is a number you cannot act on.
  const phases = await page.evaluate(
    () => (window as unknown as { migratlas: { phases: Record<string, number> } }).migratlas.phases,
  );
  const slowest = Object.entries(phases)
    .sort((a, b) => b[1] - a[1])
    .map(([name, ms]) => `${name} ${ms}ms`)
    .join(", ");
  console.log(
    `budget: heap ${heapMb.toFixed(1)} MB, ready ${readyMs} ms, ` +
      `payloads ${(payloadBytes / 1024).toFixed(0)} KiB compressed` +
      `
  phases: ${slowest}`,
  );
});

test("a gridded layer decodes to the cell count its sidecar declares", async ({ page }) => {
  // The grid format is an 8x compaction, which is only safe if it is exact. The Python side
  // pins the encoding; this pins the decoding against the same recorded cell count.
  const report = await ready(page);
  for (const name of ["marine-space-use", "marine-taxa-recorded"]) {
    const meta = await page.request
      .get(`layers/${name}.meta.json`)
      .then((r) => r.json() as Promise<{ cells: number; format: string }>);
    expect(meta.format).toBe("grid");

    const decoded = report.cells[name];
    expect(decoded, `${name} decoded ${decoded} of ${meta.cells} cells`).toBe(meta.cells);
  }
});

test("searching a species draws its own surface", async ({ page }) => {
  // The search box was a stub: thirty hand-listed animals, and selecting one said "no published
  // layer yet". Every index entry now has a per-taxon surface behind it, so a hit that draws
  // nothing means the index and the shards have gone out of step.
  await ready(page);
  await explore(page);

  const index = await page.request
    .get("taxon-index.json")
    .then((r) => r.json() as Promise<{ taxa: { scientific: string; cells: number }[] }>);
  expect(index.taxa.length).toBeGreaterThan(100);

  // The widest-ranging taxon is first, which makes this deterministic.
  const target = index.taxa[0]!;
  await page.locator("#taxon-search").fill(target.scientific.split(" ")[0]!);
  const results = page.locator(".hits button");
  await expect(results.first()).toBeVisible();
  await results.first().click();

  // Choosing a hit flies the camera, and this asserted the draw without waiting for it to land --
  // the same mistake `explore` has a comment about, in a second place. It passes alone and failed
  // in the full suite with the signature that comment describes: visible, source loaded, pointed at,
  // and zero rendered features, because under two WebGL contexts the flight had not finished inside
  // the eight seconds `expectDrawn` polls for.
  await settle(page);
  await expectDrawn(page, "selected-species");
  // Named back to the reader, with the layer it came from: a map that changed for no stated
  // reason is worse than one that did not change.
  await expect(page.locator(".chosen")).toContainText(target.scientific.split(" ")[0]!);
});

test("a species shard is fetched only when a species is chosen", async ({ page }) => {
  // 3,523 marine taxa at one degree are 9.1 MiB in total. Loading that for a search box would
  // blow the budget outright, so shards must stay lazy.
  const shardRequests: string[] = [];
  page.on("request", (request) => {
    if (/species-\d\d\.json/.test(request.url())) shardRequests.push(request.url());
  });

  await ready(page);
  await explore(page);
  await page.locator("#taxon-search").fill("zz-no-such-animal");
  expect(shardRequests, "no shard should load before a selection").toHaveLength(0);
});

test("the default build requests nothing off-origin", async ({ page }) => {
  // The defect this pins: the default basemap used to be Protomaps' demo bucket, which refuses
  // the CORS preflight for ranged requests, so every visitor met a basemap error on a globe with
  // no coastlines. Nothing outside this app may be required to draw the map.
  const external: string[] = [];
  page.on("request", (request) => {
    if (!request.url().startsWith("http://localhost")) external.push(request.url());
  });

  await ready(page);
  // Rendered, but without a camera flight to get there. The arrival view already frames the radar
  // stations, so this layer has drawn by the time the layers report in -- and `focusOn`'s `jumpTo`
  // plus its settle was most of what pushed this test through its 30s deadline once the suite grew
  // past seventy tests. Nothing is given up: in the default build the style carries no `glyphs` and
  // no `sprite`, so there is no off-origin request the *renderer* can make. Every request that could
  // leave this origin -- fonts, the layer JSONs, the bundled basemap -- has already happened, which
  // is exactly what `ready` waits for.
  await expectDrawn(page, "series-aerial-passage");
  expect(external, `off-origin requests: ${external.join(", ")}`).toHaveLength(0);
});

test("the land is hatched, and the hatch tile meets its own edge", async ({ page }) => {
  await ready(page);

  // The hatch is a repeating image rather than a fill colour, because MapLibre draws WebGL from
  // vector data and there is no way to hand a coastline to rough.js. `fill-color` stays underneath
  // it as the fallback for every frame before `addImage` lands.
  const land = await page.evaluate(() => {
    const { map } = (window as unknown as Hook).migratlas;
    return {
      pattern: map.getPaintProperty("land", "fill-pattern"),
      colour: map.getPaintProperty("land", "fill-color"),
      registered: map.hasImage("land-hatch"),
    };
  });
  expect(land.pattern, "the land is not hatched").toBe("land-hatch");
  expect(land.colour, "no fill colour under the pattern to fall back to").toBeTruthy();
  expect(land.registered, "the hatch image never reached the style").toBe(true);

  // And the part that is easy to get wrong and impossible to see: a tiled image has to meet its own
  // opposite edge. The first version rotated the canvas 45 degrees and stepped by a round 8px, which
  // put 8.49 lines in a tile-width and offset the whole family by half a spacing at every seam.
  //
  // Measured rather than argued: the step across the seam, against the largest step anywhere inside
  // the tile. A seamless tile has a seam no worse than its own roughest interior column; a broken
  // one has an outlier there, and that is the whole test.
  const seam = await page.evaluate(() => {
    const image = (window as unknown as Hook).migratlas.map.getImage("land-hatch");
    const { width, height, data } = image!.data as ImageData;
    const at = (x: number, y: number) => data[(y * width + x) * 4]!;
    const between = (left: number, right: number) => {
      let total = 0;
      for (let y = 0; y < height; y += 1) total += Math.abs(at(left, y) - at(right, y));
      return total / height;
    };

    let inside = 0;
    for (let x = 0; x < width - 1; x += 1) inside = Math.max(inside, between(x, x + 1));
    return { across: between(width - 1, 0), inside };
  });

  expect(
    seam.across,
    `the seam steps ${seam.across.toFixed(1)} where the roughest column inside steps ${seam.inside.toFixed(1)}`,
  ).toBeLessThanOrEqual(seam.inside);

  // And the tile's mean is the land colour, not something near it. Same requirement as the paper
  // grain and the same reason: `flavor.ts` records land-against-ocean and the coastline as measured
  // ratios, and a pattern that quietly darkens the land makes every one of those figures describe a
  // colour that is no longer on the screen. The strokes darken, so the ground is lifted by exactly
  // what they take back.
  const tone = await page.evaluate(() => {
    const { map } = (window as unknown as Hook).migratlas;
    const { data } = map.getImage("land-hatch")!.data as ImageData;
    const total = [0, 0, 0];
    for (let index = 0; index < data.length; index += 4) {
      total[0]! += data[index]!;
      total[1]! += data[index + 1]!;
      total[2]! += data[index + 2]!;
    }
    const count = data.length / 4;
    const declared = String(map.getPaintProperty("land", "fill-color"));
    return {
      mean: total.map((sum) => Math.round(sum / count)),
      land: [1, 3, 5].map((at) => Number.parseInt(declared.slice(at, at + 2), 16)),
    };
  });

  for (const [index, channel] of tone.mean.entries()) {
    expect(
      Math.abs(channel! - tone.land[index]!),
      `the hatch averages rgb(${tone.mean.join(" ")}) where the land is rgb(${tone.land.join(" ")})`,
    ).toBeLessThanOrEqual(2);
  }
});

test("the graticule is ruled by hand, bounded, and gone before it could mislead", async ({
  page,
}) => {
  await ready(page);

  const grid = await page.evaluate(() => {
    const { map } = (window as unknown as Hook).migratlas;
    return {
      order: map.getStyle().layers.map((layer) => layer.id),
      opacity: map.getPaintProperty("graticule", "line-opacity"),
    };
  });

  // Over the fill and under the ink, which is where a ruled grid sits on paper.
  expect(grid.order.indexOf("graticule")).toBeGreaterThan(grid.order.indexOf("land"));
  expect(grid.order.indexOf("graticule")).toBeLessThan(grid.order.indexOf("coast"));

  // The honesty constraint, and the reason a wobble is allowed here at all: a graticule is a
  // coordinate claim -- a line that says "this is thirty degrees west" -- so a drawn one is only
  // defensible while nobody can read a position off it. The opacity ramp has to reach zero, and
  // reach it before half a degree is a visible distance.
  const stops = grid.opacity as unknown[];
  const lastStop = Number(stops[stops.length - 2]);
  expect(stops.at(-1), `the graticule never fades out: ${JSON.stringify(stops)}`).toBe(0);
  expect(
    lastStop,
    `still drawn at zoom ${lastStop}, where half a degree is a visible distance`,
  ).toBeLessThanOrEqual(4);

  // And the wobble is bounded rather than merely small-looking. Asserted against the generator
  // rather than through the map, because the geometry is what has to be in bounds and MapLibre keeps
  // a source's data private -- reading it back through `querySourceFeatures` would answer for the
  // facing hemisphere only, which is a different question.
  const source = graticuleSource() as { data: GeoJSON.FeatureCollection };
  const worst: Record<string, number> = { meridian: 0, parallel: 0 };
  for (const feature of source.data.features) {
    const points = (feature.geometry as GeoJSON.LineString).coordinates as [number, number][];
    const lons = points.map(([lon]) => lon);
    const lats = points.map(([, lat]) => lat);
    // A meridian varies in latitude by design and a parallel in longitude, so which axis carries
    // the claim is decided by which one spans the globe.
    const meridian = Math.max(...lats) - Math.min(...lats) > 90;
    const values = meridian ? lons : lats;
    const nominal = Math.round(values.reduce((sum, v) => sum + v, 0) / values.length / 30) * 30;
    const off = Math.max(...values.map((v) => Math.abs(v - nominal)));
    const kind = meridian ? "meridian" : "parallel";
    worst[kind] = Math.max(worst[kind]!, off);
  }

  for (const [kind, off] of Object.entries(worst)) {
    expect(off, `a ${kind} wanders ${off.toFixed(2)} degrees off true`).toBeLessThanOrEqual(0.6);
    expect(off, `a ${kind} does not wander at all, so it is not drawn`).toBeGreaterThan(0.05);
  }
});

test("the drawn coastline is bounded, and hands over to the surveyed one", async ({ page }) => {
  await ready(page);

  const coast = await page.evaluate(() => {
    const { map } = (window as unknown as Hook).migratlas;
    const ids = map.getStyle().layers.map((layer) => layer.id);
    const opacityAt = (layer: string, zoom: number) => {
      const stops = map.getPaintProperty(layer, "line-opacity") as unknown[];
      // The ramp is `interpolate linear zoom z0 v0 z1 v1 ...`; read the pairs off the tail.
      const pairs: [number, number][] = [];
      for (let index = 3; index < stops.length; index += 2) {
        pairs.push([Number(stops[index]), Number(stops[index + 1])]);
      }
      const above = pairs.find(([z]) => z >= zoom) ?? pairs[pairs.length - 1]!;
      const below = [...pairs].reverse().find(([z]) => z <= zoom) ?? pairs[0]!;
      if (above[0] === below[0]) return above[1];
      const share = (zoom - below[0]) / (above[0] - below[0]);
      return below[1] + share * (above[1] - below[1]);
    };
    return {
      ids,
      drawnAt: [0, 1.8, 2.2, 2.6, 4].map((zoom) => opacityAt("coast-drawn", zoom)),
      trueAt: [0, 1.8, 2.2, 2.6, 4].map((zoom) => opacityAt("coast", zoom)),
    };
  });

  // Under the surveyed line, so the accurate one paints over the sketch rather than beneath it.
  expect(coast.ids.indexOf("coast-drawn")).toBeLessThan(coast.ids.indexOf("coast"));

  // The crossfade has to be complementary at every zoom sampled: there is no zoom at which the
  // globe has no coastline, and none at which the drawn one is still up after the surveyed one has
  // arrived. This is the assertion that makes the wobble defensible rather than merely small.
  for (const [index, drawn] of coast.drawnAt.entries()) {
    const surveyed = coast.trueAt[index]!;
    expect(drawn + surveyed, `both coastlines faint together at sample ${index}`).toBeGreaterThan(
      0.85,
    );
  }
  expect(coast.drawnAt.at(-1), "the sketch is still drawn where a reader could measure").toBe(0);
  expect(coast.trueAt.at(-1), "the surveyed coastline never reaches full strength").toBe(1);

  // And the deviation itself, against the real Natural Earth geometry rather than a fixture: every
  // drawn vertex within JITTER of the shore it is a sketch of, and every small island at exactly
  // zero, because a ring half a degree across displaced by half a degree is a different island.
  const land = JSON.parse(
    await readFile("public/basemap/land.geojson", "utf8"),
  ) as GeoJSON.FeatureCollection;
  const drawn = drawnCoast(land);

  const rings: number[][][] = [];
  for (const feature of land.features) {
    const geometry = feature.geometry;
    if (geometry.type === "Polygon") rings.push(...geometry.coordinates);
    else if (geometry.type === "MultiPolygon") rings.push(...geometry.coordinates.flat());
  }

  let worst = 0;
  let untouched = 0;
  let cursor = 0;
  for (const ring of rings.filter((points) => points.length >= 4)) {
    const lons = ring.map(([lon]) => lon!);
    const lats = ring.map(([, lat]) => lat!);
    const small =
      Math.max(...lons) - Math.min(...lons) < MIN_EXTENT &&
      Math.max(...lats) - Math.min(...lats) < MIN_EXTENT;
    for (let pass = 0; pass < (small ? 1 : 2); pass += 1) {
      const stroke = (drawn.features[cursor]!.geometry as GeoJSON.LineString).coordinates;
      expect(stroke.length, "a pass changed the vertex count of its ring").toBe(ring.length);
      let off = 0;
      for (const [index, [lon, lat]] of stroke.entries()) {
        const [trueLon, trueLat] = ring[index] as [number, number];
        off = Math.max(off, Math.abs(lon! - trueLon), Math.abs(lat! - trueLat));
      }
      if (small) {
        expect(off, "a small island was jittered").toBe(0);
        untouched += 1;
      }
      worst = Math.max(worst, off);
      cursor += 1;
    }
  }

  expect(cursor, "the sketch and the survey disagree about how many rings there are").toBe(
    drawn.features.length,
  );
  expect(worst, `a drawn shore is ${worst.toFixed(3)} degrees off true`).toBeLessThanOrEqual(JITTER);
  expect(worst, "nothing wobbled, so nothing was drawn").toBeGreaterThan(0.1);
  expect(untouched, "no island was small enough to be left alone").toBeGreaterThan(0);
});

test("the panel and the map never disagree about what is drawn", async ({ page }) => {
  // A small viewport, and it costs this test nothing: what is asserted is layout properties and
  // checkbox state, neither of which depends on how many pixels MapLibre fills. What it saves is
  // real -- the toggle sweep below switches on the fifty-thousand-cell detectability wash, and at
  // the default 1280x720 that render competes with the other worker's WebGL context hard enough to
  // push `the default build requests nothing off-origin` from 13s through its 30s deadline. The
  // suite runs two workers for exactly this reason; this is the same lesson one test further on.
  await page.setViewportSize({ width: 520, height: 720 });

  await ready(page);
  await explore(page);

  /**
   * Every checkbox against the layer it claims to control.
   *
   * The rows are read in DOM order and matched to the manifest in the same order, which is what
   * `Explore.svelte` renders from -- so a row's index is its layer. Matching by name would need the
   * panel to publish one, and the panel deliberately shows a title.
   */
  const compare = () =>
    page.evaluate(() => {
      const { map, loaded } = (window as unknown as Hook).migratlas;
      const boxes = [...document.querySelectorAll<HTMLInputElement>(".layers input")];
      return loaded.map((layer, index) => {
        const id =
          map
            .getStyle()
            .layers.map((entry) => entry.id)
            .find((entry) => entry === layer.meta.name || entry.endsWith(`-${layer.meta.name}`)) ??
          "";
        return {
          name: layer.meta.name,
          drawn: id ? (map.getLayoutProperty(id, "visibility") ?? "visible") !== "none" : false,
          ticked: boxes[index]?.checked ?? null,
        };
      });
    });

  const onArrival = await compare();
  expect(onArrival.length, "no layers to compare").toBeGreaterThan(0);

  // First load, before anything is touched. This is the state that was wrong: `exploreView` was
  // handed every layer that loaded and switched them all on, including the detectability wash --
  // which declares itself off, covers the whole sphere, and had its box showing unticked while it
  // was drawn over everything else.
  const disagreed = onArrival.filter((layer) => layer.drawn !== layer.ticked);
  expect(
    disagreed.map((l) => `${l.name}: drawn=${l.drawn} ticked=${String(l.ticked)}`),
    "the panel and the map disagree on arrival",
  ).toEqual([]);

  // And the direction the old tests never covered. `every layer draws features once it is switched
  // on` only ever turned things on, so switching one *off* and leaving the map drawing it would have
  // passed -- which is the same class of fault as the one above, in the other direction.
  const rows = page.locator(".layers li");
  for (let index = 0; index < (await rows.count()); index += 1) {
    await rows.nth(index).locator("input").click();
  }
  await expect
    .poll(async () => (await compare()).filter((layer) => layer.drawn !== layer.ticked).length)
    .toBe(0);

  // Every one of them actually moved, or the loop above proved nothing.
  const afterward = await compare();
  for (const [index, layer] of afterward.entries()) {
    expect(layer.ticked, `${layer.name} did not toggle`).not.toBe(onArrival[index]!.ticked);
  }
});

/**
 * The southern surface, and the sign that is the whole point of it.
 *
 * `atlas-no-net-change` was the one claim that flew the camera somewhere and drew nothing, which
 * reads as "there is nothing here" rather than "nothing is exported yet". Now it draws 496 cells of
 * change in recorded taxa -- and a change layer has a failure mode a count layer does not, which is
 * losing the direction on the way to the screen. `paint()` puts a count on `log10`, and log10 of a
 * negative number is NaN, so handing this layer to that path would silently blank every cell that
 * fell. The manifest declares the scale and this asserts the declaration was honoured.
 */
test("the atlas surface draws its losses and its gains apart", async ({ page }) => {
  await ready(page);
  // `ready` returns on the first layer to land, and explore is what loads the rest. Then polled,
  // because a fetch of 496 cells finishing is not the same event as the style having the layer.
  await explore(page);
  await expect
    .poll(
      () =>
        page.evaluate(() =>
          Boolean((window as unknown as Hook).migratlas.map.getLayer("surface-atlas-taxa-change")),
        ),
      { timeout: 20_000 },
    )
    .toBe(true);

  const drawn = await page.evaluate(async () => {
    const { map } = (window as unknown as Hook).migratlas;
    const manifest = (await fetch("layers/manifest.json").then((r) => r.json())) as {
      name: string;
      scale: string;
    }[];
    const entry = manifest.find((one) => one.name === "atlas-taxa-change");
    // From the published grid rather than out of MapLibre's source object: `_data` is private and
    // absent in v6, and what matters is what was *published* anyway.
    const grid = (await fetch("layers/atlas-taxa-change.grid.json").then((r) => r.json())) as {
      v: number[];
    };
    const values = grid.v;
    const { loaded } = (window as unknown as Hook).migratlas;
    return {
      declared: entry?.scale,
      layer: Boolean(map.getLayer("surface-atlas-taxa-change")),
      colour: map.getPaintProperty("surface-atlas-taxa-change", "circle-color"),
      stroke: map.getPaintProperty("surface-atlas-taxa-change", "circle-stroke-width"),
      expanded: loaded.find((one) => one.meta.name === "atlas-taxa-change")?.cells ?? 0,
      cells: values.length,
      losses: values.filter((value) => value < 0).length,
      gains: values.filter((value) => value > 0).length,
      finite: values.every((value) => Number.isFinite(value)),
    };
  });

  expect(drawn.declared, "the manifest no longer declares this layer diverging").toBe("diverging");
  expect(drawn.layer, "the atlas surface never reached the style").toBe(true);
  expect(drawn.cells, "no cells in the published atlas grid").toBeGreaterThan(400);
  expect(drawn.finite, "a cell carries a non-finite value").toBe(true);
  // Every published cell has to survive the grid decode. A mismatch here is the trap
  // `gridToFeatures` throws on, seen from the other side.
  expect(drawn.expanded, "the grid decoded to a different number of cells").toBe(drawn.cells);

  // Both directions are present in the data, so both have to be distinguishable in the paint.
  expect(drawn.losses, "no cells lost taxa, which the surface says is most of them").toBeGreaterThan(
    50,
  );
  expect(drawn.gains, "no cells gained taxa").toBeGreaterThan(10);

  // The colour ramp must read the raw value. `log10` here would mean the sequential painter got it.
  const colour = JSON.stringify(drawn.colour);
  expect(colour, "the change layer is painted on a count's log10 ramp").not.toContain("log10");
  expect(colour, "the ramp does not reach below zero, so a loss cannot be coloured as one").toContain(
    "-",
  );

  // Direction is carried by a second channel as well as by hue: losses are ringed, gains solid.
  // A diverging ramp alone is exactly the comparison a red-green reader cannot make.
  expect(JSON.stringify(drawn.stroke), "losses are not ringed, so direction rests on hue alone")
    .toContain("case");
});
