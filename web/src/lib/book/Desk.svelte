<script lang="ts">
  /*
    Whether the candle is lit is a fact about the surface, read off the token the surface sets
    (`--candle-lit`, 1 at night) rather than worked out here -- the surface can be night by the
    reader's choice or by the system's, and `tokens.css` is the one place that knows which.

    It is followed only so that putting the candle out can leave a curl of smoke. Lighting it is a
    CSS transition on the flame and needs nothing from here; the smoke is a one-off, and a one-off
    is the one thing a transition cannot do.
  */
  let snuffed = $state(false);

  $effect(() => {
    const root = document.documentElement;
    const read = () => getComputedStyle(root).getPropertyValue("--candle-lit").trim() === "1";
    let lit = read();
    let clear: ReturnType<typeof setTimeout> | undefined;
    const follow = () => {
      const now = read();
      if (lit && !now) {
        snuffed = true;
        clearTimeout(clear);
        clear = setTimeout(() => (snuffed = false), 2600);
      }
      lit = now;
    };
    const surface = new MutationObserver(follow);
    surface.observe(root, { attributes: true, attributeFilter: ["data-surface"] });
    const system = matchMedia("(prefers-color-scheme: dark)");
    system.addEventListener("change", follow);
    return () => {
      surface.disconnect();
      system.removeEventListener("change", follow);
      clearTimeout(clear);
    };
  });
</script>

<!--
  The desk the book is open on, and what is lying on it.

  The owner asked for the book to be on a table, with the things a field journal is written beside:
  a candle, lit at night; a pencil; a compass, for a project about where animals go; the ring a cup
  left; a leaf pressed between pages and fallen out. Nothing on it is an animal, for the reason the
  instruments are drawn instead of creatures: a drawing of one kind of animal beside a claim about
  all of them would say something the claim does not.

  All of it lies under the book's edges and in the margins of the window, behind everything a reader
  touches. Purely the ink: nothing here is read, focused or announced.
