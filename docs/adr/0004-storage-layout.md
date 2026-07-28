# ADR 0004 — Split raw archives from the working set

**Status:** accepted · 2026-07-28

## Context

The Dark Ecology radar archive alone is ~49 GB, and later phases add reanalysis and
climate-model data that dwarf it. Fast local storage is the scarce resource on a
workstation; bulk capacity usually is not.

The temptation is to put everything on whichever disk has room. Measured on the
development machine — an NVMe SSD with limited free space, and a 2 TB SATA HDD reached
from WSL through the `/mnt` translation layer:

| Location | Sequential write | Sequential read | 300 small files: create / read |
| --- | --- | --- | --- |
| native ext4 (NVMe) | 2.2 GB/s | 20.9 GB/s | 23 ms / 7 ms |
| NVMe via `/mnt` (9p) | 223 MB/s | 304 MB/s | 908 ms / 844 ms |
| HDD via `/mnt` (9p) | 94 MB/s | 333 MB/s | 782 ms / 560 ms |

Two things stand out, and neither is what one would guess:

**The translation layer dominates, not the disk.** Sequential reads from the HDD through
`/mnt` matched the SSD through `/mnt`. The protocol is the bottleneck, so putting bulk
data on the slower disk costs almost nothing for sequential access.

**Small-file operations are 35–120× slower through `/mnt`.** That is precisely the access
pattern of DuckDB scanning a hive-partitioned Parquet dataset — many part files, opened
and read repeatedly throughout an analysis session.

## Decision

Split by access pattern rather than by size.

**Raw archives → bulk disk.** Written once, read sequentially once during ingest. The
94 MB/s write means a 49 GB download spends about nine minutes writing, which is
irrelevant for a one-off. Configurable via `MIGRATLAS_RAW_DATA_DIR`.

**Lake, derived artefacts, tiles and the DuckDB file → native fast storage.** These are
the many-small-files, repeatedly-scanned working set where the translation layer would
cost two orders of magnitude. They are also far smaller: radar profiles as columnar zstd
Parquet are a fraction of the raw archive.

## Consequences

Good: the bulk of the data leaves the scarce SSD without slowing down analysis, which is
what actually gets run repeatedly. The split falls along a line that already existed in
the code — `raw_dir` was always documented as "never read by analysis" — so it cost one
optional setting rather than a restructure.

Bad: two locations to back up, and a second path that can be misconfigured. Ingest now
depends on the bulk disk being mounted, so a missing mount fails at ingest rather than at
startup.

Watch for: if a later phase needs to re-read raw archives repeatedly rather than once —
retraining a model directly against raw files, say — this split becomes the wrong one and
that data should be staged onto fast storage first.
