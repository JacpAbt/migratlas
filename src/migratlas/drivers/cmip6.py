"""CMIP6 DAMIP: the same climate simulated with and without human influence.

Pre-registered in docs/methods/phase2a-attribution.md. `historical` runs all forcings; `hist-nat`
runs only solar and volcanic, with human influence removed. The difference between them is the only
way to ask a counterfactual question of a climate that happened once.

Read from the Pangeo CMIP6 collection on Google Cloud, which is public and needs no ESGF
credentials. Chunking is 439 months x the whole globe, so a spatial subset costs the same as a
single point -- the region is read once per store and every station is taken from it in memory,
which is the lesson `adr/0006` records about ARCO-ERA5 applied before it could bite again.

Landed with `kind=simulated`, a fourth driver kind added for this. A counterfactual temperature is
not a coarse observation, and filing it as "gridded" would put a thing that happened and a thing
that did not in one bucket.
"""

import logging
from typing import TYPE_CHECKING, Final, NamedTuple

import numpy as np
import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.drivers.schema import DRIVER_SAMPLES, DriverKind
from migratlas.lake.writer import WriteResult, write_table

if TYPE_CHECKING:
    from pathlib import Path

    import pyarrow as pa

    from migratlas.features.annotate import Point

log = logging.getLogger(__name__)

SOURCE_ID: Final = "cmip6_damip"
CATALOGUE: Final = "https://storage.googleapis.com/cmip6/pangeo-cmip6.csv"

VARIABLE: Final = "tas"
TABLE: Final = "Amon"
CANONICAL: Final = "air_temperature_2m"
UNIT: Final = "degC"
KELVIN: Final = 273.15

# `historical` lives under CMIP, the counterfactual under DAMIP.
EXPERIMENTS: Final[dict[str, str]] = {"historical": "CMIP", "hist-nat": "DAMIP"}

# June and July, matching the pre-season window the response function was fitted on.
PRE_SEASON: Final[tuple[int, ...]] = (6, 7)

# `historical` ends in 2014, so that is the last year both experiments cover. The window problem
# and why a ratio survives it are in the method note.
COMMON_END: Final = 2014

# Members per model per experiment. MIROC6 and CanESM5 offer fifty each while nine models offer
# three or fewer, so an uncapped run would make the answer a statement about two models -- and
# members are averaged within a model precisely to stop that. Three is the compromise; the method
# note records that more are available if a later run wants tighter member sampling.
MAX_MEMBERS: Final = 3

REQUEST_TIMEOUT_S: Final = 300.0

# Four at once, as the NARR driver settled on: the limit is the remote store, not the CPU, and a
# wider pool multiplies peak memory by the size of one decompressed globe-wide chunk.
WORKERS: Final = 4


class Store(NamedTuple):
    """One model-member-experiment, and where its zarr lives."""

    experiment: str
    model: str
    member: str
    zstore: str


def catalogue() -> pl.DataFrame:
    """The Pangeo catalogue, cached in the raw archive like any other download."""
    from migratlas.ingest.http import RemoteFile, fetch  # noqa: PLC0415 -- avoids a cycle

    path = fetch(RemoteFile(url=CATALOGUE, name="pangeo-cmip6.csv"), SOURCE_ID)
    return pl.read_csv(path, schema_overrides={"dcpp_init_year": pl.Float64})


def stores(frame: pl.DataFrame) -> list[Store]:
    """Every usable model-member-experiment, capped and paired.

    A model is included only if it has *both* experiments: a counterfactual needs its own control,
    and a `hist-nat` run without the matching `historical` cannot contribute a fraction.

    Members are sorted as strings, so a model with ten or more contributes r1, r10, r11 rather than
    r1, r2, r3. That is deliberate rather than overlooked: ensemble members are exchangeable by
    construction -- they differ only in initial condition -- so any three are as good as any other
    three, and a lexicographic sort is reproducible without needing to parse a member id.
    """
    selected: dict[str, pl.DataFrame] = {}
    for experiment, activity in EXPERIMENTS.items():
        selected[experiment] = frame.filter(
            pl.col("activity_id") == activity,
            pl.col("experiment_id") == experiment,
            pl.col("table_id") == TABLE,
            pl.col("variable_id") == VARIABLE,
        )

    paired = set.intersection(
        *(set(subset["source_id"].unique().to_list()) for subset in selected.values())
    )
    log.info("%d models carry both experiments", len(paired))

    out: list[Store] = []
    for experiment, subset in selected.items():
        for model in sorted(paired):
            members = (
                subset.filter(pl.col("source_id") == model)
                .sort("member_id")
                # One store per member: a model can publish the same member under several
                # versions, and taking the first keeps the run reproducible.
                .unique(subset=["member_id"], keep="first", maintain_order=True)
                .head(MAX_MEMBERS)
            )
            out += [
                Store(experiment, model, row["member_id"], row["zstore"])
                for row in members.iter_rows(named=True)
            ]
    return out


def _box(points: list[Point]) -> tuple[slice, slice]:
    """The lat/lon box holding every station, in the 0-360 longitude the models use."""
    latitudes = [point.latitude for point in points]
    longitudes = [point.longitude % 360 for point in points]
    return (
        slice(min(latitudes) - 2.0, max(latitudes) + 2.0),
        slice(min(longitudes) - 2.0, max(longitudes) + 2.0),
    )


