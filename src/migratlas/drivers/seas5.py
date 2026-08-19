"""SEAS5's June issues over the radar band: the rehearsal's archived forecasts.

`phase3d-rehearsal.md` licenses exactly this: the June issue of each target year, monthly-mean
2 m temperature and total precipitation, lead months 1-6, ensemble-meaned and sampled at the
radar stations. Nothing here may be corrected against observations from after an issue date —
the point is what the forecast said, not what it should have said.

A sibling of `era5_land.py` in the same way that module is a sibling of `era5.py`: `wait`,
`locate`, the request-tag rule and the zip unwrap are imported; only the request payload, which
speaks the seasonal dataset's dialect (originating centre, system, issue month, lead months),
is its own.
"""

import logging
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.config import get_settings
from migratlas.constants import TARGET_YEARS  # fetch and grade share the years
from migratlas.drivers.era5 import CONUS_AREA, Area, RetrievalError, request_tag, wait
from migratlas.drivers.era5 import Field as Era5Field
from migratlas.drivers.era5_land import _unwrap
from migratlas.drivers.schema import DRIVER_SAMPLES, DriverKind
from migratlas.lake.writer import WriteResult, write_table

if TYPE_CHECKING:
    from pathlib import Path

    from migratlas.features.annotate import Located

log = logging.getLogger(__name__)

SOURCE_ID: Final = "seas5"
API: Final = "https://cds.climate.copernicus.eu/api"
DATASET: Final = "seasonal-monthly-single-levels"

ISSUE_MONTH: Final = 6
LEAD_MONTHS: Final = (1, 2, 3, 4, 5, 6)
"""June's leads 1-6 are June through November: the pre-season and the season in one issue."""

"""The real-time SEAS5 era, so every forecast is one the world actually received."""

FIELDS: Final[dict[str, Era5Field]] = {
    "temperature": Era5Field(
        cds_name="2m_temperature",
        canonical="seas5_air_temperature_2m",
        unit="degC",
        offset=-273.15,
    ),
    "precipitation": Era5Field(
        cds_name="total_precipitation",
        # The seasonal product serves a precipitation *rate* (m/s); scaled to mm/day so the
        # unit matches what a consumer expects from the name.
        canonical="seas5_total_precipitation",
        unit="mm day-1",
        scale=86_400_000.0,
    ),
}


