<script lang="ts">
  import { clock, world as pocket } from "../book/pocket.svelte";
  import { castOf, loadCells, WEEKS, type PlateWords, type Words } from "./data";
  import { Herd } from "./herd";
  import { Ice } from "./ice";
  import { palette } from "./ink";
  import { JOURNEY_DAYS, Journeys } from "./journeys";
  import { NightSky } from "./night";
  import { Stage, type StageState } from "./stage";
  import { STATUS_INK, StillMap } from "./still";

  /**
   * `spread`: drawn across both pages, as an atlas plate crosses the fold. `leaf`: one phone leaf,
   * the controls in the flap at its foot.
   */
  let { base, layout }: { base: string; layout: "spread" | "leaf" } = $props();

  let host = $state<HTMLDivElement | null>(null);
  let sheetA = $state<HTMLCanvasElement | null>(null);
  let sheetB = $state<HTMLCanvasElement | null>(null);
  let sheetTrails = $state<HTMLCanvasElement | null>(null);
  let sheetLive = $state<HTMLCanvasElement | null>(null);
  let words = $state<Words | null>(null);
  let layerNotes = $state<Record<string, string>>({});
  let stage: Stage | null = null;
  let size = $state({ w: 0, h: 0 });
  let now = $state<StageState | null>(null);
  let anchors = $state<Record<string, [number, number]>>({});
  let flap = $state<"peek" | "open">("peek");

  const showing = $derived(now?.showing ?? "world");
  const plate = $derived(words?.plates.find((p) => p.name === showing) ?? null);

  /*
    The still maps, each fetched the first time it is switched on and kept: never on arrival, so the
    chapter's opening payload is what it was before they existed (ADR 0021 step 6's kill condition).
  */
  const stillMaps = new Map<string, Promise<StillMap>>();
  let stillMap = $state<StillMap | null>(null);
  const still = $derived(words?.stills.find((s) => s.name === now?.still) ?? null);
  const shownMap = $derived(still && stillMap?.words.name === still.name ? stillMap : null);
  /** A still layer's own description, or the assessment's statement, which no layer manifest holds. */
  const stillNote = $derived(still ? (layerNotes[still.name] ?? shownMap?.cells.note ?? "") : "");
  let paused = $state(false);
  let speed = $state(1);

  /*
    Where each callout sits from its place, as fractions of the sheet's width: hand-placed for the
    spread, where the four places are far enough apart to name in the margins round them. A phone
    names them in the flap's list instead.
  */
  const OFFSET: Record<string, [number, number]> = {
    "north-america": [-0.19, 0.075],
    bylot: [0.03, -0.056],
    svalbard: [0.032, 0.032],
    "ya-ha-tinda": [-0.17, 0.01],
  };

  /** The map's frame on the sheet: the clock and the words have the margins. */
  function mapBox(w: number, h: number): { x: number; y: number; w: number; h: number } {
    return layout === "spread"
      ? { x: w * 0.03, y: h * 0.1, w: w * 0.94, h: h * 0.76 }
      : { x: w * 0.02, y: h * 0.12, w: w * 0.96, h: h * 0.62 };
  }

  $effect(() => {
    const canvasA = sheetA;
    const canvasB = sheetB;
    const trails = sheetTrails;
    const live = sheetLive;
    const root = host;
    if (!canvasA || !canvasB || !trails || !live || !root) return;
    let gone = false;
    let made: Stage | null = null;
    let cleanup = (): void => {};

    void (async () => {
      const cast = await castOf(base);
      if (gone) return;
      const w = cast.words;
      words = w;
      layerNotes = cast.notes;
      made = new Stage(
        { A: canvasA, B: canvasB, trails, live },
        {
          world: cast.world,
          night: new NightSky(cast.radar),
          journeys: new Journeys(cast.journeys),
          herds: { svalbard: new Herd(cast.herds.svalbard), "ya-ha-tinda": new Herd(cast.herds["ya-ha-tinda"]) },
          ice: new Ice(cast.ice),
        },
        w,
        base,
        palette(root),
        (clock.state.day / 365) * WEEKS,
        (next) => {
          now = next;
          if (!next.moving && !stage?.holding) clock.set({ day: Math.min(365, Math.floor((next.week / WEEKS) * 365)) });
        },
      );
      stage = made;
      const fit = (): void => {
        const r = root.getBoundingClientRect();
        size = { w: r.width, h: r.height };
        made?.layout(r.width, r.height, mapBox(r.width, r.height));
        anchors = Object.fromEntries(w.plates.map((p) => [p.name, made!.anchor(p)]));
      };
      fit();
      made.start();
      /*
        The still, from the first frames and not only on leaving. Arriving is a turn too, and the
        incoming page on its leaf showed paper over the atlas's half until this atlas had once been
        left -- the first visit always. Two frames, so the map and the first marks are on the sheets.
        Measured at 12 ms at 1x and 40 ms at 2x, once, while the turn runs on the compositor.
      */
      requestAnimationFrame(() =>
        requestAnimationFrame(() => {
          if (!gone && made) pocket.still = made.picture();
        }),
      );
      if (new URLSearchParams(location.search).has("debug")) {
        (window as unknown as { migratlas: Record<string, unknown> }).migratlas = {
          ...((window as unknown as { migratlas?: Record<string, unknown> }).migratlas ?? {}),
          atlas: made,
        };
      }
      const sized = new ResizeObserver(fit);
      sized.observe(root);
      const repaint = (): void => made?.repaint(palette(root));
      const watch = new MutationObserver(repaint);
      watch.observe(document.documentElement, { attributes: true, attributeFilter: ["data-surface", "data-type"] });
      const system = matchMedia("(prefers-color-scheme: dark)");
      system.addEventListener("change", repaint);
      const hidden = (): void => (document.hidden ? made?.stop() : made?.start());
      document.addEventListener("visibilitychange", hidden);
      cleanup = () => {
        sized.disconnect();
        watch.disconnect();
        system.removeEventListener("change", repaint);
        document.removeEventListener("visibilitychange", hidden);
      };
    })();

    return () => {
      gone = true;
      cleanup();
      // What a turning page shows of the atlas while it turns: this, as it was.
      if (made) pocket.still = made.picture();
      made?.dispose();
      stage = null;
    };
  });

  function choose(name: string): void {
    void stage?.show(name);
    flap = "peek";
  }

  /** Switch a still map on, where it is drawn; or off again, back to the moving world. */
  async function chooseStill(name: string): Promise<void> {
    flap = "peek";
    const said = words?.stills.find((s) => s.name === name);
    if (!stage || !said) return;
    if (now?.still === name) {
      void stage.show("world");
      return;
    }
    let pending = stillMaps.get(name);
    if (!pending) {
      pending = loadCells(base, said).then((cells) => new StillMap(said, cells));
      // A failed fetch is forgotten, so the next press asks again.
      pending.catch(() => stillMaps.delete(name));
      stillMaps.set(name, pending);
    }
    const map = await pending;
    if (!stage) return;
    stillMap = map;
    void stage.show(said.plate?.name ?? "world", map);
  }

  function toggle(): void {
    if (!stage) return;
    stage.playing = !stage.playing;
    paused = !stage.playing;
  }

  function pace(value: number): void {
    speed = value;
    if (stage) stage.speed = value;
  }

  // --- The clock: the year, or the days of a fox's journey ------------------------------------

  let rail = $state<SVGSVGElement | null>(null);
  let railWidth = $state(0);
  // The months' names from the locale rather than typed: they are a calendar, not this page's prose.
  const MONTHS = Array.from({ length: 12 }, (_, i) =>
    new Date(Date.UTC(2023, i, 1)).toLocaleString("en-GB", { month: "short", timeZone: "UTC" }),
  );
  const journey = $derived(now?.clock === "journey");
  const marks = $derived(
    journey
      ? Array.from({ length: 9 }, (_, i) => ({ at: i / 8, text: i === 0 ? "1" : String(i * 50) }))
      : MONTHS.map((month, i) => ({ at: i / 12, text: month })),
  );
  const markAt = $derived(
    now ? (journey ? Math.min(now.day, JOURNEY_DAYS) / JOURNEY_DAYS : now.week / WEEKS) : 0,
  );
  const line = $derived.by(() => {
    let d = "M 0 9";
    for (let x = 12; x <= railWidth; x += 12) d += ` L ${x} ${(9 + Math.sin(x * 0.05) * 0.9 + Math.sin(x * 0.013) * 1.4).toFixed(2)}`;
    return d;
  });

  function seek(event: PointerEvent): void {
    if (!rail || !stage) return;
    const r = rail.getBoundingClientRect();
    const f = Math.max(0, Math.min(0.9999, (event.clientX - r.left) / r.width));
    if (journey) stage.day = f * JOURNEY_DAYS;
    else stage.week = f * WEEKS;
  }

  function dateOf(week: number): string {
    const day = Math.floor((week / WEEKS) * 365);
    return new Date(Date.UTC(2023, 0, 1 + day)).toLocaleString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
  }

  /** The animal layers' generalisation statement, which a caption never repeats. */
  const note = $derived(plate ? (layerNotes[plate.layer] ?? "") : "");

  const leader = (name: string, anchor: [number, number]): string => {
    const [ax, ay] = anchor;
    const [fx, fy] = OFFSET[name] ?? [0, 0];
    const lx = ax + fx * size.w;
    const ly = ay + fy * size.w;
    return `M ${ax} ${ay} Q ${(ax + lx) / 2 + 10} ${(ay + ly) / 2 - 10} ${lx} ${ly}`;
  };
