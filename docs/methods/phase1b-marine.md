# Phase 1b — marine change detection, and why it cannot be done with what is in the lake

**Status:** blocked on data, deliberately. Recorded 2026-07-29, before any metric was written.

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

1. **Standardised repeated surveys — `SURVEY_INDEX`.** The gold standard for marine distribution
   change precisely because effort is fixed by design: the same gear, the same stations, the same
   season, every year. NOAA's bottom-trawl series (NEFSC spring and autumn, AFSC Bering Sea) are
   open, run for decades, and the poleward-shift literature for North Atlantic and Bering Sea fish
   is built on them. This is the honest Phase 1b, and it would exercise `SURVEY_INDEX` — the fourth
   of the seven evidence types and so far unused. It also keeps the realm-general claim intact,
   since passage quantiles and trend fitting already work on any timed quantity.
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
