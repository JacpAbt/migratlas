"""Dark Ecology: nightly aerial passage from the US weather radar network.

Ingests the *daily time series* product rather than the vertical profiles. The profiles
are ~220 GiB across seven records and resolve height; the daily series is 159 MiB and
already integrates reflectivity traffic over height and over each night, which is exactly
what seasonal passage-date quantiles need. Profiles become worth the bandwidth only when
the question turns to flight altitude.

The signal is aerial *biomass*: MistNet separates precipitation from biology, not birds
from bats from insects. Rows carry ``TaxonScope.UNATTRIBUTED`` accordingly.
"""

import csv
import io
import logging
import tarfile
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.evidence import EvidenceType, Realm, TaxonScope, spec_for
from migratlas.ingest import zenodo
from migratlas.ingest.http import fetch
from migratlas.lake.writer import write_evidence

if TYPE_CHECKING:
    from pathlib import Path

    import pyarrow as pa

    from migratlas.lake.writer import WriteResult

log = logging.getLogger(__name__)

SOURCE_ID: Final = "darkecology_daily"
RECORD_ID: Final = "18433334"
"""Version DOI 10.5281/zenodo.18433334. Pinned deliberately -- the concept DOI floats to
whatever is newest, which would make a published figure unreproducible."""

DAILY_ARCHIVE: Final = "daily.tar.bz2"
STATIONS_FILE: Final = "nexrad-stations.csv"

# Source column -> canonical quantity name. Filtered and unfiltered variants are both
# ingested because comparing them *is* the precipitation sensitivity test: the filtered
# ones have rain-classified volumes removed, the unfiltered ones do not.
#
# Two families, and the difference between them is a confound test rather than a detail.
# `traffic` integrates RTR = reflectivity x speed x bin height, so it is weighted by how
# fast the scatterers were moving; `reflectivity_hours` integrates VIR = reflectivity x
# bin height and carries no speed term. A drift in flight speed -- between years, or
# across a season -- therefore moves a passage-date quantile computed from `traffic` even
# with the biomass held constant. Horton et al. used a traffic rate, so `traffic` is the
# right choice for replication, and `reflectivity_hours` is the control that says whether
# the trend survives dropping the speed weighting.
QUANTITIES: Final[dict[str, str]] = {
    "traffic": "reflectivity_traffic",
    "traffic_unfiltered": "reflectivity_traffic_unfiltered",
    "reflectivity_hours": "reflectivity_hours",
    "reflectivity_hours_unfiltered": "reflectivity_hours_unfiltered",
}


@dataclass(frozen=True, slots=True)
class Station:
    callsign: str
    latitude: float
    longitude: float


def load_stations(path: Path) -> dict[str, Station]:
    """Parse the station metadata shipped alongside the data."""
    stations: dict[str, Station] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            callsign = (row.get("callsign") or "").strip()
            try:
                latitude = float(row["lat"])
                longitude = float(row["lon"])
            except KeyError, TypeError, ValueError:
                continue
            if callsign:
                stations[callsign] = Station(callsign, latitude, longitude)
    return stations


def read_daily(archive: Path) -> pl.DataFrame:
    """Read every CSV in the daily archive into one frame.

    Streams the tar rather than extracting it: the members are small and numerous, and
    unpacking 161 stations to disk first would double the IO for no benefit.
    """
    frames: list[pl.DataFrame] = []
    with tarfile.open(archive, mode="r:bz2") as tar:
        for member in tar:
            if not member.isfile() or not member.name.endswith(".csv"):
                continue
            handle = tar.extractfile(member)
            if handle is None:  # pragma: no cover -- defensive
                continue
            frames.append(
                pl.read_csv(
                    io.BytesIO(handle.read()),
                    schema_overrides={"station": pl.String, "period": pl.String},
                    try_parse_dates=True,
                )
            )
    if not frames:
        msg = f"No CSV members found in {archive}"
        raise ValueError(msg)
    log.info("read %d station files from %s", len(frames), archive.name)
    return pl.concat(frames, how="vertical_relaxed")


