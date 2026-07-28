import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  // Set VITE_BASE=/migratlas/ when deploying to a project subpath.
  const env = loadEnv(mode, process.cwd(), "VITE_");

  return {
    base: env.VITE_BASE ?? "/",
    build: {
      target: "es2023",
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
