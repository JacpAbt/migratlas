<script lang="ts">
  import {
    BOX,
    PAD,
    asDate,
    clipped,
    loadRibbon,
    rate,
    scales,
    stack,
    verticalRange,
    type RibbonDocument,
  } from "./ribbon";

  let { base }: { base: string } = $props();

  let doc = $state<RibbonDocument | null>(null);
  let failure = $state<string | null>(null);
  let drawn = $state(false);

  $effect(() => {
    loadRibbon(base)
      .then((loaded) => {
        doc = loaded;
        // Two frames, not one: the first paints the undrawn lines so the transition has a state to
        // start from. Setting it in the same frame makes the browser skip straight to the end.
        requestAnimationFrame(() => requestAnimationFrame(() => (drawn = true)));
      })
      .catch((error: unknown) => (failure = String(error)));
  });

  const scale = $derived(doc ? scales(doc) : null);
  const frame = $derived(doc ? verticalRange(doc) : null);
  const overflowing = $derived(doc ? clipped(doc) : []);
  // Labels sit on a de-overlapped copy of the endpoints; a leader joins each back to its real end.
  const labelled = $derived(
    doc && scale
      ? stack(doc.lines.map((line) => scale.yOf(line.end) + 4)).map((y, index) => ({
          y,
          line: doc!.lines[index]!,
          end: scale!.yOf(doc!.lines[index]!.end),
        }))
      : [],
  );
</script>

<!--
  The counterfactual, drawn as the argument rather than illustrating it.

  ADR 0007 decision 6: the *drawing order is the argument*. Observed strokes on first, then the
  counterfactual after it, and the reader watches the gap fail to open. Drawn together, the same two
  lines make a reader hunt for a difference instead of witnessing its size.
