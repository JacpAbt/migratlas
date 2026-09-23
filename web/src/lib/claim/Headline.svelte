<script lang="ts">
  import {
    linear,
    tickLabel,
    valueRange,
    yearRange,
    type Headline,
    type Histogram,
    type Strip,
    type Years,
  } from "./headline";

  let { headline, drawn = true }: { headline: Headline; drawn?: boolean } = $props();

  /*
    One box for the three shapes, so a chart is the same size on every claim page and the plate
    under it lands in the same place. The strip is the exception in height only: eighteen named
    bars need more rows than a pile needs bars.

    Both numbers are measured rather than chosen. The eighteen-bar strip was 34px under its own
    folio at twenty pixels a row, and 25px over its leaf at 1024x768 at seventeen; fifteen is what
    fits it on the narrowest spread, where the chart is drawn about 400px wide and a row of fifteen
    viewBox units is still taller than the 11-unit label in it.
  */
  const BOX = { width: 640, height: 280 };
  const PAD = { top: 18, right: 150, bottom: 42, left: 60 };
  /** One named bar's row, in viewBox units: a little more than the label, and no more. */
  const ROW = 15;

  const chart = $derived(headline.chart);
  const plotWidth = BOX.width - PAD.left - PAD.right;
  const plotHeight = $derived(
    (chart.kind === "strip" ? Math.max(BOX.height, 34 + chart.bars.length * ROW) : BOX.height) -
      PAD.top -
      PAD.bottom,
  );
  const boxHeight = $derived(plotHeight + PAD.top + PAD.bottom);

  // --- years -----------------------------------------------------------------------------------
  const years = $derived(chart.kind === "years" ? (chart as Years) : null);
  const yearScale = $derived.by(() => {
    if (!years) return null;
    const [first, last] = yearRange(years);
    const [low, high] = valueRange(years);
    return {
      first,
      last,
      low,
      high,
      xOf: linear([first, last], [PAD.left, PAD.left + plotWidth]),
      // Larger values sit higher, so an earlier date reads as *down* and a later one as *up*:
      // the axis is the calendar's, not the ribbon's inverted one, because these charts carry
      // speeds and distances as well as dates and one convention has to hold for all of them.
      yOf: linear([low, high], [PAD.top + plotHeight, PAD.top]),
    };
  });

  // --- histogram -------------------------------------------------------------------------------
  const pile = $derived(chart.kind === "histogram" ? (chart as Histogram) : null);
  const pileScale = $derived.by(() => {
    if (!pile || pile.bins.length === 0) return null;
    const low = pile.bins[0]!.low;
    const high = pile.bins[pile.bins.length - 1]!.high;
    const tallest = Math.max(...pile.bins.map((b) => b.count), 1);
    return {
      low,
      high,
      xOf: linear([low, high], [PAD.left, PAD.left + plotWidth]),
      hOf: linear([0, tallest], [0, plotHeight]),
    };
  });

  // --- strip -----------------------------------------------------------------------------------
  const strip = $derived(chart.kind === "strip" ? (chart as Strip) : null);
  const stripScale = $derived.by(() => {
    if (!strip || strip.bars.length === 0) return null;
    const values = strip.bars.flatMap((b) => [b.value, b.low ?? b.value, b.high ?? b.value]);
    for (const mark of strip.marks) values.push(mark.value);
    let low = Math.min(...values, 0);
    let high = Math.max(...values, 0);
    const margin = (high - low || 1) * 0.06;
    low -= margin;
    high += margin;
    const rowHeight = plotHeight / strip.bars.length;
    return {
      low,
      high,
      rowHeight,
      xOf: linear([low, high], [PAD.left, PAD.left + plotWidth]),
      yOf: (index: number) => PAD.top + rowHeight * (index + 0.5),
    };
  });

  /** Three ticks across a range: its ends and its middle, said in the chart's unit. */
  function ticks(low: number, high: number): number[] {
    return [low, (low + high) / 2, high];
  }
</script>

<!--
  The claim's headline result, drawn.

  A first reading of the book found that a project about numbers showed almost none of them as a
  picture: the claim page was a world map with one circle. This is the picture the sentence on the
  first page describes -- the busiest night sliding earlier, eighteen seas pulling in different
  directions, a pile of species centred on nothing -- drawn from the values the ledger's own
  functions produced, so it cannot disagree with the number on the record page.

  Three shapes and one vocabulary: a rust mark for what changed or what is being compared against,
  pencil for the units, a dotted rule for zero. The reading line under the chart says what one dot,
  bar or count is, in the plain register, because a chart nobody can read is decoration.
