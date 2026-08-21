# ADR 0015 — The book on the desk

**Status:** accepted · 2026-08-20. Settles the layout ADR 0013 left open and ADR 0014 constrained.
Neither is superseded: 0013's build order and chapters stand, 0014's register stands, and this
records what the spread actually is, decided by looking at it rather than by argument.

## Context

ADR 0013 fixed the build order and the chapters and deliberately left the projection open behind a
measurement. ADR 0014 fixed the register — a field sketchbook, not an old chart. What neither
settled was the shape of a page.

Four candidate layouts were built in `web/mocks/book.html` and **all four were rejected**: none read
as an object you could pick up, the map sat behind the page rather than in it, and everything was
too small to read. The owner's note was the useful part — a true double page with a line down it,
a shadow under it, the map sketched and inside the book, page-turn on the tabs, and *"have fun with
it, this is way too clean"*. The second pass built one book and offered three ways of attaching the
plate. That was approved on 2026-08-20 with variant 1.

The mock earned its keep twice over: once by settling the layout, and once by finding six defects
that would otherwise have been found in the real shell, where they would have been more expensive.
Five of them shared one cause, which is the most useful thing in this document.

## Decisions

1. **The spread is the object.** Two pages meeting exactly on the centre line, a crease darker than
   any rule on the page, paper curling into the fold and catching light at the outer edges, two
   slabs behind it with page edges seen almost end-on, and two shadows onto a desk — a long soft one
   for height and a tight dark one where a book actually touches. The desk is two faint washes, not
   a flat fill: a flat ground under a shadowed object reads as a rectangle floating on a colour.

2. **The plate is taped in.** A separate sheet, a shade off the page, hung a degree crooked with two
   torn tape strips. The two rejected alternatives are recorded because the choice was between real
   options: ink straight onto the page with no sheet and no shadow, or a tipped-in plate on heavier
   stock with a fold and a paper clip.

3. **Chapters are coloured thumb tabs, and clicking one turns the page.** The tab carries a word and
   the page carries the full title — seven full titles set vertically ran past the foot of the book.
   Tints are the palette's own hues mixed into the page's paper, ordered so no two neighbours share
   one, greys at the ends where the introduction and the back pocket are. An open tab is its own
   colour at strength, because an open tab is the same tab.

4. **The map is drawn, and so are its blanks.** rough.js over the project's own geometry, hachure on
   the largest landmasses and stroke on the rest, a wobbled graticule, the claim's own extent
   cross-hatched and labelled by hand, and a scale bar and north arrow rather than a compass rose.
   The unsurveyed ground is hatched at its own angle with the gap named beside it, which is ADR 0014
   decision 2 discharged rather than restated.

5. **The turning leaf must *be* the page component, not a copy of it.** This is the rule the mock
   paid for. Five defects, one cause — a stand-in for a page needs everything a page has:

   | what was missing | how it showed |
   | --- | --- |
   | the page's own class | the padding rule did not match, so prose jumped 20px at both ends of the turn |
   | the page's paper | `z-index` isolated the parked copy, its grain had nothing to multiply against, and the covered page went pale |
   | the page's position | the leaf hinged on the page edge at `50% + fold/2` while the crease was at `50%` |
   | only the page's shading | face and clone both carried an edge gradient, so the sheet was shaded twice and brightened when the leaf hid |
   | the page's *identity* | the covered half updated to the incoming chapter before the leaf reached it |

   In the shell the leaf is the same component instance, so all five are impossible by construction
   rather than fixed one at a time.

6. **Sizes are measured, not chosen, and the measurements move into `tokens.css`.** The book is as
   large as the window allows in both axes with no pixel cap. Reading sizes get a book scale — the
   mock's local `--pt` exists only because tokens.css has none yet. Two figures are load-bearing and
   were arrived at by measuring: seven vertical tabs stack to **38 times** the font size, so the tab
   size is clamped against the book's own height; and a plate annotation must be sized in *rendered
   pixels* and multiplied by `--font-scale-hand`, because the plate's width depends on the window
   and the hand faces do not share an x-height with the body faces.

7. **No `filter` on any ancestor of the turn.** A filter flattens 3D transforms, so a drop-shadow on
   the book turned `rotateY` into a horizontal squash. The lift is box-shadows on the sheets.

8. **Added 2026-08-21: a phone is a second container, not this one squeezed.** Every measurement
   above was chosen against a shape 375px does not have. Two pages side by side on a phone are two
   195px columns; the crease has nothing to divide, the tab stack is taller than the book, and the
   plate is drawn at a size no longer worth drawing. So below `62rem` the reader mounts
   `lib/book/Leaves.svelte` instead of `Book.svelte` and the spread does not render at all.

   The three things that make it the same book rather than a second version of it:

   - **One authored set of pages.** `Reader` declares the page snippet once and hands it to
     whichever container the window gets, so a phone's pages and a monitor's cannot drift apart.
   - **The swipe is the page turn.** A `rotateY` needs somewhere for the page to go and a
     single-page screen has nowhere; horizontal scroll-snap makes the gesture and the turn one
     movement. The next leaf's edge shows past the current one, because otherwise nothing on screen
     says there is another page. Decision 5 still holds and costs nothing here — a leaf is a `Page`.
   - **Chapters are the fore-edge of a closed notebook**, in the bottom corner a thumb rests in, and
     they fan out on a tap. Seven tabs at once is 40% of a phone screen; one tab plus the others
     edge-on behind it is what a tabbed notebook looks like closed. The tints moved out of
     `Book.svelte`'s `nth-child` rules into `lib/book/tabs.ts` so both containers read one
     assignment, including its two measured exceptions.

   Two measurements this cost: a `requestAnimationFrame` throttle on the scroll handler **latched
   permanently** in a pane that does not composite, because the only code that cleared the gate was
   the frame that never came — the same trap this document already records for `animationend`, and
   scroll events are frame-aligned anyway, so the throttle bought nothing. And `--page-pad` was
   declared on `.book`, so the first leaf mounted outside it resolved `padding: var(--page-pad)`
   to an invalid declaration the browser drops: a page whose lede ran off both edges. A container
   that shows pages owes them their measurements, and a test now asks a leaf whether it got them.

   Not settled, and named so it is not mistaken for settled: the world chapter puts its controls on
   one leaf and its map on the next, so on a phone you cannot see the map while you move the clock.
   Uniform `(chapter, side)` leaves are what make the two containers one book, and breaking that for
   one chapter needs its own decision.

