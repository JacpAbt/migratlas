# ADR 0008 — The sketchbook rebuild

**Status:** accepted · 2026-08-02

## Context

ADR 0007 chose a naturalist's field notebook and the choice was right. What shipped was a sketch of
it: four instrument drawings, one wobbled underline, one margin bracket, and everything else a CSS
box. The user's assessment, in their words, was that "the style is not a sketchbook" and "the
buttons and all of those things" were out of keeping — alongside two other complaints, that the
page is hard to read for a non-technical person and that the night surface, which ADR 0007 scoped
and this project built, could not be reached by anyone.

The question was whether to deepen what existed or start the visual layer again. **Started again**,
and the reason is not that the CSS was bad. It is that each of its ~1,300 lines was written to be
minimal, each justified by a specific bug it fixed. There was no expressive layer to deepen.

Concretely, why it did not read as a sketchbook:

- Every card was `1px solid var(--rule)` with `border-radius: 3px`. A stroked rounded rectangle is
  the most un-notebook-like object available; it is a UI card.
- Paper was a flat fill plus two gradients at 2–2.5% alpha. A texture hint, not a surface.
- Six drawn marks existed on a page of roughly forty elements.
- Buttons were `padding` + border + `background-color` on hover.
- Nothing was laid on anything. A notebook is a stack; this was one flat plane.
- Night was `#232b33`, a slate blue-grey: a dark *interface*, not a dark *artifact*.

## Decision

### 1. The architecture stays; the skin is rebuilt

Kept unchanged: the Svelte shell and its three-mode machine, `Globe.svelte`, everything in
`layers/`, `state/time.ts`, the search and shard machinery, and the data-logic modules
(`ledger.ts`, `story.ts`, `ribbon.ts`, `sandbox.ts`). Rebuilt: `styles/tokens.css`,
`notebook/ink.ts`, and every component's scoped `<style>`.

### 2. Which rules were negotiable, and which were not

This was settled with the user explicitly, because the previous ADR's constraints are a mix of
taste and integrity and treating them as one thing would have lost the second.

**Not negotiable, and still enforced by tests.** WCAG AA on both surfaces, measured in-browser
rather than eyeballed. Never colour alone. The caveat and the bias audit render *with* the claim
and never behind a control. At least one bias domain reads `open`. No creature drawn beside a claim
that cannot identify one — ADR 0007 §5 is a scientific-honesty rule, not a style. Numbers in a face
with tabular figures. `prefers-reduced-motion` lands in final state on frame one. Nothing
hard-codes a hex. The build requests nothing off-origin. Font licences ship beside the fonts.

**Negotiable, and changed.** The 1px borders, the 3px radius, the flat card, the two-kinds-of-motion
limit, and the night palette values.

**Loosened.** "Hand face for headings only, never below 20px" becomes *hand lettering may annotate
anywhere at ≥16px where contrast passes; numbers and dense labels stay mono.* Everything that made
the original rule right — tabular figures, small-size legibility — is preserved. The part that
starved the page of hand is not.

**Kept on merit though it was the user's to drop.** No number counts up to its value.

### 3. Paper is a sheet, not a div

`Sheet` renders three layers: a ground clipped to a torn path, the grain clipped to the same path,
and a drawn edge that overshoots its corners. Only the left edge is ragged — this is a leaf out of a
bound notebook, not hand-made paper with a deckle on all four sides. One irregular edge reads as
"removed from something"; four read as an effect.

Two CSS facts are load-bearing and cost a rebuild each:

- **`clip-path` and `box-shadow` do not compose.** The shadow is painted, then the element is
  clipped, so a torn card with a box-shadow has no shadow. `drop-shadow()` follows an arbitrary
  silhouette but the order is filter-then-clip, so it must sit on an *ancestor* of the clipped node
  — and not on the card, because a filter applies to the whole subtree and every word would get its
  own shadow.
- **A scrolling sheet must scroll inside the paper.** An absolutely-positioned edge inside a
  scrolling box is placed against the padding box, so the tear travels up the screen as you read.

### 4. Two states, because a hand has two

`Boxed` puts a mark round a control without touching the control: absolutely positioned,
`pointer-events: none`, so a button stays a `<button>` and a radio stays a radio.

