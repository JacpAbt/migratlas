/**
 * The reader: what a visitor is told, what they can reach from it, and what they cannot.
 *
 * Was `shell.spec.ts` and was about the arrival's three modes. The book replaced those modes with
 * pages, and the owner's instruction was to move these tests rather than delete them with the
 * component -- so every assertion here is the same assertion, aimed at where its subject went. The
 * ones with no subject left say so in their own comment rather than disappearing.
 *
 * Moving them was worth it twice before a single one was re-pointed: both roads between a claim and
 * the one animal that carries its argument were dead in the book, silently, because `Reader` passed
 * `Claim` no `onspecimen` and `species/Study.svelte` still linked to the shell's `#c=` address.
 */

import { readFileSync } from "node:fs";

import { expect, test, type Page } from "@playwright/test";

import type { Panel, Spread } from "../src/lib/book/pages";

/** The size the book is designed at, for the reason `notebook.spec.ts` gives at length. */
test.use({ viewport: { width: 1600, height: 900 } });

/** The book's own pagination, computed from the same module and documents the book uses. */
async function layout(): Promise<readonly Spread[]> {
  const { spreadsOf } = await import("../src/lib/book/pages");
  const read = (name: string) => JSON.parse(readFileSync(`public/${name}`, "utf8"));
  return spreadsOf({
    findings: read("findings.json").findings,
    introduction: read("introduction.json"),
    safeguards: read("sandbox.json"),
    dial: read("response.json"),
  });
}

/** The address of the first spread carrying a panel that matches. */
function addressOf(spreads: readonly Spread[], match: (panel: Panel) => boolean): string {
  const spread = spreads.find((one) => match(one.verso) || match(one.recto));
  if (!spread) throw new Error("no spread carries that panel");
  return `#ch=${spread.chapter.slug}&p=${spread.at}`;
}

/**
 * The spread carrying a panel, and which side of it the panel is on.
 *
 * Needed once a figure's two pages face each other: both halves of the coverage assessment render a
 * `section.coverage`, so a selector that does not name a leaf resolves to two elements and Playwright
 * refuses it -- correctly. Which side is `pages.ts`'s business, so it is asked rather than assumed.
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

/** One claim's plain-register page. */
async function claimPage(page: Page, key: string): Promise<void> {
  const spreads = await layout();
  await open(page, addressOf(spreads, (panel) => panel.kind === "finding" && panel.key === key));
}

/** One claim's record page, where the number and the specimen invitation are. */
/**
 * The page carrying a claim's figure -- its plate, its chart or its assessment.
 *
 * Its own helper because it is no longer the leaf facing the claim. The plain-method page sits
 * between them, so the figure moved to the next spread and changed sides with it, and six tests here
 * were reaching for `.page--recto .plate` on the spread the claim is on. Addressed by kind, like the
 * claim and the record beside it, so the next page inserted anywhere moves nothing here.
 */
async function figurePage(page: Page, key: string): Promise<void> {
  const spreads = await layout();
  await open(page, addressOf(spreads, (panel) => panel.kind === "figure" && panel.key === key));
}

async function recordPage(page: Page, key: string): Promise<void> {
  const spreads = await layout();
  await open(page, addressOf(spreads, (panel) => panel.kind === "record" && panel.key === key));
}

/**
 * A claim's safeguard or dial page, by index.
 *
 * `pages.ts` gives each knob and each refusal a page of its own, because three safeguard knobs came
 * to 1,306px against an 826px page. So a test that used to read a whole panel under a claim opens
 * the leaf carrying the part it is about.
 */
async function knobPage(
  page: Page,
  key: string,
  doc: "safeguards" | "dial",
  part: "knobs" | "refusals" = "knobs",
  at = 0,
): Promise<void> {
  const spreads = await layout();
  await open(
    page,
    addressOf(
      spreads,
      (panel) =>
        panel.kind === "panel" &&
        panel.key === key &&
        panel.doc === doc &&
        panel.part === part &&
        panel.at === at,
    ),
  );
}

/**
 * The page carrying the knob that asks a particular question.
 *
 * One knob to a page, so a test about one of them has to find which page it is on. Walked rather
 * than indexed: the order comes from `sandbox.json` and a test that hard-coded a position would pass
 * while pointing at a different safeguard.
 */
async function knobOf(page: Page, key: string, asks: RegExp): Promise<void> {
  const spreads = await layout();
  const pages = spreads.flatMap((one) =>
    [one.verso, one.recto].flatMap((panel) =>
      panel.kind === "panel" && panel.key === key && panel.part === "knobs"
        ? [`#ch=${one.chapter.slug}&p=${one.at}`]
        : [],
    ),
  );
  for (const address of pages) {
    await open(page, address);
    if ((await page.locator(".knob").filter({ hasText: asks }).count()) > 0) return;
  }
  throw new Error(`no page carries a knob asking ${String(asks)}`);
}

/** The page carrying the refusal that answers a particular question. */
async function refusalOf(page: Page, key: string, asks: RegExp): Promise<void> {
  const spreads = await layout();
  const pages = spreads.flatMap((one) =>
    [one.verso, one.recto].flatMap((panel) =>
      panel.kind === "panel" && panel.key === key && panel.part === "refusals"
        ? [`#ch=${one.chapter.slug}&p=${one.at}`]
        : [],
    ),
  );
  for (const address of pages) {
    await open(page, address);
    if ((await page.locator(".refusal").filter({ hasText: asks }).count()) > 0) return;
  }
  throw new Error(`no page carries a refusal about ${String(asks)}`);
}

