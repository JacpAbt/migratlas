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

**Still to settle.** The margin's behaviour on a phone, where a 13rem column does not exist. It
collapses to below the claim, still always visible, still not behind a click.

**Settled by building rather than by describing.** The hand face was chosen from four candidates
rendered as the real claim card in the real palette, because a text mockup cannot convey a pen. That
exercise also killed one candidate outright on evidence: Shadows Into Light Two renders *lighter
than the body text beneath it*, inverting the hierarchy a heading exists to establish. No
description of it would have surfaced that.
