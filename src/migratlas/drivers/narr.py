"""NCEP NARR winds at radar stations, over OPeNDAP.

Why NARR and not ARCO-ERA5 is `adr/0006`, with the measurements: every array in that bucket is
chunked one-timestep-whole-globe, so a single station-hour of 850 hPa wind costs a 154 MB read.

Two facts about this server shape everything below, both measured rather than assumed:

- **Per-request latency dominates, and striding is what costs.** One station column for a whole
  month -- 6.7 kB -- took 47 s, because the server seeks 240 times into a 92 MB array. The whole
  145-station bounding box for the same period, 1.2 MB, took 2.7 s. So fetch boxes, not points.
- **Responses are capped somewhere above 6 MB.** 120 timesteps of the box returns in 12 s; 240
  dies with `ChunkedEncodingError: Response ended prematurely`. So a month is two requests.
"""

import logging
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

from migratlas.drivers.schema import DRIVER_SAMPLES, DriverKind
from migratlas.features.annotate import Located, Point, bounding_box, match_report, nearest_cells
from migratlas.lake.writer import WriteResult, write_table

if TYPE_CHECKING:
    from datetime import date

    import pyarrow as pa

# December, after which a month range rolls into the next year.
LAST_MONTH: Final = 12

log = logging.getLogger(__name__)

SOURCE_ID: Final = "narr"
BASE: Final = "https://psl.noaa.gov/thredds/dodsC/Datasets/NARR/pressure"

# Eastward and northward wind. Named as the files are.
COMPONENTS: Final[dict[str, str]] = {"uwnd": "wind_u", "vwnd": "wind_v"}
UNIT: Final = "m s-1"

# 925 hPa, index 3 of 1000/975/950/925/900/875/850/... The Dark Ecology profiles integrate 0-3000 m
# above the radar with most mass low, so the reflectivity-weighted velocity sits nearer 750 m than
# the 1500 m of 850 hPa. One level rather than a weighted stack because levels multiply the request
# cost linearly and seven of them would turn a 3 hour extraction into a 26 hour one; the vertical
# sensitivity is measured on a subset instead, by `levels=` below.
LEVEL_HPA: Final = 925
LEVEL_INDEX: Final = 3

# The server's ceiling, found by bisection. 15 days per request, two requests per month.
MAX_STEPS: Final = 120

# NARR is 3-hourly on 00/03/.../21 UTC, so these are indices 0-3 within each day. For the
# contiguous US these span roughly 19:00-05:00 local, which is when the daily product's "night"
# sits.
NIGHT_HOURS: Final[tuple[int, ...]] = (0, 3, 6, 9)

# A night that begins on the local evening of date D carries its 00-09 UTC hours on D+1, so the
# wind for the radar night labelled D comes from the *next* UTC day. Rows are written under the
# radar night's own label, shifted by this, so that a join on date is correct by construction
# rather than by every consumer remembering the convention.
#
# Established rather than reasoned into place. `align_offset` swept -3..+2 on September 2015 and
# both the median airspeed and its spread trace a clean V with its minimum here: -2 gives
# 8.55 m/s and sd 5.00, -1 gives 7.47 and 4.34, 0 gives 8.57 and 5.34, +1 gives 10.03 and 5.73.
# Pairing a night's scatterer velocity with another night's wind can only inflate both, so the
# minimum is the alignment. Worth the check: the wrong offset does not fail, it quietly adds
# wind variance to every airspeed, which is the direction that hides a composition trend.
UTC_DAY_TO_RADAR_NIGHT: Final = -1


def stations_from(frame: pl.DataFrame) -> list[Point]:
    """One point per station, from any frame carrying station id and position."""
    unique = (
        frame.group_by("station_id")
        .agg(pl.col("station_latitude").first(), pl.col("station_longitude").first())
        .sort("station_id")
    )
    return [
        Point(
            site_id=row["station_id"],
            latitude=row["station_latitude"],
            longitude=row["station_longitude"],
        )
        for row in unique.iter_rows(named=True)
    ]


