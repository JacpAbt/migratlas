import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

export default {
  // Needed for `lang="ts"` in components. The project has no svelte-check -- that tool pins
  // TypeScript at 6 and this repo is on 7 -- so types inside markup are not checked; keep logic in
  // `.ts` where `tsc --noEmit` sees it and components thin.
  preprocess: vitePreprocess(),
  compilerOptions: {
    // Explicit rather than inferred, so a stray legacy-syntax component fails loudly instead of
    // silently opting the whole app out of runes.
    runes: true,
  },
};
