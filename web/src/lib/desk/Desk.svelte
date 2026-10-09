<script lang="ts">
  import type { Desk } from "./scene";

  let { book }: { book: HTMLElement | null } = $props();

  let canvas = $state<HTMLCanvasElement | null>(null);
  /** Exposed on the canvas for the tests: whether the candle is out, being lit, or burning. */
  let candle = $state<"loading" | "failed" | "software" | "out" | "lighting" | "lit">("loading");

  /*
    Whether this browser draws WebGL without a graphics card. The scene is a background and should
    cost nothing a reader notices; drawn in software, one frame of it took seconds and stalled the
    page. So there the painted wood is the table. `?desk=3d` draws it anyway -- the suite uses it,
    since a CI runner has no graphics card and the scene would otherwise never be tested.
  */
  function software(): boolean {
    if (new URLSearchParams(location.search).get("desk") === "3d") return false;
    const probe = document.createElement("canvas").getContext("webgl");
    const info = probe?.getExtension("WEBGL_debug_renderer_info");
    const name = info ? String(probe!.getParameter(info.UNMASKED_RENDERER_WEBGL)) : "";
    probe?.getExtension("WEBGL_lose_context")?.loseContext();
    return /swiftshader|llvmpipe|softpipe|software|basic render/i.test(name);
  }

  $effect(() => {
    const surface = canvas;
    const page = book;
    if (!surface || !page) return;
    let desk: Desk | null = null;
    let gone = false;
    const root = document.documentElement;
    // The candle burns when the surface says night: `--candle-lit` is that answer, by the reader's
    // choice or the system's, and `tokens.css` is the one place that knows which.
    const lit = () => getComputedStyle(root).getPropertyValue("--candle-lit").trim() === "1";

    /*
      Loaded after the book, never before it: the table is what the book lies on, not what a reader
      came for, and three.js and the models are about a megabyte the first page should not wait on.
      If the browser cannot draw it, the painted wood under the canvas is the table instead.
    */
    void (async () => {
      if (software()) {
        candle = "software";
        return;
      }
      await document.fonts.ready;
      await new Promise((settle) => setTimeout(settle, 150));
      const { createDesk } = await import("./scene");
      if (gone) return;
      const made = await createDesk(surface, page, import.meta.env.BASE_URL, lit(), (state) => (candle = state));
      if (gone) made.dispose();
      else desk = made;
    })().catch(() => (candle = "failed"));

    const follow = () => desk?.setLit(lit(), true);
    const watch = new MutationObserver(follow);
    watch.observe(root, { attributes: true, attributeFilter: ["data-surface"] });
    const system = matchMedia("(prefers-color-scheme: dark)");
    system.addEventListener("change", follow);
    const sized = new ResizeObserver(() => desk?.place());
    sized.observe(surface);
    sized.observe(page);

    return () => {
      gone = true;
      watch.disconnect();
      system.removeEventListener("change", follow);
      sized.disconnect();
      desk?.dispose();
    };
  });
</script>

<!--
  The table the journal lies open on: a real scene drawn under the page -- see `scene.ts`. Purely a
  picture: nothing here is read, focused or clicked.
-->
<canvas
  bind:this={canvas}
  class="desk-scene"
  class:desk-scene--ready={candle === "out" || candle === "lighting" || candle === "lit"}
  data-candle={candle}
  aria-hidden="true"
></canvas>

<style>
  .desk-scene {
    position: absolute;
    inset: 0;
    z-index: -1;
    width: 100%;
    height: 100%;
    pointer-events: none;
    opacity: 0;
    transition: opacity var(--draw-slow) var(--ease-pen);
  }

  .desk-scene--ready {
    opacity: 1;
  }
</style>
