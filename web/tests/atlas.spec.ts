import { expect, test, type Page } from "@playwright/test";

/**
 * The world chapter's atlas (ADR 0021), asked what it drew.
 *
 * The rule this file inherits from the globe it replaces: a map can look entirely right in the DOM
 * and draw nothing -- the globe once shipped an empty canvas at 60 fps with no error anywhere. So
 * nothing here trusts the page's structure about the map. The stage reports, frame by frame, what it
 * drew (`Drawn` in `lib/atlas/stage.ts`, on `window.migratlas.atlas` under `?debug=1`), and the
 * assertions read that and the canvases' pixels.
 *
 * The words are the build's: every title and lead asserted here is read from `atlas.json`, which
 * `reports/atlas.py` writes, so a changed sentence changes one file.
 *
 * Also here, from the file this was: the counterfactual and ribbon charts, the missing ledger, the
 * payload and heap budget and the off-origin rule. No test reaches the network.
 */

interface Drawn {
  showing: string;
  strokes: number;
  journeys: number;
  herd: number;
  ice: boolean;
  frames: number;
}

interface AtlasHook {
  migratlas?: {
    atlas?: { drawn: Drawn; week: number; day: number; playing: boolean; showing: string };
  };
}

interface Words {
  world: { title: string; lead: string };
  plates: { name: string; button: string; title: string; lead: string; credit: string; map: string }[];
  readout: { herd: { in: string; cells: string } };
  controls: { pause: string; play: string; world: string; show: string };
}

const words = (page: Page): Promise<Words> =>
  page.request.get("atlas.json").then((r) => r.json() as Promise<Words>);

const drawn = (page: Page): Promise<Drawn> =>
  page.evaluate(() => (window as unknown as AtlasHook).migratlas!.atlas!.drawn);

/**
 * Open the world chapter and wait for the atlas to have drawn a few frames.
 *
 * Relative, not "/?debug=1": a leading slash replaces the whole path of baseURL and lands on the
 * origin root instead of the project subpath, which `vite preview` forgives and Pages does not.
 */
async function ready(page: Page): Promise<void> {
  await page.goto("?debug=1#ch=the-world");
  await expect
    .poll(
      () => page.evaluate(() => (window as unknown as AtlasHook).migratlas?.atlas?.drawn.frames ?? 0),
      { timeout: 30_000 },
    )
    .toBeGreaterThan(2);
}

/** Choose a place from the controls' slip, as a reader does. */
async function choose(page: Page, label: string): Promise<void> {
  const flap = page.locator(".flap__grip");
  if ((await flap.count()) > 0 && (await flap.getAttribute("aria-expanded")) !== "true") await flap.click();
  await page.locator(".slip--controls button", { hasText: label }).first().click();
}

/** Arrived: the stage reports the place and no move is under way. */
async function settledOn(page: Page, name: string): Promise<void> {
  await expect
    .poll(
      async () =>
        page.evaluate(
          () =>
            `${(window as unknown as AtlasHook).migratlas?.atlas?.drawn.showing}:${
              document.querySelector(".atlas")?.hasAttribute("data-moving") ? "moving" : "still"
            }`,
        ),
      { timeout: 15_000 },
    )
    .toBe(`${name}:still`);
}

test("the atlas opens on the whole world, every system moving at once", async ({ page }) => {
  await ready(page);
  const said = await words(page);
  await expect(page.locator(".atlas__title")).toHaveText(said.world.title);

  const first = await drawn(page);
  expect(first.showing).toBe("world");
  expect(first.strokes, "no radar strokes on the world view").toBeGreaterThan(0);
  expect(first.journeys, "no fox journeys on the world view").toBeGreaterThan(0);
  expect(first.ice, "no ice edge on the world view").toBe(true);

  // Moving: frames keep coming while nobody touches it.
  await page.waitForTimeout(600);
  expect((await drawn(page)).frames).toBeGreaterThan(first.frames);

  // And the map is ink on the canvas, not an empty sheet a DOM could still look right around.
  const inked = await page.evaluate(() => {
    const sheet = document.querySelector<HTMLCanvasElement>(".atlas .sheet")!;
    const pixels = sheet.getContext("2d")!.getImageData(0, 0, sheet.width, sheet.height).data;
    // Every other pixel with any ink in it: coast, hatching and graticule are thin and partly clear.
    let count = 0;
    for (let i = 3; i < pixels.length; i += 8) if (pixels[i]! > 40) count += 1;
    return count;
  });
  expect(inked, "the world's map drew nothing").toBeGreaterThan(1000);
});