/** Open a page of the book. `?debug` so the world chapter's map is readable. */
async function open(page: Page, hash = ""): Promise<void> {
  await page.goto(`?debug=1${hash}`);
  await expect(page.locator(".book, .leaves")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
}

/** The world chapter, which is where the map, the layers, the clock and the search live. */
async function explore(page: Page): Promise<void> {
  await open(page, "#ch=the-world");
  // Thirty seconds, for the reason `notebook.spec.ts`'s own world helper states at length: this
  // waits on a WebGL context and ten layers, and the default five is a number about DOM latency.
  await expect(page.locator(".explore")).toBeVisible({ timeout: 30_000 });
  await expect(page.locator(".globe canvas")).toBeVisible({ timeout: 30_000 });
  /*
    And the layers, which arrive after the canvas does. The debug hook is published once every one of
    them has loaded, so its existence is the load-complete signal -- the same one `globe.spec.ts`
    uses and for the same reason: counting them by hand went stale the day the ice layer landed.
  */
  await page.waitForFunction(
    () => !!(window as unknown as { migratlas?: { loaded?: unknown[] } }).migratlas?.loaded?.length,
    undefined,
    { timeout: 30_000 },
  );
}

/**
 * How long to keep asking whether the camera has arrived.
 *
 * Polled, never slept. The flight is 2.2s and the layers load asynchronously before it starts, so a
 * one-shot read after a fixed wait passes alone and fails under the whole suite -- which is the flake
 * that gets re-run rather than fixed. Two of these tests did exactly that.
 */
const SETTLE_MS = 15_000;

/**
 * Where a visitor lands.
 *
 * The arrival card was an interstitial with three doors; the book puts the reader on a claim's own
 * page instead, which is the same decision ADR 0007 made -- a claim first -- reached without a card.
 * Relative, never a leading slash: that replaces the whole path of baseURL and lands on the origin
 * root rather than the project subpath, which is the trap the globe suite documents.
 */
async function arrive(page: Page): Promise<void> {
  await open(page);
  await expect(page.locator(".claim").first()).toBeVisible();
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

  /*
    The claim, why it matters and its caveat, on the page a visitor lands on -- and the number one
    leaf away rather than on the same screen. That is the one thing this test used to assert that the
    book does differently, and it is a deliberate difference: the arrival card had to carry
    everything because there was nowhere else, while pagination gave the plain register a page and
    the measurement its own. What has not changed is that neither is behind a click that hides it:
    turning one page is not the same as opening a disclosure, and the guard against a *hidden*
    number is the one below, which reads it.
  */
  await expect(page.locator(".claim__title")).not.toBeEmpty();
  await expect(page.locator(".claim__matters")).not.toBeEmpty();
  await expect(page.locator(".claim__short-caveat")).not.toBeEmpty();

  // The heading is the plain register, and it must not have gained a taxon the instrument cannot
  // see. This is the one sentence most likely to be quoted, and the radar measures aerial biomass.
  await expect(page.locator(".claim__title")).not.toHaveText(/\bbirds?\b/i);

  // The number, with its interval, one turn away and not behind anything.
  const { ARRIVAL_KEY } = await import("../src/lib/story");
  await recordPage(page, ARRIVAL_KEY);
  await expect(page.locator(".claim__value")).toHaveText(/[−-]?\d+\.\d+/);
  await expect(page.locator(".claim__caveat")).not.toBeEmpty();

  /*
    And the plate marks the claim's own ground. This replaces "the globe is live behind the card",
    which was the only reason to put a card on a globe -- the book answers the same question with a
    drawn plate per claim, and `story.ts`'s camera is what places the mark, so the assertion is that
    the figure is about *this* claim rather than a decoration.
  */
  await figurePage(page, ARRIVAL_KEY);
  // Either leaf: which side a panel lands on is `pages.ts`'s business, and a direct child of the
  // spread is what excludes the turning leaf's copy -- which was the only reason to name a side.
  await expect(page.locator(".spread > .page .plate .ink-here")).toHaveCount(1);
});

test("asking how we know is a page turn, not a disclosure", async ({ page }) => {
  /*
    The arrival asked the question with a button. The book answers it by turning: the plain register,
    then the figure, then the number with its scope and caveat, then how it could be wrong -- which
    is the order the owner asked for. What this test is for has not moved: the audit is reachable,
    it is not behind a control, and no interstitial stands between a reader and it.
  */
  const { ARRIVAL_KEY } = await import("../src/lib/story");
  await claimPage(page, ARRIVAL_KEY);
  await expect(page.locator(".claim__title")).toBeVisible();

  const spreads = await layout();
  await open(
    page,
    addressOf(spreads, (panel) => panel.kind === "bias" && panel.key === ARRIVAL_KEY),
  );
  await expect(page.locator(".bias__domain").first()).toBeVisible();
  await expect(page.locator(".spread details, .spread [hidden]")).toHaveCount(0);
});

test("the map is not covered by the thing you read it with", async ({ page }) => {
  /*
    The regression this exists for: at 56rem the claim sheet covered the sphere on a laptop, which
    makes both the camera flight and the caption explaining it pointless. There is no sheet over a
    map now -- the world chapter puts the apparatus on one leaf and the map on the other -- so the
    same worry is asked of that arrangement: the map has a real share of the spread, and the panel
    is not on top of it.

    ADR 0015 decision 8 records this arrangement as the one thing left open on a phone, where the
    two are a swipe apart rather than side by side.
  */
  await explore(page);
  const canvas = await page.locator(".globe canvas").boundingBox();
  const spread = await page.locator(".spread").boundingBox();
  expect(canvas && spread).toBeTruthy();
  expect(
    canvas!.width / spread!.width,
    `the map takes ${((canvas!.width / spread!.width) * 100).toFixed(0)}% of the spread`,
  ).toBeGreaterThan(0.3);

  // And the tools are beside it rather than over it.
  const panel = await page.locator(".explore").boundingBox();
  expect(panel!.x + panel!.width, "the tools overlap the map").toBeLessThanOrEqual(canvas!.x + 2);
});

test("turning to another claim swaps the evidence with it", async ({ page }) => {
  /*
    There is no camera to fly. This used to assert that choosing a claim flew the globe to its own
    ground and swapped the layers under it -- "the globe is an index to the arguments rather than a
    layer switcher with prose attached". The book answers the same question with a drawn plate per
    claim, marked at the camera `story.ts` records, so what is asserted is that the evidence follows
    the claim: the register changes and the plate's mark moves with it.

    The layer half did not survive the move and did not need to: the world chapter shows every
    published layer and no argument on top of it, which is the test below.
  */
  const { VIEWS } = await import("../src/lib/story");
  await claimPage(page, "marine-null");
  // The heading is the plain sentence and the precise claim is rendered under it, so the swap is
  // checked on both registers rather than on whichever one happens to be the heading today.
  await expect(page.locator(".claim__title")).toHaveText(/fish/i);

  const markOf = () =>
    page
      .locator(".spread > .page .plate .ink-here")
      .first()
      .evaluate((node) => {
        const box = (node as unknown as SVGGElement).getBoundingClientRect();
        return [Math.round(box.x + box.width / 2), Math.round(box.y + box.height / 2)];
      });
  // The register is on the claim's page and the plate is two leaves on, so each half of the swap is
  // read where it lives rather than off one spread that used to hold both.
  await figurePage(page, "marine-null");
  const marine = await markOf();

  await claimPage(page, "atlas-no-net-change");
  await expect(page.locator(".claim__title")).not.toHaveText(/fish/i);
  await figurePage(page, "atlas-no-net-change");
  const southern = await markOf();

  const moved = Math.abs(marine[0]! - southern[0]!) + Math.abs(marine[1]! - southern[1]!);
  expect(
    moved,
    `both plates mark the same spot, at ${marine.join(",")} and ${southern.join(",")}`,
  ).toBeGreaterThan(30);

  // And the two cameras really are different, so the pixels above mean something.
  expect(VIEWS["marine-null"]!.center).not.toEqual(VIEWS["atlas-no-net-change"]!.center);
});

