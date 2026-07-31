# Individual tracks, and what may be published about them

Research checkpoint, 2026-07-31. Written before any code, because the first `TRACK` source is the
first genuine exercise of the ethics gate and the policy should be argued in prose before it is
argued in a table of grid sizes.

The terrestrial realm in this lake is 100% birds — `sabap1`, `sabap2`, `bbs`. Fixing that means
either a non-bird terrestrial *survey* or a non-bird terrestrial *tracking* source, and those two
turn out to be very different propositions. The candidates were assessed against three questions:
can we get it, may we publish it, and does it answer a question about **movement**.

## 1. What the field already does with tracking data

Worth knowing before inventing a policy, because the norms are stricter than an outsider would guess.

**Cooke et al. 2017** (*Conservation Biology*, `cobi.12895`) is the reference on misuse. The
concrete practice built on it, at the Ocean Tracking Network, is an **embargo for the tag's battery
life plus two years**, after which access is registration-gated rather than open. That is not
"publish it coarsely" — it is "do not publish it, then publish it to named people".

The documented harms are real but narrower than the headlines suggest, and the distinction matters
for an honest risk assessment:

- **Attempted hacking of GPS collars on Bengal tigers in India.** Attempted, not achieved.
- **Photographers in Banff using collar signals** to locate tagged animals. Achieved, and not
  poaching.
- **Wolves.** An anti-wolf site published instructions for locating collared wolves by telemetry,
  and Idaho subsequently made telemetry-aided hunting specifically illegal. In one season, four of
  the eleven collared wolves on Yellowstone's Northern Range were shot — legally, in the hunt.

So: **the risk pathway for wolves is demonstrated and legislated against, and a data-driven kill is
not documented.** Both halves of that belong in the assessment. Claiming a proven causal chain would
overstate it; treating the pathway as hypothetical would ignore that a state legislature did not.

## 2. What GBIF's guide recommends

