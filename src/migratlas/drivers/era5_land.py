"""ERA5-Land snow depth at the herd ranges: the terrestrial covariate Phase 3a registered.

A sibling of `era5.py`, not a fork: `wait`, `locate`, `monthly` and the request-tag rule are
imported unchanged, and only the two functions that bake the dataset name into a URL or a cache
filename are reimplemented. Its own source id, because the lake replaces the partitions a write
touches and this must never share `era5`'s.

The variable is ERA5-Land's `snow_depth` — true snow thickness in metres (`sde`), not the water
equivalent plain ERA5 calls by the same words. The covariate survey flagged that trap the day
the product was chosen; the canonical name says which one this is.
"""

import logging
from typing import TYPE_CHECKING, Final

import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.config import get_settings
from migratlas.drivers.era5 import (
    Area,
    Field,
    RetrievalError,
    monthly,
    request_tag,
    to_samples,
    wait,
)
from migratlas.drivers.schema import DRIVER_SAMPLES
from migratlas.evidence import EvidenceType
from migratlas.features.annotate import Located, Point, nearest_cells
from migratlas.lake.reader import scan
from migratlas.lake.writer import WriteResult, write_table

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

SOURCE_ID: Final = "era5_land"
API: Final = "https://cds.climate.copernicus.eu/api"
DATASET: Final = "reanalysis-era5-land-monthly-means"

SNOW: Final = Field(
    cds_name="snow_depth",
    canonical="snow_depth_true_m",
    unit="m",
)

# The herds the registration names, with the years Phase 1h found usable plus the margin the
# season windows need.
HERDS: Final[tuple[str, ...]] = ("movebank_yahatinda_elk", "movebank_svalbard_reindeer")
YEARS: Final = tuple(range(2001, 2025))
BOX_DEG: Final = 1.5
ANTIMERIDIAN_DEG: Final = 180.0
"""Longitudes past this are the 0-360 convention ERA5-Land serves; the lake keeps -180..180."""
"""Half-width of the request box around each herd's centroid: small on purpose, the request
is one grid cell's worth of use."""


