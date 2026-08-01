<script lang="ts">
  import Rule from "../notebook/Rule.svelte";
  import Search from "./Search.svelte";
  import { legendRows, type DetectabilityDocument } from "../../layers/detectability";
  import type { Clock } from "../../state/time";
  import type { LoadedLayer } from "../../layers/types";
  import type { SpeciesSelection } from "../../layers/selection";
  import type { SpeciesSurfaces } from "../../search/taxon";

  let {
    layers,
    clock,
    day,
    minute,
    selection,
    surfaces,
    detectability,
    onfocus,
  }: {
    layers: LoadedLayer[];
    detectability: DetectabilityDocument | null;
    clock: Clock;
    /** Mirrored into state by the shell, since a Clock is not reactive by itself. */
    day: number;
    minute: number;
    selection: SpeciesSelection | null;
    surfaces: SpeciesSurfaces;
    onfocus: (at: [number, number]) => void;
  } = $props();

  let shown = $state(new Set<string>());
  let playing = $state(false);

  $effect(() => {
    shown = new Set(layers.filter((layer) => layer.visible ?? true).map((l) => l.meta.name));
  });

  function toggle(layer: LoadedLayer, on: boolean): void {
    layer.setVisible(on);
    const next = new Set(shown);
    if (on) next.add(layer.meta.name);
    else next.delete(layer.meta.name);
    shown = next;
  }

  // Required, not decorative: published data must never be separable from the terms it was published
  // under, so this shows the generalisation of every layer currently drawn.
  const terms = $derived([
    ...new Set(
      layers
        .filter((layer) => shown.has(layer.meta.name))
        .map((layer) => layer.terms["dwc:dataGeneralizations"])
        .filter(Boolean),
    ),
  ]);

  /**
   * The day of year as a date, formatted here rather than by trimming `formatInstant`'s output.
   *
   * That trim left "31 Jul, · week 31" on screen: the shared formatter includes a time, and cutting
   * " 09:21" off the end kept its comma. Reaching into another function's string is how that happens.
   */
  const dayLabel = $derived(
    new Date(Date.UTC(2001, 0, 1 + day)).toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
      timeZone: "UTC",
    }),
  );

  const detectabilityOn = $derived(shown.has("detectability"));
  const rows = $derived(detectability ? legendRows(detectability) : []);
</script>

<!--
  The tools, and only in explore mode.

  The old shell put these round the globe permanently, which made a *layer* the first-class thing.
  Here a claim is, and these are what is left once no claim is in hand: what is drawn, under what
  terms, at what time of year, and a way to find one animal.
