"""ERA5 monthly fields from the Copernicus Climate Data Store.

Complements `narr`, which is the wind field for North America and stops at the continent. ERA5 is
global, so it is what a European or southern-hemisphere network will need, and it is an
*independent* record of the same atmosphere -- which is the point of its first use here: whether
the radar dataset's 2012 precipitation-screening step is weather or instrument.

CDS is a queue, not a file server. A request is submitted, a job id comes back, and the result
appears when the queue gets to it -- so this polls rather than streams, and a run can legitimately
sit waiting.

Two things about access, both learned by hitting them:

- The personal access token is necessary but not sufficient. Each dataset's licence must be
  accepted once from its download tab, or every retrieval returns 403 "required licences not
  accepted" no matter how valid the token is.
- The licence to accept is **`cc-by`**, not `licence-to-use-copernicus-products`. ERA5 moved to
  CC-BY-4.0 and accepting the older Copernicus licence does not satisfy it.
"""

import hashlib
import logging
from typing import TYPE_CHECKING, Final, NamedTuple

import numpy as np
import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.config import get_settings
from migratlas.drivers.schema import DRIVER_SAMPLES, DriverKind
from migratlas.features.annotate import Located, Point, nearest_cells
from migratlas.lake.writer import WriteResult, write_table

if TYPE_CHECKING:
    from pathlib import Path

    import pyarrow as pa

log = logging.getLogger(__name__)

SOURCE_ID: Final = "era5"
API: Final = "https://cds.climate.copernicus.eu/api"
DATASET: Final = "reanalysis-era5-single-levels-monthly-means"


class Field(NamedTuple):
    """One ERA5 variable, with what it has to become before it enters the lake.

    `scale` and `offset` are applied on the way in rather than left to whatever reads the driver
    table. Precipitation arrives in metres, which invites a factor-of-1000 error downstream, and
    temperature arrives in kelvin, which invites a subtraction someone forgets.
    """

    cds_name: str
    canonical: str
    unit: str
    scale: float = 1.0
    offset: float = 0.0


FIELDS: Final[dict[str, Field]] = {
    "precipitation": Field(
        cds_name="total_precipitation",
        canonical="total_precipitation",
        unit="mm day-1",
        # Metres of water equivalent per day in the monthly-mean product.
        scale=1000.0,
    ),
    "temperature": Field(
        cds_name="2m_temperature",
        canonical="air_temperature_2m",
        unit="degC",
        offset=-273.15,
    ),
}

# North, west, south, east -- the order CDS wants, which is not the order anyone says them in.
Area = tuple[float, float, float, float]

# The radar network's own extent, so the request is small.
CONUS_AREA: Final[Area] = (50.0, -125.0, 24.0, -66.0)

# The SABAP atlas footprint with a degree of margin, for the transfer test's southern leg. North is
# the *less negative* latitude here, which is the one thing about this tuple worth stating: a
# southern box written north-first reads backwards to anyone used to the CONUS one above it.
SABAP_AREA: Final[Area] = (-21.0, 17.0, -36.0, 34.0)

POLL_SECONDS: Final = 15.0
POLL_LIMIT: Final = 240
"""One hour of waiting. A monthly-mean request for one variable is usually served from cache in
under a minute; the ceiling exists so a queue backlog fails with a message rather than hanging."""


class RetrievalError(RuntimeError):
    """A CDS request could not be completed. Carries the reason, never the token."""


def _headers() -> dict[str, str]:
    return {"PRIVATE-TOKEN": get_settings().credential("cds_token")}


def submit(
    field: Field,
    years: list[int],
    months: list[int],
    *,
    area: Area = CONUS_AREA,
) -> str:
    """Queue one request and return its job id.

    The area defaults to CONUS because that is what every caller wanted until the transfer
    test needed a southern box. It is a parameter rather than a second function because the
    request is otherwise identical, and two near-copies drift.
    """
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
        headers={**_headers(), "Content-Type": "application/json"},
        json=payload,
        timeout=120.0,
        follow_redirects=True,
    )
    if response.status_code == 403:  # noqa: PLR2004 -- the one status worth naming
        msg = (
            "CDS refused the request: the dataset licence has not been accepted. Accept the "
            f"`cc-by` licence once at https://cds.climate.copernicus.eu/datasets/{DATASET}"
            "?tab=download#manage-licences -- the token alone is not enough, and the older "
            "`licence-to-use-copernicus-products` does not cover ERA5."
        )
        raise RetrievalError(msg)
    response.raise_for_status()
    job = response.json()
    log.info("CDS job %s accepted (%d years x %d months)", job["jobID"], len(years), len(months))
    return str(job["jobID"])


