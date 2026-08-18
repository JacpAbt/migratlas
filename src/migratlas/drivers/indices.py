"""The climate-mode indices: the conditioning set phase3a-skill.md §2 registered.

Four monthly series from NOAA's own plain-text endpoints — ONI, NAO, AO from the Climate
Prediction Center, PDO from NCEI's ERSST v5 index directory. Their role in every fit is to
absorb variance shared across units, never to be interpreted, and the registry caveat says so.

The AMO is deliberately not here: PSL's canonical series went stale at January 2023, and the
honest route when the marine work needs one is computing it in-lake from ERSST.

These files update monthly and therefore carry no checksum; the fetch cache keeps the first
download, so refreshing a series means deleting its raw file first. Fine for the hindcasts,
which end years before any month a refresh would add — the standing prediction (#57) will need
a refresh policy, and should decide it in its own pre-registration rather than inherit silence.
"""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final, NamedTuple

import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.drivers.schema import DRIVER_SAMPLES, DriverKind
from migratlas.ingest.http import RemoteFile, fetch
from migratlas.lake.writer import WriteResult, write_table

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

SOURCE_ID: Final = "noaa_climate_indices"

# Values past this are sentinels (99.99, -99.9) in every one of these formats; real modes live
# within a few standard deviations of zero.
PLAUSIBLE: Final = 10.0

# ONI rows name a 3-month season; the index belongs to its centre month.
SEASON_CENTRE: Final[dict[str, int]] = {
    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12,
}  # fmt: skip


class IndexFile(NamedTuple):
    variable: str
    url: str
    layout: str
    """`oni` (season label, year, total, anomaly) or `table` (year then twelve months)."""
    derived_from: str


FILES: Final[tuple[IndexFile, ...]] = (
    IndexFile(
        "oni",
        "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
        "oni",
        "CPC:ONI, ERSSTv5 Nino-3.4 anomaly, 3-month running mean",
    ),
    IndexFile(
        "nao",
        "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/norm.nao.monthly.b5001.current.ascii.table",
        "table",
        "CPC:NAO, rotated-PC definition (not the station-based Hurrell NAO)",
    ),
    IndexFile(
        "ao",
        "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/monthly.ao.index.b50.current.ascii.table",
        "table",
        "CPC:AO, 1000 hPa height anomaly loading",
    ),
    IndexFile(
        "pdo",
        "https://www.ncei.noaa.gov/pub/data/cmb/ersst/v5/index/ersst.v5.pdo.dat",
        "table",
        "NCEI:PDO, from ERSST v5",
    ),
)


def parse_oni(text: str) -> list[tuple[int, int, float]]:
    """(year, month, value) rows from the ONI layout, unknown lines skipped by shape."""
    rows = []
    for line in text.splitlines():
        parts = line.split()
        expected_columns = 4
        if len(parts) != expected_columns or parts[0] not in SEASON_CENTRE:
            continue
        value = float(parts[3])
        if abs(value) >= PLAUSIBLE:
            continue
        rows.append((int(parts[1]), SEASON_CENTRE[parts[0]], value))
    return rows


def parse_table(text: str) -> list[tuple[int, int, float]]:
    """(year, month, value) rows from the year-then-months layout, sentinels dropped.

    Handles both current-year shapes in the wild: months simply absent, and months present as
    sentinel values like 99.99 or -99.90.
    """
    rows = []
    months_per_year = 12
    minimum_columns = 2  # a year and at least one month
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < minimum_columns or not parts[0].lstrip("-").isdigit():
            continue
        year = int(parts[0])
        for month, raw in enumerate(parts[1 : months_per_year + 1], start=1):
            try:
                value = float(raw)
            except ValueError:
                break
            if abs(value) >= PLAUSIBLE:
                continue
            rows.append((year, month, value))
    return rows


def build_indices(root: Path | None = None) -> WriteResult:
    """Fetch all four series and land them as driver samples in one write.

    One write, not four: the lake replaces the partitions a write touches, and these series
    share every year — the era5 lesson, avoided rather than relearned.
    """
    catalog.admit(SOURCE_ID)
    frames = []
    for spec in FILES:
        raw = fetch(RemoteFile(url=spec.url, name=f"{spec.variable}.txt"), SOURCE_ID)
        parser = parse_oni if spec.layout == "oni" else parse_table
        rows = parser(raw.read_text(encoding="utf-8"))
        if not rows:
            msg = f"{spec.variable}: no rows parsed from {spec.url}"
            raise ValueError(msg)
        log.info("%s: %d months, %d-%d", spec.variable, len(rows), rows[0][0], rows[-1][0])
        frames.append(_to_frame(spec, rows))
    table = pl.concat(frames)
    schema = DRIVER_SAMPLES.schema
    return write_table(
        table.select(schema.names).to_arrow().cast(schema),
        DRIVER_SAMPLES,
        source_id=SOURCE_ID,
        root=root,
    )


def _to_frame(spec: IndexFile, rows: list[tuple[int, int, float]]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "source_id": [SOURCE_ID] * len(rows),
            "site_id": [spec.variable] * len(rows),
            "period_start": [datetime(year, month, 1, tzinfo=UTC) for year, month, _ in rows],
            # A mode has no coordinates. NaN states that plainly, where a fake (0, 0) would put
            # the North Atlantic Oscillation in the Gulf of Guinea.
            "longitude": [float("nan")] * len(rows),
            "latitude": [float("nan")] * len(rows),
            "depth_m": [None] * len(rows),
            "variable": [spec.variable] * len(rows),
            "value": [value for _, _, value in rows],
            "unit": ["index"] * len(rows),
            # The least-bad kind: each index is a scalar computed from a gridded product
            # (ERSST, reanalysis heights) by its publisher — not measured at a site, not from
            # this lake's evidence, not simulated. `derived_from` carries whose definition.
            "kind": [DriverKind.GRIDDED.value] * len(rows),
            "derived_from": [spec.derived_from] * len(rows),
        },
        schema_overrides={"depth_m": pl.Float64},
    )
