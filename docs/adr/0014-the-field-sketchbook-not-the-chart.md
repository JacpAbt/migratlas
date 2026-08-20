# ADR 0014 — The field sketchbook, not the old chart

**Status:** accepted · 2026-08-20. Supersedes [ADR 0013](0013-the-scroll-and-the-chapters.md)
decision 1 and its framing only. Decisions 2 through 5 of that ADR — the projection spike, the
book's opening, the chapters as thumb tabs, and the design language carrying over — stand exactly
as written and are not reopened here.

## Context

ADR 0013 recorded an owner input from 2026-08-18 faithfully: *"like old medieval maps with doodles
around drawn in."* It then built decision 1 on the medieval idiom and, more consequentially, took
its central device from there — old charts drew monsters where knowledge ended, so `coverage-bias`
would render as the map's honest here-be-dragons.

The owner corrected the register on 2026-08-20: an **adventurer's sketchbook map**, not a medieval
one. The doodles survive; the century does not.

That is a taste decision the owner is entitled to make without further justification, and it would
have been actioned on that basis alone. But working out what it meant concretely turned up a
better reason than taste, and it is worth recording because it changes what the map may contain
rather than only what it looks like.

**A field notebook's mark is a record. An old chart's mark is a decoration.** The two registers
have opposite relationships to ignorance. A dragon in an empty sea says *we do not know what is
here, so here is something invented*. A surveyor's hatched blank with "no coverage, 1995–2025"
written beside it says *we do not know what is here, and this is the precise shape of what we do
not know*. This project has spent its whole life on the second sentence. `coverage-bias` is a
measured claim with a scope and a caveat; the detectability wash is a published data product; the
fired stop conditions are graded predictions. Rendering any of it as invented marginalia would
have dressed measurements as whimsy on the one page where the whimsy is load-bearing.

So decision 1's device was wrong on its own terms, and the correction improves it. That is worth
saying plainly rather than presenting the change as a matter of preference that happened to land
well.

## Decisions

1. **The register is a working field sketchbook, kept by somebody surveying.** Late-nineteenth to
   mid-twentieth-century naturalist's or expedition notebook: pencil under-drawing, ink over the
   top, light washes, and writing in the margin addressed to nobody. This is not a new direction —
   it is what `styles/tokens.css` already is, down to the fibre-grain paper, the two inks measured
   for contrast, and the night palette chosen as *notes taken outdoors* rather than as a dark
   theme. Decision 1 reached for a different century than the stylesheet it inherited.

2. **Ignorance is drawn, and drawn as a record.** ADR 0013's instinct — put the emptiness on the
   map instead of hiding it — is the best idea in that document and it is kept in full. The
   execution changes: unsurveyed extent gets the surveyor's treatment (hatching or stipple that
   stops at a boundary, with a written note naming the gap and its years), never an invented
   creature. `coverage-bias`, the detectability wash and the fired stop conditions all render this
   way, on the map and on their chapters.

3. **Corrections stay visible, because that is what the notebook does and what this project
   already believes.** A struck-through value with its replacement beside it is a field-notebook
   convention *and* the repository's own convention — a wrong pre-registration is recorded as a
   correction rather than edited away. The drawing language and the epistemics agree here, so the
   map may show a superseded number struck rather than removed.

4. **Instruments, not ornaments.** A scale bar and a plain north arrow are in, because a surveyor
   needs them. Anything whose only job is to look old is out. Concretely out of the register:
   sea monsters and any invented fauna; compass roses with cardinal flourishes or wind-heads;
   cartouches and scrollwork; blackletter, gothic faces and decorative drop caps; rhumb lines
   drawn as decoration; faux ageing — torn or burnt edges, foxing, coffee rings; and invented
   labels of any kind, Latin ones included. The paper grain stays, because it is a real scan at a
   measured amplitude and it carries no claim.

5. **The bounded-jitter rule already in the code is the register's core discipline, not a
   compromise with it.** `globe/coastline.ts` draws the shore by hand with an excursion smaller
   than the pixel it is drawn at and withdraws entirely by the zoom where anyone could measure
   against it; `globe/graticule.ts` does the same for the coordinate lines. That is precisely how a
   careful surveyor sketches — freely where the sketch is the point, and not at all where a reader
   would take a position off the line. Both modules keep their rules and become the pattern every
   new drawn layer follows.

## Consequences

ADR 0013's `coverage-bias` marginalia needs re-specifying before the chapter that carries it is
built — the concept survives, its rendering does not, and decision 2 above is the replacement. Any
asset acquired for the medieval reading is not acquired; nothing was, so nothing is discarded.

The build order in ADR 0013 is unchanged: projection spike first, then the book shell, then
chapters, then the world. This ADR constrains what the spike draws, and does not delay it. Because
the register is now the one the stylesheet already implements, the spike's job narrows usefully:
it is a projection question and a legibility question, not an art-direction question.

`web/tests/` gains what it can actually assert. A register is not testable, but its exclusions
partly are — no font family outside the four in `tokens.css` may reach the map, and the drawn
layers must still withdraw at the zoom their own modules promise. The rest is decided by looking,
which is what decision 2 of ADR 0013 exists to make somebody do.