def _open(component: str, year: int, month: int) -> object:
    import xarray as xr  # noqa: PLC0415 -- an optional extra, needed only for gridded drivers

    # pydap logs every request URL at INFO, which buries the run's own progress under hundreds
    # of lines. Same reasoning as the httpx logger in ingest/http.py, minus the secret.
    logging.getLogger("pydap").setLevel(logging.WARNING)
    return xr.open_dataset(f"{BASE}/{component}.{year}{month:02d}.nc", engine="pydap")


def locate(points: list[Point]) -> list[Located]:
    """Match stations to NARR cells, using any month's grid -- the grid is fixed."""
    grid = _open("uwnd", 2015, 9)
    latitudes = grid["lat"].to_numpy()  # type: ignore[index]
    longitudes = grid["lon"].to_numpy()  # type: ignore[index]
    located = nearest_cells(latitudes, longitudes, points)
    log.info("NARR grid %s: %s", latitudes.shape, match_report(located))
    return located


def _month_box(
    component: str, year: int, month: int, ys: slice, xs: slice
) -> tuple[np.ndarray, np.ndarray]:
    """One month of one component over the station box, in requests the server will serve."""
    dataset = _open(component, year, month)
    steps = int(dataset["time"].shape[0])  # type: ignore[index]
    times = dataset["time"].to_numpy()  # type: ignore[index]

    pieces = []
    for begin in range(0, steps, MAX_STEPS):
        stop = min(begin + MAX_STEPS, steps)
        pieces.append(
            dataset[component]  # type: ignore[index]
            .isel(time=slice(begin, stop), level=LEVEL_INDEX, y=ys, x=xs)
            .to_numpy()
        )
    return np.concatenate(pieces, axis=0), times


def nightly(
    located: list[Located], year: int, month: int, *, night_hours: tuple[int, ...] = NIGHT_HOURS
) -> pl.DataFrame:
    """Mean night wind at every station, labelled by the radar night it belongs to.

    The date returned is the radar night's own label, not the UTC day the hours came from --
    see `UTC_DAY_TO_RADAR_NIGHT`. That means the first night of a month is attributed to the
    last night of the previous one, so a month fetched in isolation loses one night at each
    end; a full run has neighbouring months to supply them.

    Returns long format keyed by variable, which is what `DRIVER_SAMPLES` wants and what keeps
    the set of drivers open.
    """
    ys, xs = bounding_box(located)
    frames = []
    for component, variable in COMPONENTS.items():
        values, times = _month_box(component, year, month, ys, xs)
        stamps = pl.Series("time", times).cast(pl.Datetime("ms", time_zone="UTC"))
        hours = stamps.dt.hour().to_numpy()
        dates = stamps.dt.date().to_numpy()

        keep = np.isin(hours, night_hours)
        if not keep.any():
            msg = f"{component} {year}-{month:02d}: no timesteps at hours {night_hours}"
            raise ValueError(msg)

        # One column per station, pulled out of the box by its offset within it.
        for item in located:
            column = values[keep, item.y - ys.start, item.x - xs.start]
            frames.append(
                pl.DataFrame({"utc_day": dates[keep], "value": column.astype(np.float64)})
                .group_by("utc_day")
                .agg(pl.col("value").mean())
                .with_columns(
                    date=pl.col("utc_day").dt.offset_by(f"{UTC_DAY_TO_RADAR_NIGHT}d"),
                )
                .drop("utc_day")
                .with_columns(
                    site_id=pl.lit(item.site_id),
                    variable=pl.lit(f"{variable}_{LEVEL_HPA}hPa"),
                    longitude=pl.lit(item.longitude),
                    latitude=pl.lit(item.latitude),
                )
            )
    return pl.concat(frames)


