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
        <!-- `data-claim` is the stable handle. The suite used to reach a tab by a fragment of its
             sentence, so rewording one claim broke six navigation tests that were not about
             wording at all. A key does not change when prose does. -->
        <button
          type="button"
          class="tab tab--{finding.direction}"
          class:tab--on={selected === finding.key}
          data-claim={finding.key}
          aria-current={selected === finding.key ? "true" : undefined}
          onclick={() => onchoose(finding)}
        >
          <span class="tab__what">{DIRECTION_LABEL[finding.direction]}</span>
          <!-- The plain register, because a tab is forty-six characters and the precise sentence
               is truncated to nothing useful at that width. The exact claim is on the card. -->
          <span class="tab__claim">{short(finding.plain)}</span>
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

  /*
    A tab in a notebook is a corner of the page showing past the one on top of it, so these are cut
    corners rather than rounded ones -- and the current tab is dog-eared: its corner is folded back
    further, which is how you find the page you were on.

    `clip-path` rather than a border, so the shape is the paper and not a decoration around it.
  */
  .tab {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding: var(--gap-hair) var(--gap-tight) var(--gap-hair) 0.7rem;
    max-width: 15rem;
    text-align: left;
    background: transparent;
    border: 0;
    clip-path: polygon(0.55rem 0, 100% 0, 100% 100%, 0 100%);
    cursor: pointer;
    transition:
      background-color var(--fade),
      clip-path var(--fade);
  }

  .tab:hover {
    background: var(--paper-sunken);
  }

  /* Folded back at both corners and lifted onto the paper. The rust rule underneath is the pencil
     line a reader draws under the page they are on -- colour is never the only signal, and the
     fold is the other one. */
  .tab--on {
    background: var(--paper-sunken);
    clip-path: polygon(0.9rem 0, 100% 0, 100% calc(100% - 0.5rem), calc(100% - 0.5rem) 100%, 0 100%);
  }

  .tab--on::after {
    content: "";
    position: absolute;
    right: 0.5rem;
    bottom: 0;
    left: 0.9rem;
    height: 2px;
    background: var(--rust-ink);
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
