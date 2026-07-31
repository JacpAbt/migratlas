# ADR 0007 — The field-notebook shell

**Status:** accepted · 2026-07-30

## Context

The globe works and the research behind it holds, but the shell is a flat-modern layer switcher: a
map with panels arranged around it, where a *layer* is the first-class thing and a *claim* is content
inside a panel. That has the emphasis backwards. The project's asset is not its layers — anyone can
draw a grid — it is that every number carries its own audit and the audit is interactive.

The current look also has a cheaper problem: the left column ran out of room the moment a second
chart arrived, and it is held together by two height caps tuned to today's content
(`web/src/styles.css`, `.panel--layers` and `.panel--ribbon`). A fifth panel breaks it.

Eight decisions were taken with the user on 2026-07-30. They are recorded here rather than left in
CSS because a rebuild of this size drifts, and because most of them are arguments rather than
preferences.

## Decision

### 1. A naturalist's field notebook

Paper, ink, pencil and rust. Hand-drawn rules, brackets and arrows rather than borders and boxes.
Specimen labels. Numbers set as though typed onto a form.

Chosen because it is what the project already *is*. A notebook is the artifact of showing your
working, and "show me how you know" is the whole product. It also carries the ROBITT bias blocks
natively — a margin of pencilled caveats is a notebook's native furniture, not a bolted-on
disclaimer — and it composes with the parchment basemap that already exists rather than fighting it.

```
paper   #f5efe2   a faint fibre grain, not a photograph of paper
ink     #2f3d4f   body text, rules, the observed line
rust    #b4522e   the accent: change detected, detectable, emphasis
pencil  #7d7266   margins, annotations, anything the reader did not ask for
```

Rejected: risograph (fashionable, and the misregistration reads as a rendering bug the first time
anyone sees it), storybook (invites, then undercuts an attribution result), vintage poster (type as
hero fights the dense audit tables that are most of what this shows).

### 2. Hand-lettered headings on a serif body, numbers in mono

- **Headings** — **Architects Daughter**, an upright printed hand: the lettering of someone
  annotating a technical drawing rather than writing a diary. Chosen over three alternatives
  after building the real claim card in all four, because it is the only one whose character is
  specifically *scientific* rather than generically handwritten, and so the only one that agrees
  with the instrument vocabulary decision below.
- **Body** — **Source Serif 4**, 400 and 600, 1.55 line height.
- **Every number and label** — **IBM Plex Mono** 500.

The hand face is constrained, and the constraint is the decision rather than a caveat on it:
**headings only. Never a label, never a number, never below 20px.** Hand faces have no tabular
figures, poor small-size legibility and inconsistent metrics, so a number set in one stops being a
measurement. `−0.56 ± 0.25` is mono in every context, no exceptions.

All fonts are bundled and self-hosted, 68 KB total, licences beside them in
`web/public/fonts/`. `web/tests/globe.spec.ts` asserts the default build requests nothing
off-origin, and a webfont CDN would break it — correctly, since a font host sees every visitor's
IP.

**The accepted cost:** Architects Daughter has the widest metrics of the four candidates, so a
claim heading of more than about forty characters wraps. The ledger's `claim` field is a full
sentence and stays one — it is the scientific statement, and shortening it for the layout would be
the layout deciding what the science says. So the arrival screen budgets for three lines of
heading instead.

### 3. A claim first, the globe live behind it

A visitor lands on one argument, not on a map: *something is passing earlier over North America,
−0.56 days per decade, and about half of it is us.* The globe is already running behind it with the
camera on 37–50°N. Two ways out, both offered immediately: **show me how you know**, and **just let
me explore**.