-->
<figure class="ribbon">
  {#if failure}
    <p class="ribbon__failure">The counterfactual is unavailable. {failure}</p>
  {:else if doc && scale && frame}
    <svg
      class="ribbon__chart"
      class:ribbon__chart--drawn={drawn}
      viewBox="0 0 {BOX.width} {BOX.height}"
      role="img"
      aria-label={`Autumn passage date at ${doc.terms.stations} radar stations, ${doc.window[0]} to ${doc.window[1]}: ` +
        doc.lines.map((l) => `${l.label}, ${rate(l.per_decade)}`).join("; ")}
    >
      <!-- Three date ticks and two years. Any more and the frame competes with what is in it. -->
      {#each [frame[0], doc.anchor, frame[1]] as day (day)}
        <line
          class="ribbon__grid"
          x1={PAD.left}
          x2={PAD.left + scale.plotWidth}
          y1={scale.yOf(day)}
          y2={scale.yOf(day)}
        />
        <text class="ribbon__tick" x={PAD.left - 7} y={scale.yOf(day) + 4} text-anchor="end">
          {asDate(day)}
        </text>
      {/each}
      {#each doc.window as year, index (year)}
        <text
          class="ribbon__tick"
          x={scale.xOf(year)}
          y={BOX.height - PAD.bottom + 20}
          text-anchor={index === 0 ? "start" : "end"}>{year}</text
        >
      {/each}

      <!-- The scatter is as much the point as the lines: it is what makes the size of the
           divergence legible, so it is not decoration and it is not optional. -->
      {#each doc.years as point (point.year)}
        {#if point.spread > 0}
          <line
            class="ribbon__spread"
            x1={scale.xOf(point.year)}
            x2={scale.xOf(point.year)}
            y1={scale.clamp(scale.yOf(point.observed - point.spread))}
            y2={scale.clamp(scale.yOf(point.observed + point.spread))}
          />
        {/if}
        <circle
          class="ribbon__year"
          cx={scale.xOf(point.year)}
          cy={scale.yOf(point.observed)}
          r="2.6"
        >
          <title>{point.year}: {asDate(point.observed)}, {point.stations} stations</title>
        </circle>
      {/each}

      {#each labelled as { line, y, end }, index (line.key)}
        <line
          class="ribbon__line ribbon__line--{line.key}"
          style="--order: {index}"
          x1={scale.xOf(doc.window[0])}
          x2={scale.xOf(doc.window[1])}
          y1={scale.yOf(line.start)}
          y2={end}
        />
        {#if Math.abs(y - 4 - end) > 1}
          <line
            class="ribbon__leader"
            x1={scale.xOf(doc.window[1])}
            x2={scale.xOf(doc.window[1]) + 5}
            y1={end}
            y2={y - 4}
          />
        {/if}
        <text class="ribbon__label ribbon__label--{line.key}" x={scale.xOf(doc.window[1]) + 7} {y}>
          {line.label}
        </text>
        <text class="ribbon__rate" x={scale.xOf(doc.window[1]) + 7} y={y + 13}>
          {rate(line.per_decade)}
        </text>
      {/each}
    </svg>

    <figcaption>
      <!-- The number the chart cannot make big, in words directly under it. A reader who only sees
           two nearly-parallel lines has to learn that the near-parallel *is* the finding. -->
      <p class="ribbon__size">
        The two part by {doc.divergence.toFixed(2)} days across
        {doc.window[1] - doc.window[0]} years.
      </p>

      {#if overflowing.length > 0}
        <p class="ribbon__clipped">
          {overflowing.length} of {doc.years.length} years have a sampling interval wider than the
          frame ({overflowing.join(", ")}); their bars run to the edge.
        </p>
      {/if}

      <dl class="ribbon__notes">
        {#each doc.lines as line (line.key)}
          <dt class="ribbon__key ribbon__key--{line.key}">{line.label}</dt>
          <dd>{line.note}</dd>
        {/each}
      </dl>

      <p class="ribbon__caveat">{doc.caveat}</p>
    </figcaption>
  {:else}
    <p class="ribbon__failure">Reading the counterfactual…</p>
  {/if}
</figure>

<style>
  .ribbon {
    margin: 0;
  }

  .ribbon__chart {
    display: block;
    width: 100%;
    height: auto;
    overflow: visible;
  }

  .ribbon__grid {
    stroke: var(--rule);
    stroke-width: 1;
    stroke-dasharray: 2 4;
  }

  .ribbon__tick {
    fill: var(--pencil);
    font-family: var(--font-mono);
    font-size: 12px;
  }

  .ribbon__year {
    fill: var(--line-scatter);
    fill-opacity: 0.55;
  }

  .ribbon__spread {
    stroke: var(--line-scatter);
    stroke-opacity: 0.28;
    stroke-width: 1;
  }

  .ribbon__line {
    stroke-width: 2.2;
    stroke-linecap: round;
    /* Longer than any line in a 640-unit box, so one value covers all three. */
    stroke-dasharray: 700;
    stroke-dashoffset: 700;
    /* Staggered by index: the observed line draws, then the counterfactual behind it. The delay is
       the argument, so it is calculated from the line's own order rather than hard-coded. */
    transition: stroke-dashoffset var(--draw) var(--ease-pen);
    transition-delay: calc(var(--order) * var(--draw) * 0.55);
  }

  .ribbon__chart--drawn .ribbon__line {
    stroke-dashoffset: 0;
  }

  .ribbon__line--observed {
    stroke: var(--line-observed);
  }

  /* Both counterfactuals in the same blue, the second dashed: they are nearly coincident by
     arithmetic, and contrasting hues would suggest a difference worth reading. */
  .ribbon__line--counterfactual {
    stroke: var(--line-counterfactual);
  }

  .ribbon__line--no-thermal {
    stroke: var(--line-counterfactual);
    stroke-width: 1.6;
    stroke-dasharray: 700;
    stroke-opacity: 0.8;
  }

  .ribbon__chart--drawn .ribbon__line--no-thermal {
    /* Re-dashed only once it has finished drawing, since one dasharray cannot both hide a line and
       pattern it. */
    stroke-dasharray: 5 4;
    transition:
      stroke-dashoffset var(--draw) var(--ease-pen),
      stroke-dasharray 1ms linear var(--draw);
  }

  .ribbon__leader {
    stroke: var(--pencil);
    stroke-width: 0.8;
    stroke-opacity: 0.6;
  }

  .ribbon__label {
    fill: var(--ink);
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 600;
  }

  .ribbon__label--observed {
    fill: var(--rust);
  }

  .ribbon__label--counterfactual,
  .ribbon__label--no-thermal {
    fill: var(--line-counterfactual);
  }

  .ribbon__rate {
    fill: var(--pencil);
    font-family: var(--font-mono);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
  }

  .ribbon__size {
    margin: var(--gap-tight) 0 0;
    font-size: 0.85rem;
    font-weight: 600;
  }

  .ribbon__clipped,
  .ribbon__caveat {
    margin: var(--gap-tight) 0 0;
    color: var(--pencil);
    font-size: 0.76rem;
    line-height: 1.5;
  }

  .ribbon__caveat {
    padding-top: var(--gap-tight);
    border-top: 1px dotted var(--rule);
  }

  .ribbon__notes {
    margin: var(--gap) 0 0;
    font-size: 0.76rem;
    line-height: 1.45;
  }

  .ribbon__key {
    margin-top: var(--gap-tight);
    font-family: var(--font-mono);
    font-weight: 500;
  }

  .ribbon__key--observed {
    color: var(--rust);
  }

  .ribbon__key--counterfactual,
  .ribbon__key--no-thermal {
    color: var(--line-counterfactual);
  }

  .ribbon__notes dd {
    margin: 1px 0 0;
    color: var(--ink-soft);
  }

  .ribbon__failure {
    margin: 0;
    font-family: var(--font-mono);
    font-size: var(--size-margin);
    color: var(--pencil);
  }
</style>
