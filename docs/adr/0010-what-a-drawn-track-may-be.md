# ADR 0010 — What a drawn track may be

**Status:** accepted · 2026-08-07

## Context

ADR 0009 made tracks the movement arc's first piece (`TASKS.md` #38) and named three questions for
this ADR: simplification tolerance, temporal encoding against the existing week index, and what
redaction does to a drawn line. Per the standing rule — every structural guess here has been wrong
and every measurement right — the questions were put to the policy and the lake before any design
was chosen. Both answers overturn the premise.

### What the policy says, read rather than remembered

`_INDIVIDUAL_POLICY` drops `individual_id` at **every** sensitivity, including `not_sensitive` —
"the safe path has to be the default path." No registered track source is `not_sensitive`; the two
`high` ones (wolves, mountain caribou) are withheld outright and already rendered as site content.
Without identifiers there is nothing to connect fixes into, so under the standing policy **a drawn
line does not exist as a product**. The one designed way to finer publication is
`redact.OwnerPermission` — reference, grantor, contact, date — which is built, tested and has never
been supplied for any source. That is correspondence, not engineering.

The simplification-tolerance question therefore dissolves: there is no polyline to simplify. It is
recorded here as answered by the policy before geometry could ask it.

### What the lake says, measured 2026-08-07

The remaining path is a *derived* product genuinely summarised over animals — the `megamove`
precedent — cleared at aggregate granularity: `low → as published`, `moderate → 0.5°`. Whether
such a surface can show movement depends on whether the animals move farther than a cell. Measured
per publishable source: seasonal throw is the greatest distance between any two weekly centroids
pooled across years; the k-floor keeps a cell-week only when ≥ 3 distinct animals occupy it.

| source | sensitivity | animals | seasonal throw | median animal displacement | at policy-honest grid |
| --- | --- | --- | --- | --- | --- |
| `yahatinda_elk` | moderate | 206 | **7.2 km** | 3.9 km | 5 cells at 0.5°, throw ≈ ⅛ cell |
| `svalbard_reindeer` | moderate | 116 | **4.8 km** | 3.8 km | 8 cells at 0.5°, throw ≈ 1/10 cell |
| `missouri_bison` | low | 45 | 60.8 km* | **0.6 km** | *the throw is the 2022 collar-transport artefact plus year-pooling; the animals are resident |
| `bylot_fox_gps` | low | 65 | 32.5 km | 2.5 km | 27 cells at 0.1°, but only 45 weeks covered and 7 phase1h animal-years |
| `bylot_fox_argos` | low | 170 | **76.2 km** | 1.5 km | **32 cells at 0.25°, 547 cell-weeks, 89.3% of fixes survive k ≥ 3** |

The honest reading: **the lake's terrestrial tracks are, with one exception, the wrong animals for
a movement layer.** These collar studies follow largely resident populations — which is exactly why
`phase1d` found no timing trend and `phase1h` found displacement of a few kilometres. The exception
is the Bylot Arctic foxes on Argos, whose winter weeks sit tens of kilometres from their summer
dens — the sea-ice excursions — and whose seasonal geography survives both the k-floor and a
0.25° grid.

## Decision

1. **No lines.** A per-individual path publishes only behind a recorded `OwnerPermission`, per
   source, through the `ETHICS.md` procedure. The Bylot studies (CC0, data owners who published
   full precision themselves) are the natural first ask, and asking is a task for a person, not a
   build. Until then the word "track" on this site means a derived surface.

2. **The product is a weekly presence surface, pooled across years.** One value per cell per week
   of year, `w0..w51`, exactly the encoding the radar layer already animates — one feature per
   cell centre carrying 52 properties, repainted by the existing clock, no new animation
   machinery on either end. Pooling across years matches the clock's semantics (time of year, not
   calendar time), matches the radar layer's precedent, and is itself additional de-identification.

3. **A k-anonymity floor makes "aggregate" mean something.** A cell-week publishes only when at
   least **3 distinct animals** occupy it. A cell-week holding one animal is an individual location
   wearing an aggregate hat, and the floor is what entitles the product to the aggregate policy
   rather than the individual one. The floor is enforced in the builder, which — like every tile
   builder — takes a `PublicationClearance` it cannot mint itself.

4. **A visibility bar, able to fail.** A source ships only if its seasonal throw exceeds **two
   cells at its cleared resolution** — below that the layer is a static blob captioned as
   movement, which is an overclaim drawn instead of written. Measured today: `bylot_fox_argos`
   clears it (76.2 km against 0.25° cells); elk, reindeer and bison do not, at any resolution
   their policy allows; `bylot_fox_gps` adds nothing the Argos record lacks and misses seven
   weeks of the year. **One source ships.**

5. **The arc reorders around that fact.** One fox surface does not make "the globe learn to move";
   the radar flow (#39) — measured direction over a continent — carries the arc's opening instead,
   and the weekly-surface machinery this ADR specifies is built once and shared: the fox surface,
   the green-up and sea-ice driver layers (#40), and any future migratory track source all use it.

6. **The durable fix is admission, not engineering.** The lake lacks a genuinely migratory tracked
   population because none was ever registered — the sources were chosen for the ledger, where
   they were the right choice. A candidate (an open, low-sensitivity study of a long-distance
   migrant with enough animals to clear the k-floor) enters through `DATASETS.md` as a map-layer
   role, the role that document already blesses for `megamove`: coverage that can never carry a
   trend, "not a defect as long as nobody asks them to."

## Consequences

The caption work is already constrained: ADR 0009 §2 requires "individual journeys, effort-shaped;
supports no trend" phrasing, and for a pooled surface the honest sentence is about the *herd's
year*, not any animal's journey. The fox layer's caption must also carry the k-floor and the
pooling window, the same way the marine grids carry their effort caveat.

Elk and reindeer become sayable content rather than layers: the site can state that it holds three
million fixes whose safe resolution is coarser than the herd's whole seasonal journey — the same
honest register as the wolves' refusal. Not scheduled here; recorded so the option is not lost.

What this costs: the movement arc's first drawn artifact is a driver-and-radar story with one
Arctic fox surface, not a sky full of journeys. What it buys: nothing on the globe claims a path
nobody may publish, the k-floor turns "aggregate" from a vibe into a rule a test can check, and
the visibility bar means no layer ships that a caption would have to apologise for.

Payload, measured: 547 cell-weeks for the fox surface — a few kilobytes in the series encoding,
noise against the 150 MB heap ceiling and the current 221 KiB of layers.
