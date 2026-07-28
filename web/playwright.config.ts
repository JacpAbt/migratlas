import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "tests",
  // The globe is a WebGL app: a retry that passes is a real signal about flakiness, not noise
  // to be papered over, so failures stand on the first run.
  retries: 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    ...devices["Desktop Chrome"],
    baseURL: "http://localhost:4188",
    // The bug this suite exists to catch was invisible in the DOM and visible only in what the
    // map actually drew, so a failing run needs the picture.
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  // Preview, not dev: the failure that shipped was a bundling one, and `vite dev` served the
  // broken asset correctly.
  webServer: {
    command: "npm run build && npm run preview -- --port 4188 --strictPort",
    url: "http://localhost:4188",
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
});
