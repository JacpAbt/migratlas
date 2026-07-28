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

The gate applies these defaults. Individual-granularity data is gridded and de-identified **even when
the taxon is not sensitive**, because the safe path has to be the default path rather than the one
taken when someone remembers to ask.

| Sensitivity | Aggregate evidence | Individual evidence |
| --- | --- | --- |
| `not_sensitive` | as published | 0.1° grid, 7-day delay, no identifiers |
| `low` | as published | 0.25° grid, 30-day delay, no identifiers |
| `moderate` | 0.5° grid | 1° grid, 90-day delay, no identifiers |
| `high` | 1° grid, 30-day delay | **withheld** |
| `embargoed` | **withheld** | **withheld** |

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
