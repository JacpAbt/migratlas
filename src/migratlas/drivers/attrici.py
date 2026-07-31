"""ISIMIP3a factual and counterfactual near-surface temperature, as a matched pair.

The second counterfactual, and a different question from the first. CMIP6 DAMIP asks *what if there
had been no human forcing* and answers it by running models without it. ATTRICI asks *what if there
had been no warming* and answers it by removing, from an observational product, the part of each
daily series that correlates with global mean temperature -- quantile-preserving, so internal
variability survives, and carrying no model bias because no model made it.

Pre-registration and the reason both are worth having: `docs/methods/phase2a-attrici.md`.

**Both scenarios land in one ingest, and that is not a convenience.** The factual half is the
control that licenses using the counterfactual at all: if `obsclim` disagrees with the ERA5 warming
already in the lake at the same stations, the pair describes a different place and nothing
downstream is trustworthy. Writing them separately would also delete one from every year they
share, which is the partition-replace constraint that already shaped `era5.ingest`.

**A box, not points.** `select_point` works and costs 243 KB for nine years at one station, which
would be 78 jobs. `select_bbox` over the radar footprint is 39 MB per decade-file and one job for
all six, after which stations are matched onto the grid locally as `era5.locate` does. ADR 0006's
ARCO-ERA5 problem does not recur here: ISIMIP subsets server-side, so the cost is proportional to
what was asked for rather than to the chunk it happens to live in.
"""

from __future__ import annotations

import logging
import time
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Final, NamedTuple

import httpx
import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.drivers.schema import DRIVER_SAMPLES, DriverKind
from migratlas.lake.writer import write_table

if TYPE_CHECKING:
    import pyarrow as pa

    from migratlas.features.annotate import Located, Point
    from migratlas.lake.writer import WriteResult

log = logging.getLogger(__name__)

SOURCE_ID: Final = "isimip3a"

API: Final = "https://files.isimip.org/api/v2"

TREE: Final = (
    "ISIMIP3a/InputData/climate/atmosphere/{scenario}/global/daily/historical/GSWP3-W5E5/"
    "gswp3-w5e5_{scenario}_tas_global_daily_{span}.nc"
)

# The decade files as ISIMIP cuts them. The last is nine years, not ten: `counterclim` ends in 2019
# while the radar record runs to 2025, so any claim built here covers 25 of its 31 years and has to
# say which. Same shape of mismatch as DAMIP's `historical` stopping in 2014.
SPANS: Final[tuple[tuple[str, int, int], ...]] = (
    ("1901_1910", 1901, 1910),
    ("1911_1920", 1911, 1920),
    ("1921_1930", 1921, 1930),
    ("1931_1940", 1931, 1940),
    ("1941_1950", 1941, 1950),
    ("1951_1960", 1951, 1960),
    ("1961_1970", 1961, 1970),
    ("1971_1980", 1971, 1980),
    ("1981_1990", 1981, 1990),
    ("1991_2000", 1991, 2000),
    ("2001_2010", 2001, 2010),
    ("2011_2019", 2011, 2019),
)

LAST_YEAR: Final = 2019
"""Where the counterfactual stops, so a report can state the window rather than assume it."""


class Scenario(NamedTuple):
    """One half of the pair, and what it is ontologically.

    `kind` is the load-bearing field. `obsclim` is an estimate of what the atmosphere did, so it is
    GRIDDED like any reanalysis. `counterclim` is what the atmosphere *would* have done without the
    warming, so it is SIMULATED -- a climate that never happened. That enum's docstring says "output
    of a climate model", which this is not: no model made it, a statistical detrending of
    observations did. The distinction the enum actually draws is ontological rather than about
    provenance, which is why this fits, and the docstring has been widened to say so.
    """

    name: str
    canonical: str
    kind: DriverKind
    note: str


SCENARIOS: Final[dict[str, Scenario]] = {
    "obsclim": Scenario(
        name="obsclim",
        canonical="air_temperature_2m",
        kind=DriverKind.GRIDDED,
        note="factual, bias-adjusted GSWP3-W5E5",
    ),
    "counterclim": Scenario(
        name="counterclim",
        # A separate variable name rather than a scenario column, because DRIVER_SAMPLES has no
        # scenario field and `derived_from` is free text nobody should be filtering on. Two names
        # make "which climate is this" a join condition instead of a string match.
        canonical="air_temperature_2m_counterfactual",
        kind=DriverKind.SIMULATED,
        note="counterfactual, ATTRICI v1.1 detrending of obsclim",
    ),
}

