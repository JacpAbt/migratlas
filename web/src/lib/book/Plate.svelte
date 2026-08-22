<script lang="ts">
  import { drawPlate, loadLand, PLATE_RATIO, type Ring } from "./plate";
  import { viewFor } from "../story";
  import type { Finding } from "../ledger";

  let {
    finding,
    number,
    base,
  }: {
    finding: Finding;
    /** Plate number, so the caption can be cited. */
    number: number;
    base: string;
  } = $props();

  /*
    Width only, and the height follows from the projection.

    `notebook/ink.ts`'s rule is that geometry is generated at the size it is drawn at; `PLATE_RATIO`
    is the other half of it, which this component used to break. The sheet was `flex: 1` and got the
    leftover height of the page column, so the map was scaled to a box the projection never agreed
    to -- measured at ×1.9 to ×2.1 too tall on every plate. Now the paper is the shape of the map
    rather than the map the shape of the paper.
  */
  let width = $state(0);
  const height = $derived(width / PLATE_RATIO);
  let host = $state<SVGSVGElement | null>(null);
  let rings = $state<Ring[]>([]);
  let failed = $state<string | null>(null);

  $effect(() => {
    loadLand(base)
      .then((loaded) => (rings = loaded))
      .catch((error: unknown) => (failed = String(error)));
  });

  const view = $derived(viewFor(finding));

  $effect(() => {
    if (!host || width <= 0 || rings.length === 0) return;
    // Read at draw time, so a surface change redraws in the new palette rather than restyling --
    // rough.js draws each stroke twice and there is no single path to recolour.
    const style = getComputedStyle(document.documentElement);
    const token = (name: string) => style.getPropertyValue(name).trim();
    drawPlate(
      host,
      rings,
      width,
      {
        ink: token("--ink"),
        pencil: token("--pencil"),
        faint: token("--rule-faint"),
        accent: token("--rust"),
      },
      { center: view.center, label: finding.key },
    );
  });
</script>

<!--
  A plate taped into the page: a separate sheet, a shade off the paper, hung a degree crooked.

  ADR 0015 decision 2. The sheet is `--plate-paper`, which is darker than the page by day and
  *lighter* by night -- a second sheet under a lamp is lighter than what it lies on, and mixing
  toward the sunken tone made it invisible on the dark palette.
