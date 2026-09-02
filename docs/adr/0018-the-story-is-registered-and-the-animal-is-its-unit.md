# ADR 0018 — The story is registered, and the animal is its unit

**Status:** accepted as direction · 2026-09-02. Two studies run first; the book's second arc waits
on what they say.

## Context

The owner's assessment on 2026-09-02, after reading the whole record rather than the last phase:

> at one point we started looking too deeply into single details, instead of looking at a whole at
> patterns, even if they are made of details … we lost the story we were looking for, and we kept
> finishing at "this is like this" without explaining why.

And of the book: the style is right and the writing is *"a mess of single general points, without
a general story behind it."*

Both are correct and they have one cause. The pre-registered phase is this project's only unit of
work. It has one estimand, numbered predictions and stop conditions, and it is superb at what that
shape is for: killing a claim, auditing an instrument, refusing a licence. Since 2026-08-18 it has
done that nineteen times. Five of those registrations reached the ledger and four of the five are
limits. Phases 1k, 1l, 1m, 1n and 1o are five consecutive registrations on two Swedish bird
programmes, ending at a constant offset of +0.17 ± 0.10 °latitude per decade whose cause the notes
say is not identifiable. Meanwhile `flight-advance`, the largest timing signal in the lake at
−2.10 days per decade over 12,213 series, has never had a driver fitted to it.

The machine has no counterpart for synthesis. Every note ends with *what the successor has to fix*,
and the successor is that list, so the next question is always the previous phase's residual rather
than the whole's. Nothing living holds the whole: `HANDOFF.md` is a snapshot at seven findings,
`PLAN.md` stopped on 2026-07-30, the README's research table is a list. A "why" question needs a
mechanism hypothesis from outside the previous note, and there was no slot for one.

The owner's second observation names the unit: *"most migrations are animal specific"*, and the
work has mostly read a whole of animals — a network median, a survey median, a realm. Two published
results say the whole is the wrong level and one species is too noisy: Phase 1l put a median
species trend at 1.69 standard errors from zero, and Phase 1m showed a network median is a mixture
of species that do not share a direction. What resolves that is not in either note: **a species'
trend and a species' response are different quantities.** A trend is one slope on year per series.
A response is a slope on a driver pooled across every site the species occupies, and UKBMS holds
59 taxa across 3,144 sites. The unit that is unreadable for a trend can be well determined for a
response.

## The spine, as conjecture

Assembled from measured parts, offered here so it can be registered and killed rather than assumed.
It is the axis `transfer-fails` already broke along: the one leg that responded measured dates, the
two that did not measured places.

**When animals move follows temperature.** Radar autumn passage responds at −0.66 to −0.62 days
per °C across 78 stations, about half its thirty-year advance is thermal and essentially all of
that half is anthropogenic (`f` = 0.98, 15 models). Spring plankton bloom follows sea-surface
temperature at +9.7 days per °C over 38 years. Timing is also the only quantity with interannual
skill anywhere in this project, at regional scale. Butterfly flight dates have advanced 2.10 days
per decade and their thermal response has **not been fitted** — that is the gap.

**Where animals are does not follow warming.** Marine thermal tracking has a median index of +0.06
over 673 pairs; warming does not predict which of 18 seas moved (+0.04 ± 0.18 °lat per °C); the
marine null is not a mixture along any thermal axis; southern African occupancy did not change and
surface water did not explain the little that did; both place-measuring legs of the transfer test
sit within a few percent of no response.

**What organises where-shifts is the animal, not the place.** Grouped by species, the coherence of
marine latitude trends is 0.43 against 0.16 grouped by survey, over 297 taxa — an *unregistered*
diagnostic, with Phase 3k registered to test it. Family clears the coherence floor in two bird
networks of three where latitude, range extent, thermal position, warming rate and depth all
failed. Species share their movement tendency across the seas they live in; seas do not share it
across the species that live in them.

**Kill conditions, each cheap.** If the butterflies' flight date does not respond to pre-season
temperature, the first leg stands on radar alone. If Phase 3k's species coherence falls below 0.10
under a survey-clustered interval, the third leg dies. If its drift-controlled warming slope clears
zero, the second leg is wrong and Phase 3e was confounded.

