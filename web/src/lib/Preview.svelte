<script lang="ts">
  import Ledger from "./claim/Ledger.svelte";

  let { base }: { base: string } = $props();

  // Only here, on the preview page. Which surface a visitor gets is the shell's decision and it is
  // not made yet; this exists so both palettes can be checked against real content without waiting
  // for one, since a token set that has never been rendered in its second surface is a guess.
  let surface = $state<"day" | "night">("day");

  $effect(() => {
    document.documentElement.dataset.surface = surface;
  });
</script>

<main>
  <header class="head">
    <div>
      <p class="kicker">Migratlas · component preview</p>
      <h1>The claim card</h1>
      <p class="note">
        ADR 0007, built bottom-up. Not the shell: the shell shows one claim with the globe behind it.
      </p>
    </div>

    <fieldset class="surface">
      <legend>Surface</legend>
      {#each ["day", "night"] as const as option (option)}
        <label>
          <input type="radio" name="surface" value={option} bind:group={surface} />
          {option}
        </label>
      {/each}
    </fieldset>
  </header>

  <Ledger {base} />
</main>

<style>
  main {
    max-width: 66rem;
    margin: 0 auto;
    padding: 2.5rem 1.5rem 6rem;
  }

  .head {
    display: flex;
    flex-wrap: wrap;
    gap: var(--gap);
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--gap-wide);
  }

  .kicker {
    margin: 0;
    font-family: var(--font-mono);
    font-size: var(--size-label);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--pencil);
  }

  h1 {
    margin: var(--gap-hair) 0 0;
    font-family: var(--font-hand);
    font-weight: 400;
    font-size: 2rem;
    line-height: var(--leading-hand);
  }

  .note {
    margin: var(--gap-hair) 0 0;
    font-size: 0.85rem;
    color: var(--ink-soft);
  }

  .surface {
    display: flex;
    gap: var(--gap-tight);
    align-items: center;
    margin: 0;
    padding: var(--gap-hair) var(--gap-tight);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    font-family: var(--font-mono);
    font-size: var(--size-margin);
    color: var(--ink-soft);
  }

  .surface legend {
    padding: 0 0.3rem;
    font-size: var(--size-label);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--pencil);
  }

  .surface label {
    display: flex;
    gap: 0.25rem;
    align-items: center;
    cursor: pointer;
  }

  .surface input {
    accent-color: var(--rust);
  }
</style>
