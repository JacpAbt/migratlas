<script lang="ts">
  import {
    BOX,
    PAD,
    asDate,
    clipped,
    rate,
    scales,
    stack,
    type Frame,
    type RibbonDocument,
  } from "./ribbon";

  let {
    ribbon,
    frame,
    drawn,
  }: { ribbon: RibbonDocument; frame: Frame; drawn: boolean } = $props();

  const scale = $derived(scales(frame));
  const overflowing = $derived(clipped(ribbon, frame));
  // Labels sit on a de-overlapped copy of the endpoints; a leader joins each back to its real end.
  const labelled = $derived(
    stack(ribbon.lines.map((line) => scale.yOf(line.end) + 4)).map((y, index) => ({
      y,
      line: ribbon.lines[index]!,
      end: scale.yOf(ribbon.lines[index]!.end),
    })),
  );
  // Where this ribbon's attribution stops inside the shared frame, and what kind of limit that is.
  //
  // ATTRICI's counterfactual series ends in 2019 and its line stops there. DAMIP's share is a scalar
  // fitted to 2014 and applied to the whole observed trend, so its line runs on through years that
  // never constrained it. Both are limits worth drawing, and they are not the same limit.
  const unbacked = $derived(ribbon.attributed_through < frame.years[1]);
  const extrapolated = $derived(ribbon.attributed_through < ribbon.window[1]);
</script>

<!--
  One counterfactual, drawn as the argument rather than illustrating it.

  ADR 0007 decision 6: the *drawing order is the argument*. Observed strokes on first, then the
  counterfactual after it, and the reader watches the gap fail to open. Drawn together, the same two
  lines make a reader hunt for a difference instead of witnessing its size.

  The frame is handed in rather than computed here, because it is shared with the other ribbon and a
  chart that sized itself would quietly break the only comparison that matters.