def wait(job_id: str) -> str:
    """Poll until the job succeeds, and return the URL of its result."""
    from time import sleep  # noqa: PLC0415 -- only the poll loop needs it

    import httpx  # noqa: PLC0415 -- only gridded drivers need it here

    for attempt in range(POLL_LIMIT):
        response = httpx.get(
            f"{API}/retrieve/v1/jobs/{job_id}",
            headers=_headers(),
            timeout=60.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        status = response.json().get("status")
        if status == "successful":
            results = httpx.get(
                f"{API}/retrieve/v1/jobs/{job_id}/results",
                headers=_headers(),
                timeout=60.0,
                follow_redirects=True,
            )
            results.raise_for_status()
            return str(results.json()["asset"]["value"]["href"])
        if status in {"failed", "dismissed"}:
            msg = f"CDS job {job_id} ended as {status}"
            raise RetrievalError(msg)
        if attempt % 4 == 0:
            log.info("  job %s: %s (%.0fs elapsed)", job_id, status, attempt * POLL_SECONDS)
        sleep(POLL_SECONDS)

    msg = f"CDS job {job_id} still queued after {POLL_LIMIT * POLL_SECONDS / 60:.0f} minutes"
    raise RetrievalError(msg)


def request_tag(field: Field, years: list[int], months: list[int], area: Area) -> str:
    """A short, stable label for exactly this request.

    The archive caches on the filename, and the filename used to carry only the variable. So a
    request for a different *region* found the previous region's file already present, skipped the
    download, and sampled the wrong continent -- silently, because a nearest cell exists for every
    point. Everything that distinguishes one request from another belongs in the name.
    """
    key = repr((field.cds_name, sorted(years), sorted(months), area))
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def download(field: Field, href: str, tag: str) -> Path:
    """Fetch the result into the raw archive, exactly as served."""
    from migratlas.ingest.http import RemoteFile, fetch  # noqa: PLC0415 -- avoids a cycle

    name = f"{DATASET}-{field.cds_name}-{tag}.nc"
    return fetch(RemoteFile(url=href, name=name), SOURCE_ID)


def monthly(field: Field, path: Path, located: list[Located]) -> pl.DataFrame:
    """One monthly field at each station, from the downloaded grid.

    ERA5 is a regular latitude/longitude grid, so `nearest_cells` sees it as a degenerate
    curvilinear one -- the same code that matches stations onto NARR's Lambert Conformal grid,
    which is the reason `features/annotate.py` takes 2-D coordinate arrays rather than axes.
    """
    import xarray as xr  # noqa: PLC0415 -- an optional extra, needed only for gridded drivers

    dataset = xr.open_dataset(path)
    # Named `array`, not `field`: calling it `field` shadowed this function's own Field parameter,
    # and the scale factor silently became an attribute lookup on an xarray DataArray.
    array = dataset[next(iter(dataset.data_vars))]
    # CDS has used `time` and `valid_time` for this product at different points.
    time_name = "valid_time" if "valid_time" in array.dims else "time"

    frames = []
    for item in located:
        column = array.isel(latitude=item.y, longitude=item.x).to_numpy().astype(np.float64)
        stamps = pl.Series("period_start", dataset[time_name].to_numpy()).cast(
            pl.Datetime("ms", time_zone="UTC")
        )
        frames.append(
            pl.DataFrame(
                {
                    "period_start": stamps,
                    "value": np.ravel(column) * field.scale + field.offset,
                    "site_id": [item.site_id] * len(stamps),
                    "longitude": [item.longitude] * len(stamps),
                    "latitude": [item.latitude] * len(stamps),
                }
            )
        )
    return pl.concat(frames)


def to_samples(field: Field, months: pl.DataFrame, source_id: str = SOURCE_ID) -> pa.Table:
    """Driver rows, marked GRIDDED and carrying a monthly rather than nightly period."""
    out = months.select(
        source_id=pl.lit(source_id),
        site_id=pl.col("site_id"),
        period_start=pl.col("period_start"),
        longitude=pl.col("longitude").cast(pl.Float64),
        latitude=pl.col("latitude").cast(pl.Float64),
        depth_m=pl.lit(None, dtype=pl.Float64),
        variable=pl.lit(field.canonical),
        value=pl.col("value").cast(pl.Float64),
        unit=pl.lit(field.unit),
        kind=pl.lit(DriverKind.GRIDDED.value),
        # Monthly, unlike narr's nightly rows, and said so rather than inferred from the dates.
        derived_from=pl.lit(f"{DATASET}:monthly_mean"),
    ).drop_nulls("value")
    schema = DRIVER_SAMPLES.schema
    return out.select(schema.names).to_arrow().cast(schema)


def locate(points: list[Point], path: Path) -> list[Located]:
    """Match stations onto the ERA5 grid, using the downloaded file's own coordinates."""
    import xarray as xr  # noqa: PLC0415 -- an optional extra, needed only for gridded drivers

    dataset = xr.open_dataset(path)
    latitudes = dataset["latitude"].to_numpy()
    longitudes = dataset["longitude"].to_numpy()
    # Broadcast the axes into the 2-D form nearest_cells expects.
    grid_lat, grid_lon = np.meshgrid(latitudes, longitudes, indexing="ij")
    return nearest_cells(grid_lat, grid_lon, points)


def ingest(  # noqa: PLR0913 -- every one names a dimension of the request, and folding them
    # into a config object would hide which of them the caller actually chose.
    points: list[Point],
    years: list[int],
    months: list[int],
    *,
    fields: tuple[str, ...] = ("precipitation",),
    area: Area = CONUS_AREA,
    source_id: str = SOURCE_ID,
    root: Path | None = None,
) -> WriteResult:
    """Fetch, reshape and land monthly fields for a point set.

    Every requested field is written in one call, because the lake replaces the partitions a write
    touches: landing temperature in a second write would delete the precipitation from every year
    they share. Same constraint that shaped `narr.ingest(resume=...)`, arriving from a different
    direction.
    """
    catalog.admit(source_id)
    frames = []
    located: list[Located] = []
    for name in fields:
        field = FIELDS[name]
        tag = request_tag(field, years, months, area)
        path = download(field, wait(submit(field, years, months, area=area)), tag)
        if not located:
            located = locate(points, path)
            log.info("ERA5 grid: %d stations matched", len(located))
        frames.append(monthly(field, path, located))
        log.info("  %s: %d station-months", field.canonical, frames[-1].height)

    import pyarrow as pa  # noqa: PLC0415 -- only this concatenation needs it at runtime

    table = pa.concat_tables(
        [
            to_samples(FIELDS[name], frame, source_id)
            for name, frame in zip(fields, frames, strict=True)
        ]
    )
    log.info("%d driver samples across %d field(s)", table.num_rows, len(fields))
    return write_table(table, DRIVER_SAMPLES, source_id=source_id, root=root)
