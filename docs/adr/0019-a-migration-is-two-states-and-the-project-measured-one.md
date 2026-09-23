# ADR 0019 — A migration is two states, and this project measured one

**Status:** accepted as direction · 2026-09-08. Three tests are registered from it, in the order
below. No claim is withdrawn by this ADR; one is renamed and two gain a limit they did not have.

## Context

The owner's assessment on 2026-09-08, after the three driver studies of 2026-09-03 returned a
temperature response, four species-level results and five nulls:

> we are treating migrations as a single thing, but migrations are made of movement and stationary
> time, and those two have different states and interact with the other, not as a single unit

This is correct, and unlike most framing errors it is not a mistake in any number this project
published. It is a mistake in what the numbers are numbers *of*.

A migratory year has at least three states. **Residence** — breeding, wintering, staging — is where
an animal stays and where the conditions that prepare it accumulate. **The transition** is the
departure or arrival decision. **Transit** is the route, the flight speed and the stopovers, and it
is itself residence and movement alternating. The states have different cues and they trade against
each other: an earlier departure with a longer stopover arrives on time, and a project measuring
arrival sees nothing.

Every timing quantity this project has published is a single observation of one instant, named as
if it were a property of the whole. The consequences are specific:

- **Radar passage date** is a transit observation whose cause is upstream in a residence phase.
  Passage at a station is departure plus travel plus stopover north of it. June–July temperature at
  the station is a residence covariate that stands in for the breeding grounds because summer
  temperature is spatially coherent, and it explains half. The unexplained half — −0.26 d/decade and
  a latitude-graded 2012 step that four explanations failed on — has never had a transit-side
  candidate, because every driver ever fitted to it was a residence-side driver.
- **Butterfly flight date** is not movement at all. Seventy-two of seventy-five units are residents
  and the response is an emergence date. Claim 1 currently carries a transit date, an emergence date
  and a plankton bloom under one heading, and Phase 2f's finding that its cues are real and predict
  nothing is exactly what one expects when three different quantities share a claim.
- **Marine centroids** are residence observations cut at a fixed survey date. For a seasonally
  moving fish, a fixed date cuts the annual cycle at a phase, so an apparent range shift can be a
  phenology shift — the fish arriving in the survey box earlier. Phase 3k measured the ships' share
  of the marine where-shift. The phase-cut share has never been separated from it.
- **Atlas occupancy** is residence, and is the only leg whose name already matches its state.

What survives unchanged: the radar's thermal response, re-read as *residence conditions predict the
transition*; every where-null, re-read as a residence null; and claim 3, which gets stronger,
because the balance between an animal's states is a species trait and predicts why species differ.

What must change: "when animals move" is not one quantity, and the chapter that carries it cannot
be written until the tests below say how many quantities it is.

## Decisions

**1. The state is named in every estimand from here.** A method note's estimand line says which
state the response belongs to — residence, transition, or transit — and which state its driver
belongs to. A fit that crosses states says so, because crossing states is a claim about a mechanism
and not a detail of a design.

**2. No claim is withdrawn on the strength of this ADR.** A framing error is not a measurement
error. Claims 1, 2 and 4 are re-read, and each gains its limit only when a registered test supplies
one. Two of the three tests below can supply a limit; one can only supply a positive.

**3. Three tests, in this order, and each is answerable from the lake.** A dataset audit ran before
this ADR was written, and the finding that fixed the order is that no fetch is required for any of
them:

| # | Test | Unit | What it needs | Status |
| --- | --- | --- | --- | --- |
| 1 | Is a marine where-shift a range shift or a phase cut? | species × survey family | eight regions surveyed in two or three seasons, 16–57 years each | in the lake |
| 2 | Is the radar's residual in the front's speed or in the departure? | station-year | 161 stations, 13–65°N, ground speed and direction on 17.8M of 17.8M rows | in the lake |
| 3 | Does an animal answer a warm year by staying less or moving faster? | animal-year | 5.9M GPS fixes, 5 species, median gaps 4 min to 7 h | in the lake |

Test 1 goes first because it is the only one that can find a published number to be partly an
artefact, and this project fixes its own instruments before it builds on them. Test 3 is the only
one that observes both states directly and it is the deepest build.

**4. The two states are separated by the instrument that saw them, never by assumption.** Test 1
separates them by surveying the same region in two seasons. Test 2 separates them by the ratio of
the migration front's speed through a latitude band to the flight speed measured inside it — a ratio
that is the fraction of time spent flying, and therefore the residence share of transit itself.
Test 3 separates them with a two-state model fitted per animal. Where an instrument cannot separate
them, the note says so and claims neither.

**5. What is *not* in the lake is written down rather than worked around.** Per-individual stopover
duration for a bird is the one observable these tests cannot reach, and the two records that hold it
both fail this project's access bar: Motus requires project credentials for raw detections and
EURING's data bank is by application. A second flyway's flight vectors *are* openly available
(BALTRAD_VPTS and UVA_VPTS, CC0, 151 radars, 2012–2023, on Zenodo) and are queued as a source, not
folded into a test that already has an instrument.

## Consequences

- Claim 1 is renamed rather than rewritten, and the rename waits on tests 1 and 2. Its three legs
  measure a transit date, an emergence date and a bloom date, and the book cannot call them one
  thing.
- Claim 2's marine leg gains a phase-cut limit if test 1 finds one, and is strengthened if test 1
  finds none. Both outcomes are publishable and the note grades them the same way.
- Claim 4's residual gets its first transit-side candidate in test 2. The 2012 step's latitude
  grading is a prediction of a transit explanation and a coincidence under a departure explanation,
  which is what makes it gradeable.
- The book's second arc (#77) is unblocked by tests 1 and 2 and not by test 3, so the chapter table
  in `synthesis-2026-09.md` is provisional until they run.

## What this does not do

- **It does not make this a tracking project.** Test 3's five species are mammals, which is where
  the lake's tracks are, and the two-state result is theirs and not a migration law.
- **It does not name a mechanism.** Separating states is a measurement, and every driver fitted
  across a state boundary remains a correlation.
- **It does not license a fetch.** The audit is in the record above; a source enters through the
  registry, before an analysis, or not at all.
- **It does not touch the redaction rules.** Test 3 publishes state durations and responses. It
  never publishes a position.
