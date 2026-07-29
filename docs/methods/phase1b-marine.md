# Phase 1b — marine change detection, and why it cannot be done with what is in the lake

**Status:** unblocked 2026-07-29 by FISHGLOB. The first half of this note records why the two
sources already in the lake cannot answer the question; the second half is the pre-registration
for the source that can, written before any result was computed.

Phase 1b was planned as "MegaMove one-degree space-use grids through `metrics/range.py`", as the
structural proof that the metric layer is realm-general. Two facts, both checked before writing
any analysis, make that impossible — and make a slightly different plan necessary rather than a
weaker version of the same one.

## Neither marine source has a usable time axis

**MegaMove has no time axis at all.** Every one of its 3,487,176 rows carries the same
`period_start`: 1985. It is a single pooled 1985–2018 space-use product, not a series. There is no
metric of change that can be computed from one interval, and no amount of care recovers one.

**OBIS speciesgrids has a year range, not annual counts.** Checked at the source rather than
inferred from our ingest — the parquet columns are `species, AphiaID, records, min_year, max_year,
source_obis, source_gbif, kingdom … cell`. There is exactly one row per (taxon, cell): 17,193,004
rows, `max` rows per taxon-cell = 1. The only temporal information is when that taxon was first
and last recorded in that cell, and **61% of cells are single-year** (`min_year == max_year`). Our
ingest already takes everything temporal the product contains.

So the lake holds two marine surfaces and no marine time series.

## The tempting metric is worse than nothing

OBIS's structure does permit one thing that looks like change detection: compare the latitudes of
cells whose *first* record is recent against cells first recorded long ago, per species. A poleward
shift would show as recent first-detections lying further from the equator.

That metric should not be built, because **its dominant confound points the same way as the
hypothesis.** Survey effort has expanded polewards over exactly this period — Arctic accessibility,
ice retreat opening ship tracks, new national programmes at high latitude — and any newly surveyed
cell gets a late first-detection regardless of whether the animal arrived recently or had been
there for centuries. A positive result would be indistinguishable from the history of marine
biology, and the effort proxy available here (`records`, itself an effort measure) cannot separate
them because it has no annual resolution either.

The `start-year` distribution says the same thing more bluntly: its 10th, 50th and 90th percentiles
are 1985, 2012 and 2022. Most cells were "first recorded" in the last decade and a half. That is a
statement about reporting, not about animals.

A caveat cannot rescue this. The honest options are a source that controls effort, or nothing.

## What would work, in order of preference

1. **Standardised repeated surveys — `SURVEY_INDEX`.** Chosen. See the pre-registration below.
2. **Raw OBIS or GBIF occurrence records, with event dates.** Annual counts per cell are
   recoverable, so effort correction becomes possible — target-group background, where a species'
   share of all records in a cell-year is modelled rather than its count. But effort correction is
   then the entire analysis rather than a step in it, and the full export is ~100 GB against the
   17 M rows of the gridded product. Worth doing only if a survey series cannot answer the
   question.
3. **Telemetry with per-deployment dates.** Movebank and OTN carry real timestamps, but that is
   Phase 2b, is permission-gated per study, and answers a different question — individual movement
   rather than population distribution.

## What MegaMove and OBIS are still for

Both earn their place, just not here. They are the structural proof that ingest, the ethics gate,
the taxonomy spine, the grid exporter and the web layer are realm-general: nothing in the core is
bird-shaped, and that was demonstrated by pushing a second realm through the same code. OBIS also
supplies 3,073 of the per-species surfaces behind the species search. Neither claim depends on a
time axis.

## Reproduce the two findings

```bash
make lake-check
```

```python
# MegaMove has one period; OBIS has one row per taxon-cell.
from migratlas.evidence import EvidenceType
from migratlas.lake.reader import scan

scan(EvidenceType.ABUNDANCE_SURFACE, source_id="megamove").select(
    "period_start"
).unique().collect()  # -> a single 1985 row

scan(EvidenceType.ABUNDANCE_SURFACE, source_id="obis_speciesgrids").group_by(
    "taxon_key", "cell_id"
).len().collect()["len"].max()  # -> 1
```

