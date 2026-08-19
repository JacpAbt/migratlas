"""The Continuous Plankton Recorder's western North Atlantic, as one aggregate series.

The BCO-DMO product is a 421-column matrix: eight sample columns and 413 taxon columns keyed by
CPR-internal ids that map to no taxonomy spine this project holds. Phase 3c's registered node
needs none of them individually — the bloom-timing metric runs on aggregate abundance — so each
sample lands as **one** SURVEY_INDEX row: total counted abundance across every taxon column,
taxon_key null, scope AGGREGATE. The same honesty the radar's unattributed biomass already has:
a row that named a taxon it cannot resolve would be worse than a row that names none.

Two value conventions in the file, both handled: an empty cell means the taxon was not assessed
on that sample (excluded from the sum), and the CPR trace sentinel 0.00000000010 means "seen,
below counting" (contributes its face value, which is deliberately negligible).
"""

import logging
from typing import Final

import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.evidence import EvidenceType, Realm, TaxonScope, spec_for
from migratlas.ingest.http import RemoteFile, fetch
from migratlas.lake.writer import WriteResult, write_evidence

log = logging.getLogger(__name__)

SOURCE_ID: Final = "cpr_bcodmo"
FILE_NAME: Final = "765141_v6_cpr-plankton-abundance.csv"

SAMPLE_COLUMNS: Final = (
    "SampleId",
    "Latitude",
    "Longitude",
    "MidPoint_Date_UTC",
    "Year",
    "Month",
    "Day",
    "Hour",
)

# One CPR sample filters ~3 m^3 of water over ~10 nautical miles of tow; the number itself is
# not in the file, so effort is the sample and the unit says so.
EFFORT_UNIT: Final = "sample"


def to_evidence(frame: pl.DataFrame) -> pl.DataFrame:
    """One aggregate row per sample, from the wide taxon matrix."""
    taxon_columns = [c for c in frame.columns if c.startswith("id_")]
    if not taxon_columns:
        msg = "no taxon columns found; the file's layout has changed"
        raise ValueError(msg)
    return frame.select(
        source_id=pl.lit(SOURCE_ID),
        realm=pl.lit(Realm.MARINE.value),
        taxon_scope=pl.lit(TaxonScope.AGGREGATE.value),
        taxon_key=pl.lit(None, dtype=pl.Int64),
        taxon_label=pl.lit("plankton (CPR aggregate)"),
        site_id=pl.col("SampleId"),
        period_start=pl.col("MidPoint_Date_UTC").str.to_datetime(
            "%Y-%m-%dT%H:%MZ", time_zone="UTC", time_unit="ms"
        ),
        period_end=pl.col("MidPoint_Date_UTC").str.to_datetime(
            "%Y-%m-%dT%H:%MZ", time_zone="UTC", time_unit="ms"
        ),
        site_longitude=pl.col("Longitude").cast(pl.Float64),
        site_latitude=pl.col("Latitude").cast(pl.Float64),
        site_depth_m=pl.lit(None, dtype=pl.Float64),
        count=pl.sum_horizontal([pl.col(c).fill_null(0.0) for c in taxon_columns]),
        effort=pl.lit(1.0),
        effort_unit=pl.lit(EFFORT_UNIT),
        protocol=pl.lit("cpr-silk"),
    )


def load(path: str) -> pl.DataFrame:
    """The CSV with every taxon column forced to float, so a trace value cannot break a dtype."""
    overrides = dict.fromkeys(_taxon_names(path), pl.Float64)
    return pl.read_csv(path, schema_overrides=overrides, null_values=[""])


def _taxon_names(path: str) -> list[str]:
    """From the raw header line, with no CSV machinery: an override list must not depend on
    the same inference it exists to override."""
    from pathlib import Path  # noqa: PLC0415 -- one function, stdlib

    with Path(path).open(encoding="utf-8") as handle:
        header = handle.readline().strip().split(",")
    return [c for c in header if c.startswith("id_")]


def ingest() -> WriteResult:
    """Fetch, reduce and land the aggregate series."""
    source = catalog.admit(SOURCE_ID)
    path = fetch(RemoteFile(url=source.download_uri, name=FILE_NAME), SOURCE_ID)
    rows = to_evidence(load(str(path)))
    years = rows["period_start"].dt.year()
    log.info("CPR: %d samples, %s-%s", rows.height, years.min(), years.max())
    spec = spec_for(EvidenceType.SURVEY_INDEX)
    return write_evidence(
        rows.select(spec.schema.names).to_arrow().cast(spec.schema),
        spec,
        source_id=SOURCE_ID,
    )
