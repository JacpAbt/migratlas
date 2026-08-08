# ADR 0011 — The gate aligns with the standard it cites

**Status:** accepted · 2026-08-07

## Context

The owner asked whether the gate is too strict, and whether its strictness is a standard or a
house invention. The README has always claimed the former — "the gate implements a published
standard rather than a house policy" — so the standard was read rather than remembered: GBIF's
*Current Best Practices for Generalizing Sensitive Species Occurrence Data*, the document the
README cites.

What it actually prescribes, per category: **Category 1 (extreme)** — no records at all, or
presence in a large region only; **Category 2 (high)** — 0.1° (~10 km); **Category 3 (medium)**
— 0.01° (~1 km); **Category 4 (low)** — 0.001° (~100 m); **not sensitive** — "the data should be
publicly released as-is." It strongly opposes randomization ("creates deliberately 'false'
data"), places classification with the data custodian, and is silent on temporal delay and on
dropping identifiers — with one pointed exception: "information cannot be considered sensitive if
it is readily available through other sources."

Measured against that, the individual-granularity table was two categories stricter than the
standard across the board. A *not-sensitive* collar animal got Category 2 treatment (0.1°);
`moderate` got 1.0°, coarser than the standard's *extreme-adjacent* Category 2; and identifiers
dropped at every level, which the standard never asks for. ADR 0010 measured the cost: the elk
herd's whole 7.2 km seasonal journey vanished inside cells the policy chose, and no source could
draw a line at all. Meanwhile every one of these studies is published at full precision by its
own custodians — the people the standard says decide.

The strictness was a deliberate founding choice ("the safe path has to be the default path"),
not an error. This ADR records the owner's decision of 2026-08-07 to keep the house additions
**only where they protect something**, and to take the standard's numbers everywhere else.

## Decision

### 1. Three cells of the individual table move to the standard

| Sensitivity | GBIF category | was | becomes |
| --- | --- | --- | --- |
| `not_sensitive` | not sensitive | 0.1°, 7-day delay, no ids | **as published, ids kept** |
| `low` | Category 4 | 0.25°, 30-day delay, no ids | **0.001° (~100 m), 30-day delay, ids kept** |
| `moderate` | Category 3 | 1.0°, 90-day delay, no ids | **0.01° (~1 km), 90-day delay, no ids** |
| `high` | Category 1–2 boundary | withheld | **withheld — unchanged** |
| `embargoed` | Category 1 | withheld | **withheld — unchanged** |

### 2. What is kept, and why each is needed

- **`high` individual data stays withheld.** `ETHICS.md` defines `high` as active poaching or
  persecution pressure, aggregate only — a Category 1-style call the standard itself allows.
  This is the cell that protects the wolves and the mountain caribou, and it does not move. The
  standard's Category 2 would offer them 0.1°; this project's judgement is that a persecuted
  animal's whereabouts have no safe resolution, and that judgement is recorded as deliberately
  stricter than the standard.
- **Delays stay where sensitivity is real** (30/90 days at `low`/`moderate`). GBIF's scope is
  occurrence records and says nothing about live telemetry; the delay is the telemetry
  community's own norm against real-time interception, and it is kept as a named house addition.
  At `not_sensitive` the standard's "as-is" governs and the delay goes.
- **Identifiers stay dropped at `moderate`.** Reconstructing one hunted animal's habitual sites
  from an identified 1 km track is a real capability; the standard does not consider it, and the
  house rule closes it. At `low` and `not_sensitive` the ids stay, which is what makes a drawn
  line exist.
- **The aggregate table does not change.** With individual-`moderate` at 0.01°, the aggregate
  path no longer binds anything ADR 0010 wants to build, and its remaining strictness costs
  nothing on any current or planned product.
- **Generalization over jitter, custodian-decided classification, `dwc:dataGeneralizations` on
  every layer** — already the standard's position; unchanged.

### 3. What was considered and not taken

The standard's already-public clause — data "readily available through other sources" cannot be
considered sensitive — would justify publishing the CC0 sources as-is at any sensitivity. It is
not implemented as code, deliberately: a rule that says "public elsewhere, so publish here"
would let an upstream custodian's mistake propagate through this gate unexamined. The
`OwnerPermission` path (TASKS #50) remains the mechanism for finer-than-policy publication, now
needed only for `moderate`-and-above sources — in practice, an identified elk line and nothing
else currently registered.

## Consequences

Measured against ADR 0010's own numbers, the alignment redraws its verdicts:

- **Lines exist.** `low` sources keep identifiers at 0.001°: the Bylot foxes' sea-ice excursions
  and the bison record may be drawn as paths, 100 m-generalized and 30 days delayed. The ADR 0010
  product rules stand on top — the k ≥ 3 floor for surfaces, the visibility bar, and per-source
  cell choices coarser than policy where a finer one would pinpoint dens.
- **The elk and reindeer surfaces flip from invisible to visible**: 7.2 and 4.8 km of seasonal
  throw against 0.01° cells is six and four cells of movement. Both re-enter #38's scope,
  id-less as `moderate` requires.
- **The wolves and caribou artifacts are byte-identical.** No registry entry changes, no
  published layer changes, and the refusal prose the site renders is untouched — which is also
  why this ADR could avoid touching `detectability.json` at all.
- `test_individual_data_is_never_published_at_source_resolution_by_default` asserted the old
  founding rule by name; it is rewritten to pin the new table, with the reversal recorded in its
  docstring rather than the old test quietly deleted.
- `ETHICS.md`'s tables and its "even when the taxon is not sensitive" rationale are updated in
  place — it is a procedure document, current like `tokens.css` — with a dated amendment noting
  this ADR. ADR 0010 gains a dated amendment; its text otherwise stands as the record of what
  was true under the old table.
