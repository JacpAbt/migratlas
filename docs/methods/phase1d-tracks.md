# Terrestrial mammal tracks: the first `TRACK` source, and what may be said about it

Pre-registration, 2026-08-01. Written before any bulk download and before any metric is computed.
`tracks-and-sensitivity.md` did the source assessment; this note commits to a set of studies, a
sensitivity classification for each species, an analysis unit, and the conditions under which the
result is not reported.

The order matters and is the same one Phase 1a used: predictions and stop conditions first, so a
result that fails them is a finding rather than a reason to change the method.

## 1. The seven studies

Resolved **by study id**, not by name. `tracks-and-sensitivity.md` §8 records why: matching
`"Ya Ha Tinda elk"` picked a `CUSTOM`-licensed duplicate over the CC0 study, and matching
`Canis lupus` returned stray dogs alongside wolves. A name is not an identifier.

| id | study | species | span | individuals | locations | licence |
| --- | --- | --- | --- | --- | --- | --- |
| 897981076 | Ya Ha Tinda elk, Banff, **female only** | *Cervus elaphus* | 2001–2024 | 207 | 1,795,326 | CC0 |
| 216040785 | Mountain caribou in British Columbia | *Rangifer tarandus* | 1988–2016 | 260 | 249,450 | CC BY |
| 8019591 | Missouri Bison Tracking Project | *Bison bison* | 2012–2026 | 54 | 724,967 | CC BY |
| 1241071371 | Arctic fox Bylot — GPS-UHF | *Vulpes lagopus* | | | 1,720,581 | CC0 |
| 942774711 | Arctic fox Bylot — Argos | *Vulpes lagopus* | 2007–2021 | 170 | 64,489 | CC0 |
| 2608802883 | Svalbard Reindeer — Nordenskiöld | *Rangifer tarandus* | 2009–2022 | 116 | 1,317,837 | CC BY-NC |
| 209824313 | Hebblewhite Alberta-BC Wolves | *Canis lupus* | 2000–2011 | 68 | 174,443 | CC BY |

About **6.05 million locations**, five species, seven populations. Every one has `i_can_see_data`,
`i_have_download_access`, and an open licence, all checked per study rather than assumed.

**Registered as seven sources, not one.** The registry's `Source` carries a single `licence`, and
these span CC0, CC BY and CC BY-NC. CC BY-NC forbids commercial reuse where CC0 forbids nothing, so
one entry would have to state the most restrictive terms for all of them and would misreport five.
`PROVENANCE.md` is generated from the registry, so a wrong licence there is a wrong licence published.

### What the API does, recorded because both cost a run to discover

**Events need a licence handshake.** The first `entity_type=event` request returns the study's licence
terms as HTML; the same request carrying `license-md5=<md5 of exactly those bytes>` returns the CSV.
That md5 *is* the acceptance, so the terms are stored beside the data rather than discarded — accepting
a licence is an act, and provenance should record which text was accepted.

**`max_events_per_individual` is ignored.** A request for two events per animal returned the whole
1.8M-row study, 127 MB. There is no cheap sample: a study is all-or-nothing, so the ingest caches per
study and never re-fetches.

## 2. Sensitivity, per species and per population

The classification the ethics gate has never had to make, made from the species that are actually
here. `TaxonSensitivity` is keyed per source, which matters: two of these are *Rangifer tarandus* and
they do not get the same answer.

Applying GBIF's four questions in order — is there a harmful activity, how vulnerable is this taxon to
it, would releasing this make the harm likelier, and only then which category.

| source | species | class | why |
| --- | --- | --- | --- |
| Hebblewhite wolves | *Canis lupus* | **high** | The one demonstrated pathway. An anti-wolf site published telemetry-location instructions; Idaho legislated specifically against telemetry-aided hunting; four of eleven collared wolves on Yellowstone's Northern Range were shot in a single season. Alberta runs wolf culls. |
| Mountain caribou BC | *Rangifer tarandus* | **high** | Southern mountain caribou are among the most endangered large mammals in North America, in herds of tens of animals, several extirpated within the study window. A small herd's locations are a small herd's whereabouts. |
| Svalbard reindeer | *Rangifer tarandus* | **moderate** | Same species, different answer. Svalbard's population is ~20,000, protected, hunted under a quota on Nordenskiöld Land, and there is no persecution pressure. Classifying by species alone would have been wrong in one direction or the other. |
| Ya Ha Tinda elk | *Cervus elaphus* | **moderate** | Abundant and managed, so not vulnerable in the endangerment sense — but this herd's partial migration takes it *out* of Banff into hunted ground, which is what the study is about. The disclosure and the harm are about the same boundary. |
| Missouri bison | *Bison bison* | **low** | Conservation herd on managed, fenced ground. No market, no persecution, no meaningful disturbance route. |
| Arctic fox Bylot ×2 | *Vulpes lagopus* | **low** | Trapped for fur across much of its range, so the activity exists — but Bylot Island is a national park with no resident trapping, and the population is not localised or targeted. |