def to_samples(nights: pl.DataFrame) -> pa.Table:
    """Driver rows, marked GRIDDED so they can never be confused with a measured reading."""
    out = nights.select(
        source_id=pl.lit(SOURCE_ID),
        site_id=pl.col("site_id"),
        period_start=pl.col("date").cast(pl.Datetime("ms", time_zone="UTC")),
        longitude=pl.col("longitude").cast(pl.Float64),
        latitude=pl.col("latitude").cast(pl.Float64),
        # DRIVER_SAMPLES carries depth but no height, which is a marine assumption showing
        # through. The level is in the variable name until the schema grows a vertical
        # coordinate that works for both realms.
        depth_m=pl.lit(None, dtype=pl.Float64),
        variable=pl.col("variable"),
        value=pl.col("value").cast(pl.Float64),
        unit=pl.lit(UNIT),
        kind=pl.lit(DriverKind.GRIDDED.value),
        # Says what a row is, so a reader does not have to infer the level, the aggregation or
        # the date convention from the pipeline.
        derived_from=pl.lit(f"narr:{LEVEL_HPA}hPa:night_mean:utc_day{UTC_DAY_TO_RADAR_NIGHT:+d}"),
    ).drop_nulls("value")
    schema = DRIVER_SAMPLES.schema
    return out.select(schema.names).to_arrow().cast(schema)


def months_between(
    start: date, end: date, *, only: tuple[int, ...] | None = None
) -> list[tuple[int, int]]:
    """Every (year, month) in range, optionally restricted to given calendar months."""
    wanted = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        if only is None or month in only:
            wanted.append((year, month))
        year, month = (year + 1, 1) if month == LAST_MONTH else (year, month + 1)
    return wanted


def ingest(
    points: list[Point], start: date, end: date, *, only: tuple[int, ...] | None = None
) -> WriteResult:
    """Fetch, reshape and land night winds for a point set over a date range."""
    located = locate(points)
    wanted = months_between(start, end, only=only)
    log.info("%d months to fetch, %d requests", len(wanted), len(wanted) * len(COMPONENTS) * 2)

    frames = []
    for index, (year, month) in enumerate(wanted, start=1):
        try:
            frames.append(nightly(located, year, month))
        except Exception as error:
            log.warning(
                "  %d-%02d skipped: %s: %s", year, month, type(error).__name__, str(error)[:90]
            )
            continue
        if index % 10 == 0 or index == len(wanted):
            log.info("  %d/%d months", index, len(wanted))

    if not frames:
        msg = "no months could be fetched"
        raise RuntimeError(msg)

    table = to_samples(pl.concat(frames))
    log.info("%d driver samples", table.num_rows)
    return write_table(table, DRIVER_SAMPLES, source_id=SOURCE_ID)


def align_offset(
    radar: pl.DataFrame, winds: pl.DataFrame, offsets: tuple[int, ...] = (-1, 0, 1)
) -> pl.DataFrame:
    """Which date offset between the radar's night label and NARR's UTC day is right.

    The daily product identifies a night by date without publishing the window's boundaries, and
    a night that starts on local evening D carries most of its UTC hours on D+1. Getting this
    wrong would not fail loudly -- it would add noise and shrink every airspeed difference
    towards the wind speed, which is exactly the direction that would make a real composition
    trend look like nothing.

    So it is measured. The correct offset is the one whose airspeed distribution is tightest,
    because pairing a night's scatterer velocity with the wrong night's wind can only add
    variance.
    """
    rows = []
    for offset in offsets:
        shifted = winds.with_columns(
            date=pl.col("date").dt.offset_by(f"{offset}d") if offset else pl.col("date")
        )
        joined = radar.join(shifted, on=("station_id", "date"), how="inner")
        if joined.is_empty():
            continue
        airspeed = np.hypot(
            joined["u_radar"].to_numpy() - joined["wind_u"].to_numpy(),
            joined["v_radar"].to_numpy() - joined["wind_v"].to_numpy(),
        )
        rows.append(
            {
                "offset_days": offset,
                "nights": joined.height,
                "median_airspeed": float(np.median(airspeed)),
                "iqr": float(np.subtract(*np.percentile(airspeed, [75, 25]))),
                "sd": float(np.std(airspeed)),
            }
        )
    return pl.DataFrame(rows)