---

# Pre-registration — distribution shift from FISHGLOB bottom-trawl surveys

Written 2026-07-29, before computing any trend. The analysis choices below are fixed here so
they cannot be chosen after seeing which ones give a result, which is the same discipline Phase 1a
followed.

## Source

**FISHGLOB** (Maureaud et al. 2024, *Scientific Data*): 29 scientific bottom-trawl surveys
harmonised into one schema, 216,548 hauls, 2,170 fish taxa, 1963–2021, CC BY 4.0. Effort is fixed
by design — the same gear, stratified stations and season each year — which is the property OBIS
cannot offer at any amount of effort correction.

Ingested from the **per-survey** files rather than the compiled 88 MiB one. Two reasons, both
found by trying: the compiled file contains a Latin-1 vessel name inside a haul id
(`Rémy-Martin`, from a French survey) that makes both Python readers fail on the whole file, while
the per-survey files read cleanly; and per-survey isolation means one unreadable survey costs one
survey rather than all 29.

Every haul carries what the analysis needs and one thing better than expected:

| Field | Use |
| --- | --- |
| `num`, `wgt` | catch in numbers and mass |
| `area_swept` | effort, 0% null — so CPUE is computable per haul |
| `latitude`, `longitude`, `depth` | position of the observation |
| `timestamp`, `year`, `season`, `survey_unit` | when, and which series |
| `gear` | the instrument, so a gear change is testable rather than assumed away |
| `accepted_name`, `aphia_id` | taxon, crosswalked to GBIF as every other source is |
| **`sst`, `sbt`** | **sea-surface and bottom temperature at the same place and time** |

`sst` and `sbt` are not part of `SURVEY_INDEX` and are not ingested by it, but their presence
matters: Phase 2a needs a driver measured where and when the animal was observed, and this source
carries one already. Recorded here so it is not re-derived from reanalysis later by mistake.

## Response variables

Per **species × survey_unit × year**:

1. **Abundance-weighted mean latitude** — the distribution centroid, weighted by CPUE
   (`num / area_swept`) rather than raw catch, because a haul that towed twice as far is not
   evidence of twice as many fish.
2. **Abundance-weighted mean depth** — included because the literature finds deepening as often as
   poleward movement, and reporting only latitude would let a real depth response look like no
   response at all.

Reported per `survey_unit`, never pooled across them. `NEUS-Fall` and `EBS` are different oceans,
different gear and different species pools; a pooled centroid would be an artefact of which survey
contributed most hauls in a given year.

## The confound that matters, and the fix

Effort per haul is recorded, so catch-per-unit-effort handles *how hard* each haul fished. It does
not handle **where the survey went**. Stations are added and dropped across decades, and a survey
that extended north in 2005 will show a poleward centroid shift with no fish having moved. This is
the same failure mode as the OBIS first-detection metric, and it is fatal in the same way, so it
gets the same answer: restrict to a footprint that is consistently sampled.

**Footprint rule, fixed in advance:** grid hauls to one degree, and keep only cells sampled in at
least **80% of the years** in the survey's window. The share of hauls and cells dropped is reported
alongside every estimate. A survey left with fewer than 10 consistent cells is not analysed.

## Falsification, fixed in advance

1. **Gear break.** `gear` changes within several series. Fit the trend with and without a level
   shift at each survey's gear change, exactly as the dual-polarisation break is handled in Phase
   1a. A trend that flips sign across that specification is not reported as a trend.
2. **Permutation null.** Shuffle years within species × survey_unit and refit, 200 times. The
   observed pooled trend must lie outside the null interval.
3. **Footprint sensitivity.** Repeat at 60% and 95% consistency thresholds. A result that exists
   only at one threshold is a result about the threshold.
