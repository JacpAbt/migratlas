"""The one way to read the lake.

Two traps this exists to close, both of which produce wrong answers rather than errors.

``ds.write_dataset`` strips partition columns from the files and encodes them in the path,
so ``source_id`` and ``year`` are invisible unless hive partitioning is enabled. A filter on
``source_id`` then fails loudly -- but a query that merely *selects* it gets nothing, and a
query that forgets to filter by it silently pools every source in the evidence type. The
second is worse: today ``flux`` holds one source, so pooling is invisible, and the day a
second radar network is ingested every phenology number changes with no error anywhere.

So reads go through here, hive partitioning is always on, and the source is an explicit
argument rather than something a caller may forget.
"""

from typing import TYPE_CHECKING

import polars as pl

from migratlas.config import get_settings

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from migratlas.evidence import EvidenceType


def scan_dataset(
    name: str,
    *,
    source_id: str | Sequence[str] | None,
    root: Path | None = None,
) -> pl.LazyFrame:
    """Lazily scan any lake table by directory name, restricted to named sources.

    Evidence types go through :func:`scan`; this exists for the driver samples, which live in
    the lake under the same rules without being evidence about an animal.
    """
    base = (root or get_settings().lake_dir) / name
    if not base.exists():
        msg = f"{name} has never been written to {base}. Ingest it first."
        raise FileNotFoundError(msg)

    frame = pl.scan_parquet(f"{base}/**/*.parquet", hive_partitioning=True)
    if source_id is None:
        return frame
    wanted = [source_id] if isinstance(source_id, str) else list(source_id)
    return frame.filter(pl.col("source_id").is_in(wanted))


def scan(
    evidence_type: EvidenceType,
    *,
    source_id: str | Sequence[str] | None,
    root: Path | None = None,
) -> pl.LazyFrame:
    """Lazily scan one evidence type, restricted to named sources.

    Args:
        evidence_type: Which canonical table to read.
        source_id: One source, several, or ``None`` to deliberately pool every source in
            the table. ``None`` is accepted but must be written out, so pooling is always a
            visible choice rather than an omission.
        root: Lake root; defaults to the configured one.

    Raises:
        FileNotFoundError: if the evidence type has never been written.
    """
    base = (root or get_settings().lake_dir) / str(evidence_type)
    if not base.exists():
        msg = f"No data for {evidence_type} under {base}. Ingest a source first."
        raise FileNotFoundError(msg)

    # Globbed rather than handed the directory: polars refuses a directory containing mixed
    # extensions, and anything dropped beside the data would otherwise break every read.
    frame = pl.scan_parquet(f"{base}/**/*.parquet", hive_partitioning=True)
    if source_id is None:
        return frame
    wanted = [source_id] if isinstance(source_id, str) else list(source_id)
    return frame.filter(pl.col("source_id").is_in(wanted))


def sources(evidence_type: EvidenceType, root: Path | None = None) -> list[str]:
    """Which sources are present for an evidence type."""
    base = (root or get_settings().lake_dir) / str(evidence_type)
    if not base.exists():
        return []
    return sorted(
        directory.name.removeprefix("source_id=")
        for directory in base.iterdir()
        if directory.is_dir() and directory.name.startswith("source_id=")
    )