A **box** is a thing you press and is always drawn — a button with no edge is a word. A **lasso** is
one option among several and is drawn only round the one in force; looping all three says nothing.

Pressed and chosen are a **second pass of the pen** from a different seed, offset from the first and
lighter — going over a line thickens it unevenly rather than doubling the ink. A hand does not have
a hover colour. Hover is a wash on the paper *under* the drawn box, because the ink is on the paper
and that is the order those two things exist in.

Rejected: filling a selected control. A filled pill reads as a setting the interface has; a circled
word reads as a choice someone made, and this project's whole argument is that a reader should be
making choices.

### 5. Night is black paper

`#16130f` under `#ece3d0`, warm rather than neutral for the same reason the day paper is not white.
Selectable in three states — day, system, night — because "follow the machine" is a choice and not
the absence of one: a two-state toggle cannot distinguish it, so the first click would opt out of
the system preference permanently.

The globe follows, and that half is not CSS. MapLibre paint is set in JavaScript, so every layer
implements `repaint` and the basemap has a night flavour. Four `setPaintProperty` calls rather than
`setStyle`, which would drop every source and re-fetch 450 KiB to change four colours.

### 6. The paper turns and the world does not

`view-transition-name: none` on the root is the line the whole thing rests on. A view transition
snapshots the entire document by default, which would freeze MapLibre's canvas into a still image
for the length of the turn — and a page turn that stops the world says the globe is a picture the
card is printed over, when it is the thing the claim is about.

The leaf turns about its spine, the same edge `sheetEdge` tears, and lifts as it goes because paper
does not rotate flat against a desk.

Three ways out, each the *end state* rather than a degraded one: no View Transitions support,
reduced motion, or an error inside the update. `turn.ts` reads `--draw` rather than calling
`matchMedia` again, so one block in `tokens.css` still governs every animation in the project.

### 7. Two registers, and the plain one is the heading

`plain`, `matters` and `plain_caveat` on every finding, required by the schema. The precise `claim`
and the full `caveat` are still rendered, unshortened, underneath. ADR 0007 refuses to let the
layout decide what the science says, and this does not: a second register was added above the
first, and a test asserts both are present and that neither equals the other.

The rule that makes a plain rewrite safe rather than merely shorter: **it may drop precision and may
never add reach.** A test refuses any plain sentence naming a creature on a claim whose taxon scope
is `unattributed`.

### 8. A claim has an address

`#c=<key>`, pushed rather than replaced, so back means the last claim read. The clock keeps
`replaceState` in the same hash — animating it would push hundreds of entries — and the two coexist
by both reading existing parameters before writing.

## Consequences

**Budgeted differently.** Bytes are the wrong instrument for animation: a page turn adds no payload
and can still cost a reader every frame of it. The new guard is a long task during a claim change,
ceiling 200ms, measured at 52–90ms.

That guard immediately caught a bug in itself, which is worth recording. `buffered: true` on a
longtask observer replays entries from before the observer existed, so it reported the page load —
MapLibre booting and 125,000 features decoding — as a constant 229ms for every claim, including
ones it had not clicked yet. **An interaction budget that silently measures the page load is worse
than no budget, because it reports a number and the number is about something else.**

**The suite grew from 42 to 57 browser tests and caught three real failures during the rebuild**: a
flex container with no direction collapsing the claim to zero height while leaving it in the DOM
with its text intact; a radio hidden with `clip-path: inset(50%)` staying in the accessibility tree
and ceasing to be a hit target; and the human occurrence surface, which is ADR-adjacent rather than
visual and is recorded in the git log.

**One thing found that was not the rebuild's.** `every layer draws features once it is switched on`
had been passing at 98% of its own deadline for the whole project. Its 150s budget came from timing
it alone — 66s — and doubling; under the suite it shares a machine with two other WebGL workers and
takes 130–150s. Now 240s from the contended number. No signal lost: a wedged map fails in eight
seconds at `DRAW_TIMEOUT_MS` with a state dump.

**Still to do**, and listed so the absence is a decision rather than a gap: the Explore panel has
paper and a shadow but no drawn edge, its sliders are still native, and `ink.ts` has `tick` waiting
for a use beyond the layer checkboxes. `docs/TASKS.md` item 7.

