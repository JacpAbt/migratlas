# ADR 0009 — The globe learns to move

**Status:** accepted · 2026-08-07

## Context

The founding sentence is "an interactive globe of animal movement, backed by a research pipeline."
An assessment on 2026-08-07 — the owner's judgement, checked against the frontend, the pipeline and
the documents — found the second half healthy and the first half hollowed out. The globe draws four
circle layers: two marine grids that are effort maps by their own captions, a 496-cell atlas change
grid, and a radar layer whose animation is a weekly climatology. The lake holds about six million
track fixes across seven Movebank sources and none of them produces a single piece of globe
geometry; `EvidenceType.TRACK` appears nowhere in `tiles/`. The Explore panel says it itself: the
clock "moves the night terminator rather than the data." Nothing on the globe moves.

Two decisions caused this, and each was right in isolation:

- **ADR 0007 made the globe "the index to the arguments, not the subject."** Right for the
  notebook, which is the best thing the site has — and never counterbalanced afterwards.
- **`DATASETS.md` admits sources by trend-worthiness** — fifteen years per unit, effort fixed by
  design — which selects *against* movement data. Tracks support no trend (`phase1d`), so they were
  rightly kept out of the findings, and then wrongly given no visual role either. The same document
  already blesses findings-free layers: `megamove` and `obis_speciesgrids` "can never contribute a
  trend … not a defect as long as nobody asks them to." The precedent existed and was never applied
  to the movement data.

`DATASETS.md` also names the two currencies — "a spectacular globe layer" and "research novelty …
different currencies." Since Phase 1 nearly everything was spent in the second. The correction is
content, not another rebuild.

## Decision

1. **The notebook stays.** Nothing here touches the claim cards, the margin, the sandbox or the
   plain register. The owner's words: the frontend is very nice; the problem is what it shows.

2. **Movement layers are held to the honesty bar, not the trend bar.** A drawn track is a journey,
   not evidence of change, and its caption must say so — "individual journeys, effort-shaped;
   supports no trend" — exactly the way the marine grids already disclose effort. The gate is
   unchanged: every new layer kind takes a `PublicationClearance`, per taxon where granularity is
   individual, and a redacted track is a design question (`TASKS.md` #38), not a smaller dot.

3. **The arc, in order of value.** Tracks drawn and animated (#38); the radar layer given its
   measured direction — the daily product carries reflectivity-weighted u and v, verified in
   ADR 0006 (#39); the environmental drivers put on the clock the animals already share, per
   `docs/ideas/satellite-drivers-on-the-globe.md`, whose stated precondition — Phase 2a exists —
   has been met (#40); claims, species and layers cross-linked so the marine per-species view is
   reachable from the claim it argues for (#41); and a third door on arrival once something
   actually moves (#42).

4. **The backend's next modelling arc is Phase 2b, not another trend audit.** Step-selection on
   the cleared terrestrial tracks (#44) answers the README's own unstarted question — what drives
   an individual animal's decisions — and its outputs, utilization surfaces and corridors, are
   globe-native. Forecast A (#13) stays queued and unchanged. The FluxRGNN nowcast stays refused
   for the reasons `literature-2026-07.md` §2 already gives.

5. **The research write-ups run alongside, not after** (#45–#48): the dual counterfactual, the
   temporal-detectability data product, a fourth leg for the transfer test, and a visual-ROBITT
   note. Each is mostly built or mostly writing; none blocks the arc and the arc blocks none of
   them.

## Consequences

Track rendering needs its own design pass before code: simplification tolerance, temporal encoding
against the existing week index, and what redaction does to a drawn line — a generalized grid cell
is honest about its coarseness, while a smoothed path is a specific claim about where an animal
went. That ADR is part of #38, not skipped by this one.

The performance budget absorbs new layers or the layers do not ship; the browser suite's heap
ceiling and the long-task ratio are the instruments, per ADR 0008.

The risk this ADR accepts: movement content is the most legible thing the site will show, and
legibility without a caveat is overclaim. The mitigation is the one already in force — captions are
authored in `reports/`, the schema refuses prose-free layers, and the plain register's rule ("may
drop precision, may never add reach") applies to a moving line as much as to a sentence.
