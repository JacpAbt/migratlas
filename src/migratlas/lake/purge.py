"""Remove rows the ingest gate would refuse today, from tables written before it existed.

`redact.admit_taxon_for_ingest` is a floor rather than a sensitivity classification: this is an
animal-movement atlas and there is no resolution at which human location data may be stored. It
runs at ingest, and it landed after `obis_speciesgrids` was already in the lake -- so the floor was
enforced on everything written after it and on nothing written before.

`clear_for_publication` re-checks the floor and refuses, which is why the rows were never drawn
after the check existed. That is the right behaviour and it is not enough: its own refusal message
says to delete rather than coarsen, and a rule that says data may not be stored is not satisfied by
storing it and declining to show it.

Deliberately narrow. This purges the floor and nothing else. A sensitivity reclassification is not
a reason to delete data -- the gate withholds a `high` taxon from every map while the lake keeps
every fix, because a trend computed over a population locates no animal. The floor is the one rule
where the correct action on the stored rows is deletion.
"""

import logging
import shutil
from dataclasses import dataclass
from typing import TYPE_CHECKING

import polars as pl
import pyarrow as pa

from migratlas.evidence import EvidenceType, spec_for
from migratlas.lake.reader import scan
from migratlas.lake.reader import sources as lake_sources
from migratlas.lake.writer import write_evidence
from migratlas.redact import NEVER_INGESTED_KEYS, NEVER_INGESTED_NAMES

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FloorRows:
    """Rows in one source that the ingest floor would refuse."""

    evidence_type: EvidenceType
    source_id: str
    rows: int
    labels: tuple[str, ...]
    partitions: tuple[str, ...]
    """Year partitions holding them, so a purge can rewrite those and leave the rest alone."""


def _matches_floor() -> pl.Expr:
    """The same two routes `admit_taxon_for_ingest` refuses on, as a filter.

    Both, because a source may ship names and no keys or keys and no names, and a check that
    understood only one of them would be satisfiable by accident. The name is normalised the way
    the gate normalises it rather than compared raw.
    """
    normalised = pl.col("taxon_label").str.to_lowercase().str.replace_all(r"\s+", " ")
    return pl.col("taxon_key").is_in(sorted(NEVER_INGESTED_KEYS)) | normalised.str.strip_chars(
        " "
    ).is_in(sorted(NEVER_INGESTED_NAMES))


def floor_rows(root: Path | None = None) -> list[FloorRows]:
    """Every evidence source holding a taxon the floor refuses. Reads only."""
    found: list[FloorRows] = []
    for kind in EvidenceType:
        for source_id in lake_sources(kind, root):
            hits = (
                scan(kind, source_id=source_id, root=root)
                .filter(_matches_floor())
                .select("taxon_label", "year")
                .collect()
            )
            if hits.is_empty():
                continue
            found.append(
                FloorRows(
                    evidence_type=kind,
                    source_id=source_id,
                    rows=hits.height,
                    labels=tuple(sorted({str(name) for name in hits["taxon_label"] if name})),
                    partitions=tuple(sorted({str(year) for year in hits["year"]})),
                )
            )
    return found


@dataclass(frozen=True, slots=True)
class Purged:
    source_id: str
    evidence_type: EvidenceType
    removed: int
    kept: int
    partitions: tuple[str, ...]


def purge_floor_taxa(root: Path | None = None) -> list[Purged]:
    """Rewrite every partition holding a floor taxon, without those rows.

    Partition by partition rather than source by source. `obis_speciesgrids` is 17.2 million rows
    and the floor touches 119 of them across nine years, so rewriting the source would read the
    whole table into memory to change nine files. `write_evidence` replaces the partitions it
    touches, so writing one year is a bounded operation with a bounded blast radius.
    """
    results: list[Purged] = []
    for found in floor_rows(root):
        spec = spec_for(found.evidence_type)
        removed = 0
        kept = 0
        for year in found.partitions:
            # Cast, because hive partitioning infers the column's type from the directory names:
            # a source whose years are all numeric reads back as i64, and one holding an `undated`
            # partition reads back as a string. Comparing to a string works for both.
            partition = scan(found.evidence_type, source_id=found.source_id, root=root).filter(
                pl.col("year").cast(pl.String) == year
            )
            before = partition.select(pl.len()).collect().item()
            # Selected by the schema's own field names, and in its order: `year` is a hive
            # partition the reader materialises, and the writer derives it again on the way back
            # in. Handing it to `validate` would fail on a column the schema does not have.
            surviving = (
                partition.filter(~_matches_floor()).select(spec.schema.names).collect().to_arrow()
            )
            table = surviving.cast(pa.schema(spec.schema))
            gone = before - table.num_rows
            if not gone:  # pragma: no cover -- floor_rows named this partition
                continue
            write_evidence(table, spec, source_id=found.source_id, root=root)
            _drop_if_empty(spec.name, found.source_id, year, table.num_rows, root)
            removed += gone
            kept += table.num_rows
            log.info(
                "%s/%s year=%s: %d floor rows removed, %d kept",
                found.evidence_type.value,
                found.source_id,
                year,
                gone,
                table.num_rows,
            )
        results.append(
            Purged(
                source_id=found.source_id,
                evidence_type=found.evidence_type,
                removed=removed,
                kept=kept,
                partitions=found.partitions,
            )
        )
    return results


def _drop_if_empty(
    dataset: str, source_id: str, year: str, surviving: int, root: Path | None
) -> None:
    """Remove a partition directory that the purge emptied.

    `write_dataset` deletes the partitions the incoming data covers and writes them again. A
    partition whose every row was a floor row has no incoming data, so nothing deletes it and the
    old file stays exactly where it was -- the one way this operation could silently do nothing.
    """
    if surviving:
        return
    from migratlas.config import get_settings  # noqa: PLC0415 -- import-light at module scope

    directory = (
        (root or get_settings().lake_dir) / dataset / f"source_id={source_id}" / f"year={year}"
    )
    if directory.exists():
        shutil.rmtree(directory)
        log.info("%s/%s year=%s held nothing else, partition removed", dataset, source_id, year)
