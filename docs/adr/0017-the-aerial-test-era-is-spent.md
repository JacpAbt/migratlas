# ADR 0017 — The aerial test era is spent, and one slice is reserved

**Status:** accepted · 2026-08-31

## Context

Five phases have now scored the same 143-station CONUS radar panel under the same 70/30 era split:

| phase | what it scored | what it reported |
| --- | --- | --- |
| 3a | per-station ridge, seven covariates | autumn 20/143, median `+0.0055` |
| 3d | the full two-stage pipeline, eight June SEAS5 issues | 6/136, median `−0.014`; licence refused |
| 3f | five arms of estimator and basis | calibration fired; table printed, unread |
| 3h | per-station against eleven regions | arm B median `+0.0649`, 3 of 11 regions |
| 3i | station-and-neighbours at `k` = 3, 5, 9 | registered 2026-08-23, not yet run |

Every one of those notes says the test era is touched once, and every one is telling the truth about
itself. None of them is telling the truth about the panel.

Phase 3h is explicit about what that costs: *"Phase 3f's complete ladder table — 18 rows, both
seasons, five arms, every median and count — is in `phase3f-response.md` and I have read it. Its stop
condition fired, so none of it was interpreted, but 'not interpreted' is not 'not seen'."* It then
argues, correctly, that what it had seen constrained its *design* rather than its answer, because no
figure it had seen was about a regional response. Phase 3i inherits the same argument one step
weaker, because 3h's regional numbers *are* about a smoothed response and 3i's `k = 5` sits between
3h's two scales.

`forecast-a.md` states the underlying fact in passing and nowhere makes it a rule: it describes
itself as runnable *"on a response whose test era Phase 3f has spent."*

So: per-phase blindness no longer implies panel-level blindness, and the project has been treating
the two as the same thing because each note only had to answer for itself.

**Two things are worth separating, because only one of them is a problem.**

Phases 3a, 3d, 3f, 3h and 3i differ in estimator, in target and in driver set. They are not five
attempts at one number, and none of them selected a specification by trying it on the test era and
keeping what scored. The 70/30 split was fixed in 3a and never moved; the covariate list was fixed
in 3a and never grew; every phase that changed something declared the change in advance and graded a
prediction about it.

What has nonetheless accumulated is **exposure**: five looks at the same held-out decade, by an
author who has read the previous four. That is not fraud and it is not nothing, and a project whose
argument is that held-out means held-out cannot leave it unstated.

## Decision

**1. Every aerial skill claim states its position in the sequence.** A phase scoring this panel says
which look it is and which earlier tables its author had seen. Phase 3h already does this in its §1
and it becomes the pattern rather than that phase's conscientiousness.

**2. The last three years are reserved and are not to be scored.** 2023, 2024 and 2025 are removed
from every future aerial skill phase's era split and held for **one** confirmatory run of whichever
specification the sequence finally settles on. Nothing may touch them before then — not a
sensitivity, not a diagnostic, not a smoke test.

Three years is small, and it is what is left. The record runs to 2025 and the split's test era
already begins around 2017, so reserving more would leave the training era too short to fit the
specification being confirmed. A small clean slice that has genuinely never been scored is worth
more than a large one that has.

**3. The reservation is stated in the phase that spends it.** When the confirmatory run happens, its
registration says so, and after it the slice is spent and this ADR is superseded rather than quietly
reused.

**4. `skill-sparse` carries the sequence in its caveat.** It is the ledger entry the aerial skill
work reports through, and a reader meeting "absent at most stations" should be able to see that five
phases have now asked and how.

## Consequences

**Phase 3i, registered and not yet run, is affected.** It should clip its panel to 2022 and record
the clip as an amendment before it runs. Its calibration rung reproduces Phase 3h's arm A medians to
three significant figures, and those medians were computed on the unclipped panel — so either the
calibration target moves with the clip and is re-derived once, in advance, or the phase runs
unclipped and is declared the last unreserved look. That is a decision for its own amendment and not
for this ADR; what this ADR forbids is running it unclipped *without* saying which of the two
happened.

**The reserved slice cannot rescue a specification.** If the confirmatory run disagrees with the
sequence that produced the specification, the honest output is the disagreement, and the temptation
to read three years as noise is exactly what a reservation exists to resist.

**This does not retract anything.** Phase 3a's 20 of 143, Phase 3d's refusal and Phase 3h's
`+0.0649` all stand as measured. What changes is what a *sixth* look is worth and how it must be
described.

## What this does not do

- It does not address the marine or terrestrial halves. Phase 3a's marine arm published as coverage
  and the herds never cleared a floor, so neither has a spent test era to protect.
- It does not make the sequence into a multiple-comparison correction. Nobody has counted how many
  effective tests five phases over one panel amount to, and this ADR does not pretend to have.
- It does not bound the author's memory, which is the real exposure and is not boundable. Stating it
  is the whole of what can be done.
