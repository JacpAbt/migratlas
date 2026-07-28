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
const BASE = process.env.VITE_BASE ?? "/";

export default defineConfig({
  testDir: "tests",
  // The globe is a WebGL app: a retry that passes is a real signal about flakiness, not noise
  // to be papered over, so failures stand on the first run.
  retries: 0,
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
  webServer: {
    command: `npm run build && npm run preview -- --port ${PORT} --strictPort`,
    url: `${ORIGIN}${BASE}`,
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
});