test("every place has a plate, and choosing one draws that system alone", async ({ page }) => {
  test.setTimeout(90_000);
  const maps: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("basemap/plates/")) maps.push(new URL(request.url()).pathname);
  });
  await ready(page);
  const said = await words(page);
  expect(said.plates.length).toBe(4);

  for (const plate of said.plates) {
    await choose(page, plate.button);
    await settledOn(page, plate.name);
    await expect(page.locator(".atlas__title")).toHaveText(plate.title);
    await expect(page.locator(".slip--caption strong")).toHaveText(plate.lead);
    await expect(page.locator(".slip--caption")).toContainText(plate.credit);
    await page.waitForTimeout(400);
    const now = await drawn(page);
    expect(now.ice, `${plate.name} still draws the world's ice`).toBe(false);
    if (plate.name === "north-america") {
      expect(now.strokes).toBeGreaterThan(0);
      expect(now.journeys).toBe(0);
    } else if (plate.name === "bylot") {
      expect(now.journeys).toBeGreaterThan(0);
      expect(now.strokes).toBe(0);
    } else {
      expect(now.herd, `${plate.name} drew no range`).toBeGreaterThan(0);
      expect(now.strokes + now.journeys).toBe(0);
    }
  }
  // Each plate's own map, fetched when it was chosen and not before.
  expect(maps.map((path) => path.split("/").pop())).toEqual(said.plates.map((p) => `${p.name}.geojson`));
});

test("between two plates the camera flies, and the world's callouts never show", async ({ page }) => {
  await ready(page);
  const said = await words(page);
  const [night, foxes] = said.plates;
  await choose(page, night!.button);
  await settledOn(page, night!.name);

  // Sampled through the move: the callouts belong to the world view, and a move that stopped at the
  // world on its way would show them.
  await choose(page, foxes!.button);
  let most = 0;
  for (let i = 0; i < 40; i++) {
    const shown = await page.evaluate(() => Number(getComputedStyle(document.querySelector(".atlas__callouts")!).opacity));
    most = Math.max(most, shown);
    await page.waitForTimeout(60);
  }
  expect(most, "the callouts showed during a move between two plates").toBeLessThan(0.1);
  await settledOn(page, foxes!.name);
});

test("the clock runs, stops when asked, and is in the address", async ({ page }) => {
  await ready(page);
  const said = await words(page);
  const run = page.locator(".slip--controls .row button").first();
  await expect(run).toHaveText(said.controls.pause);
  await run.click();
  await expect(run, "the clock stopped and the button still says pause").toHaveText(said.controls.play);

  const week = () => page.evaluate(() => (window as unknown as AtlasHook).migratlas!.atlas!.week);
  const stopped = await week();
  await page.waitForTimeout(500);
  expect(await week()).toBe(stopped);

  // The keyboard moves it a week, and the address follows.
  const before = new URLSearchParams((await page.evaluate(() => location.hash)).slice(1)).get("d");
  await page.locator(".atlas__clock svg").focus();
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  expect(Math.round((await week()) - stopped)).toBe(2);
  await expect
    .poll(async () => new URLSearchParams((await page.evaluate(() => location.hash)).slice(1)).get("d"))
    .not.toBe(before);
});

