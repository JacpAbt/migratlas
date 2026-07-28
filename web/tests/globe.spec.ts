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
}

interface Hook {
  migratlas: {
    map: maplibregl.Map;
    clock: { set: (patch: object) => void };
    ready: Promise<ReadyReport>;
  };
}

/** Load the app and wait for it to declare its layers added. */
async function ready(page: Page): Promise<ReadyReport> {
  await page.goto("/?debug=1");
  return page.evaluate(() => (window as unknown as Hook).migratlas.ready);
}

/** How many features the last frame actually drew for a layer. */
const rendered = (page: Page, layer: string): Promise<number> =>
  page.evaluate(
    (id) => (window as unknown as Hook).migratlas.map.queryRenderedFeatures({ layers: [id] }).length,
    layer,
  );

/**
 * Assert a layer draws, polling rather than waiting on a single event.
 *
 * `queryRenderedFeatures` answers for the last completed frame, and MapLibre's `idle` does not
 * reliably fire on a map with no tile sources — so the honest primitive is to keep asking.
 */
async function expectDrawn(page: Page, layer: string): Promise<void> {
  await expect
    .poll(() => rendered(page, layer), { message: `${layer} never drew a feature`, timeout: 15_000 })
    .toBeGreaterThan(0);
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
 * legitimately invisible from the default view. The centroid comes from the published file
 * rather than from MapLibre's internals, so the helper cannot break on a library refactor.
 */
async function focusOn(page: Page, name: string, layerId: string): Promise<void> {
  const collection = await page
    .request.get(`/layers/${name}.geojson`)
    .then((response) => response.json() as Promise<GeoJSON.FeatureCollection>);

  const points = collection.features
    .map((feature) => feature.geometry)
    .filter((geometry): geometry is GeoJSON.Point => geometry.type === "Point")
    .map((geometry) => geometry.coordinates);
  const mean = (index: number): number =>
    points.reduce((sum, point) => sum + point[index], 0) / points.length;

  await page.evaluate(
    ({ center }) => (window as unknown as Hook).migratlas.map.jumpTo({ center, zoom: 2.2 }),
    { center: [mean(0), mean(1)] as [number, number] },
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

  for (const name of report.layers) {
    const id = await mapLayerFor(page, name);
    expect(id, `no map layer for manifest entry ${name}`).not.toBe("");
    // The assertion the last failure needed: not "the layer exists" but "it drew something".
    await focusOn(page, name, id);
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
  await ready(page);
  const id = "series-aerial-passage";
  await focusOn(page, "aerial-passage", id);

  // The week lives inside the filter expression, which is the whole point of the design: the
  // clock moves an index, it never touches the source.
  const weekIndex = (): Promise<string> =>
    page.evaluate((layer) => {
      const filter = (window as unknown as Hook).migratlas.map.getFilter(layer);
      return JSON.stringify(filter).match(/"at",(\d+)/)?.[1] ?? "";
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
  await ready(page);
  await focusOn(page, "aerial-passage", "series-aerial-passage");

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

test("the default build requests nothing off-origin", async ({ page }) => {
  // The defect this pins: the default basemap used to be Protomaps' demo bucket, which refuses
  // the CORS preflight for ranged requests, so every visitor met a basemap error on a globe with
  // no coastlines. Nothing outside this app may be required to draw the map.
  const external: string[] = [];
  page.on("request", (request) => {
    if (!request.url().startsWith("http://localhost")) external.push(request.url());
  });

  await ready(page);
  await focusOn(page, "aerial-passage", "series-aerial-passage");
  expect(external, `off-origin requests: ${external.join(", ")}`).toHaveLength(0);
});
