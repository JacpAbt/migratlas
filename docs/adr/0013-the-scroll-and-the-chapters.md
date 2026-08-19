# ADR 0013 — The scroll and the chapters

**Status:** accepted as direction · 2026-08-19, with one question deliberately left open behind a
measurement. This is the build-time ADR that ADR 0012 promised: the backend it waited for is
finished — nine findings, thirty-one sources, five phase-3 method notes with every prediction
graded — so the presentation arc now has a complete story to present.

## Context

Two owner inputs since ADR 0012. The first (2026-08-18): *"maybe the globe is strange with the
style we have — what if it was instead a scroll of the world map? Lighter than a globe, and we
could have it have more stylistic things, like old medieval maps with doodles around drawn in."*
The second, implicit in the whole modeling arc: the site's argument is now as much about what
cannot be seen or predicted as about what can, and the presentation has to carry empty cells,
refused licences and fired stop conditions as first-class content, not as apologies.

The evidence favours the scroll on engineering grounds too, and it is worth recording that none
of it was known when ADR 0002 chose the globe. Every rendering trap this project has hit and paid
for was globe-projection-specific: the `queryRenderedFeatures` under-reporting that produced the
tiler misdiagnosis, the empty-canvas-at-60fps failure mode, the camera gymnastics `transfer-fails`
needs to keep three continents visible at once. A flat map shows the whole system in one glance —
which is what a project about *what moves together* needs its reader to see.

## Decisions

1. **The scroll is the primary canvas.** A flat, pannable world map in the hand-drawn-chart
   register — the notebook's own ink and paper extended to cartography. The medieval idiom is not
   decoration here: old charts drew monsters where knowledge ended, and this site's proudest
   layers are its own ignorance. `coverage-bias` renders as marginalia — the map's honest
   here-be-dragons — and the fired stop conditions get the same treatment on their chapters.

2. **The projection is decided by a spike, not an argument.** MapLibre's flat mode is Web
   Mercator, and Svalbard's reindeer and the ice edge live exactly where Mercator stretches
   worst. Before any layout work builds on the scroll, one spike renders the herd surfaces and
   the ice contours on flat Mercator in the house style and the pixels are looked at. Three
   outcomes were named in advance: Mercator with honest high-latitude framing; Mercator plus a
   small polar inset (the globe demoted to "the pole in the corner"); or a measured case that
   neither works, which reopens this decision with data. The spike's screenshots are the
   evidence, per the `Located.error_km` rule: never trust an instrument that has not been checked
   against pixels.

3. **The book opens like a book.** An introduction is the first thing a visitor sees: what this
   is, what kind of claims it makes, and how to read a caveat. The arrival's three doors survive
   as the introduction's last paragraph, not its replacement.

4. **The chapters are the argument, as thumb tabs down the side.** Their order is the ledger's
   own logic, and each chapter is a direction the findings already carry:
   - *Introduction* — what this book is.
   - *What changed* — `autumn-advance`, `anthropogenic-share`, `composition-stable`.
   - *What did not* — `marine-null`, `atlas-no-net-change`, `displacement-flat`.
   - *What we cannot see* — `coverage-bias`, the detectability wash, `transfer-fails`.
   - *What can be predicted* — `skill-sparse`, and the rehearsal's refused licence told as the
     page it deserves: the site bet against itself and won.
   - *The world* — explore: the scroll, the layers, the clock, the search.
   A story-side table maps ledger keys to chapters, the same shape as `VIEWS`, and the guard
   tests extend to it: a published claim without a chapter fails the build.

5. **The design language stays.** Sheet, Rule, the rough-ink boxes, the pencil sliders — the
   rebuild is structural, not stylistic. Everything ADR 0007 and 0008 earned carries over, and
   the ethics furniture (terms lines, caveats beside numbers, generalisation statements) is
   load-bearing in every chapter, as it already is on every claim.

## Consequences

The globe-specific test machinery (draw-walk zoom hints, the pixel probes) needs a
projection-agnostic restatement, and the payload budget conversation reopens because a flat map
culls differently. The `because` lines in `VIEWS` — written for a camera on a sphere — get
re-authored for a camera over a chart. And the arrival, claim ribbons and explore panel dissolve
into the book structure, which is where #53's fixed-but-awkward panel finally retires.

Build order: the projection spike first, then the book shell (tabs, introduction, chapter
routing), then chapter-by-chapter content, world last. Each lands behind the same gates as
everything else.
