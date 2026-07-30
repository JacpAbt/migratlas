<script lang="ts">
  import Claim from "./Claim.svelte";
  import Rule from "../notebook/Rule.svelte";
  import { loadLedger, type Ledger } from "../ledger";

  let { base }: { base: string } = $props();

  let ledger = $state<Ledger | null>(null);
  let failure = $state<string | null>(null);

  $effect(() => {
    loadLedger(base)
      .then((loaded) => (ledger = loaded))
      .catch((error: unknown) => (failure = String(error)));
  });
</script>

{#if failure}
  <!-- Degrades the same way the old panel did: says what is wrong rather than rendering nothing,
       because a blank page and a failed fetch look identical to whoever has to debug it. -->
  <p class="failure">{failure}</p>
{:else if ledger}
  <p class="count">
    {ledger.findings.length} claims · schema {ledger.schema_version} · every number recomputed from
    the lake by <code>reports/findings.py</code>
  </p>
  <Rule seed="ledger-head" tone="pencil" />

  <div class="stack">
    {#each ledger.findings as finding (finding.key)}
      <Claim {finding} />
    {/each}
  </div>
{:else}
  <p class="count">Reading the ledger…</p>
{/if}

<style>
  .stack {
    display: flex;
    flex-direction: column;
    /* Wide, because ADR 0007 shows one claim at a time. Here they are stacked only so all five can
       be judged in one screenshot; the shell will show one. The gap has to be large enough that
       nobody mistakes this page for the layout. */
    gap: 4.5rem;
    margin-top: var(--gap-wide);
  }

  .count,
  .failure {
    margin: 0;
    font-family: var(--font-mono);
    font-size: var(--size-margin);
    color: var(--pencil);
  }

  .failure {
    color: var(--rust);
  }

  code {
    font-family: var(--font-mono);
    color: var(--ink-soft);
  }
</style>