**What that means under the existing policy**, which was set in Phase 0 and is not being relaxed:

| class | grid | delay | individual id | outcome |
| --- | --- | --- | --- | --- |
| low | 0.25° | 30 days | dropped | publishable, coarse |
| moderate | 1.0° | 90 days | dropped | publishable, very coarse |
| high | — | — | — | **withheld entirely** |

So **two of the seven publish nothing** — the wolves and the mountain caribou, which are also the
most compelling. That is the gate working rather than the gate misfiring, and it is the first time it
has refused anything, because `TRACK` was empty until now.

### A policy question this forces, answered deliberately

If mountain caribou locations are withheld, may a *trend coefficient* computed from them be published?

**Yes, and the distinction is the whole point.** The gate governs derived products that disclose
*where an animal is*. "This herd's spring departure advanced by N days per decade" is a statement
about a population over three decades and localises nothing — no coordinate, no date, no individual.
Withholding it would be the failure GBIF's guide warns about as firmly as it warns about over-release:
harm through absence, where nobody acts because nobody knew.

So: **`high` withholds the map, never the finding.** Recorded here because it is a decision, not an
implication, and because the opposite reading is defensible enough that it should be argued against
rather than ignored.

## 3. The analysis unit, and the two things wrong with it

**A 1° cell**, matching how the autumn-advance trend is computed per radar station, so the
detectability layer and the trend share one definition. Chosen over per-study (which would discard
most of the data) and per-species-region (which needs a region definition that does not exist).

Both known problems are stated now rather than discovered in the results.

**Pooling a cell mixes protocols.** Mountain caribou spans GPS *and* older radio transmitters, and
fix rates differ by an order of magnitude between them. A fix-rate change looks exactly like a
behaviour change if it is not modelled, which is the lesson of the 2012 step in `phase1c-homogeneity`
and of the gear-change break terms in `phase1b-marine`. So: **a break term per (cell × sensor type),
and no trend fitted across a protocol change without one.**

**Short studies must not vote.** `Dolphin_Union_Caribou_UAV` is three days long and holds 450,042
locations — more than the 29-year caribou study. It is excluded, and by a rule rather than by hand:
**a study contributes only if its own span is ≥ 2 years**, because a study shorter than the annual
cycle cannot inform an annual date. That rule would have caught it without anybody looking.

## 4. The metric

Per individual per year, the **day-of-year at which cumulative northward displacement reaches half of
that individual's annual latitudinal range**. A median-crossing date, chosen because it is the direct
analogue of the radar's `q50_doy` — the day half the passage has happened — so the two response
variables mean the same kind of thing.

Deliberately not net-squared-displacement model fitting (Bunnefeld et al. 2011). NSD classifies
migratory from resident and is the right tool for that question; here it would add a model-selection
step between the data and the date, and the project's convention is that the first pass on a new
evidence type uses the simplest defensible metric.

An individual-year enters only with ≥ 30 fixes spread over ≥ 6 months, so a collar that failed in
April cannot contribute a spring date.

## 5. Predictions, registered now

1. **Most cells will not clear 15 years.** `tracks-and-sensitivity.md` §7 put 7 of 115 cells over the
   line as an *upper bound* from study centroids; real fixes can only spread thinner. Concretely:
   **fewer than 15 cells** will have ≥15 individual-years. If it comes in higher, the centroid bound
   was badly wrong and that is worth knowing.
2. **The elk herd will produce a usable series and the wolves will not.** 207 individuals over 24
   years against 68 over 12 — this is a check that the pipeline reflects sample size rather than a
   discovery.
3. **Sensor type will matter in the caribou.** The break term for the GPS/radio transition will be
   non-zero beyond its interval. If it is zero, the two sensors are interchangeable for this metric
   and the break term can be dropped from later work — also a result.
4. **No pooled multi-species trend will be reported.** Five species across seven populations on three
   continents do not share a response, and pooling them would produce a number about nothing. Stated
   as a prediction so that finding a tidy pooled trend is treated as a bug.

### Stop conditions

- **If no cell reaches 15 individual-years, no trend is reported at all.** The output is then a
  detectability entry — terrestrial non-bird movement, coverage present, change not measurable — which
  is the same honest shape as the marine null and is content for the coverage claim.
- **If the never-ingested floor fires, the ingest stops rather than skipping the row.** A human row in
  a mammal study means the taxon field is not what it is assumed to be, and everything downstream of
  that assumption needs re-checking. Two of these studies' *siblings* in Movebank list *Homo sapiens*
  inside multi-taxon animal studies, so this is not theoretical.
- **If a study's licence text has changed since acceptance**, its md5 will not match the stored one
  and that study is refused until the new terms are read.

## 6. What this cannot establish

