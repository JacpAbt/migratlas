import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  // Set VITE_BASE=/migratlas/ when deploying to a project subpath.
  const env = loadEnv(mode, process.cwd(), "VITE_");

  return {
    // Trimmed: `set VAR=value && cmd` on Windows carries the trailing space into the value.
    base: (env.VITE_BASE ?? "/").trim(),
    // MapLibre must not be pre-bundled. Its ESM worker is referenced relatively, and the dep
    // optimiser rewrites the import so maplibre-gl-worker.mjs 404s in dev. MapLibre then
    // silently does nothing: sources never finish loading, no tiles are requested, and the
    // map renders an empty canvas with no console error at all. Verified by a 404 on the
    // worker URL while module workers themselves worked.
    optimizeDeps: { exclude: ["maplibre-gl"] },
    build: {
      target: "es2023",
      // MapLibre alone is ~940 kB raw / ~245 kB gzipped and cannot be code-split
      // meaningfully -- it is one WebGL engine. It sits in its own chunk below, so it is
      // fetched once and cached across deploys. Warning at 500 kB would fire forever.
      chunkSizeWarningLimit: 1000,
      // No manualChunks. Forcing every module matching "maplibre-gl" into one chunk also
      // swallowed its Web Worker, which must stay a separately emitted file for
      // `new Worker(new URL("maplibre-gl-worker.mjs", import.meta.url))` to resolve. The
      // result was a completely silent failure: no console error, 60 fps, and an empty
      // globe. A caching micro-optimisation is not worth that.
    },
  };
});
