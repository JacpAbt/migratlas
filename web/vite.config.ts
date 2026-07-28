import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  // Set VITE_BASE=/migratlas/ when deploying to a project subpath.
  const env = loadEnv(mode, process.cwd(), "VITE_");

  return {
    base: env.VITE_BASE ?? "/",
    build: {
      target: "es2023",
      // MapLibre alone is ~940 kB raw / ~245 kB gzipped and cannot be code-split
      // meaningfully -- it is one WebGL engine. It sits in its own chunk below, so it is
      // fetched once and cached across deploys. Warning at 500 kB would fire forever.
      chunkSizeWarningLimit: 1000,
      rollupOptions: {
        output: {
          // MapLibre is large and changes far less often than our code, so it gets
          // its own long-lived cache entry.
          manualChunks: (id) => (id.includes("maplibre-gl") ? "maplibre" : undefined),
        },
      },
    },
  };
});
