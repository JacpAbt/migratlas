<script lang="ts">
  import { TYPE_LABEL, TYPES, type TypeChoice } from "../../state/type";
  import Boxed from "./Boxed.svelte";

  let { choice, onchoose }: { choice: TypeChoice; onchoose: (next: TypeChoice) => void } =
    $props();
</script>

<!--
  Hand, clear, dyslexia.

  Beside the surface switch and built the same way, because it is the same kind of thing: a
  setting a reader makes about how the page reaches them. Two of the three options exist for
  people who cannot read the first one comfortably, so it is a control rather than a preference
  buried somewhere -- an accessibility provision behind a menu is one nobody finds.

  A radiogroup with real radios, visually replaced rather than reimplemented. The `title` carries
  what each face is for, since three words is all the switch has room for and the reason matters
  more than the name.
-->
<fieldset class="type">
  <legend class="sr-only">Type</legend>
  {#each TYPES as option (option)}
    <label
      class="type__option"
      class:type__option--on={choice === option}
      title={TYPE_LABEL[option].why}
    >
      <input
        type="radio"
        name="type"
        value={option}
        checked={choice === option}
        onchange={() => onchoose(option)}
      />
      <Boxed seed="type-{option}" shape="lasso" active={choice === option} />
      <span>{TYPE_LABEL[option].name}</span>
    </label>
  {/each}
</fieldset>

<style>
  .type {
    display: flex;
    margin: 0;
    padding: 0;
    border: 0;
    gap: 0.15rem;
  }

  /* Circled rather than boxed, and only the one in force -- looping all three would say nothing.
     The unchosen two are just words, which is why they carry no fill and no border either. */
  .type__option {
    position: relative;
    padding: 0.3rem 0.6rem;
    border: 0;
    font-family: var(--font-mono);
    font-size: var(--size-label);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ink-soft);
    cursor: pointer;
    transition: color var(--fade);
  }

  .type__option:hover,
  .type__option--on {
    color: var(--ink);
  }

  /* Covering its label rather than clipped to a pixel: a radio hidden with `clip-path: inset(50%)`
     keeps its place in the accessibility tree and loses its place as a hit target, so the span
     intercepts every click. */
  .type__option input {
    position: absolute;
    inset: 0;
    margin: 0;
    appearance: none;
    background: none;
    border: 0;
    cursor: pointer;
  }

  .type__option:focus-within {
    outline: 2px solid var(--rust);
    outline-offset: 2px;
  }
</style>
