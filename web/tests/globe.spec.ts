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

test("every layer draws features once it is switched on", async ({ page }) => {
  const report = await ready(page);
  expect(report.layers.length).toBeGreaterThan(0);
  // Each layer gets its own patience, so the test's budget has to cover all of them plus the
  // load. Leaving it at the 30 s default meant the third layer was blamed for the deadline.
  //
  // Widened when the detectability assessment became a fourth layer. It is 50,000 features against
  // the next largest at 29,000, and the run measured 42 s against a 68 s budget -- which passes
  // alone and fails under the whole suite, i.e. exactly the flake that gets re-run rather than
  // fixed. Per-layer allowance rather than a bigger constant, so a fifth layer scales it too.
  test.setTimeout(25_000 + report.layers.length * (DRAW_TIMEOUT_MS + 9000));

  for (const [index, name] of report.layers.entries()) {
    const id = await mapLayerFor(page, name);
    expect(id, `no map layer for entry ${name}`).not.toBe("");

    // Switched on first. Not every layer ships visible -- the detectability assessment starts off
    // deliberately -- and asserting on the arrival state would either fail on that layer or, if
    // the loop simply skipped hidden ones, let a broken layer pass by staying hidden.
    const toggle = page.locator("#layer-list input").nth(index);
    if (!(await toggle.isChecked())) await toggle.check();

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

test("the findings panel publishes a result with its scope and caveat", async ({ page }) => {
  await page.goto("/");
  const panel = page.locator(".panel--findings");
  await expect(panel).toBeVisible();

  // At least one of each: a change, a null, and a limit of the work. A panel showing only the
  // changes would be lying by selection, and the null results here took as much work as the
  // positive one.
  const findings = panel.locator(".finding");
  await expect(findings.first()).toBeVisible();
  for (const direction of ["change", "null", "limit"]) {
    await expect(
      panel.locator(`.finding--${direction}`),
      `no ${direction} finding is published`,
    ).not.toHaveCount(0);
  }

  // Every card states where it holds and what would make it wrong. A number on a globe reads as
  // settled fact, so this is the assertion that stops one being published bare.
  const count = await findings.count();
  for (let index = 0; index < count; index += 1) {
    const card = findings.nth(index);
    await expect(card.locator("dt", { hasText: "Where and when" })).toHaveCount(1);
    await expect(card.locator("dt", { hasText: "Caveat" })).toHaveCount(1);
    await expect(card.locator(".finding__method")).toHaveAttribute("href", /docs\/methods\//);

    // The risk-of-bias assessment, rendered rather than merely present in the JSON. A schema that
    // carries the audit and a panel that does not show it would be worse than not having it: the
    // data would claim an honesty the page does not deliver.
    await expect(
      card.locator(".bias__domain"),
      "a claim is published with no visible risk-of-bias assessment",
    ).not.toHaveCount(0);
    await expect(card.locator(".bias__status").first()).toBeVisible();
  }

  // And at least one `open` status somewhere in the set. Every domain reading "addressed" would
  // mean either that nothing is unresolved -- which is false, the 2012 step is -- or that the
  // assessment is being written to reassure rather than to inform.
  await expect(
    panel.locator(".bias--open"),
    "nothing is marked open, which would mean the audit is decorative",
  ).not.toHaveCount(0);
});

test("the counterfactual draws three lines and states how little they part", async ({ page }) => {
  await page.goto("/");
  const panel = page.locator(".panel--ribbon");
  await expect(panel).toBeVisible();

  // Three lines: observed, without human forcing, and without any warming. Two would leave the
  // reader unable to see how much of the warming the models call natural.
  await expect(panel.locator(".ribbon__line")).toHaveCount(3);
  await expect(panel.locator(".ribbon__line--observed")).toBeVisible();
  await expect(panel.locator(".ribbon__line--counterfactual")).toBeVisible();

  // The year-to-year scatter, which is the reference the divergence has to be judged against. A
  // ribbon showing only the fitted lines would make a 0.89-day gap look like whatever the axis
  // chose to make it look like.
  const years = panel.locator(".ribbon__year");
  await expect(await years.count()).toBeGreaterThan(20);

  // And the number, in words, under the chart. This is the assertion that stops the panel being
  // "fixed" into a dramatic diverging wedge: whatever the drawing does, the size is stated.
  await expect(panel.locator(".ribbon__size")).toContainText(/part by \d+\.\d+ days/);
  await expect(panel.locator(".ribbon__caveat")).toContainText("trend");
  await expect(panel.locator(".finding__method")).toHaveAttribute("href", /docs\/methods\//);
});

test("the counterfactual is drawn to the scatter, not to the gap", async ({ page }) => {
  // The one geometric property worth pinning. If the axis were ever scaled to the divergence, the
  // gap between the two lines would grow to fill the plot -- so it must stay small relative to the
  // spread of the observed points, which is what makes the picture honest about the signal's size.
  await page.goto("/");
  const measured = await page.evaluate(() => {
    const y = (selector: string) => {
      const line = document.querySelector(selector) as SVGLineElement | null;
      return line ? Number(line.getAttribute("y2")) : NaN;
    };
    const dots = [...document.querySelectorAll(".ribbon__year")].map((dot) =>
      Number(dot.getAttribute("cy")),
    );
    return {
      gap: Math.abs(y(".ribbon__line--observed") - y(".ribbon__line--counterfactual")),
      scatter: Math.max(...dots) - Math.min(...dots),
    };
  });
  expect(measured.scatter).toBeGreaterThan(0);
  expect(
    measured.gap / measured.scatter,
    `the two lines part by ${((measured.gap / measured.scatter) * 100).toFixed(0)}% of the ` +
      "observed scatter, which means the axis is scaled to the gap rather than to the data",
  ).toBeLessThan(0.35);
});

test("the detectability layer draws, and most of it is not detectable", async ({ page }) => {
  const report = await ready(page);
  const legend = page.locator(".detectability-legend li");
  await expect(legend).toHaveCount(4);

  // Off on arrival: a first-time visitor should meet the animals before the epistemology.
  const toggle = page.locator("#layer-list input").last();
  await expect(toggle).not.toBeChecked();
  await toggle.check();
  await focusOn(page, report, "detectability", "detectability");

  // The finding, asserted through the legend the viewer actually reads. If "detectable" were ever
  // the largest share, either the lake changed profoundly or the assessment stopped assessing.
  const shares = await page.locator(".detectability-legend em").allTextContents();
  const detectable = Number.parseFloat(shares[0] ?? "0");
  expect(detectable, "nothing is detectable, so the layer is broken").toBeGreaterThan(0);
  expect(detectable, "most of the world is detectable, which is not true").toBeLessThan(50);
});

test("a missing findings file leaves the globe usable", async ({ page }) => {
  // The layers are still worth showing if the findings fail to load, so the panel degrades and
  // the map carries on. Asserted because the alternative -- an unhandled rejection taking the
  // globe down with it -- is invisible until it happens in production.
  await page.route("**/findings.json", (route) => route.fulfill({ status: 404, body: "" }));
  const report = await ready(page);
  expect(report.layers.length).toBeGreaterThan(0);
  await expect(page.locator(".finding__error")).toBeVisible();
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
   * Compressed bytes of every data payload the page fetches on load, which is what a visitor
   * actually pays. Was measured at 172 KiB when it counted only `layers/`, and that filter let two
   * of the largest payloads through: `taxon-index.json` and `detectability.json` sit at the root,
   * so 978 KiB on disk never reached the gate the budget existed to be. Counting everything is the
   * point -- a ceiling that only watches one directory measures the directory, not the page.
   */
  payloadBytesGzipped: 900_000,
};

/** Data the page fetches for itself. The basemap is excluded: it is not ours and it is not built. */
const PAYLOAD = /\/(layers\/.*|[^/]+)\.(geojson|json)$/;

test("the published layers stay inside the performance budget", async ({ page }) => {
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
  console.log(
    `budget: heap ${heapMb.toFixed(1)} MB, ready ${readyMs} ms, ` +
      `payloads ${(payloadBytes / 1024).toFixed(0)} KiB compressed`,
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

  const index = await page.request
    .get("taxon-index.json")
    .then((r) => r.json() as Promise<{ taxa: { scientific: string; cells: number }[] }>);
  expect(index.taxa.length).toBeGreaterThan(100);

  // The widest-ranging taxon is first, which makes this deterministic.
  const target = index.taxa[0]!;
  await page.locator("#taxon-search").fill(target.scientific.split(" ")[0]!);
  const results = page.locator("#taxon-results li");
  await expect(results.first()).toBeVisible();
  await results.first().click();

  await expectDrawn(page, "selected-species");
  // The notice names the layer and carries the generalisation statement with it.
  await expect(page.locator("#notice")).toContainText("occupied cells");
});

test("a species shard is fetched only when a species is chosen", async ({ page }) => {
  // 3,523 marine taxa at one degree are 9.1 MiB in total. Loading that for a search box would
  // blow the budget outright, so shards must stay lazy.
  const shardRequests: string[] = [];
  page.on("request", (request) => {
    if (/species-\d\d\.json/.test(request.url())) shardRequests.push(request.url());
  });

  await ready(page);
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

  const report = await ready(page);
  await focusOn(page, report, "aerial-passage", "series-aerial-passage");
  expect(external, `off-origin requests: ${external.join(", ")}`).toHaveLength(0);
});