test("a claim has its own address, and the back button honours it", async ({ page }) => {
  await arrive(page);

  /*
    `ch` and `p` rather than `c`, because the book addresses a page and not a claim -- and a chapter
    is the durable half: it survives a claim being added ahead of it, where an absolute page number
    would silently point somewhere else. The old `c=` address is still read, which is the test two
    above this one.
  */
  await claimPage(page, "marine-null");
  await expect(page).toHaveURL(/[#&]ch=what-did-not/);

  await claimPage(page, "coverage-bias");
  await expect(page).toHaveURL(/[#&]ch=cannot-see/);

  // `pushState` per page, so back means the last page read. The clock deliberately uses
  // `replaceState` in the same hash -- animating it would push hundreds of entries -- and the two
  // have to coexist without either erasing the other.
  await page.goBack();
  await expect(page).toHaveURL(/[#&]ch=what-did-not/);
  await expect(page.locator(".claim__title")).toHaveText(/fish/i);
});

test("a link to a claim opens that claim, with nothing in front of it", async ({ page }) => {
  /*
    Someone following a link to a finding has already been told what it is; a card would be an
    interstitial between them and the thing they clicked for. There is no card now, so what this
    guards is the other half: the link has to land on the *claim* rather than on whatever chapter is
    the default, which is what `#c=` did for one commit before `Reader` learned to read it.
  */
  await open(page, "#c=anthropogenic-share");
  await expect(page.locator(".claim__title")).toBeVisible();
  await expect(page.locator(".claim__title")).toContainText(/half of that earlier timing/i);

  // And the precise register is a turn away, not absent.
  await recordPage(page, "anthropogenic-share");
  await expect(page.locator(".claim__precise")).toHaveText(/human forcing/i);
});

test("choosing an animal says what is known about it, not just where it is", async ({ page }) => {
  await explore(page);

  // Atlantic mackerel: measured in fourteen bottom-trawl surveys, which disagree.
  await page.getByRole("searchbox").fill("Scomber scombrus");
  await page.locator(".hits button").first().click();

  const study = page.locator(".study");
  await expect(study).toBeVisible();
  await expect(study.locator("h3")).toHaveText(/Scomber scombrus/);

  // The rows are the point. `marine-null` claims surveys disagree in direction, and until these
  // were published the only number on the site was the median that averages them out.
  const rows = study.locator(".study__rows div");
  expect(await rows.count()).toBeGreaterThan(3);
  await expect(study.locator(".study__caveat")).not.toBeEmpty();
});

test("an animal the gate refuses has a page saying so, with no location on it", async ({ page }) => {
  await explore(page);
  await page.getByRole("searchbox").fill("Canis lupus");
  await page.locator(".hits button").first().click();

  const withheld = page.locator(".study__one--withheld");
  await expect(withheld).toBeVisible();
  await expect(withheld).toContainText(/held back/i);
  // The rationale, not just the refusal. An unexplained refusal cannot be reviewed.
  await expect(withheld.locator(".study__caveat")).toContainText(/Cooke et al/);

  // And nothing on it could put anyone within reach of an animal.
  const prose = (await withheld.textContent()) ?? "";
  expect(prose).not.toMatch(/-?\d{1,3}\.\d{3,}/);
});

test("a species page is fetched only when a species is chosen", async ({ page }) => {
  await explore(page);

  const asked: string[] = [];
  page.on("request", (request) => {
    if (/species-study-\d+\.json/.test(request.url())) asked.push(request.url());
  });

  // Typing must not cost a shard. 2.2 MB of study pages has no business loading for a reader who
  // is looking at the globe.
  await page.getByRole("searchbox").fill("Scomber");
  await expect(page.locator(".hits button").first()).toBeVisible();
  expect(asked, "a keystroke fetched a study shard").toEqual([]);

  await page.locator(".hits button").first().click();
  await expect(page.locator(".study")).toBeVisible();
  expect(asked.length, "choosing a species fetched more than its own shard").toBe(1);
});

test("a study card leads back to the claim its evidence feeds", async ({ page }) => {
  await explore(page);

  await page.getByRole("searchbox").fill("Scomber");
  await page.locator(".hits button").first().click();
  await expect(page.locator(".study")).toBeVisible();

  /*
    The road back, and it was dead. `Study.svelte` links to `#c=<key>` -- the address the *shell*
    read -- and the book reads `ch` and `p`, so "read the claim this evidence feeds" went nowhere
    from the day the book became the front door. Rather than rewrite the link, `Reader` now reads
    `c` as an address of its own and resolves it to that claim's first page: those links exist
    outside this repository too, because they are what the deployed site has been handing out.
  */
  await page.locator(".study__claim").first().click();
  await expect(page.locator(".claim__title")).toContainText("Fish are not all moving");
  await expect(page).toHaveURL(/[#&]c=marine-null/);
});

test("a claim's specimen button opens the fish that carries its argument", async ({ page }) => {
  /*
    The other half, and it was dead too -- worse than dead, invisible. `Claim` renders the invitation
    only when it is given somewhere to go, and `Reader` passed nothing, so the button did not exist
    and no test noticed. It is on the record page, which is where the number it belongs to is.
  */
  await recordPage(page, "marine-null");

  // Computed in the reports layer, so the button names whichever species most decisively went both
  // ways in the current lake rather than one someone typed.
  const invitation = page.locator(".claim__specimen");
  await expect(invitation).toBeVisible();
  await invitation.click();

  // The preselect is consumed through the same code path as a visitor's click, which runs after
  // explore's data is up -- and the wave made that load heavier. CI hit 5s with the study still
  // on its way; this is the load-gated wait other tests already get, not a new patience.
  await expect(page.locator(".study")).toBeVisible({ timeout: 15_000 });
  await expect(page.locator(".study")).toContainText("north");
});

test("the year can be set moving, and the control says so", async ({ page }) => {
  /*
    The arrival's third door is gone with the card. What it was for is not: a reader who wants to
    watch a year rather than read about one, and a control that does not lie about whether the clock
    is running. The door has become the button in the world chapter's own tools, which is where the
    clock always lived -- `Shell` only pressed it on the reader's behalf.
  */
  await explore(page);
  const run = page.locator(".explore .run").first();
  await expect(run).toBeVisible();
  await run.click();
  await expect(run, "the clock is running and the button still says Play").toContainText(/pause/i);
});

test("the world chapter offers the whole map, not the last claim's filter", async ({ page }) => {
  /*
    The regression this exists for: explore mode inherited the last claim's layer subset, so a reader
    who asked for the map got one claim's evidence still filtered onto it -- which reads as a bug
    rather than a choice.

    It cannot happen the same way now and the assertion moved with the reason. The chapter draws
    nothing until asked, on the owner's decision -- nine layers composited read as satellite imagery
    over a basemap that is already paper and ink -- so "the whole map" is a claim about what is
    *offered*: every published layer in the panel, and none of them inherited from wherever the reader
    has been. Visited after a claim, which is the state that used to break it.
  */
  await claimPage(page, "marine-null");
  await explore(page);

  // Every published layer is on the list, counted from the manifest rather than written here.
  const manifest = await page.request
    .get("layers/manifest.json")
    .then((r) => r.json() as Promise<{ name: string }[]>);
  // Plus one: the detectability assessment is not a manifest layer -- it is computed and added by
  // `addDetectability` -- and it still gets a control, which is the point of counting at all.
  await expect(page.locator(".explore .layers li")).toHaveCount(manifest.length + 1);

  // And none of them is drawn, so nothing was carried over from the claim.
  const drawn = await page.evaluate(() => {
    const map = (window as unknown as { migratlas?: { map?: unknown } }).migratlas?.map as
      | { getStyle: () => { layers: { id: string; layout?: { visibility?: string } }[] } }
      | undefined;
    return (map?.getStyle().layers ?? [])
      .filter((layer) => /^(series|surface|contour|tracks|seasonal|detectability)/.test(layer.id))
      .filter((layer) => layer.layout?.visibility !== "none")
      .map((layer) => layer.id);
  });
  expect(drawn, `the chapter arrived drawing ${drawn.join(", ")}`).toEqual([]);

  // Ticking one draws one, which is the whole of what the chapter is for.
  await page.locator(".explore .layers input").first().check();
  await expect
    .poll(
      () =>
        page.evaluate(() => {
          const map = (window as unknown as { migratlas?: { map?: unknown } }).migratlas?.map as
            | { getStyle: () => { layers: { id: string; layout?: { visibility?: string } }[] } }
            | undefined;
          return (map?.getStyle().layers ?? []).filter(
            (layer) => layer.layout?.visibility !== "none" && /^(series|surface)-/.test(layer.id),
          ).length;
        }),
      { message: "ticking a layer drew nothing", timeout: 30_000 },
    )
    .toBeGreaterThan(0);

  // And the camera is still the whole sphere: nothing is leading the reader anywhere on this chapter.
  const wide = await settled(page);
  expect(wide.zoom).toBeLessThan(3);
});
test("every claim is reachable, and says what it found before anyone reads it", async ({ page }) => {
  /*
    The index was a tab per claim with its direction printed on it, so a reader could see at a glance
    that the ledger holds nulls and limits and not only changes -- an index of the positives alone
    would be lying by selection. The book has no index; it has chapters, and the direction is on the
    claim's own page in the banner.

    So this asserts the same property against the new shape: every published claim has a page that
    can be reached, and the three directions are all present across them. It reads the banner rather
    than a tab label, and it walks the ledger rather than counting tabs -- the count used to be a
    literal 6, so landing a sixth finding failed a test about the index for a reason that had nothing
    to do with the index.
  */
  const published = await page.request
    .get("findings.json")
    .then((r) => r.json() as Promise<{ findings: { key: string }[] }>);
  expect(published.findings.length).toBeGreaterThan(1);

  const spreads = await layout();
  const kinds = new Set<string>();
  for (const finding of published.findings) {
    const where = spreads.find((one) =>
      [one.verso, one.recto].some(
        (panel) => panel.kind === "finding" && panel.key === finding.key,
      ),
    );
    expect(where, `no page carries the claim "${finding.key}"`).toBeTruthy();
    await open(page, `#ch=${where!.chapter.slug}&p=${where!.at}`);
    const banner = (await page.locator(".claim__banner").first().textContent()) ?? "";
    kinds.add(banner.trim().toLowerCase());
  }

  const said = [...kinds].join(" ");
  expect(said, "no claim reports a change").toContain("change detected");
  expect(said, "no claim reports a null").toContain("no change");
  expect(said, "no claim reports a limit").toContain("limit");
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

test("every published claim has exactly one chapter, and every chapter is real", async ({ page }) => {
  /*
    ADR 0013 asked for this guard by name: the chapters are the argument, so a claim with no chapter
    is a result the book has nowhere to put. Two failures it has to catch, and they fail differently
    -- an unplaced claim disappears from the book silently, while a claim placed twice appears twice
    and reads as two findings.
  */
  await arrive(page);
  const keys = await page.evaluate(async () => {
    const ledger = (await fetch("findings.json").then((r) => r.json())) as {
      findings: { key: string }[];
    };
    return ledger.findings.map((f) => f.key);
  });

  const { CHAPTERS, chapterOf } = await import("../src/lib/story");

  for (const key of keys) {
    const chapter = chapterOf(key);
    expect(chapter, `no chapter carries the claim "${key}"`).toBeTruthy();
    const homes = CHAPTERS.filter((c) => c.keys.includes(key)).map((c) => c.slug);
    expect(homes, `"${key}" is in more than one chapter`).toHaveLength(1);
  }

  // And nothing is promised that the ledger does not publish: a key here with no finding behind it
  // would render a chapter with a hole in it rather than fail.
  for (const chapter of CHAPTERS) {
    for (const key of chapter.keys) {
      expect(keys, `chapter "${chapter.slug}" names a claim "${key}" that is not published`).toContain(
        key,
      );
    }
    expect(chapter.title, `chapter "${chapter.slug}" has no title`).toBeTruthy();
    expect(chapter.tab, `chapter "${chapter.slug}" has no tab label`).toBeTruthy();
    // The tab is the word on the thumb; the mock found seven full titles ran past the foot of the
    // book, so this holds the shorthand to something a tab can actually carry.
    expect(chapter.tab.length, `chapter "${chapter.slug}" has a tab label too long to set`)
      .toBeLessThanOrEqual(12);
  }

  const slugs = CHAPTERS.map((c) => c.slug);
  expect(new Set(slugs).size, "two chapters share a slug").toBe(slugs.length);
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

    /*
      The measurement stays on one line, wherever it is printed. Broken after "days" it read as two
      facts rather than as one number with an interval -- which is a property of the number and the
      column it is set in, not of the card it used to be on, so it is asserted on the record page.
    */
    const { ARRIVAL_KEY } = await import("../src/lib/story");
    await recordPage(page, ARRIVAL_KEY);
    const lines = await page.locator(".claim__value").first().evaluate((node) => {
      const style = getComputedStyle(node);
      return node.getBoundingClientRect().height / Number.parseFloat(style.lineHeight || "0");
    });
    /*
      One line on a tablet and at most two on a phone. The rule this protects is that the number and
      its interval read as one fact -- broken after "days" it read as two -- and at 390px a mono
      string of "-0.56 +/- 0.25 days per decade" cannot be set on one line at a legible size. What
      is not negotiable is that it does not fragment further than that, so the bar is by width
      rather than a single figure that would have to be loosened for the smaller screen.
    */
    expect(lines, `the measurement is on ${lines.toFixed(1)} lines`).toBeLessThan(
      width < 500 ? 2.4 : 1.8,
    );

    // The way on is reachable without scrolling: the fore-edge on a phone, the folio on a tablet.
    await expect(page.locator(".thumb, [data-turn]").first()).toBeInViewport();

      expect(await overflow()).toBeLessThanOrEqual(1);

    /*
      The claim responds to the room it is given rather than to the viewport. On a 768px tablet the
      old sheet was narrower than any sensible media-query breakpoint, and a two-column layout
      squeezed the body to 230px and wrapped the hand heading over nine lines. The book answers this
      structurally -- one panel per page, and a container chosen by width -- so what is asserted is
      the outcome: a column wide enough to set a sentence in.
    */
    await claimPage(page, ARRIVAL_KEY);
    const body = await page.locator(".claim__body").first().boundingBox();
    expect(body, "no claim body").toBeTruthy();
    expect(
      body!.width,
      `the claim body is ${Math.round(body!.width)}px wide, which is a column of two-word lines`,
    ).toBeGreaterThan(300);

    // The audit is still there and still not behind a control -- it is a leaf of its own now.
    const spreads = await layout();
    await open(
      page,
      addressOf(spreads, (panel) => panel.kind === "bias" && panel.key === ARRIVAL_KEY),
    );
    await expect(page.locator(".bias__finding").first()).toBeVisible();
    await expect(page.locator("details, [hidden]")).toHaveCount(0);

    // Nothing the map owns may be printed *over* the claim, and that is the requirement -- not that
    // the boxes never touch. The first version compared bounding boxes, which is stricter than what
    // matters and failed on CI over a few pixels of harmless overlap while the notice was perfectly
    // readable. Occlusion is the real test: ask the browser what is actually on top at the centre of
    // each control, and require it to be that control.
    // Polled, not sampled once. The attribution control registers each source's credit as that
    // source loads and only then collapses to its compact "i", so a single reading can catch it
    // spread across the whole width of a 390px phone with its centre under the sheet -- which is
    // what it did, intermittently, and only under full-suite load. The requirement is about the
    // settled page; a control that is really buried stays buried and this still fails.
    await expect
      .poll(
        () =>
          page.evaluate(() => {
            const hits: string[] = [];
            for (const selector of [
              ".maplibregl-ctrl-attrib",
              ".maplibregl-ctrl-group",
              ".maplibregl-ctrl-scale",
            ]) {
              for (const node of document.querySelectorAll(selector)) {
                const box = node.getBoundingClientRect();
                if (box.width === 0 || box.height === 0) continue;
                const at = document.elementFromPoint(
                  box.left + box.width / 2,
                  box.top + box.height / 2,
                );
                if (!at || !(node.contains(at) || at.contains(node))) {
                  hits.push(`${selector} is under ${at?.className || at?.tagName || "nothing"}`);
                }
              }
            }
            return hits;
          }),
        { message: "something the map owns is printed over the claim" },
      )
      .toEqual([]);
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
  // Not on every claim: a chart on each would be decoration, and the plate answers a different
  // question. `book.spec.ts` asserts the routing; this is about what the chart itself says.
  await claimPage(page, "marine-null");
  await expect(page.locator(".chart__svg")).toHaveCount(0);

  await claimPage(page, "anthropogenic-share");
  // One chart to a page, and both of them in the book -- counted by visiting each below.
  /*
    Read across two leaves. `figures.ts` gives the ribbon four pages because two charts on one
    overflowed it by 536px, so the pair is compared by visiting both rather than by querying one
    page -- which is the same comparison, and the reason for it is unchanged: shared axes, because
    two charts on their own extents would make a 0.89-day gap and a 0.29-day gap look the same size.
  */
  const spreads = await layout();
  // Deduplicated: a spread holding two of the figure's four pages contributes its address twice,
  // which counted the same leaf as two charts and made a pair of charts look like three.
  const chartPages = [
    ...new Set(
      spreads.flatMap((one) =>
        [one.verso, one.recto].flatMap((panel) =>
          panel.kind === "figure" && panel.key === "anthropogenic-share"
            ? [`#ch=${one.chapter.slug}&p=${one.at}`]
            : [],
        ),
      ),
    ),
  ];

  /*
    Read a leaf at a time, not a spread at a time.

    The ribbon's two chart pages face each other now that the plain-method page shifted the parity,
    so a count taken over the spread returned one reading of four lines where the assertion wants two
    readings of two. That would have passed as "four lines" while hiding the thing being checked:
    that there are two charts and each carries its own pair.
  */
  const readEach = async <T>(read: (leaf: string) => Promise<T>): Promise<T[]> => {
    const out: T[] = [];
    for (const address of chartPages) {
      await open(page, address);
      for (const side of ["verso", "recto"] as const) {
        const leaf = `.spread > .page--${side}`;
        if ((await page.locator(`${leaf} .chart__svg`).count()) === 0) continue;
        out.push(await read(leaf));
      }
    }
    return out;
  };

  // On a chart page before asking to see a chart. The claim's own leaf carried one while the figure
  // faced it; the plain-method page moved the figure to the next spread.
  await open(page, chartPages[0]!);
  await expect(page.locator(".chart__svg").first()).toBeVisible();

  /*
    Two charts, not one with four lines -- two of four lines would nearly coincide and two would sit
    far apart, which invites averaging, and an average of two different quantities is nothing. Two
    *pages* now: they came to 1,362px on an 826px page, so `figures.ts` gives each its own leaf. Both
    still exist and each still carries its own pair of lines, which is what this counted.
  */
  const lines = await readEach((leaf) => page.locator(`${leaf} .chart__line`).count());
  expect(lines, "not two charts, one per page").toHaveLength(2);
  expect(lines.reduce((sum, n) => sum + n, 0), "not four lines across the pair").toBe(4);
  expect(new Set(lines).size, "the two charts do not carry the same number of lines").toBe(1);

  // One frame for both, which is the assertion the whole design rests on. Each chart drawn to its
  // own extents would make a 0.89-day gap and a 0.29-day gap look the same size, and would stretch
  // the shorter window's slope. Compared on the rendered geometry rather than the source numbers,
  // because it is the pixels that would lie.
  const geometry = await readEach((leaf) =>
    page
      .locator(`${leaf} .chart__svg`)
      .first()
      .evaluate((node) =>
        [...node.querySelectorAll(".chart__tick")].map((t) => t.textContent?.trim()).join("|"),
      ),
  );
  expect(geometry.length, "fewer than two charts in the book").toBe(2);
  expect(new Set(geometry).size, "the two charts do not share one frame").toBe(1);

  // The observed line draws before the counterfactual: the drawing order is the argument, because a
  // reader watches the gap fail to open rather than hunting for it.
  // On a chart page: `readEach` above leaves the reader on the last of them, which may be the one
  // carrying the reading rather than a chart.
  await open(page, chartPages[0]!);
  const delays = await page
    .locator(".chart__line")
    .evaluateAll((nodes) => nodes.map((n) => getComputedStyle(n).transitionDelay));
  expect(delays.length, "no lines to read a delay from").toBeGreaterThan(1);
  expect(new Set(delays).size, "the lines all draw at once").toBeGreaterThan(1);

  // Both charts say where their own attribution stops, not only in the caveat -- and they say
  // different things, because ATTRICI's counterfactual series ran out where DAMIP's share is a ratio
  // carried past the window that fitted it. globe.spec.ts checks the geometry; this checks the words.
  const limits = (
    await readEach((leaf) => page.locator(`${leaf} .chart__beyond-label`).allTextContents())
  ).flat();
  expect(limits).toHaveLength(2);
  expect(limits.join(" ")).toMatch(/no counterfactual after 2019/);
  expect(limits.join(" ")).toMatch(/share fitted only to 2014/);

  // Each size stated in words, which is what stops a chart being "improved" into a diverging wedge.
  // Read across the pair, because each chart states its own.
  const sizes = (
    await readEach((leaf) => page.locator(`${leaf} .chart__size`).allTextContents())
  ).flat();
  expect(sizes.length, "no chart states its size in words").toBeGreaterThan(0);
  expect(sizes.join(" ")).toMatch(/part by \d+\.\d+ days/);

  /*
    And the disagreement explained, at body size rather than as a footnote -- two numbers that differ
    by a factor of two with no explanation would be worse than publishing one of them. It is the
    ribbon's third page, which `figures.ts` titles with the question it answers.
  */
  await open(
    page,
    addressOf(
      spreads,
      (panel) => panel.kind === "figure" && panel.key === "anthropogenic-share" && panel.at === 2,
    ),
  );
  const gap = page.locator(".pair__gap");
  await expect(gap).toContainText(/differ/i);
  // Two registers here now, as on a claim. Retargeted rather than loosened: `.pair__gap p` would
  // match either paragraph, so it would go on passing while the precise text was quietly dropped.
  await expect(gap.locator(".pair__plain")).toContainText("neither is wrong");
  await expect(gap.locator(".pair__precise")).toContainText("not two estimates of one number");

  const size = await gap
    .locator(".pair__precise")
    .evaluate((n) => parseFloat(getComputedStyle(n).fontSize));
  const footnote = await page
    .locator(".pair__caveat")
    .evaluate((n) => parseFloat(getComputedStyle(n).fontSize));
  expect(size, "the explanation is not set at footnote size").toBeGreaterThan(footnote);
});

test("the detectability assessment is the coverage claim's own number", async ({ page }) => {
  await arrive(page);

  /*
    Its own leaf. The assessment is two pages -- what could be measured, and what is held back -- and
    they face each other now, so both render a `section.coverage` on one spread and an unscoped
    selector resolves to two. Named rather than narrowed with `.first()`, because "whichever comes
    first in the DOM" is not the page this half of the test is about.
  */
  const measured = pageAt(
    await layout(),
    (panel) => panel.kind === "figure" && panel.key === "coverage-bias" && panel.at === 0,
  );
  await open(page, measured.at);

  const coverage = page.locator(`.spread > .page--${measured.side} .coverage`);
  await expect(coverage).toBeVisible();
  // The headline, as a share rather than a count: "1,997 cells" means nothing without a denominator.
  await expect(coverage.locator(".coverage__lead")).toContainText(/%/);
  // A key, because four unlabelled greys are not a map of anything.
  await expect(coverage.locator(".coverage__legend li")).toHaveCount(4);
  // And every source, with the best it can do -- the point being that most of them can do nothing.
  await expect(coverage.locator("tbody tr")).not.toHaveCount(0);

  // The two sources the gate refuses, named rather than omitted. A map that silently skipped them
  // would read as a map with no wolves in it, when the lake holds 174,443 wolf fixes and will not
  // draw one -- and a reader could not tell that refusal from a hole in the coverage.
  /*
    The withheld sources are the assessment's second page. `figures.ts` splits it there because the
    whole thing overflowed a page by 459px, on the seam the material already had: what could be
    measured, and then what is held back from the map entirely.
  */
  const spreads = await layout();
  await open(
    page,
    addressOf(
      spreads,
      (panel) => panel.kind === "figure" && panel.key === "coverage-bias" && panel.at === 1,
    ),
  );
  const held = page.locator(".held");
  await expect(held).toBeVisible();
  await expect(held.locator("li")).toHaveCount(2);
  await expect(held).toContainText("Rangifer tarandus");
  await expect(held).toContainText("Canis lupus");
  // Withheld means withheld, not coarsened -- the distinction the policy turns on.
  await expect(held).toContainText(/withheld entirely/i);
  // And the finding survives the refusal, which is the deliberate decision in phase1d-tracks.md §2.
  await expect(held).toContainText(/locates no animal/i);

  // The terrestrial realm is no longer birds-only, asserted through the panel rather than the
  // ledger -- back on the assessment's first page, where the per-source table is.
  await claimPage(page, "coverage-bias");
  await open(
    page,
    addressOf(
      spreads,
      (panel) => panel.kind === "figure" && panel.key === "coverage-bias" && panel.at === 0,
    ),
  );
  const sources = await coverage.locator("tbody tr th").allTextContents();
  expect(sources.filter((name) => name.startsWith("movebank_")).length).toBeGreaterThan(0);
  await expect(coverage.locator(".coverage__ceiling").first()).not.toBeEmpty();
});

test("explore carries the tools, with the terms every drawn layer was published under", async ({
  page,
}) => {
  await explore(page);

  const panel = page.locator(".explore");
  await expect(panel).toBeVisible();

  // One toggle per layer, including the assessment, which starts off. Counted from the manifest
  // rather than written here: the literal was 4 and publishing a fifth layer broke this test
  // instead of the thing it is meant to protect, which is that every layer gets a control.
  const published = await page.evaluate(async () => {
    const manifest = (await fetch("layers/manifest.json").then((r) => r.json())) as unknown[];
    return manifest.length;
  });
  const toggles = panel.locator(".layers input");
  await expect(toggles, "a published layer has no toggle, or one has two").toHaveCount(
    published + 1,
  );

  // Required, not decorative: published data must never be separable from the terms it was
  // published under. This is the assertion the old page had and the shell has to keep.
  /*
    The terms of every layer *currently drawn*, so one is drawn first. On a bare globe the paragraph
    is absent, and that is the rule working rather than a gap in it: the obligation attaches to data
    on screen, and what must never happen is a layer drawn with its terms missing.
  */
  await expect(panel.locator(".terms")).toHaveCount(0);
  await panel.locator(".layers input").first().check();
  await expect(panel.locator(".terms")).not.toBeEmpty();

  // The clock reads as a date rather than as a day number, and without the stray punctuation a
  // trimmed shared formatter left behind.
  const clockface = await panel.locator(".clockface").textContent();
  expect(clockface).toMatch(/^\d{1,2} \w{3} · week \d{1,2}$/);

  // Moving the slider moves the label, so the control is wired to the clock and not decorative.
  await panel.locator(".time input").fill("120");
  await expect(panel.locator(".clockface")).not.toHaveText(clockface!);

  // Search is loaded and knows how many animals it holds.
  await expect(panel.locator("#taxon-search")).toHaveAttribute("placeholder", /Search [\d,]+ animals/);
});

test("switching on the assessment brings its key with it", async ({ page }) => {
  await explore(page);

  const panel = page.locator(".explore");
  // The regression: the legend was on the claim and missing here, which is the worse way round --
  // the layer can be switched on from this panel and could not be read once it was.
  await expect(panel.locator(".key li")).toHaveCount(0);

  await panel.locator(".layers input").last().check();
  await expect(panel.locator(".key li")).toHaveCount(4);
  await expect(panel.locator(".key li").first()).toContainText("%");
});

test("searching an animal draws it and says which one is shown", async ({ page }) => {
  await explore(page);

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
 * A bird with a result and no surface.
 *
 * The other half of the search: `taxon-index.json` holds what is drawn, `species-index.json` holds
 * what is only studied, and every SABAP bird is in the second. The test above searches a whale that
 * has a layer, so it never touched this path.
 */

test("a studied bird has a page, and it carries both numbers", async ({ page }) => {
  await explore(page);

  await page.locator("#taxon-search").fill("Acridotheres");
  const hits = page.locator(".hits button");
  await expect(hits.first()).toBeVisible();
  await hits.first().click();

  const card = page.locator(".study__one--occupancy");
  await expect(card).toBeVisible();

  // This read `undefined` for 560 birds when it shipped. The label is a Record keyed by a
  // TypeScript union, the kinds are written in Python, and the shard JSON is cast rather than
  // validated -- so nothing in `tsc` could see the missing entry. `test_species_pages.py` guards
  // the coverage; this asserts a reader sees the words.
  await expect(card.locator(".study__kind")).toHaveText("how much of the region it occupies");

  // The exhibit this wave exists for. The atlas finding's second claim is that correcting for
  // detection did not change the answer, and a reader can only check that against a number.
  await expect(card.locator(".study__rows dt")).toHaveText([
    "Occupancy, corrected for detection",
    "Reporting rate, uncorrected",
    "Against the other five-year window",
  ]);
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
  /*
    Two leaves rather than one card. The number is on the claim's record page and the knob is on its
    own, because three of them came to 1,306px against an 826px page -- so the invariant is read
    across the two, which is the same invariant: the default setting must reproduce what the ledger
    published, or the panel is a toy.
  */
  await recordPage(page, "autumn-advance");
  const published = await page.locator(".claim__value").first().textContent();
  const match = published?.match(/-?\d+\.\d+/);
  expect(match, `no number in the claim value "${published}"`).toBeTruthy();

  /*
    Every knob on this claim, at its published setting, must show the claim's own figure -- a panel
    that disagreed with the number a leaf earlier would undermine both. Walked by page rather than by
    index, because each knob has one: the count comes from `sandbox.json`, so a fourth safeguard
    added upstream is checked rather than silently skipped.
  */
  const { knobsFor, loadSandbox } = await import("../src/lib/sandbox/sandbox");
  const doc = JSON.parse(
    readFileSync("public/sandbox.json", "utf8"),
  ) as Parameters<typeof knobsFor>[0];
  const knobs = knobsFor(doc, "autumn-advance");
  expect(knobs.length, "the sandbox holds no knobs for this claim").toBeGreaterThan(1);
  void loadSandbox;

  for (const [index] of knobs.entries()) {
    await knobPage(page, "autumn-advance", "safeguards", "knobs", index);
    const knob = page.locator(".knob").first();
    await expect(knob, `no knob on page ${index}`).toBeVisible();
    await expect(knob.locator(".option--on em")).toHaveText("published");
    await expect(knob.locator(".knob__value")).toContainText(match![0].replace("-", "−"));
    await expect(knob.locator(".knob__delta--published")).toBeVisible();
  }
});

test("switching a safeguard off moves the number and says which way", async ({ page }) => {
  // One knob to a page, so the page carrying this one is found rather than assumed.
  await knobOf(page, "autumn-advance", /hardware upgrade/i);
  // Named rather than first. Two knobs face each other now that the plain-method page changed the
  // parity, so the leftmost one on the spread is not necessarily the one this test is about.
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
  await knobOf(page, "autumn-advance", /shuffl/i);

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
  // Not on the autumn advance: it is the marine null's counter-analysis. Asserted on that claim's
  // own audit page, which is where a refusal of its would be if it had one.
  await knobPage(page, "autumn-advance", "safeguards", "knobs", 0);
  await expect(page.locator(".refusal")).toHaveCount(0);
  /*
    A refusal is a page of its own now, beside the knob it belongs with. `sandbox.ts` keys this one to
    `marine-null` -- "the analysis that would have said there was a single global poleward shift, and
    why it must not be run" -- so it is on that claim's refusals leaf.
  */
  await knobPage(page, "marine-null", "safeguards", "refusals", 0);

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

/**
 * The response dial.
 *
 * A different object from the sandbox and the difference is the whole point, so it is asserted from
 * the reader's side. The sandbox asks what the published number owes to a correction; the dial asks
 * what a different world would do to it. The failure mode being guarded is not a wrong number -- the
 * Python pins those against the fit -- it is a panel that reads as a forecast, which would undo the
 * two phases this project spent earning the right to refuse one.
 */

/** The dial's first knob page. Its two refusals are two leaves further on. */
async function dialPage(page: Page): Promise<void> {
  await knobPage(page, "anthropogenic-share", "dial", "knobs", 0);
}

test("the dial sits on the attribution claim, at the sensitivity the fit published", async ({
  page,
}) => {
  await dialPage(page);

  const dial = page.locator(".response .knob").filter({ hasText: /June-July before migration/i });
  await expect(dial).toBeVisible();

  // The published position is the fitted sensitivity itself: a degree warmer, 0.66 days earlier.
  await expect(dial.locator(".option--on em")).toHaveText("published");
  await expect(dial.locator(".knob__value")).toContainText("−0.66 days");
  await expect(dial.locator(".knob__delta--published")).toBeVisible();
});

test("asking for nothing implies nothing, and warmer implies earlier", async ({ page }) => {
  await dialPage(page);
  const dial = page.locator(".response .knob").filter({ hasText: /June-July before migration/i });

  await dial.locator(".option", { hasText: "as it was" }).click();
  const unchanged = await dial.locator(".knob__value").textContent();
  expect(Number.parseFloat(unchanged!.replace("−", "-"))).toBe(0);

  // Sign is the claim here. Warmer must move passage earlier, which is a negative number of days,
  // and a dial that got this backwards would still render a plausible-looking figure.
  await dial.locator(".option", { hasText: "1.5 °C warmer" }).click();
  const warmer = await dial.locator(".knob__value").textContent();
  expect(Number.parseFloat(warmer!.replace("−", "-"))).toBeLessThan(-0.9);

  await dial.locator(".option", { hasText: "1.5 °C cooler" }).click();
  const cooler = await dial.locator(".knob__value").textContent();
  expect(Number.parseFloat(cooler!.replace("−", "-"))).toBeGreaterThan(0.9);
});

test("the dial stops where the fit stops, and offers no position past it", async ({ page }) => {
  await dialPage(page);
  const dial = page.locator(".response .knob").filter({ hasText: /June-July before migration/i });

  // Ninety per cent of the record's within-station departures lie inside roughly ±1.8 °C, so ±1.5
  // is offered and ±2 is not. A dial that offered it would be extrapolating in the reader's hand.
  await expect(dial.locator(".option", { hasText: "1.5 °C warmer" })).toBeVisible();
  await expect(dial.locator(".option", { hasText: "2 °C warmer" })).toHaveCount(0);
});

test("the flat driver is published as flat rather than left out", async ({ page }) => {
  /*
    Two navigations, because the two things asserted are on two pages.

    The dial's knobs are a page each and its standfirst is printed once, on the first of them, so the
    page carrying the wind knob does not carry the lead. They shared a leaf until the plain-method
    page shifted the parity -- which is the kind of coincidence a test should not rest on, since which
    knob lands on which page is `response.json`'s order to decide.
  */
  await knobOf(page, "anthropogenic-share", /winds were more favourable/i);

  // Wind support is the obvious mechanism and it measures nothing: −0.24 ± 0.39 days per m/s, an
  // interval straddling zero. Publishing it is the point -- a panel carrying only the drivers that
  // worked would be selecting for its own story -- so its absence is the failure to catch.
  const wind = page.locator(".response .knob").filter({ hasText: /winds were more favourable/i });
  await expect(wind).toBeVisible();
  await expect(wind.locator(".knob__value")).toContainText("−0.24 days");

  // And the panel says why a flat driver is in it at all, on the page that carries its standfirst.
  await dialPage(page);
  await expect(page.locator(".response__lead")).toContainText(/published because it is flat/i);
});

test("the dial refuses to be read as a forecast, and refuses to leave its own range", async ({
  page,
}) => {
  /*
    The dial's two refusals -- one bounding it at the range the fit is informed over, one saying
    plainly that a sensitivity is not a forecast -- are a page each, facing its knobs. Found by
    walking them rather than assuming an order that `response.json` owns.
  */
  await refusalOf(page, "anthropogenic-share", /2 °C warmer than usual/i);

  const beyond = page.locator(".response .refusal").filter({ hasText: /2 °C warmer than usual/i });
  await expect(beyond.locator(".refusal__verdict")).toContainText(/Withheld/);
  // The bound is the band and not the extreme, and the reason is in the verdict rather than implied.
  await expect(beyond.locator(".refusal__verdict")).toContainText(/single observation|one observation/i);

  // Its own page. The two refusals shared a spread until the plain-method page flipped the parity,
  // and a test that reads both off one leaf is asserting a layout rather than a refusal.
  await refusalOf(page, "anthropogenic-share", /this coming autumn/i);
  const forecast = page.locator(".response .refusal").filter({ hasText: /this coming autumn/i });
  await expect(forecast.locator(".refusal__verdict")).toContainText(/did not beat chance/i);

  // The evidence is behind a click, as everywhere else in this panel: a number we say is
  // unsupported does not get printed at full size beside the ones we stand behind.
  await expect(forecast.locator(".refusal__rows")).toHaveCount(0);
  await forecast.getByRole("button", { name: /show me the wrong answer/i }).click();
  await expect(forecast.locator(".refusal__rows")).toContainText("20 of 143");
});