4. **Depth as a discriminant.** A spurious footprint effect should move latitude and depth
   together in whatever direction the new stations lie. A biological response need not.

## What this can and cannot support

It can support: distribution shift, per survey and per species, with effort controlled by design
and a stated consistent footprint.

It cannot support: a global marine claim. 29 surveys is continental-shelf coverage of the North
Atlantic, North Pacific and a few other shelves — fish, on the bottom, where trawls can go. No
open ocean, no pelagic megafauna, no southern hemisphere to speak of. MegaMove and OBIS remain the
sources for global extent, and their role is to say where the surveys are silent rather than to
supply a trend.

## Result — no global shift, strong regional disagreement

Run 2026-07-29 on 2,831,609 survey rows: 220,002 hauls, 29 survey units, 1,676 taxa. Every choice
above was fixed before this table existed.

**Pooled: median −0.011 ± 0.019 °/decade across 2,240 species-survey pairs, 48% moving poleward,
permutation null [−0.009, +0.009].** The median sits at the very edge of the null and its interval
straddles zero, and a 48/52 split of directions is a coin flip. **Under this specification there is
no global poleward shift.**

The footprint sensitivity check is the reassuring part: −0.010, −0.011 and −0.011 °/decade at 60%,
80% and 95% consistency thresholds. The null is not an artefact of where the threshold was put.

What is not null is the disagreement *between* surveys, which reaches opposite signs:

| Survey unit | °lat/decade | m depth/decade | consistent cells | rows kept | years |
| --- | --- | --- | --- | --- | --- |
| IE-IGFS | −0.217 | +0.48 | 30 | 94% | 2003–2020 |
| BITS-1 | −0.183 | +0.31 | 19 | 67% | 1992–2020 |
| GMEX-Fall | −0.119 | +0.17 | 19 | 80% | 1983–2024 |
| … | | | | | |
| NEUS-Spring | +0.101 | +1.73 | 40 | 94% | 1968–2020 |
| WCANN | +0.126 | +6.36 | 35 | 99% | 2003–2018 |
| GSL-N | +0.154 | −11.79 | 26 | 94% | 1983–2019 |
| SWC-IBTS-4 | +0.258 | +1.94 | 17 | 66% | 1990–2020 |

Two reasons this need not contradict the published poleward-shift literature. Those results are
usually computed for selected species, or as community indices weighted by thermal affinity, where
this is a deliberately blunt unweighted median over every species with fifteen usable years. And a
shift can be real in a subset of species while the median across all of them is zero.

**The depth column is reported and not claimed.** Its magnitudes are larger and far more variable
than latitude's, and the footprint rule does not constrain it: a one-degree cell can span a shelf
break, so hauls that moved *within* a cell can move a depth centroid without the footprint
noticing. Nor-BTS at −14.9 m/decade over seventeen years, on 60% of its rows, is the clearest
number to distrust.

## Remaining limitations

1. **Within-cell movement is uncontrolled.** One degree is up to ~110 km of latitude and, on a
   shelf, hundreds of metres of depth. A finer footprint would control it and would also shrink
   the consistent footprint toward nothing; the 95% threshold check is the closest available
   reassurance, not a fix.
2. **Species selection is blunt by design.** Fifteen usable years within one survey, no thermal
   affinity weighting, no exclusion of species whose range is largely outside the survey box. A
   species whose distribution is truncated by the survey's edge cannot move outward and biases
   its own trend toward zero.
3. **Three surveys report only catch-per-unit-area.** EBS, AI and GOA publish CPUA with no raw
   catch and no swept area, so their weights are the source's own standardisation rather than
   ours. A weighted mean is invariant to a constant rescaling of weights, so this cannot affect
   their centroids, but it does mean their effort model is not identical to the others'.
4. **The run takes about eight minutes**, dominated by 200 permutations over 2,240 series.

## Reproduce

```bash
make ingest-fishglob
make phase1b-report
```
