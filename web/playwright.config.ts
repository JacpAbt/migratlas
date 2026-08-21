import process from "node:process";

import { defineConfig, devices } from "@playwright/test";

const PORT = 4188;
const ORIGIN = `http://localhost:${PORT}`;

/**
 * Serve from wherever the build was told it would live.
 *
 * A GitHub Pages project site is served from `/<repo>/`, and `vite preview` honours the build's
 * `base`. Reading the same variable here means the suite exercises the deployed path rather than
 * one that only exists locally — a subpath is otherwise exactly the kind of thing that passes in
 * CI and 404s in production.
 */
// Trimmed for the same reason check-build trims it: `set VAR=x && cmd` on Windows
// carries the trailing space into the value.
const BASE = (process.env.VITE_BASE ?? "/").trim();

export default defineConfig({
  testDir: "tests",
  // The globe is a WebGL app: a retry that passes is a real signal about flakiness, not noise
  // to be papered over, so failures stand on the first run.
  retries: 0,
  /*
    Two workers, not the default half-the-cores.

    All three spec files now boot a globe, so the default three workers meant three WebGL contexts
    competing for one GPU and one main thread. Everything measured slower than it is: the
    layer-draw test takes 66s alone and was taking 130-240s, and the interaction budget read 204ms
    against a real 52-90ms. Both were "fixed" once by raising their ceilings, which is treating a
    scheduler as a subject.

    Raising a ceiling to absorb contention costs the thing the number was for. Two contexts is what
    this machine actually drives, and the wall clock barely moves -- the suite was already
    saturated, so the third worker was mostly waiting.

    **One worker locally, since 2026-08-21, and the same argument one step further.** The suite has
    grown since the paragraph above was written: the layer-draw test took 66s alone then and takes
    3.4 minutes now, after eight commits added the green wave, the ice, the herds, the fox journeys
    and southern Africa. At two workers that test intermittently exceeded its own ten-minute hang
    detector, and the interaction budget -- calibrated at 132-228ms here -- read 310ms and 338ms in
    the same runs while passing every time it ran alone. Two instruments going marginal at once is
    the saturation this comment already describes, arriving at the next worker down.

    So local runs are serial. That keeps both numbers sharp, which is the whole point of having
    them, and costs wall clock that was mostly spent waiting anyway. CI keeps two, because its own
    budgets are deliberately looser -- 2000ms and 90s against 300ms and 30s -- so contention there
    cannot make a calibrated number lie.
  */
  workers: process.env.CI ? 2 : 1,
  /*
    A per-test timeout is a hang detector, not a budget.

    Playwright's 30s default was calibrated against this laptop, where the suite runs in 7 minutes.
    A GitHub runner takes 13.8 for the same 80 tests: `ready` alone is 8.9s there against 3.4 here,
    and two correct tests that walk every claim or toggle every layer ran out of clock and reported
    a timeout with no assertion attached. That says nothing about the page.

    Raised on CI only, so the local number keeps its edge as an early warning. This is not the
    ceiling-raising the workers comment warns about: performance has its own instruments here -- the
    heap, payload and ready budget, and the claim-change ratio measured against a repaint of the
    same page. Slowness is meant to fail *those*, with a number attached, rather than leak out as
    unrelated tests running out of time.
  */
  timeout: process.env.CI ? 90_000 : 30_000,
  reporter: process.env.CI ? "github" : "list",
  use: {
    ...devices["Desktop Chrome"],
    baseURL: `${ORIGIN}${BASE}`,
    // The bug this suite exists to catch was invisible in the DOM and visible only in what the
    // map actually drew, so a failing run needs the picture.
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  // Preview, not dev: the failure that shipped was a bundling one, and `vite dev` served the
  // broken asset correctly.
  /*
    **Do not run `npm run build` while a local run is in flight.** `reuseExistingServer` is on
    locally, so the suite serves whatever is in `dist/` -- and a manual build swaps the application
    under a suite that already read its test files off disk. That produced one run on 2026-08-21
    where a passing test began failing at number 45 with no code change to blame: the old tests were
    driving a newer app. The failure looks like a regression and is an artefact of the harness.
  */
  webServer: {
    command: `npm run build && npm run preview -- --port ${PORT} --strictPort`,
    url: `${ORIGIN}${BASE}`,
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
});
