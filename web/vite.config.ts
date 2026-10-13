import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  // Set VITE_BASE=/migratlas/ when deploying to a project subpath.
  const env = loadEnv(mode, process.cwd(), "VITE_");

  return {
    plugins: [svelte()],
    // Trimmed: `set VAR=value && cmd` on Windows carries the trailing space into the value.
    base: (env.VITE_BASE ?? "/").trim(),
    build: {
      target: "es2023",
      // The desk's scene is three.js, about 660 kB raw and 170 kB compressed, in a chunk of its
      // own that the book does not wait for. One engine, not something to split further, so a
      // warning at Vite's 500 kB would fire on every build and teach everyone to ignore it.
      chunkSizeWarningLimit: 1000,
    },
  };
});
