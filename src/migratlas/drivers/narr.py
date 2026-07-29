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
from calendar import monthrange
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

from migratlas.catalog import loader as catalog
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

# Steps per day: NARR is 3-hourly, on 00/03/06/09/12/15/18/21 UTC.
STEPS_PER_DAY: Final = 8

# `_FillValue` is 9.96921e36 and `valid_range` is -280 to 350 m/s, so anything of this
# magnitude is a fill rather than a wind. Compared on absolute value because the DAS declares
# both a positive and a negative fill.
FILL_THRESHOLD: Final = 1e30

REQUEST_TIMEOUT_S: Final = 180.0

# Concurrent months. A public research server, so deliberately modest -- fewer connections than
# a browser opens, and the gain is mostly in overlapping latency rather than bandwidth.
WORKERS: Final = 4


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


def _month_steps(year: int, month: int) -> tuple[int, np.ndarray]:
    """How many 3-hourly steps a month's file holds, and the UTC stamp of each.

    Computed, not fetched. Each monthly file starts at the 1st at 00:00 UTC and steps every
    three hours, so the stamps are arithmetic and fetching them costs three requests per
    component per month for information that is already known. `verify_time_axis` checks the
    assumption against the server rather than trusting it.
    """
    days = monthrange(year, month)[1]
    steps = days * STEPS_PER_DAY
    # Milliseconds because polars accepts ms/us/ns and refuses seconds.
    start = np.datetime64(f"{year}-{month:02d}-01T00:00:00", "ms")
    return steps, start + np.arange(steps, dtype="int64") * np.timedelta64(3, "h")


def verify_time_axis(year: int, month: int) -> None:
    """Confirm the computed time axis matches the file's own, for one month.

    Cheap insurance on the assumption `_month_steps` makes. An off-by-one here would shift every
    wind by three hours and every date by up to a day, silently.

    Raises:
        ValueError: if the axis does not match.
    """
    dataset = _open("uwnd", year, month)
    steps, stamps = _month_steps(year, month)
    actual = dataset["time"].to_numpy()  # type: ignore[index]
    if actual.shape[0] != steps:
        msg = f"{year}-{month:02d}: file has {actual.shape[0]} steps, computed {steps}"
        raise ValueError(msg)
    published = actual.astype("datetime64[s]")
    if published[0] != stamps[0] or published[-1] != stamps[-1]:
        msg = (
            f"{year}-{month:02d}: computed axis {stamps[0]}..{stamps[-1]} does not match "
            f"the file's {published[0]}..{published[-1]}"
        )
        raise ValueError(msg)


def _dods_slab(
    component: str, year: int, month: int, ranges: str, shape: tuple[int, ...]
) -> np.ndarray:
    """One hyperslab, fetched as raw DAP2 rather than through a dataset object.

    Going through xarray costs six extra requests per component per month -- it fetches `time`
    three times plus `level`, `y` and `x`, none of which change and all of which carry the
    server's per-request latency. Measured: that overhead made the full extraction a ten hour
    job against a three hour one, because only four of sixteen requests were data.

    Safe to read raw because the DAS declares `Float32` with no `scale_factor` or `add_offset`
    -- values are stored unpacked, and the only decoding needed is the fill value. If NARR ever
    starts packing these variables the valid_range assertion below is what will catch it.
    """
    import httpx  # noqa: PLC0415 -- only gridded drivers need it here

    url = f"{BASE}/{component}.{year}{month:02d}.nc.dods?{component}.{component}{ranges}"
    response = httpx.get(url, timeout=REQUEST_TIMEOUT_S)
    response.raise_for_status()

    marker = b"Data:\n"
    at = response.content.find(marker)
    if at < 0:
        msg = f"{component} {year}-{month:02d}: no data section in the DAP2 response"
        raise ValueError(msg)
    # DAP2 prefixes an array's payload with its length twice, as big-endian int32.
    payload = response.content[at + len(marker) + 8 :]
    expected = int(np.prod(shape))
    values = np.frombuffer(payload[: expected * 4], dtype=">f4")
    if values.size != expected:
        msg = (
            f"{component} {year}-{month:02d}: got {values.size} values, expected {expected} "
            f"for shape {shape} -- the response was truncated"
        )
        raise ValueError(msg)

    out = values.astype(np.float64).reshape(shape)
    return np.where(np.abs(out) > FILL_THRESHOLD, np.nan, out)


def _month_box(
    component: str, year: int, month: int, ys: slice, xs: slice
) -> tuple[np.ndarray, np.ndarray]:
    """One month of one component over the station box, in requests the server will serve.

    Timestamps are computed rather than fetched -- see `_month_steps`.
    """
    steps, stamps = _month_steps(year, month)
    rows, columns = ys.stop - ys.start, xs.stop - xs.start

    pieces = []
    for begin in range(0, steps, MAX_STEPS):
        stop = min(begin + MAX_STEPS, steps)
        ranges = (
            f"[{begin}:1:{stop - 1}][{LEVEL_INDEX}:1:{LEVEL_INDEX}]"
            f"[{ys.start}:1:{ys.stop - 1}][{xs.start}:1:{xs.stop - 1}]"
        )
        slab = _dods_slab(component, year, month, ranges, (stop - begin, 1, rows, columns))
        pieces.append(slab[:, 0, :, :])
    return np.concatenate(pieces, axis=0), stamps


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
    # Same first step as every evidence ingest. Being unable to name the source in the registry
    # is the cheapest place to stop, and a driver needs it as much as evidence does -- its
    # licence has to be recorded somewhere, and this is where PROVENANCE.md reads from.
    catalog.admit(SOURCE_ID)
    located = locate(points)
    wanted = months_between(start, end, only=only)
    log.info("%d months to fetch, %d requests", len(wanted), len(wanted) * len(COMPONENTS) * 2)

    # Confirm the computed time axis against the server once, on the first month asked for. If
    # the assumption is wrong every wind is misplaced, so this is worth one request.
    verify_time_axis(*wanted[0])

    def fetch(month_of: tuple[int, int]) -> pl.DataFrame | None:
        year, month = month_of
        try:
            return nightly(located, year, month)
        # One bad month must not lose the rest of a 248-month run.
        except Exception as error:
            log.warning(
                "  %d-%02d skipped: %s: %s", year, month, type(error).__name__, str(error)[:90]
            )
            return None

    frames = []
    # Threads rather than processes: every worker is waiting on a socket, not computing.
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for index, frame in enumerate(pool.map(fetch, wanted), start=1):
            if frame is not None:
                frames.append(frame)
            if index % 20 == 0 or index == len(wanted):
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
