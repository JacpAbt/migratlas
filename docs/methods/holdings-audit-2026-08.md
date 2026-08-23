# Holdings audit — what each source can support, what it cannot, and why

**Status, 2026-08-23.** Every row count, year count and span below was read out of the lake today
through `lake.reader.scan()` with an explicit `source_id`, not remembered and not copied from an
earlier note. Every schema claim was read off the frame's own columns. Where a source is absent from
the lake that is reported as absent. Nothing here fits a model or computes a new quantity about the
world: it classifies holdings, and the classification is the deliverable.

Asked for by the owner, and asked in a better form than the question it replaced. Not *which sources
can carry a trend* — the detectability assessment already answers that and publishes it — but **why
the others cannot, whether things individually uninformative are jointly informative, and where the
unused value actually is.** The audit covers all 35 registry entries, including the productive ones,
because restricting it to the refused half would have missed the answer.

---

## 1. A correction to the denominator, before anything else

The registry holds **35 entries: 20 evidence sources and 15 drivers or support tables.**

| | entries |
| --- | --- |
| evidence — measures animals | 20 |
| drivers and support — measures the world, or joins to a source | 15 |

The drivers are `narr`, `era5`, `era5_south`, `era5_land`, `oisst`, `seas5`, `cmip6_damip`,
`cmip6_scenariomip`, `isimip3a`, `jrc_gsw`, `nsidc_sea_ice_index`, `pku_gimms_ndvi`,
`noaa_climate_indices`, `cpr_bcodmo`, `cmems_bgc`, and `ukbms_sites` is a coordinate table that joins
to `ukbms_phenology`.

**So "seven of thirty-five sources can carry a trend" is wrong twice over**, and it was said in
conversation on the way to this audit. A driver was never meant to carry a trend — asking whether
ERA5 can support a range shift is a category error. The real ratio is **7 of 20**, and the interesting
question is what the other thirteen are for.

---

## 2. The holding, measured today

77.0 million evidence rows. `used by` names published findings only; map layers are noted separately
because a layer is not a claim.

| source | realm | kind | rows | years | span | ceiling | used by |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `darkecology_daily` | aerial | flux | 17,848,788 | 31 | 1995–2025 | detectable | 5 findings |
| `darkecology_profiles` | aerial | flux | **0** | — | — | *not assessed* | nothing |
| `ebird_status_trends` | aerial | abundance | 730,003 | 1 | 2023 | no-time-axis | nothing |
| `isimip3a` | aerial | **null** | — | — | — | *not assessed* | nothing |
| `fishglob` | marine | survey index | 2,831,609 | 62 | 1963–2024 | detectable | 2 findings |
| `megamove` | marine | abundance | 3,487,176 | 1 | 1985 | no-time-axis | map layer |
| `obis_speciesgrids` | marine | abundance | 17,192,885 | — | 1520–2025 | effort-not-measured | map layer |
| `bbs` | terrestrial | survey index | 7,548,397 | 59 | 1966–2025 | **detectable** | **nothing** |
| `sbs_point_counts` | terrestrial | survey index | 490,869 | 50 | 1975–2024 | **detectable** | **nothing** |
| `sbs_fixed_routes` | terrestrial | survey index | 468,933 | 30 | 1996–2025 | **detectable** | **nothing** |
| `ukbms_phenology` | terrestrial | survey index | 627,752 | 49 | 1973–2021 | *not assessed* | **nothing** |
| `sabap1` | terrestrial | survey index | 3,123,626 | 58 | 1901–1999 | detectable | 2 findings |
| `sabap2` | terrestrial | survey index | 16,618,692 | 46 | 1930–2026 | detectable | 2 findings |
| `movebank_yahatinda_elk` | terrestrial | track | 1,784,888 | 23 | 2001–2024 | effort-not-measured | 1 finding |
| `movebank_svalbard_reindeer` | terrestrial | track | 1,317,837 | 14 | 2009–2022 | effort-not-measured | 1 finding |
| `movebank_bylot_fox_gps` | terrestrial | track | 1,720,570 | 8 | 2018–2025 | effort-not-measured | map layer |
| `movebank_bylot_fox_argos` | terrestrial | track | 64,485 | 15 | 2007–2021 | effort-not-measured | map layer |
| `movebank_missouri_bison` | terrestrial | track | 720,077 | 11 | 2012–2026 | effort-not-measured | nothing |
| `movebank_mountain_caribou_bc` | terrestrial | track | 249,450 | 21 | 1988–2016 | withheld from maps | nothing |
| `movebank_hebblewhite_wolves` | terrestrial | track | 174,443 | 12 | 2000–2011 | withheld from maps | nothing |

**28.2 million rows — 37% of the holding — feed no published finding.** Of those, 10.6 million feed
no finding *and* no map layer *and* are not withheld by the sensitivity gate: `bbs`,
`sbs_point_counts`, `sbs_fixed_routes`, `ukbms_phenology`, `movebank_missouri_bison`,
`ebird_status_trends`, and two entries with nothing behind them at all.