-->
<figure class="chart">
  <figcaption class="chart__ask">
    <h4>{ribbon.question}</h4>
    <p>{ribbon.method_note}</p>
  </figcaption>

  <svg
    class="chart__svg"
    class:chart__svg--drawn={drawn}
    viewBox="0 0 {BOX.width} {BOX.height}"
    role="img"
    aria-label={`${ribbon.question} Autumn passage date at ${ribbon.terms.stations} radar stations, ` +
      `${ribbon.window[0]} to ${ribbon.window[1]}: ` +
      ribbon.lines.map((l) => `${l.label}, ${rate(l.per_decade)}`).join("; ")}
  >
    <!-- Three date ticks and the frame's own years. Any more and the frame competes with what is
         in it. Ticks come from the shared frame, so both charts carry an identical rule. -->
    {#each [frame.days[0], (frame.days[0] + frame.days[1]) / 2, frame.days[1]] as day (day)}
      <line
        class="chart__grid"
        x1={PAD.left}
        x2={PAD.left + scale.plotWidth}
        y1={scale.yOf(day)}
        y2={scale.yOf(day)}
      />
      <text class="chart__tick" x={PAD.left - 7} y={scale.yOf(day) + 4} text-anchor="end">
        {asDate(day)}
      </text>
    {/each}
    {#each frame.years as year, index (year)}
      <text
        class="chart__tick"
        x={scale.xOf(year)}
        y={BOX.height - PAD.bottom + 20}
        text-anchor={index === 0 ? "start" : "end"}>{year}</text
      >
    {/each}

    {#if unbacked}
      <!-- The years the attribution does not reach, shaded rather than left to the caveat. An empty
           quarter reads as missing data; a shaded one with a label reads as a stated limit. And where
           the line *continues* into the band, the shading is the only thing saying it is extrapolated
           -- nothing about a drawn line distinguishes fitted from carried-on. -->
      <rect
        class="chart__beyond"
        x={scale.xOf(ribbon.attributed_through)}
        y={PAD.top}
        width={scale.xOf(frame.years[1]) - scale.xOf(ribbon.attributed_through)}
        height={scale.plotHeight}
      />
      <line
        class="chart__edge"
        x1={scale.xOf(ribbon.attributed_through)}
        x2={scale.xOf(ribbon.attributed_through)}
        y1={PAD.top}
        y2={PAD.top + scale.plotHeight}
      />
      <text
        class="chart__beyond-label"
        x={scale.xOf(ribbon.attributed_through) + 5}
        y={PAD.top + scale.plotHeight - 6}
      >
        {extrapolated
          ? `share fitted only to ${ribbon.attributed_through}`
          : `no counterfactual after ${ribbon.attributed_through}`}
      </text>
    {/if}

    <!-- The scatter is as much the point as the lines: it is what makes the size of the
         divergence legible, so it is not decoration and it is not optional. -->
    {#each ribbon.years as point (point.year)}
      {#if point.spread > 0}
        <line
          class="chart__spread"
          x1={scale.xOf(point.year)}
          x2={scale.xOf(point.year)}
          y1={scale.clamp(scale.yOf(point.observed - point.spread))}
          y2={scale.clamp(scale.yOf(point.observed + point.spread))}
        />
      {/if}
      <circle class="chart__year" cx={scale.xOf(point.year)} cy={scale.yOf(point.observed)} r="2.6">
        <title>{point.year}: {asDate(point.observed)}, {point.stations} stations</title>
      </circle>
    {/each}

    {#each labelled as { line, y, end }, index (line.key)}
      <line
        class="chart__line chart__line--{line.key}"
        style="--order: {index}"
        x1={scale.xOf(ribbon.window[0])}
        x2={scale.xOf(ribbon.window[1])}
        y1={scale.yOf(line.start)}
        y2={end}
      />
      <!-- Dotted, and horizontal before it turns. A straight diagonal from the line's end to a label
           in the right margin crosses the shaded years and reads as the line continuing through them,
           which is the one thing this chart is shaped to prevent. -->
      <path
        class="chart__leader"
        d={`M ${scale.xOf(ribbon.window[1])} ${end} H ${scale.xOf(frame.years[1]) + 4} V ${y - 4}`}
      />

      <!-- A tick at the line's true end, so the eye has something to stop on before the guide. -->
      <circle class="chart__stop" cx={scale.xOf(ribbon.window[1])} cy={end} r="2.2" />
      <text class="chart__label chart__label--{line.key}" x={scale.xOf(frame.years[1]) + 7} {y}>
        {line.label}
      </text>
      <text class="chart__rate" x={scale.xOf(frame.years[1]) + 7} y={y + 13}>
        {rate(line.per_decade)}
      </text>
    {/each}
  </svg>

  <!-- The number the chart cannot make big, in words directly under it. A reader who only sees two
       nearly-parallel lines has to learn that the near-parallel *is* the finding. -->
  <p class="chart__size">
    <!-- The window's ends, not a count of years. The divergence is the slope difference over
         window[1] − window[0] decades, so a count would print 24 for 1995 to 2019 and a reader
         counting the years would get 25. -->
    The two part by {ribbon.divergence.toFixed(2)} days between {ribbon.window[0]} and
    {ribbon.window[1]}.
  </p>

  {#if overflowing.length > 0}
    <p class="chart__aside">
      {overflowing.length} of {ribbon.years.length} years have a sampling interval wider than the
      frame ({overflowing.join(", ")}); their bars run to the edge.
    </p>
  {/if}

  <dl class="chart__notes">
    {#each ribbon.lines as line (line.key)}
      <dt class="chart__key chart__key--{line.key}">{line.label}</dt>
      <dd>{line.note}</dd>
    {/each}
  </dl>

  <p class="chart__aside chart__aside--caveat">{ribbon.caveat}</p>
</figure>

<style>
  .chart {
    margin: 0;
  }

  .chart__ask h4 {
    margin: 0;
    font-family: var(--font-hand);
    font-size: 1.1rem;
    font-weight: 400;
    line-height: var(--leading-hand);
  }

  .chart__ask p {
    margin: var(--gap-hair) 0 var(--gap-tight);
    color: var(--ink-soft);
    font-size: 0.78rem;
    line-height: 1.45;
  }

  .chart__svg {
    display: block;
    width: 100%;
    height: auto;
    overflow: visible;
  }

  .chart__grid {
    stroke: var(--rule);
    stroke-width: 1;
    stroke-dasharray: 2 4;
  }

  .chart__tick {
    fill: var(--pencil);
    font-family: var(--font-mono);
    font-size: 12px;
  }

  .chart__beyond {
    fill: var(--paper-sunken);
    fill-opacity: 0.75;
  }

  .chart__edge {
    stroke: var(--rule);
    stroke-width: 1;
  }

  .chart__beyond-label {
    fill: var(--pencil);
    font-family: var(--font-mono);
    font-size: 10px;
  }

  .chart__year {
    fill: var(--line-scatter);
    fill-opacity: 0.55;
  }

  .chart__spread {
    stroke: var(--line-scatter);
    stroke-opacity: 0.28;
    stroke-width: 1;
  }

  .chart__line {
    stroke-width: 2.2;
    stroke-linecap: round;
    /* Longer than any line in a 640-unit box, so one value covers both. */
    stroke-dasharray: 700;
    stroke-dashoffset: 700;
    /* Staggered by index: the observed line draws, then the counterfactual behind it. The delay is
       the argument, so it is calculated from the line's own order rather than hard-coded. */
    transition: stroke-dashoffset var(--draw) var(--ease-pen);
    transition-delay: calc(var(--order) * var(--draw) * 0.55);
  }

  .chart__svg--drawn .chart__line {
    stroke-dashoffset: 0;
  }

  .chart__line--observed {
    stroke: var(--line-observed);
  }

  .chart__line--counterfactual {
    stroke: var(--line-counterfactual);
  }

  /* Dotted and unfilled: a guide to a label, never mistakable for a fitted line. */
  .chart__leader {
    fill: none;
    stroke: var(--pencil);
    stroke-width: 0.8;
    stroke-opacity: 0.5;
    stroke-dasharray: 1.5 2.5;
  }

  .chart__stop {
    fill: var(--paper);
    stroke: var(--pencil);
    stroke-width: 1;
  }

  .chart__label {
    fill: var(--ink);
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 600;
  }

  .chart__label--observed {
    fill: var(--rust);
  }

  .chart__label--counterfactual {
    fill: var(--line-counterfactual);
  }

  .chart__rate {
    fill: var(--pencil);
    font-family: var(--font-mono);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
  }

  .chart__size {
    margin: var(--gap-tight) 0 0;
    font-size: 0.85rem;
    font-weight: 600;
  }

  .chart__aside {
    margin: var(--gap-tight) 0 0;
    color: var(--pencil);
    font-size: 0.76rem;
    line-height: 1.5;
  }

  .chart__aside--caveat {
    padding-top: var(--gap-tight);
    border-top: 1px dotted var(--rule);
  }

  .chart__notes {
    margin: var(--gap) 0 0;
    font-size: 0.76rem;
    line-height: 1.45;
  }

  .chart__key {
    margin-top: var(--gap-tight);
    font-family: var(--font-mono);
    font-weight: 500;
  }

  .chart__key--observed {
    color: var(--rust);
  }

  .chart__key--counterfactual {
    color: var(--line-counterfactual);
  }

  .chart__notes dd {
    margin: 1px 0 0;
    color: var(--ink-soft);
  }
</style>