## Decisions

1. **The two studies run before the book is rewritten.** Phase 3k as registered on 2026-09-01, and
   a new registration for the butterflies' thermal response, fitted per species and pooled, on the
   design `phase2a-timing.md` used for the radar. Writing the book around an untested conjecture
   would be the one thing this project has never done.

2. **The animal is the unit of every "why" question from here.** A response is fitted per species,
   or per group of species that share a strategy, before it is fitted per network or per realm. A
   network-level number is published as a summary of species-level responses, not in place of one.
   Where a species' response cannot be determined, the note says so per species rather than
   pooling past the problem — Phase 1l's 1.69 binds on trends and this decision is about responses,
   and the two are not to be confused in either direction.

3. **The synthesis is registered like a phase.** Once both studies have run, a method note states
   the spine as numbered claims, each with its evidence class, its `n`, and what would kill it, and
   the book's argument is written from that note. A synthesis that cannot be wrong is prose; this
   one has to be able to lose a leg in public the way every phase has.

4. **A successor is chosen against the whole, not the residual.** Every registration from here
   carries one line under *Why this note exists* saying which leg of the registered spine it bears
   on, or that it bears on none and why it is worth running anyway. The "what the successor has to
   fix" lists stay, as inventories rather than as the queue.

5. **The book's second arc is a story arc.** It follows the studies and the synthesis note, and it
   respects the decisions already made: chapters by the reader's question, a results-free first
   opening, prose authored in `reports/`. What changes is which questions — the spine's, not the
   ledger's `direction` field — and that the argument gets prose of its own: a synthesis page after
   the opening, an opener per chapter, a bridge per claim naming the claim that raised it, and a
   `matters` register that says what the result means for the animal rather than for the method.
   Recorded here as direction; the build-time ADR is that arc's to write.

## Consequences

`docs/TASKS.md` carries the two studies and the synthesis as numbered items, and the book arc as
the item that waits on them. Phase 3k's registration is unchanged by this; its amendments, if any,
are written in its own note before it runs, as every phase's are.

Decision 2 changes what a good result looks like. A network median that clears zero is no longer a
finding on its own; the finding is how the species inside it respond, and whether they agree. That
is the owner's instinct made into a rule, and it is also what Phase 1m's fired stop condition was
trying to say.

## What this does not do

- It does not weaken any convention. Pre-registration, stop conditions, one change at a time and
  recompute-on-build are untouched; the synthesis is *added* under them, not exempted from them.
- It does not promote the spine. Two of its three legs are measured nulls and one is a diagnostic.
  Until the synthesis note is written and graded it is a hypothesis about this project's own
  results, and the book is not to state it as more.
- It does not retract the methodological phases. The audits found real defects — a circularity that
  was small, intervals that were 3 to 4.5 times too tight, a leverage rule that was missing — and
  the ledger is truer for them. What changes is how the next question is chosen.

## Amendment, 2026-09-02, the same day, after Phase 3k ran

The spine's third leg lost the evidence it was written on, within hours. Its marine support was the
unregistered diagnostic that species coherence is 0.43 against 0.16 for surveys. Phase 3k's
registered version came in at 0.326 against 0.178 — 1.83 times, under the registered two — and then
an unregistered check found that a between-group share has a chance level near `(k − 1) / n`, so 171
species over 1,148 pairs *start* at 0.20 with their labels shuffled where 23 surveys start at 0.04.
Over chance the species carries +0.12 and the survey +0.14. The animal and the sea explain about the
same, and the 2.8 times was mostly the number of groups. Phase 1o's family coherences were measured
against the same fixed floor with 14 to 30 groups, and are exposed to the same correction; that is
now #78.

Two things stand and one changes. Decision 2 stands: it is about a species' *response* to a driver,
and every quantity in Phase 3k is a *trend*, so the decision has not yet been tested. The
methodological lesson stands and is the sharper one — the project's coherence instrument compared
groupings of very different sizes on one scale for a week, in three phases and two published
findings. What changes is that the spine's third leg is a hypothesis with no evidence for it in this
lake, and the synthesis note (#76) must say so or drop it. The first leg is still untested and the
second is still measured nulls; the book waits on both as before.