def pre_season(store: Store, points: list[Point], end: int = COMMON_END) -> pl.DataFrame:
    """June-July mean temperature at each station, per year, for one store.

    The whole box is read once and the stations taken from it in memory, because the chunks span
    the globe: subsetting to a point saves nothing and costs one read per station.
    """
    import xarray as xr  # noqa: PLC0415 -- an optional extra, needed only for gridded drivers

    # Anonymous access for the cloud store, nothing for a local path -- fsspec's local filesystem
    # does not take a token, and a local store is how this gets tested against a 360-day calendar.
    options = {"token": "anon"} if "://" in store.zstore else None
    dataset = xr.open_zarr(store.zstore, storage_options=options, chunks=None)
    latitudes, longitudes = _box(points)
    window = (
        dataset[VARIABLE]
        .sel(lat=latitudes, lon=longitudes)
        # Sliced by year alone, not by "-12-31". Climate models do not all use a real calendar, and
        # in HadGEM3's 360-day one every month has thirty days, so asking for 31 December raises
        # rather than clamping -- it silently cost that model its place in the ensemble.
        .sel(time=slice(str(end - 100), str(end)))
    )
    window = window.sel(time=window["time.month"].isin(PRE_SEASON)).load()

    years = window["time.year"].to_numpy()
    rows = []
    for point in points:
        column = window.sel(
            lat=point.latitude, lon=point.longitude % 360, method="nearest"
        ).to_numpy()
        frame = (
            pl.DataFrame({"year": years, "value": column.astype(np.float64) - KELVIN})
            .group_by("year")
            .agg(pl.col("value").mean())
            .with_columns(
                site_id=pl.lit(point.site_id),
                longitude=pl.lit(point.longitude),
                latitude=pl.lit(point.latitude),
                experiment=pl.lit(store.experiment),
                model=pl.lit(store.model),
                member=pl.lit(store.member),
            )
        )
        rows.append(frame)
    return pl.concat(rows)


def to_samples(frame: pl.DataFrame) -> pa.Table:
    """Driver rows, marked simulated and carrying which simulation they came from."""
    out = frame.select(
        source_id=pl.lit(SOURCE_ID),
        site_id=pl.col("site_id"),
        # July of the year, as a stand-in for the June-July window. The window is in the variable
        # name so the date is only ever used as a year.
        period_start=pl.datetime(pl.col("year"), 7, 1, time_zone="UTC").cast(
            pl.Datetime("ms", time_zone="UTC")
        ),
        longitude=pl.col("longitude").cast(pl.Float64),
        latitude=pl.col("latitude").cast(pl.Float64),
        depth_m=pl.lit(None, dtype=pl.Float64),
        variable=pl.lit(f"{CANONICAL}_junjul_") + pl.col("experiment"),
        value=pl.col("value").cast(pl.Float64),
        unit=pl.lit(UNIT),
        kind=pl.lit(DriverKind.SIMULATED.value),
        # Which simulation. "A simulated temperature" is meaningless without this.
        derived_from=pl.concat_str(
            [
                pl.lit("cmip6:"),
                pl.col("experiment"),
                pl.lit(":"),
                pl.col("model"),
                pl.lit(":"),
                pl.col("member"),
            ]
        ),
    ).drop_nulls("value")
    schema = DRIVER_SAMPLES.schema
    return out.select(schema.names).to_arrow().cast(schema)


def ingest(points: list[Point], *, root: Path | None = None) -> WriteResult:
    """Fetch, reshape and land the pre-season temperature under both experiments."""
    from concurrent.futures import ThreadPoolExecutor  # noqa: PLC0415 -- only this needs it

    catalog.admit(SOURCE_ID)
    wanted = stores(catalogue())
    models = len({store.model for store in wanted})
    log.info("%d stores to read (%d models, cap %d members)", len(wanted), models, MAX_MEMBERS)

    def read(store: Store) -> pl.DataFrame | None:
        try:
            return pre_season(store, points)
        # One model must not lose the ensemble: a store can be missing a year, use a calendar
        # xarray cannot decode, or simply be unreadable.
        except Exception as error:
            log.warning(
                "  %s %s %s skipped: %s: %s",
                store.experiment,
                store.model,
                store.member,
                type(error).__name__,
                str(error)[:80],
            )
            return None

    frames = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        # One line per store rather than one per ten. Ninety lines is nothing, and the alternative
        # is a run that has printed nothing for eight minutes and gives no way to tell a slow
        # store from a hung one.
        for index, (store, frame) in enumerate(
            zip(wanted, pool.map(read, wanted), strict=True), start=1
        ):
            if frame is not None:
                frames.append(frame)
            log.info(
                "  %2d/%d %s %s %s%s",
                index,
                len(wanted),
                store.experiment,
                store.model,
                store.member,
                "" if frame is not None else "  SKIPPED",
            )

    if not frames:
        msg = "no CMIP6 stores could be read"
        raise RuntimeError(msg)

    combined = pl.concat(frames)
    got = combined.group_by("experiment").agg(pl.col("model").n_unique().alias("models"))
    for row in got.iter_rows(named=True):
        log.info("%s: %d models", row["experiment"], row["models"])

    table = to_samples(combined)
    log.info("%d driver samples", table.num_rows)
    return write_table(table, DRIVER_SAMPLES, source_id=SOURCE_ID, root=root)