# West, east, south, north -- the order CDO takes and the order this API passes through. The radar
# network's own extent, matching `era5.CONUS_AREA` so the two panels sample the same box.
CONUS_BBOX: Final[tuple[float, float, float, float]] = (-125.0, -66.0, 24.0, 50.0)

POLL_SECONDS: Final = 10.0
POLL_LIMIT: Final = 90


class RetrievalError(RuntimeError):
    """The job did not produce a file."""


def spans_for(years: list[int]) -> list[tuple[str, int, int]]:
    """The decade files that cover the requested years, and only those."""
    wanted = set(years)
    return [span for span in SPANS if wanted & set(range(span[1], span[2] + 1))]


def paths_for(years: list[int], scenarios: tuple[str, ...]) -> list[str]:
    """Every file one job needs. Refuses silently-empty requests rather than submitting them."""
    spans = spans_for(years)
    if not spans:
        msg = f"no ISIMIP3a decade file covers {min(years)}-{max(years)}; it ends at {LAST_YEAR}"
        raise RetrievalError(msg)
    return [
        TREE.format(scenario=SCENARIOS[name].name, span=span[0])
        for name in scenarios
        for span in spans
    ]


def submit(paths: list[str], bbox: tuple[float, float, float, float] = CONUS_BBOX) -> str:
    """Ask for a box out of each file. Returns a job id."""
    response = httpx.post(
        API,
        json={
            "paths": paths,
            "operations": [{"operation": "select_bbox", "bbox": list(bbox)}],
        },
        timeout=120.0,
    )
    response.raise_for_status()
    body = response.json()
    if body.get("status") == "error":
        # The API validates before queueing and says which field is wrong -- passing a point as
        # [lon, lat] answers "latitude is < -90" rather than quietly returning the wrong cell.
        msg = f"ISIMIP refused the request: {body.get('errors')}"
        raise RetrievalError(msg)
    job = body.get("id")
    if not job:
        msg = f"no job id in {body}"
        raise RetrievalError(msg)
    log.info("ISIMIP job %s queued for %d file(s)", job[:12], len(paths))
    return str(job)


def wait(job: str) -> str:
    """Poll until the zip exists, and return its URL."""
    for attempt in range(POLL_LIMIT):
        response = httpx.get(f"{API}/{job}", timeout=60.0)
        response.raise_for_status()
        body = response.json()
        status = body.get("status")
        if status == "finished":
            errors = (body.get("meta") or {}).get("errors") or {}
            if errors:
                msg = f"job {job} finished with errors: {errors}"
                raise RetrievalError(msg)
            log.info("ISIMIP job %s finished: %s files", job[:12], body["meta"]["created_files"])
            return str(body["file_url"])
        if status in {"failed", "error"}:
            msg = f"job {job} {status}: {body}"
            raise RetrievalError(msg)
        if attempt % 6 == 0:
            log.info("  %s after %.0fs", status, attempt * POLL_SECONDS)
        time.sleep(POLL_SECONDS)

    msg = f"job {job} still {status} after {POLL_LIMIT * POLL_SECONDS:.0f}s"
    raise RetrievalError(msg)


def download(url: str, into: Path) -> list[Path]:
    """Fetch the zip and expand it. Returns the NetCDF files, in the order ISIMIP named them."""
    into.mkdir(parents=True, exist_ok=True)
    archive = into / "isimip.zip"
    with httpx.stream("GET", url, timeout=600.0, follow_redirects=True) as response:
        response.raise_for_status()
        with archive.open("wb") as handle:
            for chunk in response.iter_bytes(1 << 20):
                handle.write(chunk)
    log.info("%.1f MiB downloaded", archive.stat().st_size / (1 << 20))

    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(into)
    return sorted(path for path in into.rglob("*.nc"))


def locate(points: list[Point], path: Path) -> list[Located]:
    """Match stations onto the ISIMIP grid, using the downloaded file's own coordinates.

    Half a degree, so a station-point sample is a cell mean over roughly 50 km. Coarser than NARR's
    32 km and finer than CMIP6's 1-2 degrees; a report should call it regional, not local.
    """
    import numpy as np  # noqa: PLC0415 -- only gridded drivers need it
    import xarray as xr  # noqa: PLC0415 -- an optional extra

    from migratlas.features.annotate import nearest_cells  # noqa: PLC0415

    dataset = xr.open_dataset(path, engine="h5netcdf")
    latitudes = dataset["lat"].to_numpy()
    longitudes = dataset["lon"].to_numpy()
    # Broadcast the axes into the 2-D form nearest_cells expects, as era5.locate does: the function
    # takes coordinate arrays rather than axes because NARR is Lambert Conformal and has no
    # latitude axis to search.
    grid_lat, grid_lon = np.meshgrid(latitudes, longitudes, indexing="ij")
    return nearest_cells(grid_lat, grid_lon, points)