def submit(field: Era5Field, years: list[int], *, area: Area = CONUS_AREA) -> str:
    """Queue one seasonal request: ECMWF SEAS5 only, June issues, leads 1-6."""
    import httpx  # noqa: PLC0415 -- only gridded drivers need it here

    payload = {
        "inputs": {
            "originating_centre": "ecmwf",
            "system": "51",
            "variable": [field.cds_name],
            "product_type": ["monthly_mean"],
            "year": [str(year) for year in years],
            "month": [f"{ISSUE_MONTH:02d}"],
            "leadtime_month": [str(lead) for lead in LEAD_MONTHS],
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
            "CDS refused the request: accept the licence once at "
            f"https://cds.climate.copernicus.eu/datasets/{DATASET}?tab=download#manage-licences"
        )
        raise RetrievalError(msg)
    response.raise_for_status()
    job = response.json()
    log.info("CDS job %s accepted (%s, %d issues)", job["jobID"], field.cds_name, len(years))
    return str(job["jobID"])


def download(field: Era5Field, href: str, tag: str) -> Path:
    from migratlas.ingest.http import RemoteFile, fetch  # noqa: PLC0415 -- avoids a cycle

    name = f"{DATASET}-{field.cds_name}-{tag}.nc"
    return fetch(RemoteFile(url=href, name=name), SOURCE_ID)


def fetch_issues(field_name: str) -> Path:
    """The archive file for one field, all target years' June issues, unwrapped."""
    field = FIELDS[field_name]
    years = list(TARGET_YEARS)
    tag = request_tag(field, years, [ISSUE_MONTH], CONUS_AREA)
    return _unwrap(download(field, wait(submit(field, years)), tag))


def ensemble_monthly(field: Era5Field, path: Path, located: list[Located]) -> pl.DataFrame:
    """Ensemble-mean monthly values per station: issue year, valid month, value.

    The seasonal file carries an ensemble dimension the deterministic products lack; the mean
    over members is the registered forecast, taken here so nothing downstream ever sees a
    member and mistakes spread handling for a modelling choice.
    """
    import xarray as xr  # noqa: PLC0415 -- gridded drivers only

    dataset = xr.open_dataset(path)
    array = dataset[next(iter(dataset.data_vars))]
    member_dims = [d for d in ("number", "realization", "member") if d in array.dims]
    if member_dims:
        array = array.mean(dim=member_dims[0])
    time_name = next(
        d for d in ("forecast_reference_time", "time", "indexing_time") if d in array.dims
    )
    lead_name = next(
        (
            d
            for d in ("forecastMonth", "leadtime_month", "forecast_month", "valid_time")
            if d in array.dims
        ),
        None,
    )

    frames = []
    for item in located:
        column = array.isel(latitude=item.y, longitude=item.x)
        issues = pl.Series("issue", dataset[time_name].to_numpy()).cast(
            pl.Datetime("ms", time_zone="UTC")
        )
        for index, issue in enumerate(issues):
            values = column.isel({time_name: index}).to_numpy().astype(np.float64).ravel()
            leads = list(LEAD_MONTHS)[: len(values)]
            frames.append(
                pl.DataFrame(
                    {
                        "issue": [issue] * len(leads),
                        "lead_month": leads,
                        "value": values * field.scale + field.offset,
                        "site_id": [item.site_id] * len(leads),
                        "longitude": [item.longitude] * len(leads),
                        "latitude": [item.latitude] * len(leads),
                    }
                )
            )
    del lead_name  # the lead axis is positional after the issue selection; named dims vary
    return pl.concat(frames)


def to_samples(field: Era5Field, months: pl.DataFrame) -> pl.DataFrame:
    """Driver rows: period_start is the VALID month (issue June + lead - 1), kind simulated.

    `derived_from` carries the issue date, because a forecast value without its issue date is
    a number with no epistemic address.
    """
    return months.select(
        source_id=pl.lit(SOURCE_ID),
        site_id=pl.col("site_id"),
        period_start=pl.col("issue").dt.offset_by(pl.format("{}mo", pl.col("lead_month") - 1)),
        longitude=pl.col("longitude").cast(pl.Float64),
        latitude=pl.col("latitude").cast(pl.Float64),
        depth_m=pl.lit(None, dtype=pl.Float64),
        variable=pl.lit(field.canonical),
        value=pl.col("value").cast(pl.Float64),
        unit=pl.lit(field.unit),
        # SIMULATED, not GRIDDED: a forecast is a modelled future, not a measurement estimate,
        # and the schema's own docstring names exactly this distinction.
        kind=pl.lit(DriverKind.SIMULATED.value),
        derived_from=pl.format("SEAS5 June issue {}", pl.col("issue").dt.year()),
    )


def ingest(root: Path | None = None) -> WriteResult:
    """Both fields, all June issues 2017-2024, one write."""
    from migratlas.drivers.era5 import locate  # noqa: PLC0415 -- gridded drivers only
    from migratlas.drivers.narr import stations_from  # noqa: PLC0415
    from migratlas.reports.phase1 import load_conus_nights  # noqa: PLC0415 -- heavy

    catalog.admit(SOURCE_ID)
    points = stations_from(load_conus_nights())
    frames = []
    for name, field in FIELDS.items():
        path = fetch_issues(name)
        located = locate(points, path)
        frames.append(to_samples(field, ensemble_monthly(field, path, located)))
        log.info("%s: %d forecast station-months", name, frames[-1].height)
    table = pl.concat(frames)
    schema = DRIVER_SAMPLES.schema
    return write_table(
        table.select(schema.names).to_arrow().cast(schema),
        DRIVER_SAMPLES,
        source_id=SOURCE_ID,
        root=root,
    )