9. **Added 2026-08-21: a page that scrolls is not a page.** The owner's note was that scrolling the
   left page "kinda takes away the sketchbook feel", and the measurement was worse than the note:
   at 1600x900, against a page whose budget is 826px, the left page of *What did not* held
   **6,855px** — eight and a third screens on one leaf, with the sentence at the fold cut in half.
   Every chapter overflowed, two rectos included. A page with a scrollbar is a document wearing a
   book's clothes.

   **A book's answer to "this does not fit" is another page.** So the unit of the book is a *panel*:
   one page's worth of one thing, declared in `lib/book/pages.ts`. A claim is a run of panels —
   the finding in plain language, its figure, the record, the risk of bias, what it survived, then
   one safeguard knob or one dial to a page — folded into spreads two at a time, ending on blank
   paper rather than sharing a leaf with the next claim. The book went from 7 scrolling chapters to
   **35 spreads, 70 pages**, and the folio in the corner became a real page number instead of
   decoration.

   Panels are **declared, not measured**, and every split is at a seam the material already had.
   Which seams was decided by measuring, and the numbers are in the module: the bias table and what
   a claim survived were put on one page and overflowed by 231 and 304 on the two longest audits, so
   they are two pages facing each other; the counterfactual ribbon overflowed by 1,406 whole and 536
   with its charts alone, so it is one chart to a page and then the reading of them; the coverage
   assessment separates what could be measured from what is held back. Nothing was shortened to fit
   — `reports/findings.py` refuses to publish a claim without its caveat, and a layout that dropped
   one to save a page would do by omission what that refusal exists to prevent.

   Three things this cost, all worth recording:

   - **Reading sizes are now a fraction of the page**, which reverses a note in `tokens.css`. That
     note was right about the thing it was about — a reader's 100/115/130% preference, which the
     mock offered and the owner set to 100%. This is a different quantity. A page that scrolls fits
     any content at any window by definition; a page that does not has to hold the same panel at
     826px and at 726px. With the type fixed, 23 of 28 spreads overflowed at 1280x800 against 9 at
     1600x900, and every fix would have been a split that was wrong at the other size. Now the
     spread is a scaled copy of itself at every window and both sizes fit.
   - **The book's documents load before the first frame.** How many passages the introduction has,
     and which claims carry an audit or a dial, decide how many pages there are — so a folio printed
     before they arrive renumbers itself under the reader and a link to a page opens a different
     page. A book cannot count its own pages later. The four documents together are 56 KB; the
     460 KB assessment behind one figure is still lazy, because it changes nothing about where the
     pages fall.
   - **`figures.ts` declares page counts and a test asserts the documents agree.** The ribbon's own
     document is fetched by the component that draws it, so the pagination cannot count its charts.
     The declaration is therefore a claim about a file, and the test is what keeps it true.

   **The guard is the point.** `tests/book.spec.ts` walks all 70 pages by the corner at both
   supported sizes and asserts no page exceeds itself, that every page is reachable by turning, and
   that the folios run without a gap. Before pagination `.page__inner` scrolled, so every chapter
   fitted *by definition* and no test could see the 6,855px page. Without the guard the next
   paragraph added to a claim puts the scrollbar back in silence.

   Rejected, with a reason: CSS multi-column fragmentation. Flowing each chapter into page-sized
   columns needs no packing logic and would serve the phone and the spread with one mechanism, which
   is genuinely attractive. It cannot carry a `rotateY` turn — and that turn is what decision 5's
   five defects bought.

   Three defects the tests found while this was built, each of which would have shipped: the dial's
   two refusals got no pages at all, because `refusalsFor` keys the *safeguards'* one refusal to
   `marine-null` while the dial's travel with its dials — one pair of selectors for two documents
   made half a panel unreachable in a book that prints everything. The introduction was allocated a
   page for passages four to six of a document that has four. And the record page printed
   `finding.scope`, which the facing plate's caption already carried — the same sentence twice, two
   leaves apart, and up to 144px of the overflow.

## Consequences

`tokens.css` gains a book reading scale and the two plate tints, which are the only new visual
values this needs; every colour in the mock is already a token or a `color-mix` of one, and that
constraint holds in the shell.

`web/mocks/book.html` stays until the shell lands, as the reference the shell is checked against,
and goes when it does. It is dev-only — Vite builds `index.html` alone — so it costs the production
bundle nothing meanwhile.

Two things the mock could not answer and the shell must: it is a still, so panning, zooming and the
map's behaviour under interaction are untested; and its motion was verified by driving the
animation's own timeline rather than by watching it, because the pane it was built in does not
composite frames. Both belong in `web/tests/`, which already asks the map what it drew rather than
trusting pixels.

The reduced-motion path is a full path here as everywhere: `tokens.css` zeroes every duration, and
the turn is skipped rather than run at zero length.
