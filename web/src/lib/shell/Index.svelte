<script lang="ts">
  import { DIRECTION_LABEL, type Finding } from "../ledger";

  let {
    findings,
    selected,
    onchoose,
    onclear,
  }: {
    findings: Finding[];
    /** The claim being read, or null while exploring. */
    selected: string | null;
    onchoose: (finding: Finding) => void;
    onclear: () => void;
  } = $props();

  /** First clause only. The tabs are an index, and the full sentence is on the claim itself. */
  function short(claim: string): string {
    const cut = claim.split(/[:—;]| -- /)[0] ?? claim;
    return cut.length > 46 ? `${cut.slice(0, 44).trimEnd()}…` : cut.replace(/\.$/, "");
  }
</script>

<!--
  The index: the globe is an index to a set of arguments, and this is the index made visible.

  Not a layer switcher. The old shell listed what went *in*; this lists what came *out*, and the
  layers follow from the claim rather than the other way round. Every entry says whether it found a
  change, a null or a limit, so a reader can see before clicking that the set is not all positives.
-->
<nav class="index" aria-label="Claims">
  <ul>
    {#each findings as finding (finding.key)}
      <li>
        <button
          type="button"
          class="tab tab--{finding.direction}"
          class:tab--on={selected === finding.key}
          aria-current={selected === finding.key ? "true" : undefined}
          onclick={() => onchoose(finding)}
        >
          <span class="tab__what">{DIRECTION_LABEL[finding.direction]}</span>
          <span class="tab__claim">{short(finding.claim)}</span>
        </button>
      </li>
    {/each}
    <li>
      <button type="button" class="tab tab--clear" class:tab--on={selected === null} onclick={onclear}>
        <span class="tab__what">globe</span>
        <span class="tab__claim">Just the map</span>
      </button>
    </li>
  </ul>
</nav>

<style>
  .index {
    position: absolute;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: 3;
    /* Fixed rather than content-derived: `--strip` is what the sheet above and MapLibre's controls
       both clear, so the strip has to be exactly that tall or the reservation is a guess. */
    height: var(--strip);
    padding: var(--gap-tight) var(--gap);
    background-color: var(--paper);
    background-image: var(--grain);
    border-top: 1px solid var(--rule);
  }

  ul {
    display: flex;
    gap: var(--gap-tight);
    /* Scrolls sideways rather than wrapping to two rows: this strip has to keep a predictable
       height, because the reading sheet above reserves space for exactly one. */
    overflow-x: auto;
    margin: 0 auto;
    padding: 0;
    max-width: 78rem;
    height: 100%;
    align-items: center;
    list-style: none;
    /* Hidden rather than thin: a horizontal scrollbar inside a 3.5rem strip eats a third of it, and
       on a phone that is the difference between two lines of tab and one. The fade below is the
       affordance instead. */
    scrollbar-width: none;
    /* Fades the right edge so it is visible that there is more strip than screen. Costs a slightly
       pale last tab when scrolled to the end, which is cheaper than a reader never learning the
       other four claims exist. */
    mask-image: linear-gradient(to right, #000 calc(100% - 1.75rem), transparent);
  }

  ul::-webkit-scrollbar {
    display: none;
  }

  li {
    flex: none;
  }

  .tab {
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding: var(--gap-hair) var(--gap-tight);
    max-width: 15rem;
    text-align: left;
    background: transparent;
    border: 1px solid transparent;
    /* The state that matters is which claim is open, and it is carried by a drawn underline in the
       accent rather than by a filled tab: a notebook marks a page, it does not highlight it. */
    border-bottom: 2px solid transparent;
    border-radius: var(--radius) var(--radius) 0 0;
    cursor: pointer;
    transition: background-color var(--fade), border-color var(--fade);
  }

  .tab:hover {
    background: var(--paper-sunken);
  }

  .tab--on {
    border-bottom-color: var(--rust-ink);
    background: var(--paper-sunken);
  }

  .tab__what {
    font-family: var(--font-mono);
    font-size: var(--size-label);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--pencil);
  }

  /* Direction in words above and colour on the label, never colour alone. */
  .tab--change .tab__what {
    color: var(--rust);
  }

  .tab__claim {
    font-size: 0.82rem;
    line-height: 1.3;
    color: var(--ink);
    /* One line per tab. The full sentence is the claim's own heading; this is a way back to it. */
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .tab--clear .tab__claim {
    color: var(--ink-soft);
  }

  @media (max-width: 40rem) {
    /* Narrower, so more than one and a half tabs are on screen. At 15rem a phone showed the open
       claim and half of the next, which reads as a broken layout rather than as a scrollable list. */
    .tab {
      max-width: 11rem;
    }
  }
</style>