It is seven populations, chosen because they are open and long, which is not a sample of anything.
Two are in one national park; one is fenced; one is female-only. There is no claim here about
terrestrial mammals in general, and the coverage claim should say so in the same breath as it reports
that the terrestrial realm is no longer entirely birds.

And a track measures where a collared animal went, not where the population went. Collars go on
animals that can be caught, in places researchers can reach, in years that were funded.

---

## Results, 2026-08-01

6,047,093 locations across seven studies, every study's row count matching its own published
deployed-location figure exactly. `make report-phase1d` / `migratlas report phase1d-tracks`.

**1,517 eligible individual-years** from 690 individuals, after the ≥30-fix and ≥6-month thresholds.

### The coverage screen — prediction 1 HOLDS

| | |
| --- | --- |
| 1° cells touched | **51** |
| cells with ≥15 distinct years | **2** |

Prediction 1 said fewer than fifteen would clear it. Two did:

| cell | years | individual-years | sensors |
| --- | --- | --- | --- |
| 51°N, 116°W — Ya Ha Tinda / Banff | 21 (2002–2024) | 512 | 1 |
| 72°N, 80°W — Bylot Island | 17 (2007–2025) | 183 | 2 |

Three caribou cells and two Svalbard cells sit at **14 years**, one short. The upper bound from study
centroids in `tracks-and-sensitivity.md` §7 put 7 of 115 cells over the line; the real answer on real
fixes is 2 of 51. The bound was generous in the direction it was expected to be generous.

### The metric answered a different question than the note thought

**1,477 of 1,517 individual-years get a crossing date — 97%.** The pre-registration said residents
would yield none, and pointed at Svalbard's sedentary reindeer as the case. That was wrong: *any*
animal that moves at all crosses the middle of its own annual range, so the metric times movement
without detecting whether the movement was a migration. It remains a phenology metric and the direct
analogue of the radar's `q50_doy`; it is not a migration test, and deciding which animals migrate
needs net-squared-displacement fitting, which this does not do.

### The unit had to be corrected mid-run, and the reason is in the data

Cell (51, 116°W) holds **elk and wolves**. Fitted per bare cell — as pre-registered — their medians
pool, merging a predator's calendar with its prey's, and the run returned +2.14 d/decade for a series
that was two species deep. A radar station measures one aggregate signal; a 1° cell does not.

So the unit is **(cell × taxon)**. The cell still earns its place — Bylot's two fox studies pool into
one 17-year series where neither reaches 15 alone — so the fix adds the taxon rather than abandoning
the cell. That lands closer to `phase1b-marine`'s species-region unit than this note anticipated, and
it is recorded as a correction because the pre-registered choice was tested and found wrong.

### One series fits, and it is not distinguishable from zero

| cell × taxon | years | individual-years | trend |
| --- | --- | --- | --- |
| 51°N 116°W, *Cervus elaphus* | 20 | 495 | **+1.21 ± 21.51 d/decade** |

The interval is eighteen times the estimate. Nothing else reaches the floor: Bylot's foxes fall from
17 coverage years to 13 once a cell-year needs three animals, and every caribou and reindeer cell
falls with them.

**So there is no terrestrial mammal timing trend to report, and that is the pre-registered outcome
rather than a disappointment.** The output is a detectability entry — coverage present, change not
measurable — which is the same shape as the marine null and belongs on the coverage claim.

### Prediction 3 holds emphatically, and it is the more useful result

Where a cell holds two instruments, the instrument moves the date more than any credible trend could:

| cell × taxon | sensors | shift |
| --- | --- | --- |
| 54°N 123°W, *Rangifer tarandus* | GPS vs Radio Transmitter | **−46.8 days** |
| 73°N 80°W, *Vulpes lagopus* | Argos vs GPS | **+9.4 days** |

Forty-seven days against a trend of order one day per decade. The break term was pre-registered as
mandatory and it turns out to be the whole story: the longest terrestrial series in the lake, 29 years
of mountain caribou, cannot carry a timing trend because half of it was measured with a different
instrument. That is worth more to the coverage map than a fitted number would have been.

### Prediction 2 — HOLDS, and prediction 4 — HELD BY CONSTRUCTION

The elk herd produced the only usable series and the wolves did not, as predicted from sample size
alone. No pooled multi-species trend was computed at any point; the code groups by taxon and the
report says so.

### Incidental findings

- **The elk study ships 10,438 rows with no taxon name** (1,784,888 of 1,795,326 are labelled). They
  are dropped from the trend rather than pooled into an unlabelled series, and they would be refused
  at publication anyway: `taxon_scope` is EXACT and the gate refuses an EXACT claim with no key.
- **Movebank returns `sensor_type_id` as a bare number.** The caribou's two instruments arrive as 653
  and 673. Resolved to names at ingest from `entity_type=tag_type`, because "GPS vs Radio Transmitter
  differ by 46.8 days" is a warning where "653 vs 673" is a puzzle.
