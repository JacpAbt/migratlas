# Ethics and animal safety

Publishing animal locations can get animals killed. A Chinese cave gecko was extirpated at its type
locality after the description was published. Save the Elephants gives live positions to rangers but
delays public release by months. This document is the procedure that keeps this project from being
the reason something similar happens, and [`src/migratlas/redact.py`](../src/migratlas/redact.py) is
its enforcement.

It follows a published standard rather than a house invention:

- [GBIF, *Current Best Practices for Generalizing Sensitive Species Occurrence Data*](https://docs.gbif.org/sensitive-species-best-practices/master/en/) (Chapman 2020)
- [TDWG Sensitive Species Extension](https://www.tdwg.org/community/dwc/sensitive-species/)
- `dwc:dataGeneralizations` for stating publicly what was done

## The two rules that do the work

**Fail closed.** A taxon with no sensitivity classification is not publishable. Not "publishable at
low resolution", not "publishable pending review" — refused, by the gate, with an error. Unclassified
is not a synonym for safe, and the moment that equivalence is allowed the whole procedure is
decorative.

**Aggregation and delay, never jitter alone.** Random coordinate offsetting feels protective and
isn't. A camera-trap study showed naive 1 km obfuscation could be narrowed to roughly 13% of the
candidate area using public satellite imagery and simple heuristics. Snapping to a grid destroys
information; jitter hides it behind a puzzle that a motivated person solves.

### And one floor beneath both

**Humans never enter the lake.** *Homo sapiens* and the genus *Homo* are refused at ingest, by key and
by name, at `redact.admit_taxon_for_ingest` — and again at publication, ahead of even the licence
check, for rows that might predate the floor.

This is not a sensitivity classification, and it is deliberately not expressible as one. Sensitivity
lives per source in the registry, and the failure it closes is exactly that **nobody wrote an entry**:
an unclassified taxon falls through to the source's `default_sensitivity`, which was chosen while
thinking about animals.

It was found, not anticipated. Movebank hosts human tracking studies beside animal ones — an
open-licence study of twelve people sits in the same taxon list as the caribou — so an ingest that
trusted the archive's taxon field would have landed human location data here. Nothing about the design
prevented that; a floor does. See `docs/methods/tracks-and-sensitivity.md` §7.

A registry entry cannot lower it. `not_sensitive` with a valid licence is the most permissive thing a
source can say, the source-level gate accepts it, and the taxon floor still refuses.

## Sensitivity is not a property of a species

It is a property of **(taxon × realm × evidence type)**. A white shark occurrence record from a
public beach and a white shark satellite track are not the same disclosure. One flag per species
cannot express that, so the registry classifies the combination.

| Class | Meaning |
| --- | --- |
| `not_sensitive` | No known market, no targeted persecution, no disturbance concern. |
| `low` | Plausible but weak concern — common species, diffuse range. |
| `moderate` | Known disturbance risk, or localised populations that could be targeted. |
| `high` | Active poaching, collection or persecution pressure. Aggregate only. |
| `embargoed` | Not publishable at any resolution, by owner instruction or law. |

## The decision procedure

For each new source, and for each taxon within it, before ingest:

1. **Ask the operative question.** Not "is this species rare?" but: *would publishing this, at this
   resolution, at this moment, increase the risk to the animal from targeted exploitation or
   disturbance?* Rarity is a weak proxy; a commercial market or a persecution history is a strong one.
2. **Check the obvious registers.** IUCN Red List category, CITES appendices, and the relevant
   national sensitive-species lists. These seed the classification; they do not settle it.
3. **Check what the owner already did.** If the publisher generalised the data, we do not un-generalise
   it, and we record that they did so separately from anything we do.
4. **Default upward when uncertain.** If two classifications are arguable, take the more restrictive
   one and note why. The cost of being too careful is a coarser map.
5. **Record it** in `catalog/registry.yaml` with the reasoning. An unrecorded decision is not a
   decision.

## What publication then looks like

The gate applies these defaults. The individual-evidence grids are GBIF's own category
resolutions — not sensitive as published, `low` as Category 4, `moderate` as Category 3. Two
house additions sit on top of the standard, each kept because it closes a hole the standard's
occurrence-shaped scope never considers: a **delay** where sensitivity is real, because a live
tagged animal can be intercepted from a fresh position, and **identifier dropping at
`moderate`**, because one hunted animal's habitual sites can be read off an identified track.
`high` stays withheld outright — this document defines it as active persecution pressure, and a
persecuted animal's whereabouts have no safe resolution.

| Sensitivity | Aggregate evidence | Individual evidence |
| --- | --- | --- |
| `not_sensitive` | as published | as published |
| `low` | as published | 0.001° grid (~100 m), 30-day delay, identifiers kept |
| `moderate` | 0.5° grid | 0.01° grid (~1 km), 90-day delay, no identifiers |
| `high` | 1° grid, 30-day delay | **withheld** |
| `embargoed` | **withheld** | **withheld** |

*Amended 2026-08-07, per [ADR 0011](adr/0011-the-gate-aligns-with-its-standard.md).* The first
version of this table was two categories stricter than the standard for individual evidence —
0.1° even for a not-sensitive taxon, identifiers dropped at every level — a deliberate founding
choice ("the safe path has to be the default path") reviewed and narrowed once its cost was
measured: it forbade every drawn track and hid a 7 km seasonal migration inside a single cell,
while protecting data the custodians themselves publish at full precision. The strictness that
protects something stayed; the rest now follows the standard this document cites.

Aggregate evidence means `ABUNDANCE_SURFACE`, `FLUX` and `SURVEY_INDEX` — already summarised over
animals. Everything else, including `OCCURRENCE`, counts as individual: one observation pins one
animal to one place at one time, which is exactly what makes rare-species records sensitive.

Every published layer carries its `dwc:dataGeneralizations` statement, so a user can tell degraded
data from precise data and knows fuller data may exist from the owner.

## Owner permission

Finer publication than the default requires recorded permission, with a reference, who granted it,
a contact, and a date. A permission with no contact and no date is a recollection, and recollections
do not survive audit.

An embargo cannot be unlocked by a permission. If an owner changes their mind, the classification
changes — not an override on top of it.

## Publication ledger

Every taxon-and-source combination that has ever been published, with its classification and
generalisation. Empty until Phase 1 publishes anything.

| Source | Taxon | Realm | Evidence | Sensitivity | Generalisation | Permission | Date |
| --- | --- | --- | --- | --- | --- | --- | --- |
| _(none yet)_ | | | | | | | |

## If you are unsure

Do not publish. Open an issue, ask the data owner, or leave the layer out. There is no deadline here
that justifies guessing, and this is a hobby project — the asymmetry between "the map is coarser than
it could have been" and "we helped someone find an animal" is not close.