`obis_speciesgrids`' year column is the union of per-record period bounds, not a per-year series, so
its 322 distinct values are not 322 years of sampling. Reported as a dash rather than as a number
that would flatter it.

---

## 3. The finding that reorders the question

**Four sources with measured effort, three of them certified by this project's own assessment as able
to carry a trend, have never been asked anything.**

`bbs`, `sbs_point_counts`, `sbs_fixed_routes` and `ukbms_phenology` all carry the same columns in the
lake — `count`, `effort`, `effort_unit`, `protocol`, `site_id`, `year` — which is the exact shape the
atlas and radar analyses needed and got their answers from. Together: **9.1 million rows across spans
of 30, 49, 50 and 59 years.**

**Corrected 2026-08-23, having been wrong when first written.** The sentence above originally said all
four carry a *measured* effort column. Three do: `bbs` is 0.00% null on `effort`, `sbs_point_counts`
0.51%, `sbs_fixed_routes` 0.11%. **`ukbms_phenology` is 100% null** — it has the column and none of
the values, set that way on purpose by `ingest/ukbms.py`, because a flight-date series has no catch to
denominate. The claim was measured for the three count networks and generalised to the fourth without
being checked, which is the failure this note's own status line was written to prevent. It changes
nothing about the fourth source being idle and worth asking, and it changes what it is idle *for*:
a timing series, not an abundance one.

`bbs`, `sbs_point_counts` and `sbs_fixed_routes` appear in `src/migratlas/reports/` in **exactly one
file**: `detectability.py`. They appear in `docs/methods/` only in notes *about coverage*. They exist
in this codebase to be listed as capable. `ukbms_phenology` is not even listed — see §6.

That reorders the owner's question. The hypothesis behind it was that data which cannot carry a trend
alone might carry one together. That hypothesis is sound and §4 says where it applies. But **the
largest unexploited asset here is not data that cannot answer a question. It is data that can, and has
not been asked.** The North American Breeding Bird Survey is one of the longest designed monitoring
programmes in existence, it is in this lake with its effort denominator intact, and this project has
computed nothing from it.

---

## 4. The taxonomy of refusals — six kinds, and they do not share a remedy

The coverage assessment gives eleven sources one of three labels. Underneath those three labels are
six structurally different failures, and collapsing them is what makes the holding look uniformly
dead. Each is stated with what would fix it and, more importantly, **what would be fabricated by
applying the wrong fix.**

### Class 1 — Undenominated effort

*`obis_speciesgrids`, and the five drawable track sources.*

No measured record of how hard anyone looked, or of how many collars were deployed where. The track
version is structural rather than anyone's oversight, and `detectability.py` states it exactly: a
radar station is fixed infrastructure and a trawl survey has a design, but a collar goes on an animal
that could be caught, in a place researchers could reach, in a year that was funded.

**Two remedies, and the first is already proven inside this repository.** Change the estimand to one
that needs no denominator: displacement between two fixed calendar windows is a property of the
animal, not of how hard anyone looked. `displacement-flat` is a published finding built on two sources
this table marks `effort-not-measured`, which is the demonstration that the label is
**estimand-specific** — it means *cannot carry a trend in where animals are*, and says nothing about
how they move. The site currently reads as though it meant the second.

The other remedy is to reconstruct effort from the data and **calibrate the reconstruction against a
source where effort is measured** — discard `bbs`'s effort column, rebuild it from records per
site-year, and ask whether the recovered trend matches the one computed with the true denominator.
Either the proxy is licensed for sources that lack effort, or it is closed with a publishable reason.

**What pooling alone would fabricate:** nothing about distribution becomes estimable by adding more
undenominated sources. Pooling buys power, not identification, and an unidentified quantity measured
more precisely is still unidentified.

### Class 2 — Short of a floor

*`movebank_svalbard_reindeer` (14 years against a floor of 15); the Bylot fox pair (17 years pooled,
falling to 13 once a cell-year minimum applies).*

**This is the class the owner's hypothesis is exactly right about, and the only one.** A series too
short to carry its own trend can borrow strength from siblings; `models/trends.py` already holds the
random-intercept and random-slope machinery, and `TASKS.md` #62 has it queued. The decisive test is
available without new data: handicap the aerial panel to fourteen-year series and ask whether a
hierarchical fit recovers the answer the full panel gives.

### Class 3 — Precision mismatch

*`movebank_bylot_fox_gps` (metres, 1.72M rows, 2018–2025) against `movebank_bylot_fox_argos`
(kilometres, 64k rows, 2007–2021).*

The same site, the same population, two instruments whose location error differs by three orders of
magnitude, and the switch falls in 2018 — inside any window a trend would be fitted over.

