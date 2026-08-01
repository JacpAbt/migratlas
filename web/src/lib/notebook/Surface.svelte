<script lang="ts">
  import { SURFACE_LABEL, SURFACES, type Surface } from "../../state/surface";

  let { surface, onchoose }: { surface: Surface; onchoose: (next: Surface) => void } = $props();
</script>

<!--
  Day, system, night.

  Three options rather than a toggle, because "follow the machine" is a choice and not the absence
  of one: a reader whose laptop dims at sunset wants the paper to dim with it, and a reader who
  picked day wants day at midnight. A two-state switch cannot express the difference, so the first
  click would silently opt out of the system preference for good.

  A radiogroup rather than three buttons: they are one setting with three values, and a screen
  reader should say so. The radios are real and visually hidden, so keyboard behaviour is the
  platform's rather than something reimplemented here.
-->
<fieldset class="surface">
  <legend class="sr-only">Paper</legend>
  {#each SURFACES as option (option)}
    <label class="surface__option" class:surface__option--on={surface === option}>
      <input
        type="radio"
        name="surface"
        value={option}
        checked={surface === option}
        onchange={() => onchoose(option)}
      />
      <span>{SURFACE_LABEL[option]}</span>
    </label>
  {/each}
</fieldset>

<style>
  .surface {
    display: flex;
    margin: 0;
    padding: 0;
    border: 0;
    gap: 1px;
  }

  .surface__option {
    /* One drawn box split in three, rather than three boxes: the options are one control. */
    position: relative;
    padding: 0.25rem 0.5rem;
    border: 1px solid var(--rule);
    font-family: var(--font-mono);
    font-size: var(--size-label);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ink-soft);
    cursor: pointer;
    transition:
      background-color var(--fade),
      color var(--fade);
  }

  .surface__option:first-of-type {
    border-radius: var(--radius) 0 0 var(--radius);
  }

  .surface__option:last-of-type {
    border-radius: 0 var(--radius) var(--radius) 0;
  }

  .surface__option:hover {
    background: var(--paper-sunken);
  }

  .surface__option--on {
    background: var(--paper-sunken);
    border-color: var(--pencil);
    color: var(--ink);
  }

  /* Transparent and covering its label, rather than clipped to a pixel in the corner.
     `clip-path: inset(50%)` keeps a radio in the accessibility tree but leaves it one pixel wide
     under the text, so the label's own span is what a pointer hits -- and `check()` on the radio
     times out with "span intercepts pointer events". Covering the label makes the real control the
     hit target, which is also what makes the styling a skin on a radio rather than a fake one. */
  .surface__option input {
    position: absolute;
    inset: 0;
    margin: 0;
    appearance: none;
    background: none;
    border: 0;
    cursor: pointer;
  }

  .surface__option:focus-within {
    outline: 2px solid var(--rust);
    outline-offset: 2px;
  }
</style>