test("with reduced motion, a choice is a cut rather than a flight", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await ready(page);
  const said = await words(page);
  const herd = said.plates.find((p) => p.name === "svalbard")!;
  await choose(page, herd.button);
  await expect(page.locator(".atlas")).not.toHaveAttribute("data-moving", "");
  await settledOn(page, herd.name);
  expect(await page.evaluate(() => (window as unknown as AtlasHook).migratlas!.atlas!.playing)).toBe(false);
});

test("a herd's readout counts cells, never animals", async ({ page }) => {
  await ready(page);
  const said = await words(page);
  await choose(page, said.plates.find((p) => p.name === "ya-ha-tinda")!.button);
  await settledOn(page, "ya-ha-tinda");
  const readout = page.locator(".atlas__what");
  await expect(readout).toContainText(said.readout.herd.in);
  await expect(readout).toContainText(said.readout.herd.cells);
});

test("the atlas takes no pointer meant for the page, and a turning page carries its still", async ({
  page,
}) => {
  await ready(page);
  for (const sheet of await page.locator(".atlas .sheet").all()) {
    expect(await sheet.evaluate((node) => getComputedStyle(node).pointerEvents)).toBe("none");
  }
  await page.locator('.spread > .page--verso [data-turn="back"]').click();
  const still = page.locator(".leaf .world__still, .stale .world__still").first();
  await expect(still).toBeAttached();
  expect(await still.getAttribute("src")).toMatch(/^data:image\/png/);
});

test("turning onto the atlas for the first time, the incoming page carries it", async ({ page }) => {
  // The defect this pins: the still was only taken as the atlas was left, so on a first visit the
  // incoming page on the leaf was blank paper over the atlas's half for the length of the turn.
  await ready(page);
  await page.locator('.spread > .page--verso [data-turn="back"]').click();
  await expect(page.locator(".leaf")).toHaveCount(0);
  const before = await page.evaluate(() => location.hash);

  // A fresh document on the spread before, so nothing is left of the atlas from this one.
  await page.goto("about:blank");
  await page.goto(`?debug=1${before}`);
  await expect(page.locator(".atlas")).toHaveCount(0);

  // The leaf lives for one turn, about a second: watched rather than polled.
  await page.evaluate(() => {
    const seen = { still: false };
    (window as unknown as { seen: typeof seen }).seen = seen;
    new MutationObserver(() => {
      const img = document.querySelector<HTMLImageElement>(".leaf .leaf__back .world__still");
      if (img?.src.startsWith("data:image/png")) seen.still = true;
    }).observe(document.body, { subtree: true, childList: true, attributes: true });
  });
  await page.locator('.spread > .page--recto [data-turn="on"]').click();
  await expect(page.locator(".leaf")).toHaveCount(0);
  expect(
    await page.evaluate(() => (window as unknown as { seen: { still: boolean } }).seen.still),
    "the incoming page turned blank over the atlas",
  ).toBe(true);
});

test("the atlas's data is fetched before the reader reaches it, and not from the front door", async ({
  page,
}) => {
  // The defect this pins: the data was fetched when the atlas mounted, which is when the page turns
  // onto it, so on a slow connection both halves of the spread were paper under the turning leaf.
  const asked: string[] = [];
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/atlas.json") || path.endsWith("/bylot-journeys.geojson")) asked.push(path.split("/").pop()!);
  });

  await page.goto("?debug=1");
  await expect(page.locator(".spread")).toBeVisible();
  await page.waitForTimeout(1500);
  expect(asked, "the front door fetched the atlas's data").toEqual([]);

  // A pointer on the atlas's tab is a reader who may be about to go there.
  await page.locator(".tabs .tab").last().hover();
  await expect.poll(() => asked.length, { message: "pointing at the atlas's tab fetched nothing" }).toBe(2);

  // A fresh document on the spread before the atlas: fetched without a turn, the atlas not mounted.
  await page.goto("?debug=1#ch=the-world");
  await page.locator('.spread > .page--verso [data-turn="back"]').click();
  await expect(page.locator(".leaf")).toHaveCount(0);
  const before = await page.evaluate(() => location.hash);
  await page.goto("about:blank");
  asked.length = 0;
  await page.goto(`?debug=1${before}`);
  await expect.poll(() => asked.length, { message: "the spread before the atlas fetched nothing" }).toBe(2);
  await expect(page.locator(".atlas")).toHaveCount(0);

  // And arriving fetches none of it again: the atlas is handed what was already asked for.
  await page.locator('.spread > .page--recto [data-turn="on"]').click();
  await expect
    .poll(() => page.evaluate(() => (window as unknown as AtlasHook).migratlas?.atlas?.drawn.frames ?? 0))
    .toBeGreaterThan(2);
  expect(asked.sort()).toEqual(["atlas.json", "bylot-journeys.geojson"]);
});