def daily(path: Path, located: list[Located]) -> pl.DataFrame:
    """Station-days out of one decade file."""
    import numpy as np  # noqa: PLC0415
    import xarray as xr  # noqa: PLC0415

    dataset = xr.open_dataset(path, engine="h5netcdf")
    array = dataset["tas"]
    times = pl.Series("period_start", dataset["time"].to_numpy()).cast(pl.Date)

    frames = []
    for item in located:
        # Kelvin in, celsius out, converted here rather than left to whatever reads the table --
        # the same reason `era5.Field` carries its own offset.
        column = array.isel(lat=item.y, lon=item.x).to_numpy().astype(np.float64) - 273.15
        frames.append(
            pl.DataFrame(
                {
                    "site_id": [item.site_id] * len(times),
                    "period_start": times,
                    # The matched *cell* centre, not the station, matching what era5 records: the
                    # value is a cell mean and pretending it sits at the station would misstate
                    # where a 0.5-degree average applies. `Located.error_km` carries the distance.
                    "longitude": [item.longitude] * len(times),
                    "latitude": [item.latitude] * len(times),
                    "value": column,
                }
            )
        )
    return pl.concat(frames)


def to_samples(scenario: Scenario, days: pl.DataFrame) -> pa.Table:
    """Driver rows, carrying the scenario in the variable name and its ontology in `kind`."""
    out = days.select(
        source_id=pl.lit(SOURCE_ID),
        site_id=pl.col("site_id"),
        period_start=pl.col("period_start"),
        longitude=pl.col("longitude").cast(pl.Float64),
        latitude=pl.col("latitude").cast(pl.Float64),
        depth_m=pl.lit(None, dtype=pl.Float64),
        variable=pl.lit(scenario.canonical),
        value=pl.col("value").cast(pl.Float64),
        unit=pl.lit("degC"),
        kind=pl.lit(scenario.kind.value),
        derived_from=pl.lit(f"gswp3-w5e5:{scenario.name} — {scenario.note}"),
    ).drop_nulls("value")
    schema = DRIVER_SAMPLES.schema
    return out.select(schema.names).to_arrow().cast(schema)


def ingest(
    points: list[Point],
    years: list[int],
    *,
    scenarios: tuple[str, ...] = ("obsclim", "counterclim"),
    root: Path | None = None,
    cache: Path | None = None,
) -> WriteResult:
    """Fetch both climates for a point set and land them in one write.

    One job for every file, because the API takes a list of paths and one bbox operation, and
    because both scenarios have to land together: a second write would delete the first from every
    year they share. The default is both, since asking for the counterfactual alone would land a
    climate that never happened with nothing to check it against.
    """
    import pyarrow as pa  # noqa: PLC0415

    catalog.admit(SOURCE_ID)
    if len(scenarios) == 1:
        log.warning(
            "requesting %s alone: the pair is the control, and one half cannot be validated",
            scenarios[0],
        )

    into = cache or Path("~/migratlas-data/scratch/isimip3a").expanduser()
    files = download(wait(submit(paths_for(years, scenarios))), into)
    log.info("%d file(s) extracted", len(files))

    located: list[Located] = []
    tables = []
    for name in scenarios:
        scenario = SCENARIOS[name]
        # ISIMIP names the output after the input, so the scenario is in the filename. Matching on
        # it rather than on position: a job that returned files in another order would otherwise
        # label the counterfactual as factual, which is the one mistake here that must not be quiet.
        mine = [path for path in files if f"_{scenario.name}_" in path.name]
        if not mine:
            msg = f"no file for {scenario.name} among {[p.name for p in files]}"
            raise RetrievalError(msg)

        if not located:
            located = locate(points, mine[0])
            log.info("ISIMIP grid: %d of %d stations matched", len(located), len(points))

        frame = pl.concat([daily(path, located) for path in mine])
        frame = frame.filter(pl.col("period_start").dt.year().is_in(years))
        log.info("  %s: %d station-days", scenario.canonical, frame.height)
        tables.append(to_samples(scenario, frame))

    table = pa.concat_tables(tables)
    log.info("%d driver samples across %d scenario(s)", table.num_rows, len(scenarios))
    return write_table(table, DRIVER_SAMPLES, source_id=SOURCE_ID, root=root)
