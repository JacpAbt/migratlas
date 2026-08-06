<script lang="ts">
  import Ticked from "../notebook/Ticked.svelte";
  import Rule from "../notebook/Rule.svelte";
  import { BRACKET_WIDTH, bracket } from "../notebook/ink";
  import type { Finding } from "../ledger";

  let { finding }: { finding: Finding } = $props();

  // Measured for the same reason the rule is: stretched, a 3px hook on a 400px column becomes an
  // 8px flag, and the spine's wobble smears into a curve.
  let height = $state(0);
  let spine = $state<SVGSVGElement | null>(null);

  $effect(() => {
    if (!spine || height <= 0) return;
    spine.replaceChildren();
    bracket(spine, finding.key, height, "var(--pencil)");
  });

  // A domain reading "not applicable" is a real answer and is shown as one. What must never happen
  // is a domain missing from the block entirely, which would read as "no risk here".
  const shown = $derived(finding.bias);
</script>

<!--
  The margin: the audit, always visible, never behind a control.

  ADR 0007 decision 7. `reports/findings.py` refuses to publish a claim with no caveat and the
  browser suite asserts the caveat is rendered; putting any of this behind a "more" toggle would
  satisfy the letter of both and break the point. A caveat has to arrive *with* the number. It does
  not have to arrive at the same size, and here it does not.
-->
<aside class="margin" aria-label="How this claim could be wrong">
  <svg
    bind:this={spine}
    class="margin__spine"
    bind:clientHeight={height}
    viewBox="0 0 {BRACKET_WIDTH} {Math.max(height, 1)}"
    width={BRACKET_WIDTH}
    aria-hidden="true"
  >
  </svg>

  <div class="margin__body">
    <section>
      <h3>Risk of bias</h3>
      <dl class="bias">
        {#each shown as domain (domain.domain)}
          <dt class="bias__domain">{domain.domain}</dt>
          <dd class="bias__status bias__status--{domain.status.replace(/ /g, '-')}">
            {domain.status}
          </dd>
          <dd class="bias__finding">{domain.finding}</dd>
        {/each}
      </dl>
    </section>

    {#if finding.supporting.length > 0}
      <section>
        <h3>Survived</h3>
        <Rule seed={`${finding.key}-survived`} tone="rule" />
        <ul class="survived">
          {#each finding.supporting as line (line)}
            <li><Ticked seed={line} on box={false} /><span>{line}</span></li>
          {/each}
        </ul>
      </section>
    {/if}

    <section class="specimen">
      <h3>Specimen</h3>
      <p>
        {finding.realm} · {finding.taxon_scope} · {finding.evidence_type.replace(/_/g, " ")}
      </p>
    </section>
  </div>
</aside>

<style>
  .margin {
    display: grid;
    grid-template-columns: 8px 1fr;
    gap: 0 var(--gap-tight);
    align-items: stretch;
    font-family: var(--font-mono);
    font-size: var(--size-margin);
    line-height: 1.55;
    color: var(--pencil);
  }

  .margin__spine {
    width: 8px;
    height: 100%;
    overflow: visible;
  }

  .margin__spine path {
    fill: none;
    stroke: var(--rule);
    stroke-width: 1.2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .margin__body {
    display: flex;
    flex-direction: column;
    gap: var(--gap);
    min-width: 0;
  }

  h3 {
    margin: 0 0 var(--gap-hair);
    font-size: var(--size-label);
    font-weight: 500;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--pencil);
  }

  .bias {
    display: grid;
    /* Domain and status on one row, the finding spanning both underneath. A three-column layout put
       the finding in a 5rem gutter and hyphenated every word in it. */
    grid-template-columns: 1fr auto;
    gap: 0;
    margin: 0;
  }

  .bias__domain {
    grid-column: 1;
    color: var(--ink-soft);
  }

  .bias__status {
    grid-column: 2;
    margin: 0;
    text-align: right;
  }

  /* Never colour alone: the word is right there saying the same thing, because a colour distinction
     is not available to every reader. */
  .bias__status--open {
    color: var(--status-open);
    font-weight: 500;
  }

  .bias__status--bounded {
    color: var(--status-bounded);
  }

  .bias__status--addressed {
    color: var(--status-addressed);
  }

  .bias__finding {
    grid-column: 1 / -1;
    margin: 0 0 var(--gap-tight);
    font-family: var(--font-body);
    font-size: 0.76rem;
    line-height: 1.5;
    color: var(--pencil);
  }

  .survived {
    margin: var(--gap-hair) 0 0;
    padding: 0;
    list-style: none;
  }

  /* A hanging tick, not a bullet, and now a drawn one rather than the U+2713 glyph -- which came
     from whichever font had it and was the last mark on the page still set in type. Flex with the
     mark on its own line-height, so a wrapping item still aligns under its first word. */
  .survived li {
    display: flex;
    gap: 0.3rem;
    font-family: var(--font-body);
    font-size: 0.76rem;
    line-height: 1.5;
    margin-bottom: var(--gap-hair);
  }

  .survived :global(.ticked) {
    margin-top: 0.15rem;
  }

  .specimen p {
    margin: 0;
    color: var(--ink-soft);
  }
</style>