-->
<figure class="headline" class:headline--drawn={drawn}>
  <h3 class="headline__title">{headline.title}</h3>
  <svg
    class="headline__svg"
    viewBox="0 0 {BOX.width} {boxHeight}"
    role="img"
    aria-label={`${headline.title}. ${headline.reading}`}
  >
    {#if years && yearScale}
      {@const scale = yearScale}
      {#each ticks(scale.low, scale.high) as value (value)}
        <line
          class="headline__grid"
          x1={PAD.left}
          x2={PAD.left + plotWidth}
          y1={scale.yOf(value)}
          y2={scale.yOf(value)}
        />
        <text class="headline__tick" x={PAD.left - 8} y={scale.yOf(value) + 4} text-anchor="end">
          {tickLabel(value, years.unit, scale.high - scale.low)}
        </text>
      {/each}
      {#each [scale.first, scale.last] as year, index (year)}
        <text
          class="headline__tick"
          x={scale.xOf(year)}
          y={PAD.top + plotHeight + 22}
          text-anchor={index === 0 ? "start" : "end"}>{year}</text
        >
      {/each}
      {#each years.series as series, index (series.key)}
        {#each series.points as point (point.year)}
          <circle
            class="headline__point headline__point--{index}"
            cx={scale.xOf(point.year)}
            cy={scale.yOf(point.value)}
            r="3"
          >
            <title>{point.year}: {tickLabel(point.value, years.unit, scale.high - scale.low)}, {point.n} units</title>
          </circle>
        {/each}
        {#if series.trend}
          <line
            class="headline__trend headline__trend--{index}"
            style="--order: {index}"
            x1={scale.xOf(scale.first)}
            x2={scale.xOf(scale.last)}
            y1={scale.yOf(series.trend.start)}
            y2={scale.yOf(series.trend.end)}
          />
          <text
            class="headline__label headline__label--{index}"
            x={PAD.left + plotWidth + 8}
            y={scale.yOf(series.trend.end) + 4 + (index === 1 ? 14 : 0)}
          >
            {series.label}
          </text>
        {/if}
      {/each}
      <text class="headline__unit" x={PAD.left} y={PAD.top - 6}>{years.unit}</text>
    {:else if pile && pileScale}
      {@const scale = pileScale}
      {#each pile.bins as bin (bin.low)}
        <rect
          class="headline__bar"
          x={scale.xOf(bin.low) + 0.5}
          y={PAD.top + plotHeight - scale.hOf(bin.count)}
          width={Math.max(scale.xOf(bin.high) - scale.xOf(bin.low) - 1, 1)}
          height={scale.hOf(bin.count)}
        >
          <title>{bin.count} between {tickLabel(bin.low, pile.unit, scale.high - scale.low)} and {tickLabel(bin.high, pile.unit, scale.high - scale.low)}</title>
        </rect>
      {/each}
      <line
        class="headline__base"
        x1={PAD.left}
        x2={PAD.left + plotWidth}
        y1={PAD.top + plotHeight}
        y2={PAD.top + plotHeight}
      />
      {#each ticks(scale.low, scale.high) as value, index (value)}
        <text
          class="headline__tick"
          x={scale.xOf(value)}
          y={PAD.top + plotHeight + 22}
          text-anchor={index === 0 ? "start" : index === 2 ? "end" : "middle"}
        >
          {tickLabel(value, pile.unit, scale.high - scale.low)}
        </text>
      {/each}
      {#each pile.marks as mark, index (mark.label)}
        {#if mark.value >= scale.low && mark.value <= scale.high}
          <line
            class="headline__mark headline__mark--{index}"
            x1={scale.xOf(mark.value)}
            x2={scale.xOf(mark.value)}
            y1={PAD.top}
            y2={PAD.top + plotHeight}
          />
          <text
            class="headline__label headline__label--{index}"
            x={scale.xOf(mark.value) + 5}
            y={PAD.top + 12 + index * 14}
          >
            {mark.label}
          </text>
        {/if}
      {/each}
      <text class="headline__unit" x={PAD.left + plotWidth} y={PAD.top + plotHeight + 36} text-anchor="end">
        {pile.n.toLocaleString()} counted, in {pile.unit}{pile.clipped > 0 ? `; ${pile.clipped} beyond the edges` : ""}
      </text>
    {:else if strip && stripScale}
      {@const scale = stripScale}
      {#each strip.marks as mark, index (mark.label)}
        <line
          class="headline__mark headline__mark--{index}"
          x1={scale.xOf(mark.value)}
          x2={scale.xOf(mark.value)}
          y1={PAD.top}
          y2={PAD.top + plotHeight}
        />
        <text class="headline__label" x={scale.xOf(mark.value) + 5} y={PAD.top - 5}>
          {mark.label}
        </text>
      {/each}
      {#each strip.bars as bar, index (bar.label)}
        <text
          class="headline__row"
          x={PAD.left - 8}
          y={scale.yOf(index) + 4}
          text-anchor="end"
        >
          {bar.label}
        </text>
        {#if bar.low !== null && bar.high !== null}
          <line
            class="headline__interval"
            x1={scale.xOf(bar.low)}
            x2={scale.xOf(bar.high)}
            y1={scale.yOf(index)}
            y2={scale.yOf(index)}
          />
        {/if}
        <line
          class="headline__stem"
          x1={scale.xOf(0)}
          x2={scale.xOf(bar.value)}
          y1={scale.yOf(index)}
          y2={scale.yOf(index)}
        />
        <circle class="headline__point headline__point--0" cx={scale.xOf(bar.value)} cy={scale.yOf(index)} r="3.2">
          <title>{bar.label}: {tickLabel(bar.value, strip.unit, scale.high - scale.low)}</title>
        </circle>
      {/each}
      {#each ticks(scale.low, scale.high) as value, index (value)}
        <text
          class="headline__tick"
          x={scale.xOf(value)}
          y={PAD.top + plotHeight + 22}
          text-anchor={index === 0 ? "start" : index === 2 ? "end" : "middle"}
        >
          {tickLabel(value, strip.unit, scale.high - scale.low)}
        </text>
      {/each}
      <text class="headline__unit" x={PAD.left + plotWidth} y={PAD.top + plotHeight + 36} text-anchor="end">
        {strip.unit}
      </text>
    {/if}
  </svg>
  <figcaption class="headline__reading">{headline.reading}</figcaption>
</figure>

<style>
  .headline {
    display: flex;
    flex-direction: column;
    gap: var(--gap-tight);
    margin: 0;
    min-height: 0;
  }

  .headline__title {
    margin: 0;
    font-family: var(--font-hand);
    font-weight: 400;
    font-size: calc(1.15rem * var(--font-scale-hand));
    line-height: var(--leading-hand);
  }

  /* A hair off square, like everything else on the page. */
  .headline__svg {
    display: block;
    width: 100%;
    height: auto;
    overflow: visible;
    rotate: -0.6deg;
  }

  .headline__grid,
  .headline__base {
    stroke: var(--rule);
    stroke-width: 1;
  }

  .headline__tick,
  .headline__row,
  .headline__unit,
  .headline__label {
    font-family: var(--font-mono);
    font-size: 11px;
    fill: var(--pencil);
  }

  .headline__row {
    font-family: var(--font-body);
    fill: var(--ink-soft);
  }

  .headline__label {
    font-family: var(--font-hand);
    font-size: 13px;
    fill: var(--ink-soft);
  }

  .headline__point {
    fill: var(--line-observed);
    stroke: var(--paper);
    stroke-width: 0.8;
  }

  .headline__point--1 {
    fill: var(--line-counterfactual);
  }

  .headline__bar {
    fill: var(--line-scatter);
    opacity: 0.75;
  }

  .headline__trend {
    stroke: var(--line-observed);
    stroke-width: 2.4;
    stroke-linecap: round;
  }

  .headline__trend--1 {
    stroke: var(--line-counterfactual);
  }

  .headline__label--1 {
    fill: var(--line-counterfactual);
  }

  .headline__mark {
    stroke: var(--rust-ink);
    stroke-width: 1.4;
    stroke-dasharray: 4 3;
  }

  .headline__mark--1 {
    stroke: var(--ink-soft);
    stroke-dasharray: 1.5 3;
  }

  .headline__interval {
    stroke: var(--rule);
    stroke-width: 3;
    stroke-linecap: round;
  }

  .headline__stem {
    stroke: var(--line-observed);
    stroke-width: 1.4;
  }

  /*
    Drawn on arrival, the way the ribbon is: the trend is written after the points, so a reader
    watches the line go through the pile rather than finding it already there. Durations come
    from the tokens, so the reduced-motion block zeroes them.
  */
  .headline--drawn .headline__trend {
    stroke-dasharray: 1000;
    stroke-dashoffset: 1000;
    animation: headline-draw var(--draw-slow) var(--ease-pen) forwards;
    animation-delay: calc(var(--draw-quick) + var(--order, 0) * var(--draw-quick));
  }

  @keyframes headline-draw {
    to {
      stroke-dashoffset: 0;
    }
  }

  .headline__reading {
    margin: 0;
    font-size: var(--size-margin);
    line-height: 1.5;
    color: var(--ink-soft);
  }
</style>