-->
<figure class="plate">
  <!--
    The measurement is on the sheet, which is in normal flow, and not on an absolutely positioned
    child. `Sheet.svelte` binds a flow element for the same reason and works; binding the absolute
    child here reported clientWidth 531 to the DOM and 0 to the component, so nothing ever drew.
  -->
  <div class="plate__sheet" style="aspect-ratio: {PLATE_RATIO}" bind:clientWidth={width}>
    {#if failed}
      <p class="plate__failure" role="status">The basemap did not load: {failed}</p>
    {:else}
      <svg bind:this={host} width={width} height={height} aria-hidden="true"></svg>
    {/if}
    <span class="tape tape--start" aria-hidden="true"></span>
    <span class="tape tape--end" aria-hidden="true"></span>
  </div>
  <figcaption>
    <b>Plate {number}.</b> {view.because}

    <!--
      A key, because a drawing without one is asking to be guessed at.

      The owner's note was that the maps should say more about what they are showing, and the sharper
      half of that was that the caption was saying it about something else: `because` was written as
      the *layer's* description -- "ringed where the count fell, solid where it rose" -- and the plate
      draws none of that. A reader was being sent looking for marks that are not on the paper.

      So the caption is the ground and this is the marks, and there are exactly three because the
      plate draws exactly three groups. `book.spec.ts` holds the two lists to the same length: a mark
      with no entry is a mark nobody can read, and an entry with no mark is this file lying again.
    -->
    <ul class="plate__key">
      <li><span class="key__mark key__mark--here"></span>The ground this claim is about</li>
      <li><span class="key__mark key__mark--land"></span>Coastlines, drawn rather than plotted</li>
      <li><span class="key__mark key__mark--grid"></span>The graticule, every 30 degrees</li>
    </ul>

    <span class="plate__scope">{finding.scope}</span>
    <!-- Where the measurement itself is, since this sheet carries none of it. The plates exist so a
         claim chapter need not boot a globe, and that trade is only honest if the globe is named. -->
    <span class="plate__elsewhere">The measured layers are in the world chapter.</span>
  </figcaption>
</figure>

<style>
  .plate {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    margin: 0;
  }

  .plate__sheet {
    position: relative;
    /* Its height is its width over `PLATE_RATIO`, set inline because the number belongs to the
       projection. Not `flex: 1`: that is what gave the map the page's leftover height. */
    flex: 0 0 auto;
    width: 100%;
    background: var(--plate-paper);
    transform: rotate(-1.1deg);
    box-shadow:
      0 1px 2px rgb(0 0 0 / 18%),
      0 6px 14px rgb(0 0 0 / 12%);
  }

  .plate__sheet svg {
    position: absolute;
    inset: 0;
    display: block;
  }

  .plate__failure {
    margin: 0;
    padding: var(--gap);
    font-size: var(--size-margin);
    color: var(--status-open);
  }

  /*
    Tape: a surface rather than a mark, so a filled strip with visible edges rather than a drawn
    outline. Low alpha over the page, which is what sticky tape on paper looks like.
  */
  .tape {
    position: absolute;
    width: 5.4rem;
    height: 1.7rem;
    background: color-mix(in srgb, var(--paper-sunken) 72%, transparent);
    border: 1px solid color-mix(in srgb, var(--rule) 60%, transparent);
  }

  .tape--start {
    top: -0.7rem;
    left: -1.1rem;
    transform: rotate(-26deg);
  }

  .tape--end {
    right: -1.2rem;
    bottom: -0.6rem;
    transform: rotate(-21deg);
  }

  figcaption {
    margin-top: var(--gap);
    font-size: var(--size-margin);
    color: var(--ink-soft);
  }

  .plate__scope {
    display: block;
    margin-top: var(--gap-hair);
    color: var(--pencil);
  }

  .plate__elsewhere {
    display: block;
    margin-top: var(--gap-hair);
    color: var(--pencil);
  }

  .plate__key {
    display: flex;
    flex-wrap: wrap;
    gap: var(--gap-hair) var(--gap);
    margin: var(--gap-tight) 0 0;
    padding: 0;
    list-style: none;
  }

  .plate__key li {
    display: flex;
    align-items: center;
    gap: 0.4em;
  }

  /* Each swatch is the mark it stands for, at the weight the plate draws it. A coloured square with
     a label beside it would be a legend for a chart; these are the pen. */
  .key__mark {
    flex: 0 0 auto;
    width: 1.15em;
    height: 1.15em;
  }

  .key__mark--here {
    border: 2px solid var(--rust);
    border-radius: 50%;
    /* Off-round, because the drawn ring is rough.js at roughness 2.2 and a perfect circle in the key
       reads as a different mark from the one on the sheet. */
    transform: rotate(-8deg) scale(1.02, 0.94);
  }

  .key__mark--land {
    border: 1px solid var(--ink);
    background: repeating-linear-gradient(
      -38deg,
      var(--pencil) 0 1px,
      transparent 1px 4px
    );
  }

  /* One weight up from the sheet's own. The graticule is drawn at `--rule-faint` because a reference
     line belongs under the thing it refers to, and a 1px sample of it inside a 1.15em box was below
     seeing -- a key entry nobody can see is not a key entry. The mark stays faint; the sample reads. */
  .key__mark--grid {
    border: 1px solid var(--rule);
    background:
      linear-gradient(var(--pencil) 0 0) no-repeat center / 100% 1px,
      linear-gradient(var(--pencil) 0 0) no-repeat center / 1px 100%;
  }
</style>