</script>

<!--
  The world chapter as a drawn atlas (ADR 0021). The canvases are the map and what moves on it; the
  words, the controls and the callouts are the page's, so they are read, focused and clicked as text.
-->
<div class="atlas atlas--{layout}" bind:this={host} data-showing={showing} data-moving={now?.moving ? "" : undefined}>
  <canvas class="sheet" bind:this={sheetA} aria-hidden="true"></canvas>
  <canvas class="sheet sheet--over" bind:this={sheetB} aria-hidden="true"></canvas>
  <canvas class="sheet" bind:this={sheetTrails} aria-hidden="true"></canvas>
  <canvas class="sheet" bind:this={sheetLive} aria-hidden="true"></canvas>

  {#if words}
    <h2 class="atlas__title">{still?.title ?? plate?.title ?? words.world.title}</h2>
    <p class="atlas__now" role="status">
      <span class="atlas__date">{now ? (journey ? "" : dateOf(now.week)) : ""}</span>
      <span class="atlas__what">{now?.readout ?? ""}</span>
    </p>

    {#if layout === "spread"}
      <svg class="atlas__leaders" aria-hidden="true" style:opacity={now?.callouts ?? 1}>
        {#each words.plates as p (p.name)}
          {@const anchor = anchors[p.name]}
          {#if anchor}
            <path d={leader(p.name, anchor)} />
            <circle cx={anchor[0]} cy={anchor[1]} r="2" />
          {/if}
        {/each}
      </svg>
      <div class="atlas__callouts" style:opacity={now?.callouts ?? 1} class:is-off={(now?.callouts ?? 1) < 0.9}>
        {#each words.plates as p (p.name)}
          {@const anchor = anchors[p.name]}
          {#if anchor}
            {@const [fx, fy] = OFFSET[p.name] ?? [0, 0]}
            <button
              type="button"
              class="callout"
              style:left="{anchor[0] + fx * size.w}px"
              style:top="{anchor[1] + fy * size.w}px"
              onclick={() => choose(p.name)}
              tabindex={(now?.callouts ?? 1) < 0.9 ? -1 : 0}
            >
              {p.callout}<small>{p.under}</small>
            </button>
          {/if}
        {/each}
      </div>
    {/if}

    <div class="atlas__slips" class:atlas__slips--flap={layout === "leaf"} class:is-open={flap === "open"}>
      {#if layout === "leaf"}
        <button type="button" class="flap__grip" aria-expanded={flap === "open"} onclick={() => (flap = flap === "open" ? "peek" : "open")}>
          {words.controls.show}
        </button>
      {/if}
      <div class="slip slip--caption">
        {#if still}
          <p><strong>{still.lead}</strong> {still.caption}</p>
          {#if shownMap}
            <ul class="key" class:key--count={shownMap.kind === "count"}>
              {#if shownMap.kind === "status"}
                {@const shares = shownMap.shares()}
                {#each still.key as row (row.value)}
                  {@const ink = STATUS_INK[row.value]}
                  <li>
                    <svg class="key__mark" viewBox="0 0 12 12" aria-hidden="true">
                      <rect
                        x="1"
                        y="1"
                        width="10"
                        height="10"
                        style:fill={ink?.tone === "accent" ? "var(--rust-ink)" : "var(--pencil)"}
                        style:fill-opacity={ink?.alpha ?? 0.3}
                      />
                    </svg>
                    <span>{row.means}</span>
                    <em>{(shares[row.value] ?? 0).toFixed(1)}%</em>
                  </li>
                {/each}
              {:else if shownMap.kind === "change"}
                {#each still.key as row (row.value)}
                  <li>
                    <svg class="key__mark" viewBox="0 0 12 12" aria-hidden="true">
                      <circle cx="6" cy="6" r="4" class={row.value} />
                    </svg>
                    <span>{row.means}</span>
                  </li>
                {/each}
              {:else}
                {#each shownMap.samples() as count (count)}
                  <li>
                    <svg class="key__mark" viewBox="0 0 12 12" aria-hidden="true">
                      <circle cx="6" cy="6" r={(5.5 * shownMap.dot(count)) / 0.48} />
                    </svg>
                    <em>{count.toLocaleString("en-GB")}</em>
                  </li>
                {/each}
                <li class="key__unit">{still.unit}</li>
              {/if}
            </ul>
          {/if}
          <p class="slip__note">{words.world.still}</p>
          {#if stillNote}<p class="slip__note">{stillNote}</p>{/if}
          <p class="slip__note terms">{still.credit}</p>
          {#if still.plate}<p class="slip__note">{still.plate.credit}</p>{/if}
        {:else}
          <p>
            <strong>{plate?.lead ?? words.world.lead}</strong>
            {plate?.caption ?? words.world.caption}
          </p>
          {#if note}<p class="slip__note">{note}</p>{/if}
          {#if plate}<p class="slip__note">{plate.credit}</p>{/if}
        {/if}
      </div>
      <div class="slip slip--controls">
        <div class="show" role="group" aria-label={words.controls.show}>
          <span>{words.controls.show}</span>
          <button type="button" aria-pressed={showing === "world" && !now?.still} onclick={() => choose("world")}>
            {words.controls.world}
          </button>
          {#each words.plates as p (p.name)}
            <button type="button" aria-pressed={showing === p.name} onclick={() => choose(p.name)}>{p.button}</button>
          {/each}
        </div>
        <div class="show show--stills" role="group" aria-label={words.controls.stills}>
          <span>{words.controls.stills}</span>
          {#each words.stills as s (s.name)}
            <button type="button" aria-pressed={now?.still === s.name} onclick={() => void chooseStill(s.name)}>
              {s.button}
            </button>
          {/each}
        </div>
        <div class="row">
          <button type="button" onclick={toggle}>{paused ? words.controls.play : words.controls.pause}</button>
          <span aria-hidden="true">·</span>
          {#each [[0.5, words.controls.slow], [1, words.controls.normal], [2, words.controls.fast]] as const as [value, label] (value)}
            <button type="button" aria-pressed={speed === value} onclick={() => pace(value)}>{label}</button>
          {/each}
        </div>
      </div>
    </div>

    <div class="atlas__clock" bind:clientWidth={railWidth}>
      <svg
        bind:this={rail}
        role="slider"
        tabindex="0"
        aria-label={journey ? words.controls.journey : words.controls.clock}
        aria-valuemin="0"
        aria-valuemax={journey ? JOURNEY_DAYS : WEEKS}
        aria-valuenow={Math.round(journey ? (now?.day ?? 0) : (now?.week ?? 0))}
        onpointerdown={(e) => {
          if (stage) stage.holding = true;
          rail?.setPointerCapture(e.pointerId);
          seek(e);
        }}
        onpointermove={(e) => stage?.holding && seek(e)}
        onpointerup={() => stage && (stage.holding = false)}
        onkeydown={(e) => {
          if (!stage || (e.key !== "ArrowLeft" && e.key !== "ArrowRight")) return;
          const by = e.key === "ArrowLeft" ? -1 : 1;
          if (journey) stage.day = Math.max(0, Math.min(JOURNEY_DAYS, stage.day + by * 7));
          else stage.week = (stage.week + by + WEEKS) % WEEKS;
        }}
      >
        <path class="rail" d={line} />
        {#each marks as m (m.text)}
          <line class="tick" x1={m.at * railWidth} x2={m.at * railWidth} y1="4" y2="14" />
          <text x={m.at * railWidth + 4} y="30">{m.text}</text>
        {/each}
        <path
          class="mark"
          d="M {markAt * railWidth - 0.5} -2 L {markAt * railWidth + 0.6} 18 M {markAt * railWidth - 4} 0 L {markAt * railWidth} -4 L {markAt * railWidth + 4.5} 0.5"
        />
      </svg>
    </div>
  {/if}
</div>

<style>
  .atlas {
    position: absolute;
    inset: 0;
    overflow: hidden;
    color: var(--ink);
    font-family: var(--font-body);
    /* The map and its strokes take no pointer: only the words and controls on it do. */
    pointer-events: none;
  }

  .sheet {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }

  .sheet--over {
    opacity: 0;
  }

  .atlas__title {
    position: absolute;
    left: 4%;
    top: 4%;
    max-width: 38%;
    margin: 0;
    font-family: var(--font-hand);
    font-size: var(--size-lede);
    font-weight: 400;
    line-height: 1.15;
    rotate: -1deg;
  }

  .atlas__now {
    position: absolute;
    right: 4%;
    top: 4%;
    margin: 0;
    max-width: 40%;
    text-align: right;
    font-size: var(--size-margin);
    line-height: 1.35;
    rotate: 0.8deg;
  }

  .atlas__date {
    display: block;
    font-family: var(--font-hand);
    font-size: var(--size-lede);
  }

  .atlas__what {
    color: var(--rust);
  }

  .atlas__title,
  .atlas__now {
    text-shadow:
      0 0 4px var(--paper),
      0 0 8px var(--paper);
  }

  .atlas__leaders {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    overflow: visible;
    stroke: var(--ink);
    fill: var(--ink);
    stroke-width: 1;
    transition: opacity var(--draw-quick);
  }

  .atlas__leaders path {
    fill: none;
    opacity: 0.7;
  }

  .atlas__callouts {
    position: absolute;
    inset: 0;
    transition: opacity var(--draw-quick);
  }

  .atlas__callouts.is-off {
    pointer-events: none;
  }

  .callout {
    position: absolute;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    pointer-events: auto;
    padding: 0.2em 0.45em;
    font: inherit;
    font-family: var(--font-hand);
    font-size: var(--size-margin);
    line-height: 1.15;
    text-align: left;
    color: var(--ink);
    background: color-mix(in srgb, var(--paper) 80%, transparent);
    border: 0;
    rotate: -1.2deg;
    cursor: pointer;
    text-decoration: underline wavy color-mix(in srgb, var(--rust-ink) 60%, transparent);
    text-underline-offset: 0.3em;
  }

  .callout small {
    font-family: var(--font-body);
    font-size: 0.78em;
    color: var(--ink-soft);
  }

  .callout:hover,
  .callout:focus-visible {
    color: var(--rust);
  }

  .slip {
    pointer-events: auto;
    padding: 0.7em 0.9em;
    background: var(--plate-paper);
    box-shadow:
      0 1px 1px rgb(0 0 0 / 14%),
      2px 4px 8px rgb(30 18 6 / 22%);
    font-size: var(--size-margin);
    line-height: 1.45;
  }

  .slip p {
    margin: 0;
  }

  .slip p + p {
    margin-top: 0.4em;
  }

  /* A still map's key: what each mark is, and for the assessment how much of the world it covers. */
  .key {
    list-style: none;
    margin: 0.45em 0 0;
    padding: 0;
    display: grid;
    gap: 0.1em;
  }

  .key li {
    display: flex;
    align-items: center;
    gap: 0.45em;
  }

  .key em {
    margin-left: auto;
    font-style: normal;
    font-variant-numeric: tabular-nums;
  }

  .key--count {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.15em 0.8em;
  }

  .key--count em {
    margin-left: 0;
  }

  .key__mark {
    flex: none;
    width: 0.95em;
    height: 0.95em;
    overflow: visible;
  }

  .key--count circle,
  .key .gain {
    fill: var(--ink);
  }

  .key .loss {
    fill: none;
    stroke: var(--rust-ink);
    stroke-width: 1.5;
  }

  .slip__note {
    color: var(--ink-soft);
    font-size: 0.9em;
  }

  .atlas--spread .slip--caption {
    position: absolute;
    left: 3%;
    bottom: calc(14% + 1.6rem);
    max-width: 26%;
    rotate: -0.6deg;
  }

  .atlas--spread .slip--controls {
    position: absolute;
    right: 3%;
    bottom: calc(14% + 1.6rem);
    rotate: 0.6deg;
  }

  .slip--controls {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.35em;
    font-size: var(--size-label);
  }

  .show {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.1em;
  }

  .show > span,
  .row {
    color: var(--ink-soft);
  }

  .row {
    display: flex;
    gap: 0.5em;
    align-items: baseline;
  }

  .slip--controls button {
    font: inherit;
    color: var(--ink);
    background: none;
    border: 0;
    padding: 0.1em 0.2em;
    cursor: pointer;
    text-decoration: underline wavy color-mix(in srgb, var(--rust-ink) 70%, transparent);
    text-underline-offset: 0.25em;
  }

  .slip--controls button[aria-pressed="true"] {
    color: var(--rust);
  }

  /* Clear of the folios below it: the folio in each outer corner is the page's turn control, and
     a clock laid over it took the click. */
  .atlas__clock {
    position: absolute;
    left: 6%;
    right: 6%;
    bottom: calc(3.5% + 1.6rem);
    height: 36px;
    pointer-events: auto;
  }

  .atlas__clock svg {
    width: 100%;
    height: 100%;
    overflow: visible;
    cursor: ew-resize;
    touch-action: none;
  }

  .atlas__clock text {
    font-size: 12px;
    font-family: var(--font-body);
    fill: var(--ink-soft);
  }

  .rail {
    fill: none;
    stroke: var(--ink);
    stroke-width: 1.3;
    stroke-linecap: round;
  }

  .tick {
    stroke: var(--ink-soft);
  }

  .mark {
    fill: none;
    stroke: var(--rust-ink);
    stroke-width: 2.4;
    stroke-linecap: round;
  }

  /* --- One leaf, on a phone: the slips in a flap at the foot ------------------------------- */

  /* Under the settings, which sit over the top of a phone's leaf. */
  .atlas--leaf .atlas__title {
    top: calc(4% + 2.4rem);
    max-width: 80%;
  }

  .atlas--leaf .atlas__now {
    top: auto;
    bottom: 34%;
    left: 4%;
    right: 4%;
    max-width: none;
    text-align: left;
  }

  .atlas--leaf .atlas__clock {
    bottom: calc(var(--page-foot, 0px) + 3.2rem);
  }

  .atlas__slips--flap {
    position: absolute;
    inset: auto 0 var(--page-foot, 0);
    z-index: 2;
    display: flex;
    flex-direction: column;
    gap: 0.5em;
    max-height: 3rem;
    overflow: hidden;
    pointer-events: auto;
    background: var(--plate-paper);
    border-top: 1px solid var(--rule);
    box-shadow: 0 -3px 10px rgb(0 0 0 / 14%);
    transition: max-height var(--draw-quick);
  }

  .atlas__slips--flap.is-open {
    max-height: 70%;
    overflow-y: auto;
  }

  .atlas__slips--flap .slip {
    box-shadow: none;
    background: none;
  }

  .flap__grip {
    padding: 0.6rem var(--gap-tight);
    font-family: var(--font-body);
    font-size: var(--size-label);
    letter-spacing: var(--tracking-label);
    text-transform: uppercase;
    text-align: left;
    color: var(--ink-soft);
    background: none;
    border: 0;
    cursor: pointer;
  }
</style>