**What pooling would fabricate:** a trend in any movement metric, manufactured by the instrument
change rather than by the animals. This is not hypothetical: `phase1d` measured that changing the
collar moves a date by **46.8 days**. Remedy is to analyse separately, or to model the error
explicitly and register that decision before fitting.

### Class 4 — Invalid by construction

*`movebank_missouri_bison`.*

A fenced conservation herd. Its movement is bounded by a fence rather than by habitat or weather, so
it cannot answer a question about habitat- or weather-driven movement at any sample size.

**There is no remedy and that is the point.** It shares the label `effort-not-measured` with class 2,
which makes a validity failure look like a power problem — the single most misleading thing in the
current assessment. It should be reclassified. It remains legitimate as a control or an illustration.

### Class 5 — No time axis, permanently

*`megamove` (3.5M rows, every one stamped 1985), `ebird_status_trends` (730k rows, 2023 only).*

Neither can be a response to a question about change, now or later, because neither has years.
`ebird_status_trends` additionally cannot be redistributed, so it is analysis-only by licence.

Both are legitimate as **spatial priors or masks** — where to look, which cells matter, what to
weight — and `megamove` already earns its place as a map layer. Recording this so they stop reading
as unfinished work.

### Class 6 — Aggregated away before it reached the lake

*`obis_speciesgrids`.*

17.2 million rows, the second largest evidence holding, and the ingested product carries
`period_start` and `period_end` per taxon-cell rather than per-year records. Even a perfect effort
proxy needs per-year observations to correct, so the limitation is in the product chosen, not in OBIS.

**Remedy is a re-ingest decision, not a modelling one — and it should be made after class 1's
calibration, not before.** If effort cannot be reconstructed on a source where the answer is known,
there is no point paying for per-year OBIS records.

---

## 5. Sources that are used, and used narrowly

The audit was extended to the productive sources because the same question applies to them.

**The atlases hold far more than the epochs analysed.** `sabap1` spans 1901–1999 and `sabap2`
1930–2026 in the lake — 19.7 million rows — while `atlas-no-net-change` compares 1987–1991 against
2008–2012, two five-year windows chosen for protocol comparability. That choice is right for *that*
claim and it leaves most of a century unexamined. Whether anything outside the epochs is usable is a
question nobody has asked; the honest prior is that early records lack the protocol the finding
depends on, which is exactly what an effort proxy would be for.

**`fishglob` carries `site_depth_m`, and the marine null is about latitude.** Phase 3g used depth for
oxygen; `marine-null` did not. A depth-shift estimand on the same 2.8 million rows is a different
question about the same animals — and one the literature treats as the other half of marine
redistribution.

**`darkecology_daily` is doing most of the work.** Five of nine findings rest on one source. That is
not a criticism of the source; it is the concentration risk that the whole rest of this document is
about.

---

## 6. Three sources invisible to the coverage assessment

The detectability figure lists fifteen sources. Twenty are evidence sources. The missing five are the
two withheld by the sensitivity gate — correctly, and they appear in `withheld` instead — and three
that are simply absent:

- **`darkecology_profiles`: zero rows in the lake.** Registered and admitted, never ingested. The
  refusal to build a nowcast on 220 GiB of vertical profiles is recorded and sound, but the registry
  currently advertises a source with nothing behind it.
- **`isimip3a`: an `evidence_type` key present and set to null**, with `realm: aerial`. It is a
  driver filed as evidence, or an evidence source with no type; either way it is a registry defect
  that makes every count in this document require a manual correction.
- **`ukbms_phenology`: 627,752 rows over 49 years, with a measured effort column, not assessed at
  all.** Phase 1j ingested it on 2026-08-20 and a stop condition fired, so no leg was computed. That
  was correct. But an ingested source with an effort denominator and a 49-year span is not
  "unassessable", and the assessment does not mention it.

---

## 7. What this audit cannot establish

- **Whether any of the remedies works.** Every one is a hypothesis with a test named, and the tests
  have not been run. Nothing here licenses a claim about animals.
- **Whether the idle sources have anything in them.** That `bbs` *can* carry a trend is the
  detectability assessment's judgement, measured on span and effort. Whether it carries an
  *interesting* one is unknown, and a null from it would be a real result rather than a wasted pass.
- **Anything about the drivers' adequacy.** Fifteen entries were classified here as "not evidence"
  and then set aside. Whether the driver side is sufficient for the *why* question is the covariate
  survey's subject, not this one's.
- **Whether the row counts mean what they suggest.** A row is a row; `sabap2`'s 16.6 million and
  `bbs`'s 7.5 million are not comparable units of information, and no attempt is made here to put
  them on one scale.
- **The sensitivity classifications.** Two sources are withheld from maps and this audit takes that as
  given. It notes only what the gate itself already states: a rate of change over a population
  locates no animal, so a withheld source may still contribute to a finding.
