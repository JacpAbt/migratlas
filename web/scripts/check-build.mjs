/**
 * Assert the built output has no dangling asset references.
 *
 * Written after shipping a globe that never rendered. MapLibre's Web Worker was referenced
 * but never emitted, so it 404ed at runtime — and MapLibre's failure mode is silent: no
 * console error, no map error event, a healthy 60 fps, and an empty canvas. `tsc` passed and
 * `vite build` passed. CI was green throughout.
 *
 * This cannot replace a browser smoke test, but it is free and catches the specific class:
 * an emitted bundle naming a sibling file that does not exist.
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import process from "node:process";

/**
 * Where this build expects to be served from. Must match the deploy's VITE_BASE.
 *
 * Trimmed: `set VAR=value && cmd` on Windows puts the space before `&&` into the value, and a
 * base of "/migratlas/ " fails in ways that look nothing like a stray space.
 */
const BASE = (process.env.VITE_BASE ?? "/").trim();

const DIST = "dist";
const ASSETS = join(DIST, "assets");

/** Files a bundle may reference that live outside assets/ or are provided at runtime. */
const IGNORED = [
  /^https?:\/\//,
  /^data:/,
  /^blob:/,
  // MapLibre embeds both worker names as strings for its own runtime branch; the one it
  // actually uses is overridden by setWorkerUrl, so a bare mention is not a reference.
  /^maplibre-gl-worker(-dev)?\.mjs$/,
];

function fail(message) {
  console.error(`check-build: ${message}`);
  process.exitCode = 1;
}

if (!statSync(DIST, { throwIfNoEntry: false })) {
  fail(`no ${DIST}/ — run the build first`);
  process.exit(1);
}

const assetNames = new Set(readdirSync(ASSETS));
const jsFiles = [...assetNames].filter((name) => name.endsWith(".js") || name.endsWith(".mjs"));

// 1. A worker asset must exist. MapLibre cannot parse a single tile without it, and its
//    absence is invisible at runtime.
const workers = [...assetNames].filter((name) => /worker/i.test(name));
if (workers.length === 0) {
  fail(
    "no worker asset in dist/assets — MapLibre will 404 its worker and render nothing, " +
      "silently. Import it with ?worker&url and pass it to setWorkerUrl.",
  );
} else {
  console.log(`check-build: worker asset present (${workers.join(", ")})`);
}

// 2. Every hashed sibling a bundle names must have been emitted. A dangling name is answered
//    by a dev server's SPA fallback with index.html and a 200, so the browser parses HTML as
//    JavaScript — which is exactly how this failed before.
// Must begin with an alphanumeric: MapLibre embeds the bare suffix "-dev.mjs" to branch on
// its own filename, and that is a string comparison rather than a reference to anything.
const referencePattern = /["'`]([A-Za-z0-9][A-Za-z0-9._-]*\.(?:mjs|js))["'`]/g;
let dangling = 0;
for (const file of jsFiles) {
  const body = readFileSync(join(ASSETS, file), "utf8");
  for (const [, referenced] of body.matchAll(referencePattern)) {
    if (IGNORED.some((pattern) => pattern.test(referenced))) continue;
    if (referenced === file) continue;
    if (!assetNames.has(referenced)) {
      fail(`${file} references ${referenced}, which was not emitted`);
      dangling += 1;
    }
  }
}
if (dangling === 0) console.log(`check-build: no dangling asset references in ${jsFiles.length} bundles`);

// 3. The worker must be self-contained. Vite's ?worker&url inlines its dependencies; a plain
//    file copy does not, and the difference is invisible until runtime.
for (const worker of workers) {
  const body = readFileSync(join(ASSETS, worker), "utf8");
  const imports = [...body.matchAll(/\bfrom\s*["']([^"']+)["']/g)].map(([, target]) => target);
  const external = imports.filter((target) => target.startsWith(".") || target.startsWith("/"));
  if (external.length > 0) {
    fail(`${worker} still imports ${external.join(", ")} — use ?worker&url so deps are bundled`);
  }
}

// 4. index.html must reference its assets at the base it was built for. A subpath deploy that
//    rebuilds without VITE_BASE emits /assets/index.js instead of /migratlas/assets/index.js:
//    every asset 404s, the page is blank, and the deploy is green. That shipped once.
const html = readFileSync(join(DIST, "index.html"), "utf8");
const referenced = [...html.matchAll(/(?:src|href)="([^"]+)"/g)]
  .map(([, url]) => url)
  .filter((url) => url.includes("/assets/"));

if (referenced.length === 0) {
  fail("index.html references no assets at all");
} else {
  const wrong = referenced.filter((url) => !url.startsWith(`${BASE}assets/`));
  if (wrong.length > 0) {
    fail(
      `index.html references ${wrong.join(", ")} but this build is based at "${BASE}". ` +
        "Every asset would 404 and the page would render nothing. Set VITE_BASE for the build.",
    );
  } else {
    console.log(`check-build: ${referenced.length} asset references match base "${BASE}"`);
  }
}

if (process.exitCode) {
  console.error("check-build: FAILED");
} else {
  console.log("check-build: ok");
}
