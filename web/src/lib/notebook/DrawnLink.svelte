<script lang="ts">
  import type { Snippet } from "svelte";
  import Rule from "./Rule.svelte";

  let {
    href,
    seed,
    class: className = "",
    children,
  }: {
    href: string;
    /** What the underline's wobble is drawn from, so the same link is underlined the same way. */
    seed: string;
    /** Passed through, so a page's own selector -- and the contrast sweep's -- still finds it. */
    class?: string;
    children: Snippet;
  } = $props();
</script>

<!--
  A link written by hand and underlined by hand.

  It was the browser's underline under a typewriter face, the one mark on a drawn page that a reader
  could tell came out of a stylesheet. The words are the marker face the page's prose is set in, and
  the line under them is the same stroke as the rule under each heading, drawn at the words' width
  rather than stretched to it.
-->
<a class="drawn-link {className}" {href} rel="noopener" target="_blank">
  <span>{@render children()}</span>
  <Rule {seed} tone="rust" draw={false} />
</a>

<style>
  .drawn-link {
    display: inline-flex;
    flex-direction: column;
    align-self: flex-start;
    max-width: 100%;
    font-family: var(--font-body);
    font-size: calc(var(--size-margin) * 1.15);
    line-height: 1.35;
    color: var(--rust);
    text-decoration: none;
  }

  /* Tucked up under the words: a rule's box is ten pixels for a line drawn through its middle. */
  .drawn-link :global(.rule) {
    margin-top: -2px;
  }

  .drawn-link:hover,
  .drawn-link:focus-visible {
    color: var(--rust-ink);
  }
</style>
