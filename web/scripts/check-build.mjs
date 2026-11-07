/**
 * Assert the built output has no dangling references: no bundle naming a file that was not emitted,
 * no data file the atlas draws from left out, no asset path built for the wrong base.
 *
 * Written after shipping a globe that never rendered. MapLibre's Web Worker was referenced but never
 * emitted, so it 404ed at runtime -- and the failure was silent: no console error, a healthy 60 fps,
 * an empty canvas. `tsc` passed and `vite build` passed. CI was green throughout. MapLibre left the
 * build with ADR 0021; the atlas that replaced it fails the same way for a different reason, a data
 * file it fetches at runtime that is not there, which is what the second check is for.
 *
 * This cannot replace a browser smoke test, but it is free and catches the specific class: an
 * emitted build naming a sibling file that does not exist.
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
const IGNORED = [/^https?:\/\//, /^data:/, /^blob:/];

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

// 1. Every hashed sibling a bundle names must have been emitted. A dangling name is answered by a
//    dev server's SPA fallback with index.html and a 200, so the browser parses HTML as JavaScript
//    -- which is exactly how the globe failed. A name must begin with an alphanumeric, so a bare
//    suffix compared as a string is not read as a reference.
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

// 2. Every file the atlas draws from must be in the build. It fetches them at runtime, and a missing
//    one leaves it waiting on a promise that rejects into the console: the page and its words are
//    there, and the map is blank paper. Named by the documents the atlas reads -- each plate's map
//    and each still map's cells in `atlas.json`, each layer in the manifest -- and the world's
//    outline, which `lib/atlas/data.ts` names itself.
const read = (path) => JSON.parse(readFileSync(join(DIST, path), "utf8"));
const atlas = read("atlas.json");
const manifest = read("layers/manifest.json");
const EXTENSION = { geojson: ".geojson", grid: ".grid.json", json: ".json" };
const wanted = [
  "basemap/land.geojson",
  "basemap/borders.geojson",
  ...atlas.plates.map((plate) => plate.map),
  ...atlas.stills.flatMap((still) => [still.data, ...(still.plate ? [still.plate.map] : [])]),
  ...manifest.map((layer) => `layers/${layer.name}${EXTENSION[layer.format] ?? ".json"}`),
];
const missing = wanted.filter((path) => !statSync(join(DIST, path), { throwIfNoEntry: false }));
if (missing.length > 0) {
  fail(`the atlas draws from ${missing.join(", ")}, which the build does not contain`);
} else {
  console.log(`check-build: all ${wanted.length} files the atlas draws from are in the build`);
}

// 3. index.html must reference its assets at the base it was built for. A subpath deploy that
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
