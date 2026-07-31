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
