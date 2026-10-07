<script lang="ts">
  import { verdict, type VerdictMark } from "./ink";

  let { seed, status }: { seed: string; status: string } = $props();

  const SIZE = 20;

  /** Which mark a verdict gets, by the ledger's own word for it. */
  const MARK: Record<string, VerdictMark> = {
    addressed: "tick",
    bounded: "wave",
    open: "query",
    "not applicable": "dash",
  };

  const INK: Record<VerdictMark, string> = {
    tick: "var(--status-addressed)",
    wave: "var(--status-bounded)",
    query: "var(--status-open)",
    dash: "var(--pencil)",
  };

  let host = $state<SVGSVGElement | null>(null);
  const mark = $derived(MARK[status] ?? "dash");

  $effect(() => {
    if (!host) return;
    host.replaceChildren();
    verdict(host, seed, mark, SIZE, INK[mark]);
  });
</script>

<!--
  The mark a marker leaves beside a verdict: a tick, a wavy line, a ringed question, a dash.

  The audit's verdicts were words alone, set small at the end of each row, and the page read as a
  form. A reader grading something in a notebook marks it, and the mark is what the eye finds first;
  the word beside it stays, because colour and shape are never the only signal -- ADR 0008 -- and the
  word is the meaning. Drawn, not lettered: a "?" set in the hand face would be text, and the word
  beside it is read as the verdict's whole text.
-->
<svg
  bind:this={host}
  class="verdict verdict--{mark}"
  viewBox="0 0 {SIZE} {SIZE}"
  width={SIZE}
  height={SIZE}
  aria-hidden="true"
></svg>

<style>
  .verdict {
    flex: none;
    overflow: visible;
    vertical-align: -0.28em;
    margin-right: 0.3em;
  }

  .verdict :global(path) {
    fill: none;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
</style>