-->
<div class="desk-things" class:desk-things--snuffed={snuffed} aria-hidden="true">
  <div class="glow"></div>

  <svg class="thing candle" viewBox="0 0 60 214">
    <!-- The saucer it stands in. -->
    <path class="brass" d="M 4 198 C 4 189 56 189 56 198 C 56 207 4 207 4 198 Z" />
    <path class="line" d="M 55 196 C 65 191 66 204 55 202" />
    <path class="line faint" d="M 6 199 C 8 192 52 191 54 198" />
    <!-- The candle, its top worn down, two drips down its side. -->
    <path class="wax" d="M 16 62 C 15 102 17 150 16 195 C 25 198 35 198 44 195 C 43 150 45 102 44 62 Z" />
    <path class="line faint" d="M 17 64 C 16 104 18 152 17 193" />
    <path class="wax-top" d="M 16 62 C 16 55 44 55 44 62 C 44 68 16 68 16 62 Z" />
    <path class="wax" d="M 20 64 C 19 74 23 78 24 68 Z" />
    <path class="wax" d="M 36 65 C 36 84 41 86 41 67 Z" />
    <!-- The wick, black from the last time it burned. -->
    <path class="wick" d="M 30 59 C 29 54 31 52 30 47" />
    <!-- The flame: grows from the wick when the surface goes to night, and flickers while lit. -->
    <g class="flame">
      <g class="flame__body">
        <path class="flame__outer" d="M 30 48 C 21 40 23 25 30 12 C 37 25 39 40 30 48 Z" />
        <path class="flame__core" d="M 30 46 C 26 41 27 33 30 27 C 33 33 34 41 30 46 Z" />
      </g>
    </g>
    <!-- And the smoke it leaves when it is put out. -->
    <path class="smoke" d="M 30 46 C 24 36 36 28 30 18 C 24 10 34 4 29 -6 C 26 -12 32 -18 30 -26" />
  </svg>

  <svg class="thing pencil" viewBox="0 0 262 34">
    <path class="wood" d="M 34 6 L 8 17 L 34 28 Z" />
    <path class="lead" d="M 15 14 L 8 17 L 15 20 Z" />
    <path class="paint" d="M 34 6 L 236 5 L 238 29 L 34 28 Z" />
    <path class="line faint" d="M 35 13 L 236 12" />
    <path class="line faint" d="M 35 21 L 237 21" />
    <path class="ferrule" d="M 236 5 L 250 5 L 250 29 L 238 29 Z" />
    <path class="line faint" d="M 241 6 L 241 28 M 245 6 L 245 28" />
    <path class="eraser" d="M 250 6 C 259 6 259 28 250 28 Z" />
  </svg>

  <svg class="thing compass" viewBox="0 0 124 132">
    <path class="line" d="M 54 12 C 52 0 72 0 70 12" />
    <circle class="brass" cx="62" cy="70" r="56" />
    <path class="line faint" d="M 10 72 C 12 40 40 16 66 15" />
    <circle class="dial" cx="62" cy="70" r="45" />
    <path class="line" d="M 62 29 L 62 36 M 62 104 L 62 111 M 21 70 L 28 70 M 96 70 L 103 70" />
    <path class="line faint" d="M 33 41 L 37 45 M 91 41 L 87 45 M 33 99 L 37 95 M 91 99 L 87 95" />
    <text class="letter" x="62" y="48" text-anchor="middle">N</text>
    <path class="needle needle--north" d="M 62 38 L 68 70 L 56 70 Z" />
    <path class="needle needle--south" d="M 56 70 L 68 70 L 62 102 Z" />
    <circle class="pivot" cx="62" cy="70" r="3" />
  </svg>

  <svg class="thing ring" viewBox="0 0 140 140">
    <path class="stain" d="M 70 12 C 104 10 130 38 128 72 C 126 106 98 130 66 128 C 34 126 10 100 12 66 C 14 34 40 14 70 12 Z" />
    <path class="stain thin" d="M 72 22 C 100 22 120 46 118 72 C 116 100 94 118 68 118 C 42 118 22 96 24 70 C 26 44 46 24 72 22 Z" />
    <path class="stain blot" d="M 120 98 C 128 102 130 112 122 114 C 116 115 114 104 120 98 Z" />
  </svg>

  <svg class="thing pressed" viewBox="0 0 132 64">
    <path class="pressed__blade" d="M 18 32 C 40 6 90 4 126 30 C 92 56 44 58 18 32 Z" />
    <path class="line" d="M 2 36 C 8 35 13 34 18 32 C 50 30 90 29 126 30" />
    <path class="line faint" d="M 40 31 L 52 16 M 62 30 L 74 13 M 84 30 L 96 15 M 44 32 L 58 46 M 66 31 L 80 48 M 88 30 L 100 44" />
  </svg>
</div>