test("the atlas follows the paper it is read on", async ({ page }) => {
  await ready(page);
  /** The mean brightness of the world map's ink: dark on day paper, light on night paper. */
  const ink = () =>
    page.evaluate(() => {
      const sheet = document.querySelector<HTMLCanvasElement>(".atlas .sheet")!;
      const pixels = sheet.getContext("2d")!.getImageData(0, 0, sheet.width, sheet.height).data;
      let sum = 0;
      let n = 0;
      for (let i = 0; i < pixels.length; i += 4 * 8) {
        if (pixels[i + 3]! < 160) continue;
        sum += (pixels[i]! + pixels[i + 1]! + pixels[i + 2]!) / 3;
        n += 1;
      }
      return n ? sum / n : -1;
    });
  await page.locator(".surface").getByRole("radio", { name: "Day", exact: true }).check();
  await expect.poll(ink, { timeout: 10_000 }).toBeLessThan(110);
  await page.locator(".surface").getByRole("radio", { name: "Night", exact: true }).check();
  await expect.poll(ink, { message: "the paper turned and the ink did not", timeout: 10_000 }).toBeGreaterThan(140);
});

test("the atlas's words are written in the marker face, never typed", async ({ page }) => {
  // Moved here from the face test in `notebook.spec.ts`, which walks the pages: the atlas's words sit
  // on the spread over the pages rather than on one.
  await ready(page);
  const token = (name: string) =>
    page.evaluate((n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim(), name);
  const body = await token("--font-body");
  const mono = await token("--font-mono");
  for (const selector of [".slip--caption", ".slip--controls button", ".atlas__clock text"]) {
    const face = await page.locator(selector).first().evaluate((node) => getComputedStyle(node).fontFamily);
    expect(face, `${selector} is not in the marker face`).toContain(body.split(",")[0]!.replace(/["']/g, ""));
    expect(face, `${selector} is typed`).not.toContain(mono.split(",")[0]!.replace(/["']/g, ""));
  }
});

test("on a phone the world is one leaf, the atlas on it, its words in the flap", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await ready(page);
  await expect(page.locator(".atlas--leaf")).toBeVisible();
  const said = await words(page);
  const grip = page.locator(".flap__grip");
  await expect(grip).toHaveAttribute("aria-expanded", "false");
  await grip.click();
  await expect(page.locator(".slip--controls")).toBeInViewport();
  const foxes = said.plates.find((p) => p.name === "bylot")!;
  await page.locator(".slip--controls button", { hasText: foxes.button }).first().click();
  await settledOn(page, foxes.name);
  expect((await drawn(page)).journeys).toBeGreaterThan(0);
});

test("each counterfactual is drawn to the scatter, and both to one frame", async ({
  page,
}) => {
  // The two geometric properties worth pinning, measured off the rendered SVG rather than the source
  // numbers, because it is the pixels that would lie.
  //
  // Scaled to the gap, the divergence would grow to fill the plot. And scaled *per chart*, DAMIP's
  // 0.89-day gap and ATTRICI's 0.29-day gap would render the same height -- so the reader would see
  // two counterfactuals agreeing where the whole finding is that they do not.
  await ready(page);
  /*
    One chart to a page: `figures.ts` gives the ribbon four, because two charts on one overflowed it
    by 536px. So the pair is read by visiting both leaves, which is the same comparison the frame
    argument below needs -- each drawn to its own extents would make a 0.89-day gap and a 0.29-day
    gap render the same height.
  */
  const geometryOf = () =>
    page.locator(".chart__svg").evaluateAll((nodes) =>
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
          gap: Math.abs(
            y(".chart__line--observed") - y(".chart__line--counterfactual"),
          ),
          scatter: Math.max(...dots) - Math.min(...dots),
          ticks: ticks.join(","),
        };
      }),
    );

  const charts: Awaited<ReturnType<typeof geometryOf>> = [];
  for (const at of [0, 1, 2, 3]) {
    await page.goto(`?debug=1#ch=why-it-changed&p=${at}`);
    await expect(page.locator(".book")).toBeVisible();
    if ((await page.locator(".chart__svg").count()) === 0) continue;
    charts.push(...(await geometryOf()));
  }

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
  expect(
    new Set(gaps).size,
    `both gaps render at ${gaps[0]}px`,
  ).toBeGreaterThan(1);
});

test("no ribbon is drawn past its own frame, and each shades where its evidence stops", async ({
  page,
}) => {
  // Three things I found by looking at a screenshot rather than by a failing test, which is why they
  // are here: a label that printed past the SVG's right edge, a leader that crossed the shaded years
  // as a straight diagonal and read as the line continuing through them, and only one of the two
  // charts shading at all -- which told a reader DAMIP carried evidence to 2025 when `f` is fitted to
  // 2014. Eyes do not run in CI.
  // Across the pair's two leaves, for the reason the test above gives: one chart to a page.
  const readChart = () =>
    page.locator(".chart__svg").evaluateAll((nodes) =>
      nodes.map((node) => {
        const box = (node as unknown as SVGSVGElement).viewBox.baseVal;
        const labels = [
          ...node.querySelectorAll<SVGTextElement>(
            ".chart__label, .chart__rate",
          ),
        ];
        return {
          overflowing: labels
            .filter(
              (label) => label.getBBox().x + label.getBBox().width > box.width,
            )
            .map((label) => label.textContent?.trim()),
          // The plot's right edge, so a band can be told apart from no band at all.
          band:
            node.querySelector<SVGRectElement>(".chart__beyond")?.x.baseVal
              .value ?? null,
          lineEnds: [
            ...node.querySelectorAll<SVGLineElement>(".chart__line"),
          ].map((line) => Math.round(line.x2.baseVal.value)),
        };
      }),
    );

  const measured: Awaited<ReturnType<typeof readChart>> = [];
  for (const at of [0, 1, 2, 3]) {
    await page.goto(`?debug=1#ch=why-it-changed&p=${at}`);
    await expect(page.locator(".book")).toBeVisible();
    if ((await page.locator(".chart__svg").count()) === 0) continue;
    measured.push(...(await readChart()));
  }

  for (const chart of measured) {
    expect(
      chart.overflowing,
      "labels printing past the chart's own box",
    ).toEqual([]);
    // Both lines in a ribbon end at the same x -- its window's end. One reaching further would be a
    // counterfactual drawn over years its own method never saw.
    expect(new Set(chart.lineEnds).size).toBe(1);
  }

  // Every chart declares where its attribution stops, and they stop in different places: DAMIP's
  // share is fitted to 2014, ATTRICI's counterfactual series ends in 2019.
  const bands = measured.map((chart) => chart.band);
  expect(
    bands.every((band) => band !== null),
    "a chart with no limit drawn",
  ).toBe(true);
  expect(
    new Set(bands).size,
    "both charts shade from the same year",
  ).toBeGreaterThan(1);

  // And the two labels say different things, because they are different kinds of limit -- a series
  // that ran out against a ratio carried past what fitted it.
  const said = await page.locator(".chart__beyond-label").allTextContents();
  expect(new Set(said.map((text) => text.trim())).size).toBe(said.length);
});


test("a missing ledger says so rather than leaving a blank page", async ({
  page,
}) => {
  /*
    The old shell degraded to a globe with a broken panel, because layers were its subject. The
    book's subject is the claims, so there is nothing to carry on with -- and this test's own reason
    for existing turned out to describe what the book did when it became the front door: `main.ts`
    awaited the ledger and rejected unhandled, which is a blank page and no message. Invisible until
    it happens in production, exactly as written here before it happened.

    So the assertion changed shape and kept its point: the failure is *stated*. There is no
    half-working page to check, which is the honest outcome rather than a lesser one.
  */
  await page.route("**/findings.json", (route) =>
    route.fulfill({ status: 404, body: "" }),
  );
  await page.goto("?debug=1#ch=the-world");

  const notice = page.locator(".boot-failure");
  await expect(notice).toBeVisible();
  await expect(notice).toContainText(/did not load/i);
  // The reason, not just the refusal: an unexplained failure cannot be diagnosed.
  await expect(notice.locator(".boot-failure__detail")).toContainText("404");

  // And nothing pretending to be a book.
  await expect(page.locator(".book, .leaves")).toHaveCount(0);
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
   *
   * Raised again at 2498 KiB measured, when two honest growths landed together: the green wave
   * (226 KiB, the 10th layer) and the herd surfaces recovering the ~40% of their cells a label
   * collision had been silently merging. Same caveats as above.
   */
  payloadBytesGzipped: 3_000_000,
};

/** Data the page fetches for itself. The basemap is excluded: it is not ours and it is not built. */
const PAYLOAD = /\/(layers\/.*|[^/]+)\.(geojson|json)$/;

test("the published layers stay inside the performance budget", async ({
  page,
}) => {
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
        .then(({ responseBodySize }): [string, number] => [
          url.pathname,
          responseBodySize,
        ])
        .catch((): [string, number] => [url.pathname, 0]),
    );
  });

  const started = Date.now();
  await ready(page);
  const readyMs = Date.now() - started;

  // Collect first. usedJSHeapSize counts garbage that simply has not been swept yet, and the
  // same run measured 45 MB and 141 MB on consecutive attempts -- a gate that bimodal fails at
  // random, which is worse than no gate. What the README promises is steady-state retained heap,
  // and that is what a collection makes observable.
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("HeapProfiler.collectGarbage");
  const heapMb = await page.evaluate(() => {
    const memory = (
      performance as Performance & { memory?: { usedJSHeapSize: number } }
    ).memory;
    return memory ? memory.usedJSHeapSize / 1_048_576 : 0;
  });
  await cdp.detach();

  const measured = await Promise.all(sizes);
  const payloadBytes = measured.reduce((sum, [, bytes]) => sum + bytes, 0);

  expect((await drawn(page)).frames, "nothing drawn means the budget proves nothing").toBeGreaterThan(0);
  expect(
    payloadBytes,
    "measured no payload bytes, so the budget proves nothing",
  ).toBeGreaterThan(100_000);
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

test("the default build requests nothing off-origin", async ({ page }) => {
  // The defect this pins: the default basemap used to be Protomaps' demo bucket, which refused the
  // CORS preflight for ranged requests, so every visitor met a basemap error on a globe with no
  // coastlines. Nothing outside this app may be required to draw the map -- the world's outline, a
  // plate's own map and every layer are served from here.
  const external: string[] = [];
  page.on("request", (request) => {
    if (!request.url().startsWith("http://localhost")) external.push(request.url());
  });
  await ready(page);
  const said = await words(page);
  await choose(page, said.plates[0]!.button);
  await settledOn(page, said.plates[0]!.name);
  expect(external, `off-origin requests: ${external.join(", ")}`).toHaveLength(0);
});
