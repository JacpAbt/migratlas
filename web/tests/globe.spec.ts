import { expect, test, type Page } from "@playwright/test";

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

interface ReadyReport {
  basemap: "detail" | "outline";
  layers: string[];
  cells: Record<string, number>;
  centers: Record<string, [number, number]>;
}

interface Hook {
  migratlas: {
    map: maplibregl.Map;
    clock: { set: (patch: object) => void };
    ready: Promise<ReadyReport>;
  };
}

/**
 * Load the app and wait for it to declare its layers added.
 *
 * Relative, not "/?debug=1": a leading slash replaces the whole path of baseURL, which lands on
 * the origin root instead of the project subpath. `vite preview` happens to redirect the root to
 * its base, so an absolute path passes locally and would fetch somebody else's site on Pages.
 */
async function ready(page: Page): Promise<ReadyReport> {
  await page.goto("?debug=1");
  return page.evaluate(() => (window as unknown as Hook).migratlas.ready);
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
  await page.evaluate(
    (at) => (window as unknown as Hook).migratlas.map.jumpTo({ center: at, zoom: 2.2 }),
    center as [number, number],
  );
  await expectDrawn(page, layerId);
}


test("the globe reaches a usable style with coastlines", async ({ page }) => {
  const report = await ready(page);
  expect(report.basemap).toBe("outline");
  await expect(page.locator("#globe canvas")).toBeVisible();
  // Bundled land, so a globe always looks like a globe.
  await expectDrawn(page, "land");
});

test("every manifest layer draws features", async ({ page }) => {
  const report = await ready(page);
  expect(report.layers.length).toBeGreaterThan(0);
  // Each layer gets its own patience, so the test's budget has to cover all of them plus the
  // load. Leaving it at the 30 s default meant the third layer was blamed for the deadline.
  test.setTimeout(20_000 + report.layers.length * (DRAW_TIMEOUT_MS + 4000));

  for (const name of report.layers) {
    const id = await mapLayerFor(page, name);
    expect(id, `no map layer for manifest entry ${name}`).not.toBe("");
    // The assertion the last failure needed: not "the layer exists" but "it drew something".
    await focusOn(page, report, name, id);
  }
});

test("the layer panel publishes its generalisation statement", async ({ page }) => {
  await ready(page);
  // Required, not decorative: published data must never be separable from the terms it was
  // published under.
  await expect(page.locator("#layer-terms")).not.toBeEmpty();

  await page.locator(".maplibregl-ctrl-attrib-button").click();
  await expect(page.locator(".maplibregl-ctrl-attrib-inner")).toContainText("resolution");
});

test("advancing the clock re-times the series layer without rebuilding it", async ({ page }) => {
  const report = await ready(page);
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
  await page.evaluate(() => (window as unknown as Hook).migratlas.clock.set({ day: 250 }));

  await expect.poll(weekIndex).toBe("35");
  expect(before).not.toBe("35");
  await expectDrawn(page, id);
  expect(fetches, "a week change must not refetch the layer").toBe(0);
});

test("a station popup states the caveat with the number", async ({ page }) => {
  const report = await ready(page);
  await focusOn(page, report, "aerial-passage", "series-aerial-passage");

  const point = await page.evaluate(() => {
    const { map } = (window as unknown as Hook).migratlas;
    const feature = map.queryRenderedFeatures({ layers: ["series-aerial-passage"] })[0];
    const coordinates = (feature.geometry as GeoJSON.Point).coordinates as [number, number];
    const { x, y } = map.project(coordinates);
    return { x: Math.round(x), y: Math.round(y) };
  });

  await page.locator("#globe canvas").click({ position: point });
  const popup = page.locator(".maplibregl-popup-content");
  await expect(popup).toContainText("Autumn passage shift");
  // The radar cannot tell a bird from a bat from an insect, so no reading of this layer may
  // omit that.
  await expect(popup).toContainText("aerial biomass, not birds");
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
  readyMs: 4000,
  /**
   * Compressed layer bytes, which is what a visitor actually pays. Measured at 172 KiB for the
   * three published layers -- 858 KiB on disk, served gzipped. Headroom for roughly a tripling.
   */
  layerBytesGzipped: 600_000,
};

test("the published layers stay inside the performance budget", async ({ page }) => {
  // request.sizes(), not response.body() and not content-length. content-length is absent on
  // the chunked grid responses, so reading the header measured 94 KiB of an 858 KiB payload --
  // and reading the bodies instead made Chromium retain them, which pushed the measured heap
  // from 45 MB to 141 MB. An instrument that perturbs its subject is worse than none.
  const sizes: Promise<number>[] = [];
  page.on("response", (response) => {
    if (!/\/layers\/.*\.(geojson|json)$/.test(response.url())) return;
    sizes.push(
      response
        .request()
        .sizes()
        .then(({ responseBodySize }) => responseBodySize)
        .catch(() => 0),
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

  const layerBytes = (await Promise.all(sizes)).reduce((sum, n) => sum + n, 0);

  expect(report.layers.length, "no layers means the budget proves nothing").toBeGreaterThan(0);
  expect(layerBytes, "measured no layer bytes at all, so the budget proves nothing").toBeGreaterThan(
    100_000,
  );
  expect(heapMb, `heap ${heapMb.toFixed(1)} MB`).toBeLessThan(BUDGET.heapMb);
  expect(readyMs, `ready in ${readyMs} ms`).toBeLessThan(BUDGET.readyMs);
  expect(layerBytes, `layers total ${(layerBytes / 1024).toFixed(0)} KiB compressed`).toBeLessThan(
    BUDGET.layerBytesGzipped,
  );
  console.log(
    `budget: heap ${heapMb.toFixed(1)} MB, ready ${readyMs} ms, ` +
      `layers ${(layerBytes / 1024).toFixed(0)} KiB compressed`,
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

test("the default build requests nothing off-origin", async ({ page }) => {
  // The defect this pins: the default basemap used to be Protomaps' demo bucket, which refuses
  // the CORS preflight for ranged requests, so every visitor met a basemap error on a globe with
  // no coastlines. Nothing outside this app may be required to draw the map.
  const external: string[] = [];
  page.on("request", (request) => {
    if (!request.url().startsWith("http://localhost")) external.push(request.url());
  });

  const report = await ready(page);
  await focusOn(page, report, "aerial-passage", "series-aerial-passage");
  expect(external, `off-origin requests: ${external.join(", ")}`).toHaveLength(0);
});