def submit(field: Field, years: list[int], months: list[int], *, area: Area) -> str:
    """Queue one ERA5-Land request. The land dataset's licence is the same `cc-by`."""
    import httpx  # noqa: PLC0415 -- only gridded drivers need it here

    payload = {
        "inputs": {
            "product_type": ["monthly_averaged_reanalysis"],
            "variable": [field.cds_name],
            "year": [str(year) for year in years],
            "month": [f"{month:02d}" for month in months],
            "time": ["00:00"],
            "area": list(area),
            "data_format": "netcdf",
        }
    }
    response = httpx.post(
        f"{API}/retrieve/v1/processes/{DATASET}/execute",
        headers={
            "PRIVATE-TOKEN": get_settings().credential("cds_token"),
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120.0,
        follow_redirects=True,
    )
    if response.status_code == 403:  # noqa: PLR2004 -- the one status worth naming
        msg = (
            "CDS refused the request: accept the `cc-by` licence once at "
            f"https://cds.climate.copernicus.eu/datasets/{DATASET}?tab=download#manage-licences"
        )
        raise RetrievalError(msg)
    response.raise_for_status()
    job = response.json()
    log.info("CDS job %s accepted (%s, %d years)", job["jobID"], field.cds_name, len(years))
    return str(job["jobID"])


def download(field: Field, href: str, tag: str) -> Path:
    """Fetch into the raw archive under this dataset's own truthful cache name."""
    from migratlas.ingest.http import RemoteFile, fetch  # noqa: PLC0415 -- avoids a cycle

    name = f"{DATASET}-{field.cds_name}-{tag}.nc"
    return fetch(RemoteFile(url=href, name=name), SOURCE_ID)


def herd_centroid(source_id: str) -> Point:
    """The herd's range centre, from its own fixes: median latitude and longitude."""
    import numpy as np  # noqa: PLC0415 -- only the medians need it

    fixes = scan(EvidenceType.TRACK, source_id=source_id).select("latitude", "longitude").collect()
    return Point(
        site_id=source_id,
        latitude=float(np.median(fixes["latitude"].to_numpy())),
        longitude=float(np.median(fixes["longitude"].to_numpy())),
    )


def ingest(root: Path | None = None) -> WriteResult:
    """Land monthly snow depth at both herd centroids, in one write.

    One request per herd (the boxes are 3,000 km apart; one box covering both would be mostly
    ocean), one write for both (the partition rule), the nearest land cell to each centroid.
    """
    catalog.admit(SOURCE_ID)
    frames = []
    for herd in HERDS:
        point = herd_centroid(herd)
        area: Area = (
            point.latitude + BOX_DEG,
            point.longitude - BOX_DEG,
            point.latitude - BOX_DEG,
            point.longitude + BOX_DEG,
        )
        years = list(YEARS)
        months = list(range(1, 13))
        tag = request_tag(SNOW, years, months, area)
        path = _unwrap(download(SNOW, wait(submit(SNOW, years, months, area=area)), tag))
        located = _locate(point, path)
        frame = monthly(SNOW, path, located)
        # Back to the lake's own -180..180 before anything is written.
        frames.append(
            frame.with_columns(
                longitude=pl.when(pl.col("longitude") > ANTIMERIDIAN_DEG)
                .then(pl.col("longitude") - 360.0)
                .otherwise(pl.col("longitude"))
            )
        )
        log.info("%s: %d snow months", herd, frames[-1].height)

    import pyarrow as pa  # noqa: PLC0415 -- only this concatenation needs it at runtime

    table = pa.concat_tables([to_samples(SNOW, frame, SOURCE_ID) for frame in frames])
    return write_table(table, DRIVER_SAMPLES, source_id=SOURCE_ID, root=root)


def _unwrap(path: Path) -> Path:
    """The netCDF inside, when CDS delivers a zip wearing a .nc name.

    ERA5-Land results arrive as a zip archive whose one member is the actual netCDF -- the
    single-levels dataset does not do this, which is why era5.py never needed to know. Detected
    by magic bytes rather than trusted from the extension, extracted once beside the archive.
    """
    import zipfile  # noqa: PLC0415 -- only this unwrapping needs it

    with path.open("rb") as handle:
        if handle.read(2) != b"PK":
            return path
    extracted = path.with_suffix(".unwrapped.nc")
    if not extracted.exists():
        with zipfile.ZipFile(path) as bundle:
            members = [m for m in bundle.namelist() if m.endswith(".nc")]
            if len(members) != 1:
                msg = f"{path.name}: expected one netCDF member, found {members}"
                raise ValueError(msg)
            extracted.write_bytes(bundle.read(members[0]))
        log.info("unwrapped %s -> %s", path.name, extracted.name)
    return extracted


def _locate(point: Point, path: Path) -> list[Located]:
    """Match the centroid onto the grid, minding ERA5-Land's 0-360 longitudes.

    The single-levels product returns the requested box in -180..180; ERA5-Land returns the
    same box in 0..360, and a western-hemisphere point compared raw sits an ocean away from
    every cell. The point is shifted to the file's own convention, never the file to ours.
    """
    import numpy as np  # noqa: PLC0415 -- gridded drivers only
    import xarray as xr  # noqa: PLC0415 -- gridded drivers only

    dataset = xr.open_dataset(path)
    latitudes = dataset["latitude"].to_numpy()
    longitudes = dataset["longitude"].to_numpy()
    longitude = point.longitude
    if float(longitudes.max()) > ANTIMERIDIAN_DEG and longitude < 0.0:
        longitude += 360.0
    grid_lat, grid_lon = np.meshgrid(latitudes, longitudes, indexing="ij")
    return nearest_cells(grid_lat, grid_lon, [Point(point.site_id, point.latitude, longitude)])
