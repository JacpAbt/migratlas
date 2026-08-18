# ADR 0012 — The book, not the skeleton

**Status:** accepted as direction · 2026-08-08. The build is deliberately deferred: backend first,
then one presentation arc, then version 1.0. A build-time ADR will fix the final design; this one
records what the owner asked for so the backend is finished with the destination in view.

## Context

The owner's assessment, with the movement arc complete: *"what we have now is a great skeleton,
not well presented."* Two specific asks and one general one. The chapters should be **tabs on the
side of the sketchbook**, as a bound book carries them, not a strip along the bottom. A visitor
should be **introduced first** — open the site, learn what this is, understand, and then go to the
world or into the chapters for depth. And overall: *"we are not explaining the story well of what
we are showing."*

The assessment is right, and it is the same shape as the 2026-08-07 one that started the movement
arc: the parts are sound and the presentation does not carry them. ADR 0007 chose the notebook and
ADR 0008 made the paper real; neither ever taught the site to *introduce itself*. A visitor still
lands mid-argument, on one claim, with no statement of what the book in their hands is.

Two defects reported in the same breath, logged as #53 rather than fixed here: the Explore panel's
controls overlap at some widths, and the Play button does not visibly run the year. Both live in
the panel this ADR will dissolve, but the site is live and they should not wait for v1.0.

## The direction, imagined

1. **The site is a book on a desk, and the desk is the globe.** v1.0 completes the metaphor the
   sketchbook rebuild started: the notebook has a first opening, thumb-index tabs down its side
   edge, and the sphere behind it is what the book is about — visible from every page, flown by
   every chapter.

2. **Arrival becomes an introduction, not a headline.** The first opening says what this is — a
   globe of animal movement; every number recomputed from the data on every build; every claim
   carrying its own audit — in a few sentences, while the year plays behind it: darts turning,
   herds breathing, ice walking. Then the ways in, with context instead of instead-of-context.
   The current arrival's virtue (the number arrives with its caveat) survives inside the first
   chapter rather than being the front door.

3. **Chapters tell the story in order, and the order is the argument.** The findings are not
   seven parallel tabs; they are a narrative with a spine: what the radar saw — the same sky,
   checked — how much of it is us — the seas do not agree — the south, checked — where nothing
   can be seen — what does not transfer. Side tabs carry the chapters; the bottom strip retires.
   The ledger's honesty (nulls and limits beside changes) becomes *pacing* instead of a list.

4. **The world is the map in the book's back pocket.** Explore mode gets its own presentation
   pass: the single tall panel decomposed — layers, clock, and search as their own small sheets —
   per-layer terms behind each layer's own chip instead of a concatenated wall of
   generalization statements, and the clock given a real transport. This is where #53's defects
   die structurally rather than being patched.

5. **What must survive, because it is not presentation.** The caveat arrives with the number and
   never behind a control. The margin audit is always visible. No creature beside an unattributed
   claim. No number counts up to its value. AA on both surfaces, measured in-browser. All prose
   authored in the reports layer. The plain register may drop precision and may never add reach.
   Every rule ADR 0008 marked non-negotiable remains so.

## Build order

Backend to v1.0 first, so the rebuild presents everything at once rather than being rebuilt again:
the green wave (#40), the elk finding (#43), step-selection (#44), Forecast A (#13), and the
migratory-source admission (#49) if a candidate survey finds one. The write-ups (#45–#48) run
alongside as writing. Then the presentation arc (#52), opened with its own ADR that turns this
direction into a design the way ADR 0008 turned ADR 0007's choice into paper.

## Consequences

Frontend work between now and the rebuild is triage only (#53) — nothing new gets built on the
bottom strip or the tall panel, because building on what will be dissolved is work spent twice.
The backend fronts, by contrast, now build *toward a known presentation*: every new layer and
finding should keep its prose, captions and per-layer terms clean, because the book that will
finally present them is already on order.