-->
<aside class="explore" aria-label="Layers and time">
  <section>
    <h2>Drawn now</h2>
    <Rule seed="explore-layers" tone="pencil" />
    <ul class="layers">
      {#each layers as layer (layer.meta.name)}
        <li>
          <label>
            <input
              type="checkbox"
              checked={shown.has(layer.meta.name)}
              onchange={(event) => toggle(layer, event.currentTarget.checked)}
            />
            <span class="layers__title" title={layer.meta.description}>{layer.meta.title}</span>
            <em>{layer.meta.value_kind.replace(/_/g, " ")}</em>
          </label>
        </li>
      {/each}
    </ul>
    <!-- The key, whenever the layer it explains is drawn. Four unlabelled greys are not a map of
         anything, so this is required rather than a nicety -- and it was missing here while being
         present on the claim, which is the worse way round. -->
    {#if detectabilityOn && rows.length > 0}
      <ul class="key">
        {#each rows as row (row.status)}
          <li>
            <span class="key__swatch" style="background: {row.colour}"></span>
            <span class="key__means">{row.means}</span>
            <em>{row.share.toFixed(1)}%</em>
          </li>
        {/each}
      </ul>
    {/if}

    {#if terms.length > 0}
      <p class="terms">{terms.join(" ")}</p>
    {/if}
  </section>

  <section>
    <h2>Time of year</h2>
    <Rule seed="explore-time" tone="pencil" />
    <p class="clockface">{dayLabel} · week {Math.floor(day / 7) + 1}</p>
    <div class="time">
      <input
        type="range"
        min="0"
        max="365"
        step="1"
        value={day}
        aria-label="Day of year"
        oninput={(event) => clock.set({ day: event.currentTarget.valueAsNumber })}
      />
      <button
        type="button"
        aria-pressed={playing}
        onclick={() => {
          clock.toggle();
          playing = clock.playing;
        }}
      >
        {playing ? "Pause" : "Play"}
      </button>
    </div>
    <label class="utc">
      <span>Time of day, UTC</span>
      <input
        type="range"
        min="0"
        max="1439"
        step="10"
        value={minute}
        oninput={(event) => clock.set({ minute: event.currentTarget.valueAsNumber })}
      />
    </label>
    <p class="hint">
      This one moves the night terminator rather than the data: the radar layer is a weekly mean, and
      night is where the nocturnal migration in it happens. Only the nightly aerial passage is
      time-indexed. The gridded surfaces are one value per cell
      for their whole period, so the slider does not move them.
    </p>
  </section>

  <section>
    <h2>Find an animal</h2>
    <Rule seed="explore-search" tone="pencil" />
    <Search {selection} {surfaces} {onfocus} />
  </section>
</aside>

<style>
  .explore {
    position: absolute;
    top: var(--gap);
    right: var(--gap);
    z-index: 2;
    display: flex;
    flex-direction: column;
    gap: var(--gap);
    width: min(20rem, calc(100vw - 2 * var(--gap)));
    /* Clears the index strip below it and scrolls if it cannot fit, rather than growing under it. */
    max-height: calc(100% - var(--strip) - var(--attrib) - 2 * var(--gap));
    overflow-y: auto;
    padding: var(--gap);
    background-color: var(--paper);
    background-image: var(--grain);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    box-shadow: var(--shadow-sheet);
    font-size: 0.8rem;
  }

  h2 {
    margin: 0;
    font-family: var(--font-mono);
    font-size: var(--size-label);
    font-weight: 500;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--pencil);
  }

  .explore :global(.rule) {
    margin: var(--gap-hair) 0 var(--gap-tight);
    max-width: 8rem;
  }

  .layers {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .layers label {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0 var(--gap-tight);
    align-items: baseline;
    padding: 2px 0;
    cursor: pointer;
  }

  .layers input {
    accent-color: var(--rust-ink);
  }

  .layers__title {
    line-height: 1.35;
  }

  .layers em {
    grid-column: 2;
    font-family: var(--font-mono);
    font-style: normal;
    font-size: var(--size-label);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--pencil);
  }

  .key {
    margin: var(--gap-tight) 0 0;
    padding: 0 0 0 1.35rem;
    list-style: none;
    font-size: 0.7rem;
  }

  .key li {
    display: flex;
    align-items: baseline;
    gap: var(--gap-tight);
    margin-top: 1px;
    color: var(--ink-soft);
  }

  .key__swatch {
    flex: none;
    width: 0.55rem;
    height: 0.55rem;
    border: 1px solid var(--rule);
    border-radius: 50%;
  }

  .key__means {
    flex: 1;
    line-height: 1.35;
  }

  .key em {
    font-family: var(--font-mono);
    font-style: normal;
    font-size: var(--size-label);
    color: var(--pencil);
    font-variant-numeric: tabular-nums;
  }

  .terms,
  .hint {
    margin: var(--gap-tight) 0 0;
    font-size: 0.7rem;
    line-height: 1.45;
    color: var(--pencil);
  }

  .clockface {
    margin: 0;
    font-family: var(--font-mono);
    font-size: 0.78rem;
    color: var(--ink);
  }

  .time {
    display: flex;
    gap: var(--gap-tight);
    align-items: center;
    margin-top: var(--gap-hair);
  }

  .time input {
    flex: 1;
    min-width: 0;
    accent-color: var(--rust-ink);
  }

  .time button {
    flex: none;
    padding: 2px var(--gap-tight);
    background: transparent;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--ink);
    cursor: pointer;
  }

  .time button:hover {
    background: var(--paper-sunken);
  }

  .utc {
    display: flex;
    gap: var(--gap-tight);
    align-items: center;
    margin-top: var(--gap-tight);
    font-size: 0.7rem;
    color: var(--pencil);
  }

  .utc input {
    flex: 1;
    min-width: 0;
    accent-color: var(--pencil);
  }

  @media (max-width: 52rem) {
    .explore {
      /* Full width and top-anchored: a 20rem panel floating over a 390px globe leaves neither
         usable. It scrolls, and the globe is reachable by scrolling the panel out of the way. */
      top: auto;
      right: var(--gap-tight);
      bottom: calc(var(--strip) + var(--attrib));
      left: var(--gap-tight);
      width: auto;
      max-height: 55%;
    }
  }
</style>