The globe becomes the index to a set of arguments rather than the subject. Rejected: scrollytelling
(one authored path, and it fights exploration for a large multiple of the work), permanent split
(spends 38% of a laptop's width before drawing anything), keeping today's shape (leaves the
storytelling exactly where it is).

### 4. Svelte 5

Least ceremony for a page that is mostly imperative MapLibre calls plus reactive panels, ~5 KiB of
runtime, and no virtual DOM to fight over a map that owns its own lifecycle. The existing
`state/time.ts` clock maps onto runes almost directly.

Kept as-is through the rebuild: MapLibre, the `layers/manifest.json` machinery, the taxon index, the
grid decoder, and the CI performance budget. `web/tests/globe.spec.ts` — 15 tests, heap ceiling,
off-origin assertion — is the contract the rebuild must keep passing, not a suite to rewrite.

### 5. Plates only where the taxon is known

Public-domain plates from the Biodiversity Heritage Library, and **only** beside a claim that
actually identifies something: SABAP2's species, FISHGLOB's fish, MegaMove's sharks, turtles and
whales. Named, dated, credited, linked.

The radar claim gets a radar. It measures aerial biomass and cannot separate birds from bats from
insects — that is the caveat the whole of `phase1c-homogeneity.md` exists to bound — so a swallow
drawn beside it would contradict, in the most legible register the page has, what the words
underneath say. **The absence of a creature is the caveat made visible.**

Where a taxon is known but no plate exists, a silhouette. Never a generic bird standing in for a
taxon. BHL's historical collections skew hard to birds and fish, which is the exact skew this
project keeps correcting for, so plate availability must never decide what gets shown.

Instruments carry the rest of the vocabulary: radar dishes and range circles, trawl nets and
swept-area rectangles, part-filled atlas cards, a 50-stop route as pencil ticks, the CMIP6 ensemble
as fifteen grey threads.

### 6. Ink that draws itself, and camera flights

Two kinds of motion, nothing else:

- **SVG paths stroke on** as if drawn by hand — the ribbon's three lines, heading underlines,
  brackets.
- **The globe flies** between claims, so a reader sees where the evidence is.

The ribbon is why this is worth building at all: **the drawing order is the argument.** Observed
draws, then the counterfactual draws after it, and the reader *watches the gap fail to open*. Drawn
together, the same two lines make the reader hunt for a difference instead of witnessing its size.

`prefers-reduced-motion` gets a full path, and it is not a faster animation — every element lands in
its **final state on frame one**.

No idle globe spin, no parallax, and above all **no number counts up to its value**. A counting
number reads as a score. `−0.56 ± 0.25` is a measurement with an interval on it.

### 7a. A figure and a sandbox belong to the claim they are evidence for

Not to a panel of their own. The counterfactual is the attribution's argument, the detectability
assessment is the coverage limit's number, and the confound knobs are the safeguards behind whichever
claim they were computed against. Each renders inside its own claim and nowhere else, so a reader
never has to carry a number from one part of the page to another.

The sandbox is the exception that proves the margin rule. **One control on the page hides something,
and it is the OBIS refusal's figure** — a `+4.42°` apparent poleward shift against an audited
−0.011 °/decade. It is behind a button that says exactly what it will show, because printing a number
we assert is unsupported at full size beside the numbers we assert *are* supported would put both in
the same register. Clicking is the reader choosing to see the mistake, not being shown it as a
result.

One thing the panel must never imply, and it took reading the values to notice: **switching the
safeguards off makes the effect larger, not smaller.** Dropping the speed weighting takes the autumn
advance from −0.56 to −0.65; fitting a break at the detected outage takes it to −0.90. Three of the
four break specifications exceed the published one. So the published number is the conservative
choice among defensible ones — the opposite of the story an interactive "switch the safeguards off"
panel usually tells, and the panel says so in its own opening line.

### 7. One thing at a time, with a margin that is always there

A claim fills the page. Its five bias domains, its survived tests and its method link sit in a
genuine margin column: 8px, pencil grey, small — and never behind a click.

The distinction matters and is the reason progressive disclosure was rejected. `reports/findings.py`
refuses to publish a claim with no caveat and the browser suite asserts the caveat is *rendered*.
Putting it behind a `[more]` control would satisfy the letter of both and break the point: a caveat
has to arrive **with** the number. It does not have to arrive at the same size.

Rejected: a dense spread (a fourteen-year-old bounces off it), progressive disclosure (above).

### 8. Dark mode as a second surface, not an inversion

**Night field notes.** Not the day palette inverted — a different artifact, the way a notebook read
by torchlight is a different object from one on a desk.

```
day                     night
paper   #f5efe2         slate   #232b33
ink     #2f3d4f         chalk   #d9d3c4
rust    #b4522e         ember   #d9814a
pencil  #7d7266         graphite #8a8578
```

The ember is not the rust: `#b4522e` on slate loses the saturation that makes it read as *change* and
*detectable*, so it shifts warmer and lighter to hold the same job.

Honest scope, agreed with the user up front: this is roughly a week of the rebuild, not a day. It
needs a dark `EARTH_FLAVOR` for MapLibre (~15 keys), the ribbon's three line colours re-checked
against slate, and the detectability greys re-tuned — those four were chosen specifically to read as
"mostly grey" against parchment and will not transfer.

Every colour goes through a CSS custom property from the first commit. Nothing hard-codes a hex: not
the SVG chart, not the MapLibre paint expressions, not the detectability ramp. That is a prerequisite
for the second surface rather than a nicety, and it is cheap only if it is done from the start.

## Consequences

**What this costs.** A rebuild rather than a restyle, with a second full palette inside it. The
existing browser suite has to keep passing throughout, which is the thing that makes the rebuild
safe and also the thing that makes it slower.

**What it buys.** A shell where the audit is the design rather than an appendix to it, and where two
of the eight decisions — no creature beside an unattributed claim, no number that counts up — make
the page refuse an overclaim that a prettier page would happily make.

**Small screens are a decision, not a fallback.** The card is used at three widths -- a preview page,
a 52rem sheet on a globe, and a phone -- so it responds with a **container query**, not a media query.
A media query asks about the viewport, and on a 768px tablet the sheet is 522px while the viewport is
comfortably past any breakpoint: the two-column layout squeezed the claim body to 230px and wrapped
the hand heading over nine lines. Below the width two columns need, the margin drops under the claim
and stays exactly as visible.

Two rules for what the map owns, and the difference is not cosmetic. The **attribution** is a licence
notice, so the reading sheet reserves height for it and it never moves. **Zoom, projection and scale**
drive a globe that, at phone and tablet width, is entirely behind an opaque sheet -- 200px of buttons
printed over the claim's own text, controlling something the reader cannot see -- so they are hidden
while a claim is open and return the moment the sheet stops covering the sphere.

**Progress, 2026-07-31.** Tokens, the claim card and the shell are built and live at `/shell.html`
alongside the shipped globe, which keeps its own 15 tests untouched. The shell has three modes --
arriving, reading, exploring -- and `web/src/lib/story.ts` holds the per-claim camera and layer set,
because a camera position is presentation and does not belong in `reports/findings.py`.

**The panels landed 2026-07-31, and where they landed is the substantive change.** A figure belongs
to the *claim* it is evidence for, not to a panel of its own: the counterfactual is the attribution's
argument and the detectability assessment is the coverage limit's number, so each appears with its
claim and nowhere else. Only two claims have a figure, because only two have one that adds something
the sentence does not — the marine null and the composition control both say "indistinguishable from
zero", and a flat line drawn three times teaches nothing.

The tools — layer toggles with their generalisation statements, the clock, species search, and the
assessment's key — live in explore mode, which is what is left when no claim is in hand. The old page
put them around the globe permanently, which is what made a *layer* the first-class thing.

**The swap happened 2026-07-31.** `index.html` is the shell; the old page, its stylesheet, its two
panel modules and the `claims.html` preview are deleted. One entry point again.

Two things were carried across rather than lost with it. The **station popup** came free, since it
lives in `layers/series.ts` and the shell reuses that. The **night terminator** did not, and it was
ported deliberately: this globe's headline layer is *nocturnal* passage, so where night currently is
says something about when the animals fly. Its time-of-day control came back with it.

The old page's tests were **retargeted, not deleted.** That was a correction: the claim that they were
superseded was wrong, and checking properly found five assertions that are about the app rather than
its markup — the performance budget, the off-origin guarantee, clock-driven filter swapping without a
refetch, a grid decoding to the cell count its sidecar declares, and species shards staying lazy. Two
were genuinely superseded and were dropped. All three suites now target the one shipped page, split by
concern instead: `globe.spec.ts` is the map and the budget, `notebook.spec.ts` is type and contrast and
the refusals, `shell.spec.ts` is the modes and the navigation.

**Settled by building rather than by describing.** The hand face was chosen from four candidates
rendered as the real claim card in the real palette, because a text mockup cannot convey a pen. That
exercise also killed one candidate outright on evidence: Shadows Into Light Two renders *lighter
than the body text beneath it*, inverting the hierarchy a heading exists to establish. No
description of it would have surfaced that.