**ADR 0007's colour block is stale** and is left as written. It records `pencil #7d7266` and night
`graphite #8a8578` where the tokens shipped `#6b6157` and, now, `#9a9384` — each darkened or
lightened after the contrast test failed it. The ADR is a record of a decision on a date, not a
description of the current file; `tokens.css` is the current file.

## Amendment, 2026-10-05, the owner reading the book as finished

The owner found the parts of the book a hand had not written, and named them: the audit's domains
and verdicts, its headings, the "For the record" register, the direction banner, the refusal's
label, a knob's settings, and every "The plan, written down before we looked" link. All were set in
the typewriter face under section 2's "numbers and dense labels stay mono".

**Labels are no longer mono.** They are words, and the reason section 2 gave for mono -- tabular
figures, so a number stays a measurement -- reaches figures, not words. The small-size legibility
reason survives intact, because they move to the body face, Shantell Sans, a marker hand drawn to
stay legible at interface sizes, and not to the display hand, which section 2 still keeps at 16px
and above. A link is underlined by `notebook/DrawnLink.svelte` with the same stroke as the rule
under a heading, not the browser's line.

**Figures are unchanged and still enforced:** a value, a column of counts, an axis, a code path stay
mono, and `web/tests/notebook.spec.ts` holds the record's figure to it beside the labels it now
differs from. Whether a standalone figure -- the record's headline value, a knob's reading -- should
be written instead is the owner's call and is not taken here.

## Amendment, 2026-10-07, the owner's decision on standalone figures

The 2026-10-05 amendment left one question to the owner: whether a figure that stands alone -- the
record's headline value, a knob's reading -- should be written rather than typed. Shown one
record page with its value written, its plain caveat in the margin and an arrow back to the
paragraph, the owner answered: do it for all thirteen.

**A standalone figure is written.** The record's value and a knob's reading are set in the display
hand, at sizes above section 2's 16px floor. **A figure in a column of figures stays typed** -- the
coverage shares, a refusal's numbers, an axis, a table's counts -- because that is what section 2's
tabular-figures reason was always about: digits that have to line up with the digits above them.
`web/tests/notebook.spec.ts` now holds the coverage legend's shares to the typed face where it held
the record's value. The margin note is the claim's own plain caveat, the sentence its finding page
already carries; no words were written for it.

## Amendment, 2026-10-09, the book lies on a real table

The owner asked for the space around the book to be a table the journal lies on, with a candle that
is out by day and is lit by a match, animated, when the surface turns to night. Two attempts were
turned down: a desk drawn in the doodles' ink ("another journal"), and one painted in CSS ("fake
objects… ignoring depth, perspective"). Offered a live 3D scene, the owner chose it.

**The table is a three.js scene under the book, and the book stays HTML.** The camera looks straight
down, the one view in which a flat page and a table in perspective can share a picture, and it is
placed so the book's rectangle on the screen covers a book-sized rectangle of the table: an open
journal 0.56 m wide. Everything else is at its real size against that, so perspective, shadows and
the candle's light fall on it as they would on the wood. `web/src/lib/desk/scene.ts` holds the
geometry; the scanned models and the wood are CC0, from Poly Haven, recorded with the recipe that
shrank them in `web/public/desk/README.md`. Nothing on the table is an animal: section 2's rule
against a creature beside a claim that cannot identify one reaches the margin around every claim.

**It costs the reader nothing they came for.** The scene and three.js are a separate chunk, 661 KB
(167 KB gzipped), plus 0.92 MB of models and wood, loaded after the fonts and the book; the canvas
takes no pointer events and is hidden from assistive technology. It draws only while something
moves. Where a browser draws WebGL without a graphics card, one frame took seconds, so there the
painted walnut under the canvas is the table and no scene is made; `?desk=3d` makes it anyway,
which is how the suite tests it on a runner that has no graphics card.

**What this fixes for later work.** The camera cannot tilt: a view from the side would need the book
itself in the scene, which is the book rebuilt, not a background changed. On a window the book
nearly fills, the things on the table are cropped at its edges, because their size is what makes
them read as real and there is no margin to move them into.
