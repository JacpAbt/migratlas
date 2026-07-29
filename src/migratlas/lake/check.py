"""Detect schema drift in the lake.

Written after a real incident. ``ABUNDANCE_SURFACE`` gained ``cell_id`` and ``cell_system``
between two ingests, so one source's files had the columns and another's did not. DuckDB
reads a mixed directory by silently intersecting the schemas, which means the new columns
simply vanished from every query -- no error, no warning, just missing data. A schema change
has to be followed by re-ingesting the affected sources, and something has to notice when it
was not.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pyarrow.parquet as pq

from migratlas.config import get_settings
from migratlas.evidence import SPECS, spec_for

if TYPE_CHECKING:
    from pathlib import Path

    from migratlas.evidence import EvidenceType
    from migratlas.lake.spec import TableSpec


@dataclass(frozen=True, slots=True)
class Drift:
    """One file whose schema differs from its dataset's canonical schema."""

    path: str
    missing: tuple[str, ...]
    unexpected: tuple[str, ...]

    def __str__(self) -> str:
        parts = []
        if self.missing:
            parts.append(f"missing {list(self.missing)}")
        if self.unexpected:
            parts.append(f"unexpected {list(self.unexpected)}")
        return f"{self.path}: {'; '.join(parts)}"


def check_dataset(spec: TableSpec, root: Path | None = None) -> list[Drift]:
    """Compare every Parquet file in one dataset against its canonical schema.

    Partition columns are excluded: hive partitioning stores them in the path, not the file,
    so their absence is correct rather than drift.

    Takes a ``TableSpec`` rather than an evidence type because drivers live in the lake under
    the same rules and are not evidence about animals.
    """
    base = (root or get_settings().lake_dir) / spec.name
    if not base.exists():
        return []

    expected = set(spec.schema.names) - set(spec.partition_by)
    drifts: list[Drift] = []
    for path in sorted(base.rglob("*.parquet")):
        actual = set(pq.read_schema(path).names)
        missing = tuple(sorted(expected - actual))
        unexpected = tuple(sorted(actual - expected - set(spec.partition_by)))
        if missing or unexpected:
            drifts.append(Drift(path=str(path), missing=missing, unexpected=unexpected))
    return drifts


def check_evidence_type(evidence_type: EvidenceType, root: Path | None = None) -> list[Drift]:
    """Drift check for one evidence type. A thin wrapper over :func:`check_dataset`."""
    return check_dataset(spec_for(evidence_type), root)


def check_all(root: Path | None = None) -> dict[str, list[Drift]]:
    """Check every dataset in the lake: the evidence types, and the driver samples."""
    from migratlas.drivers.schema import DRIVER_SAMPLES  # noqa: PLC0415 -- avoids a cycle

    checked: dict[str, list[Drift]] = {
        str(evidence_type): drifts
        for evidence_type in SPECS
        if (drifts := check_dataset(spec_for(evidence_type), root))
    }
    if drifts := check_dataset(DRIVER_SAMPLES, root):
        checked[DRIVER_SAMPLES.name] = drifts
    return checked
