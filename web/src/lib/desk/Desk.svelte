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
      Loaded as soon as the book is on the page, and shown on its first finished frame with no fade:
      the owner saw the painted wood for a second and then the table fade in over it, and asked for
      the table at once. Until then the margin is the table's own colour, `--table-tone`. It used to
      wait for the fonts and 150 ms more, so as not to compete with the book; the book's own files
      are requested before this runs, and three.js is a separate chunk, so the page never waits on it.
      If the browser cannot draw it, the painted walnut is the table instead.
    */
    void (async () => {
      if (software()) {
        candle = "software";
        return;
      }
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
{#if candle === "software" || candle === "failed"}
  <div class="desk-painted" aria-hidden="true"></div>
{/if}
<canvas
  bind:this={canvas}
  class="desk-scene"
  class:desk-scene--ready={candle === "out" || candle === "lighting" || candle === "lit"}
  data-candle={candle}
  aria-hidden="true"
></canvas>

<style>
  .desk-scene,
  .desk-painted {
    position: absolute;
    inset: 0;
    z-index: -1;
    width: 100%;
    height: 100%;
    pointer-events: none;
  }

  /* Hidden until its first frame is drawn, then shown in that frame: no fade. */
  .desk-scene {
    visibility: hidden;
  }

  .desk-scene--ready {
    visibility: visible;
  }

  .desk-painted {
    /*
      A walnut table, painted: what lies under the book wherever the scene is not drawn, as in a
      browser with no graphics card. Boards running across
      the window, each a slightly different tone with a dark seam between, the grain streaked along
      them, fine pores across it, daylight from the upper left and the room falling off toward the
      corners. At night the same wood, darker.

      The grain and the pores are noise generated in the browser, so nothing is downloaded for them.
    */
    background-color: var(--wood);
    background-image:
      radial-gradient(ellipse 90% 70% at 22% 0%, rgb(255 236 204 / var(--wood-light)), transparent 70%),
      radial-gradient(ellipse 75% 75% at 50% 50%, transparent 55%, rgb(24 12 4 / 50%) 100%),
      repeating-linear-gradient(
        to bottom,
        rgb(20 9 2 / 0%) 0 calc(24vh - 3px),
        rgb(20 9 2 / 55%) calc(24vh - 2px),
        rgb(255 220 180 / 12%) calc(24vh - 1px) 24vh
      ),
      repeating-linear-gradient(
        to bottom,
        rgb(255 240 220 / 6%) 0 24vh,
        rgb(0 0 0 / 7%) 24vh 48vh,
        rgb(255 240 220 / 2%) 48vh 72vh
      ),
      url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='p' x='0' y='0' width='100%25' height='100%25'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.02 0.9' numOctaves='2' seed='4' stitchTiles='stitch'/%3E%3CfeColorMatrix values='.33 .33 .33 0 0 .33 .33 .33 0 0 .33 .33 .33 0 0 0 0 0 0 1'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23p)'/%3E%3C/svg%3E"),
      url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1200' height='700'%3E%3Cfilter id='g' x='0' y='0' width='100%25' height='100%25'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.0016 0.055' numOctaves='5' seed='11' stitchTiles='stitch'/%3E%3CfeColorMatrix values='.33 .33 .33 0 0 .33 .33 .33 0 0 .33 .33 .33 0 0 0 0 0 0 1'/%3E%3CfeComponentTransfer%3E%3CfeFuncR type='linear' slope='2.4' intercept='-.7'/%3E%3CfeFuncG type='linear' slope='2.4' intercept='-.7'/%3E%3CfeFuncB type='linear' slope='2.4' intercept='-.7'/%3E%3C/feComponentTransfer%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23g)'/%3E%3C/svg%3E");
    background-size: auto, auto, auto, auto, 300px 300px, 1200px 700px;
    background-blend-mode: normal, multiply, normal, normal, soft-light, overlay;
  }
</style>
