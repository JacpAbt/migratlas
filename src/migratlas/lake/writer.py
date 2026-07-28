"""Write validated evidence tables into the partitioned Parquet lake."""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds

from migratlas.config import get_settings
from migratlas.lake.check import check_evidence_type
from migratlas.lake.identifiers import new_run_id

if TYPE_CHECKING:
    from pathlib import Path

    from migratlas.evidence import EvidenceSpec

UNDATED = "undated"
"""Partition value for records with no usable date, e.g. a museum record with only a
collector's name. Dropping them would bias the historical baseline."""


@dataclass(frozen=True, slots=True)
class WriteResult:
    run_id: str
    source_id: str
    evidence_type: str
    rows: int
    partitions: tuple[str, ...]
    path: str
    written_at: str


def write_evidence(
    table: pa.Table,
    spec: EvidenceSpec,
    *,
    source_id: str,
    root: Path | None = None,
) -> WriteResult:
    """Validate and write one evidence table.

    Re-running for the same source replaces the partitions it touches, so ingest is
    idempotent rather than accumulating duplicate rows on a retry.
    """
    spec.validate(table)
    _check_single_source(table, source_id)

    partitioned = _add_partition_columns(table, spec)
    dataset_root = (root or get_settings().lake_dir) / str(spec.evidence_type)
    _refuse_mixed_schemas(spec, dataset_root, source_id)
    dataset_root.mkdir(parents=True, exist_ok=True)

    file_format = ds.ParquetFileFormat()
    ds.write_dataset(
        partitioned,
        base_dir=dataset_root,
        format=file_format,
        partitioning=ds.partitioning(
            pa.schema([partitioned.schema.field(name) for name in spec.partition_by]),
            flavor="hive",
        ),
        # zstd over snappy: better ratio at comparable speed on columnar float data,
        # once Parquet's own encodings have run.
        file_options=file_format.make_write_options(compression="zstd", compression_level=3),
        existing_data_behavior="delete_matching",
        basename_template=f"part-{source_id}-{{i}}.parquet",
    )

    result = WriteResult(
        run_id=new_run_id(),
        source_id=source_id,
        evidence_type=str(spec.evidence_type),
        rows=partitioned.num_rows,
        partitions=spec.partition_by,
        path=str(dataset_root),
        written_at=datetime.now(UTC).isoformat(),
    )
    _write_manifest(result, dataset_root.parent / "_manifests" / str(spec.evidence_type))
    return result


def _refuse_mixed_schemas(spec: EvidenceSpec, dataset_root: Path, source_id: str) -> None:
    """Refuse to write if another source's files predate the current schema.

    Learned the hard way: when ``ABUNDANCE_SURFACE`` gained two columns, the older source's
    files kept the old schema and DuckDB read the mixed directory by *intersecting* schemas.
    The new columns vanished from every query with no error at all. Failing here is far
    better than a separate check nobody runs -- a schema change must be followed by
    re-ingesting the sources that predate it.
    """
    drifts = [
        drift
        for drift in check_evidence_type(spec.evidence_type, dataset_root.parent)
        if f"source_id={source_id}/" not in drift.path.replace("\\", "/")
    ]
    if drifts:
        others = sorted({_source_of(drift.path) for drift in drifts})
        msg = (
            f"Refusing to write {source_id!r}: {len(drifts)} existing file(s) under "
            f"{spec.evidence_type} do not match the current schema (sources: {others}). "
            f"A mixed directory is read by intersecting schemas, so the newer columns would "
            f"silently disappear. Re-ingest those sources first. Example: {drifts[0]}"
        )
        raise ValueError(msg)


def _source_of(path: str) -> str:
    for part in path.replace("\\", "/").split("/"):
        if part.startswith("source_id="):
            return part.removeprefix("source_id=")
    return "unknown"


def _check_single_source(table: pa.Table, source_id: str) -> None:
    """Refuse a table mixing sources, or claiming a different one than the caller.

    ``source_id`` is a partition key, so a mismatch here would scatter one source's rows
    under another's directory and quietly corrupt every later query.
    """
    if not table.num_rows:
        return
    distinct = pc.unique(table.column("source_id")).to_pylist()
    if distinct != [source_id]:
        msg = (
            f"Table declares source_id {distinct} but is being written as "
            f"{source_id!r}. One table, one source."
        )
        raise ValueError(msg)


def _add_partition_columns(table: pa.Table, spec: EvidenceSpec) -> pa.Table:
    """Attach any partition column that is derived rather than stored."""
    if "year" not in spec.partition_by:
        return table
    if spec.time_column is None:  # pragma: no cover -- guarded by a schema test
        msg = f"{spec.evidence_type} partitions by year but declares no time column"
        raise ValueError(msg)

    timestamps = table.column(spec.time_column)
    years = pc.cast(pc.year(timestamps), pa.string())
    years = pc.fill_null(years, UNDATED)
    return table.append_column(pa.field("year", pa.string(), nullable=False), years)


def _write_manifest(result: WriteResult, manifests: Path) -> None:
    """Record what was written, keyed by a time-ordered run id.

    The audit trail for "where did this number come from", which matters more here than
    usual: published figures have to be traceable to a specific ingest.

    Deliberately outside the dataset directory: a directory of mixed file extensions is
    rejected by some readers, and metadata sitting among the data invites exactly that.
    """
    manifests.mkdir(parents=True, exist_ok=True)
    (manifests / f"{result.run_id}.json").write_text(
        json.dumps(asdict(result), indent=2) + "\n", encoding="utf-8"
    )