def to_evidence(daily: pl.DataFrame, stations: dict[str, Station]) -> pa.Table:
    """Reshape the daily series into FLUX rows, one per station-date-window-quantity."""
    known = pl.DataFrame(
        {
            "station": [s.callsign for s in stations.values()],
            "station_latitude": [s.latitude for s in stations.values()],
            "station_longitude": [s.longitude for s in stations.values()],
        }
    )

    # An inner join drops stations with no published coordinates. They cannot be placed on
    # a map or matched to a driver raster, so carrying them would only defer the problem.
    joined = daily.join(known, on="station", how="inner")
    dropped = daily.height - joined.height
    if dropped:
        missing = sorted(set(daily["station"]) - set(known["station"]))
        log.warning("dropped %d rows from stations with no coordinates: %s", dropped, missing)

    long = joined.unpivot(
        index=[
            "station",
            "date",
            "period",
            "period_length",
            "fraction_missing",
            "fraction_rain",
            "u",
            "v",
            "direction",
            "speed",
            "station_latitude",
            "station_longitude",
        ],
        on=list(QUANTITIES),
        variable_name="source_column",
        value_name="magnitude",
    ).drop_nulls("magnitude")

    frame = long.select(
        source_id=pl.lit(SOURCE_ID),
        realm=pl.lit(Realm.AERIAL.value),
        taxon_scope=pl.lit(TaxonScope.UNATTRIBUTED.value),
        taxon_key=pl.lit(None, dtype=pl.Int64),
        taxon_label=pl.lit(None, dtype=pl.String),
        station_id=pl.col("station"),
        # The labelled date at midnight UTC, not the exact window start -- the daily
        # product identifies a night by date and does not publish its boundaries.
        timestamp=pl.col("date").cast(pl.Datetime("ms", time_zone="UTC")),
        station_longitude=pl.col("station_longitude"),
        station_latitude=pl.col("station_latitude"),
        # Vertically integrated, so no height bin applies.
        height_min_m=pl.lit(None, dtype=pl.Float64),
        height_max_m=pl.lit(None, dtype=pl.Float64),
        magnitude=pl.col("magnitude").cast(pl.Float64),
        quantity=pl.col("source_column").replace_strict(QUANTITIES),
        integration_hours=pl.col("period_length").cast(pl.Float64),
        coverage_fraction=(1.0 - pl.col("fraction_missing")).cast(pl.Float64),
        rain_fraction=pl.col("fraction_rain").cast(pl.Float64),
        window_kind=pl.col("period"),
        direction_deg=pl.col("direction").cast(pl.Float64),
        speed_ms=pl.col("speed").cast(pl.Float64),
        # Left null: the daily product does not say which hardware generation produced a
        # night, and the dual-polarisation break has to be established from station
        # upgrade dates rather than guessed here.
        instrument_generation=pl.lit(None, dtype=pl.String),
        quality_flag=pl.lit(None, dtype=pl.String),
    )
    # Reorder explicitly: polars does not guarantee that keyword order in select()
    # survives into column order, and cast() matches by position.
    schema = spec_for(EvidenceType.FLUX).schema
    return frame.select(schema.names).to_arrow().cast(schema)


def ingest(*, force: bool = False) -> WriteResult:
    """Download, reshape and land the daily series. Idempotent."""
    source = catalog.admit(SOURCE_ID)
    log.info("ingesting %s (%s)", source.title, source.licence)

    rec = zenodo.record(RECORD_ID)
    if source.doi and rec.version_doi != source.doi:
        msg = (
            f"Registry pins DOI {source.doi} but Zenodo record {RECORD_ID} now reports "
            f"{rec.version_doi}. Reconcile before ingesting."
        )
        raise ValueError(msg)

    archive = fetch(rec.files[DAILY_ARCHIVE], SOURCE_ID, force=force)
    stations_path = fetch(rec.files[STATIONS_FILE], SOURCE_ID, force=force)

    stations = load_stations(stations_path)
    log.info("%d stations with coordinates", len(stations))

    table = to_evidence(read_daily(archive), stations)
    log.info("%d evidence rows", table.num_rows)

    return write_evidence(table, spec_for(EvidenceType.FLUX), source_id=SOURCE_ID)