<style>
  .desk-things {
    position: absolute;
    inset: 0;
    z-index: -1;
    pointer-events: none;
    --h: var(--book-h);
  }

  .thing {
    position: absolute;
    display: block;
    height: auto;
    overflow: visible;
  }

  .thing path,
  .thing circle {
    stroke: var(--ink-soft);
    stroke-width: 1.4;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .line {
    fill: none;
  }

  .faint {
    stroke-opacity: 0.45;
  }

  /* --- Where each thing lies, in book heights, so it lies the same way at every window --- */

  .candle {
    left: calc(var(--h) * -0.118);
    bottom: calc(var(--h) * 0.03);
    width: calc(var(--h) * 0.072);
  }

  .pencil {
    left: calc(var(--h) * -0.135);
    top: calc(var(--h) * 0.38);
    width: calc(var(--h) * 0.34);
    rotate: -21deg;
  }

  .compass {
    right: calc(var(--h) * -0.125);
    bottom: calc(var(--h) * -0.05);
    width: calc(var(--h) * 0.17);
    rotate: 9deg;
  }

  .ring {
    right: calc(var(--h) * -0.1);
    top: calc(var(--h) * -0.07);
    width: calc(var(--h) * 0.2);
  }

  /* Not `.leaf`: that is the turning sheet, which the tests find by that name. */
  .pressed {
    left: calc(var(--h) * 0.42);
    bottom: calc(var(--h) * -0.075);
    width: calc(var(--h) * 0.16);
    rotate: -13deg;
  }

  /* --- The inks: tokens, so night redraws them --- */

  .brass {
    fill: var(--brass);
  }

  .wax {
    fill: var(--wax);
  }

  .wax-top {
    fill: color-mix(in srgb, var(--wax) 80%, var(--ink-soft));
  }

  .wick {
    fill: none;
    stroke: var(--ink) !important;
    stroke-width: 1.8 !important;
  }

  .wood {
    fill: var(--wood-raw);
  }

  .lead,
  .pivot {
    fill: var(--ink);
  }

  .paint {
    fill: var(--pencil-paint);
  }

  .ferrule {
    fill: var(--brass);
  }

  .eraser {
    fill: color-mix(in srgb, var(--rust) 55%, var(--paper));
  }

  .dial {
    fill: var(--paper);
  }

  .letter {
    font-family: var(--font-hand);
    font-size: 13px;
    fill: var(--ink-soft);
  }

  .needle--north {
    fill: var(--rust);
  }

  .needle--south {
    fill: var(--paper);
  }

  .stain {
    fill: none;
    stroke: var(--stain) !important;
    stroke-width: 3.5 !important;
  }

  .stain.thin {
    stroke-width: 1.4 !important;
  }

  .stain.blot {
    fill: var(--stain);
    stroke-width: 0 !important;
  }

  .pressed__blade {
    fill: var(--leaf);
  }

  /* --- The candle --- */

  /*
    Lit by the surface: `--candle-lit` is 1 at night and 0 by day, and the flame's size follows it,
    so switching to night grows the flame from the wick and switching back shrinks it into it. The
    transition is the lighting; with reduced motion its duration is zero and the flame is simply
    there, or simply not.
  */
  .flame {
    transform-box: view-box;
    transform-origin: 30px 48px;
    scale: var(--candle-lit);
    opacity: var(--candle-lit);
    transition:
      scale var(--draw) var(--ease-pen) calc(var(--draw-quick) / 2),
      opacity var(--fade) linear calc(var(--draw-quick) / 2);
  }

  .flame__body {
    transform-box: view-box;
    transform-origin: 30px 48px;
    animation: flicker 2.3s ease-in-out infinite alternate;
    animation-play-state: var(--candle-flicker);
  }

  .flame__outer {
    fill: var(--flame);
    stroke: color-mix(in srgb, var(--flame) 70%, var(--rust)) !important;
    stroke-width: 0.8 !important;
  }

  .flame__core {
    fill: var(--flame-core);
    stroke: none !important;
  }

  @keyframes flicker {
    0% {
      transform: scale(1, 1) skewX(0deg);
    }

    30% {
      transform: scale(0.96, 1.05) skewX(2deg);
    }

    55% {
      transform: scale(1.03, 0.97) skewX(-1.5deg);
    }

    80% {
      transform: scale(0.98, 1.04) skewX(1deg);
    }

    100% {
      transform: scale(1.01, 0.99) skewX(-0.5deg);
    }
  }

  /* The pool of light it throws on the desk, under the book's edge. */
  .glow {
    position: absolute;
    left: calc(var(--h) * -0.082 - var(--h) * 0.6);
    bottom: calc(var(--h) * 0.245 - var(--h) * 0.6);
    width: calc(var(--h) * 1.2);
    aspect-ratio: 1;
    border-radius: 50%;
    background: radial-gradient(circle, var(--glow) 0%, transparent 62%);
    opacity: var(--candle-lit);
    transition: opacity var(--draw-slow) var(--ease-pen);
  }

  .smoke {
    fill: none;
    stroke: var(--pencil) !important;
    stroke-width: 1.2 !important;
    stroke-dasharray: 90;
    stroke-dashoffset: 90;
    opacity: 0;
  }

  .desk-things--snuffed .smoke {
    animation: smoke 2.4s ease-out forwards;
  }

  @keyframes smoke {
    0% {
      stroke-dashoffset: 90;
      opacity: 0.8;
      translate: 0 0;
    }

    60% {
      opacity: 0.5;
    }

    100% {
      stroke-dashoffset: 0;
      opacity: 0;
      translate: 2px -14px;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .flame__body,
    .desk-things--snuffed .smoke {
      animation: none;
    }
  }
</style>