[Current Best Practices for Generalizing Sensitive Species Occurrence
Data](https://docs.gbif.org/sensitive-species-best-practices/master/en/) sets four categories:

| category | generalisation |
| --- | --- |
| 1 — extreme | no coordinates, or 1 degree |
| 2 — high | 0.1 degree (~10 km) |
| 3 — medium | 0.01 degree (~1 km) |
| 4 — low | 0.001 degree (~100 m) |

Reached through four questions, in order: is there a harmful human activity; how vulnerable is the
taxon to it; would releasing this data make the harm more likely; and only then, what category.

Two things it says that are easy to miss. **A list of sensitive taxa is not a list of threatened
taxa** — the test is whether disclosure enables harm, not whether the animal is rare. And **withholding
can itself cause harm**, through development that proceeds because nobody knew what was there. So the
guide argues against blanket restriction as firmly as against blanket release.

## 3. Our gate is already stricter than that, and it already decides most of this

`redact.py` has two policy tables, and the one for individual-granularity evidence is severe:

| sensitivity | grid | delay | individual id |
| --- | --- | --- | --- |
| not sensitive | 0.1° | 7 days | dropped |
| low | 0.25° | 30 days | dropped |
| moderate | 1.0° | 90 days | dropped |
| high | withheld | — | — |
| embargoed | withheld | — | — |

**Even a species we classify as not sensitive gets GBIF's category-2 treatment**, plus a delay, plus
de-identification. Which means the question "may we publish tracks" has already been answered, in
Phase 0, and the answer is no: we never publish a track. What could be published is a gridded,
de-identified, delayed *surface* — and for anything classified high, nothing at all.

That is a good position to be in. It means the per-taxon decision is not "how precisely do we draw a
wolf" but "does this species appear in a 1° cell three months late, or not at all". A 1° cell 90 days
stale is not an aid to anybody, which is the point of setting the floor where Phase 0 set it.

## 4. The Arctic Animal Movement Archive

269 studies, **62 million locations, 15,585 animals, 1987–present** as of November 2022; caribou,
moose, bears, wolves, eagles, geese, ducks, seals and whales. Described in *Science* (2020) and
assembled deliberately as an archive for reuse, which is what separates it from Movebank's per-study
long tail.

Access facts, verified rather than assumed:

- **The API needs an account.** A request for the CC0 study list returned **HTTP 401**. There is no
  anonymous path, not even to enumerate what is open.
- **Licence is per study**, from CC0, CC BY, CC BY-NC, or custom terms. Movebank's terms of use bind
  the user to each study's own licence; there is no blanket redistribution right for the collection.
- The collection is a mix of public and controlled-access studies, and the archive asks users to
  contact data owners about intended use. `sdavidson@ab.mpg.de` is named for negotiating sharing.

So the shape of the work is: get an account, enumerate the AAMA studies by licence, and **classify
sensitivity from the species that are actually in the accessible ones** — not from a list guessed in
advance. That ordering matters: a policy written before the species list is a policy written about
hypothetical animals.

## 5. The Portal Project, and why it does not substitute

Verified from the repository rather than from a summary:

- **CC0** — checked in `weecology/PortalData/LICENSE`, so redistribution is unrestricted.
- Rodents from **1977 to present**, still running. Live Zenodo archive
  (`10.5281/zenodo.1215988`) and a living data paper (`10.1101/332783`).
- **The best effort denominator in the lake**: 24 plots of 0.25 ha, each with 49 permanent trapping
  stations on a 7×7 grid at 6.25 m spacing, censused repeatedly for 49 years.

Two things disqualify it from the job it was proposed for.

**It is an experiment, not a survey.** Plots are assigned to rodent removals, kangaroo-rat
exclusions, ant removals and seed additions, and the assignments changed in 1985, 1987, 2005, 2009
and 2015. A trend computed across plots is a trend in the treatments. `Portal_plots.csv` gives
treatment by plot over time, so control-only analysis is tractable and honest — but it is a
manipulation experiment being read as a monitoring series, and it would have to say so loudly.

**And it is not a movement source.** The entire study area is about 20 hectares. There is no
movement in it to detect: what Portal measures is abundance and composition, superbly, at one point.
For an animal-movement atlas it is a taxon tick that answers no question the atlas asks. It would
occupy exactly one cell of the detectability map.

That is the finding that reorders the options. Portal was on the shortlist as the "publishable"
non-bird terrestrial source, and it is publishable — but the gap is *terrestrial non-bird
**movement***, and Portal has none.

## 6. Where this leaves it

AAMA is the source that answers the question. It is 38 years of mammal migration in the
fastest-warming region on Earth, which is both the strongest driver signal available and the most
charismatic content in the project. Its costs are calendar time, not work: an account, an
enumeration, and possibly correspondence with study owners.

Portal remains worth having later, as an abundance series and a teaching object, and it should be
recorded as what it is rather than as a movement source.

**Reptiles, unchanged from the earlier assessment.** Most terrestrial reptiles do not migrate; what
is studied is range shift from occurrence records, which lands straight back in the effort-bias trap
`phase1b-marine.md` documents for OBIS. The reptiles that do move long distances are sea turtles, and
MegaMove already holds them under the marine realm. They belong on the coverage page as an
**explained absence**, which is itself the honest teaching point about what a movement atlas can
cover.

## 7. The enumeration, 2026-07-31

Account acquired, so §4's ordering could finally be run: enumerate first, classify sensitivity from
the species that are actually reachable. **Metadata only — no location data was requested.**

### Two facts about the API that a later ingest must not forget

**`i_can_see_data=true` cannot be trusted.** The same authenticated call returned the *unfiltered*
8,688-study set on one attempt and the correct 2,031 on the next, minutes apart, with no change to the
request. A run that silently got the wrong one would have quadrupled the denominator under every
count below. **The filter has to be re-applied client-side**, and this note exists so the next person
does not discover it by publishing a wrong number.

**Line counting is not row counting.** The first reading of this endpoint reported "13,523 studies"
from `len(text.splitlines())`. Quoted fields contain newlines: the same response is 4,190 physical
lines for 2,031 studies. Row counts come from a real CSV reader, and `csv.reader` and polars agree
exactly on this feed with zero ragged rows.

### What survives the filters

| | studies |
| --- | --- |
| in Movebank | 8,688 |
| data visible to this account | 2,031 |
| has deployed locations | 1,873 |
| downloadable | 900 |
| open licence (CC family) | 825 |
| north of 55°N | **152** |
| …and ≥15 years *inside one study* | **5** |

That last row is the one that decides what this source can be. `MIN_YEARS` is 15 across this project,
and five studies clearing it is not an archive of change — it is an archive of snapshots.

But a study is not obviously the unit. The radar's trend is per *station*, so the analogue is per
cell, and many short studies in one place could clear the threshold where no single study does.
Computed as an **upper bound** from each study's single reported centroid — generous, because a
study's animals were not all at its centroid:

- **115** 1° cells touched by an open Arctic study
- **7** cells whose pooled study-years reach 15
- deepest cell: **33 distinct years, 1987–2019**

So the verdict is mostly grey. AAMA-region open data belongs in the same part of the detectability map
as MegaMove and OBIS — vast coverage, no trend available — with a handful of exceptions.

### The taxon gap *is* fillable, and two series are deep

88 taxa across the 152 open Arctic studies. Split by group, and this is the answer to the question
the whole note was written for:

| terrestrial mammal | studies | distinct years | ~individuals |
| --- | --- | --- | --- |
| **Rangifer tarandus** (caribou/reindeer) | 5 | **35** (1988–2022) | 1,286 |
| Vulpes lagopus (Arctic fox) | 8 | 19 (2007–2025) | 270 |
| Vulpes vulpes (red fox) | 5 | 16 (2009–2025) | 41 |
| Ovis dalli | 2 | 7 | 136 |
| Canis lupus | 2 | 5 | 58 |
| Alces alces | 2 | 6 | 60 |
| Nyctereutes procyonoides | 1 | 6 | 30 |
| Lepus arcticus | 1 | 2 | 25 |

**Caribou is the source.** 35 distinct years across 1,286 individuals, open licence, and the strongest
driver signal available anywhere in this lake. It is also, unambiguously, a terrestrial non-bird
mammal that migrates — which is exactly the gap.

One marine series is deeper still and was not being looked for: **Odobenus rosmarus** (walrus), one
study, **33 distinct years 1987–2019, ~921 individuals**. That is the 33-year cell above. Worth
recording because it is the single deepest track series in the open set.

Birds remain the bulk — 70 taxa, 121 study-taxon pairs, led by *Uria lomvia* at 14 studies. No fish in
the open Arctic subset at all.

### Canis lupus is present, so the gate's first real test is not hypothetical

§1 documented the wolf pathway: an anti-wolf site published telemetry-location instructions, Idaho
legislated against telemetry-aided hunting, and four of eleven collared wolves on Yellowstone's
Northern Range were shot in one season. Two open-licence Arctic wolf studies are in this set.

So `taxon_sensitivity` gets a **`high`** entry for *Canis lupus* with that rationale, and under the
individual-granularity policy `high` means **withheld — nothing published at any resolution**. Not a
coarse grid, not a delay. The gate refuses, and it refuses about a real species in a real source,
which is what it was built in Phase 0 to do.

### And one refusal nobody planned for

**`Homo sapiens` appears in the taxon list.** One open-licence study, 12 individuals, 2026. Movebank
hosts human tracking studies alongside animal ones, and an ingest that trusted the archive's taxon
field would land human location data in this lake.

`EMBARGOED` exists for exactly this. It needs to be a refusal in code with a test, not a line in a
document — a `Homo sapiens` entry that the ingest checks before it writes anything, so the refusal
cannot be forgotten by whoever adds the next study.

### A method note on my own shortcut

Grouping 88 species by a hand-written genus list put four birds in an UNCLASSIFIED bucket — *Chen
canagica*, *Plectrophenax nivalis*, *Zonotrichia atricapilla*, *Setophaga striata*. Harmless in a
screening pass, and a concrete argument that the ingest must resolve taxa through the GBIF spine
(`taxonomy.py`) rather than any list written by hand: a missed genus in a classifier that fed the
sensitivity lookup would be a species falling through to the source default, which is the one failure
mode the individual-granularity rule exists to prevent.
