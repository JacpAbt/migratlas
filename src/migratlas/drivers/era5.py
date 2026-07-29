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

import logging
from typing import TYPE_CHECKING, Final

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

# Total precipitation, metres of water equivalent per day in the monthly-mean product. Converted
# to millimetres on the way in, because a driver in metres invites a factor-of-1000 error in
# whatever reads it.
VARIABLE: Final = "total_precipitation"
CANONICAL: Final = "total_precipitation"
UNIT: Final = "mm day-1"
M_TO_MM: Final = 1000.0

# North, west, south, east. The radar network's own extent, so the request is small.
CONUS_AREA: Final[tuple[float, float, float, float]] = (50.0, -125.0, 24.0, -66.0)

POLL_SECONDS: Final = 15.0
POLL_LIMIT: Final = 240
"""One hour of waiting. A monthly-mean request for one variable is usually served from cache in
under a minute; the ceiling exists so a queue backlog fails with a message rather than hanging."""


class RetrievalError(RuntimeError):
    """A CDS request could not be completed. Carries the reason, never the token."""


def _headers() -> dict[str, str]:
    return {"PRIVATE-TOKEN": get_settings().credential("cds_token")}


def submit(years: list[int], months: list[int]) -> str:
    """Queue one request and return its job id."""
    import httpx  # noqa: PLC0415 -- only gridded drivers need it here

    payload = {
        "inputs": {
            "product_type": ["monthly_averaged_reanalysis"],
            "variable": [VARIABLE],
            "year": [str(year) for year in years],
            "month": [f"{month:02d}" for month in months],
            "time": ["00:00"],
            "area": list(CONUS_AREA),
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


def download(href: str) -> Path:
    """Fetch the result into the raw archive, exactly as served."""
    from migratlas.ingest.http import RemoteFile, fetch  # noqa: PLC0415 -- avoids a cycle

    name = f"{DATASET}-{VARIABLE}.nc"
    return fetch(RemoteFile(url=href, name=name), SOURCE_ID)


def monthly(path: Path, located: list[Located]) -> pl.DataFrame:
    """Monthly precipitation at each station, from the downloaded grid.

    ERA5 is a regular latitude/longitude grid, so `nearest_cells` sees it as a degenerate
    curvilinear one -- the same code that matches stations onto NARR's Lambert Conformal grid,
    which is the reason `features/annotate.py` takes 2-D coordinate arrays rather than axes.
    """
    import xarray as xr  # noqa: PLC0415 -- an optional extra, needed only for gridded drivers

    dataset = xr.open_dataset(path)
    field = dataset[next(iter(dataset.data_vars))]
    # CDS has used `time` and `valid_time` for this product at different points.
    time_name = "valid_time" if "valid_time" in field.dims else "time"

    frames = []
    for item in located:
        column = field.isel(latitude=item.y, longitude=item.x).to_numpy().astype(np.float64)
        stamps = pl.Series("period_start", dataset[time_name].to_numpy()).cast(
            pl.Datetime("ms", time_zone="UTC")
        )
        frames.append(
            pl.DataFrame(
                {
                    "period_start": stamps,
                    "value": np.ravel(column) * M_TO_MM,
                    "site_id": [item.site_id] * len(stamps),
                    "longitude": [item.longitude] * len(stamps),
                    "latitude": [item.latitude] * len(stamps),
                }
            )
        )
    return pl.concat(frames)


def to_samples(months: pl.DataFrame) -> pa.Table:
    """Driver rows, marked GRIDDED and carrying a monthly rather than nightly period."""
    out = months.select(
        source_id=pl.lit(SOURCE_ID),
        site_id=pl.col("site_id"),
        period_start=pl.col("period_start"),
        longitude=pl.col("longitude").cast(pl.Float64),
        latitude=pl.col("latitude").cast(pl.Float64),
        depth_m=pl.lit(None, dtype=pl.Float64),
        variable=pl.lit(CANONICAL),
        value=pl.col("value").cast(pl.Float64),
        unit=pl.lit(UNIT),
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


def ingest(
    points: list[Point], years: list[int], months: list[int], *, root: Path | None = None
) -> WriteResult:
    """Fetch, reshape and land monthly precipitation for a point set."""
    catalog.admit(SOURCE_ID)
    path = download(wait(submit(years, months)))
    located = locate(points, path)
    log.info("ERA5 grid: %d stations matched", len(located))
    table = to_samples(monthly(path, located))
    log.info("%d driver samples", table.num_rows)
    return write_table(table, DRIVER_SAMPLES, source_id=SOURCE_ID, root=root)
