"""CMEMS biogeochemical reanalysis, reduced to one oxygen series per survey footprint.

`phase3g-oxygen.md` licenses exactly this: the footprint-mean dissolved oxygen per survey unit per
month, read at the depth nearest that unit's own median haul depth. The footprint is the survey's
own -- the same consistent 1° cells `phase1b` analyses -- so the water averaged is the water the
trawls fished over, at roughly the depth they fished it.

Three things about this route were measured rather than assumed, and each cost or would have cost a
run.

**The credential is required, and probing the metadata says otherwise.** The ARCO zarr serves
`.zmetadata`, `.zgroup` and every coordinate array to an anonymous HTTPS request -- so a probe that
opens the store and prints its axes concludes the data is public. It is not: the first `o2` chunk
answers 403. Metadata open, chunks closed. This module went down that road and came back.

**A 403 from the raw store can also mean the wrong zarr format.** The installed zarr is 3.x and the
store is v2, so a direct `open_zarr` without `zarr_format=2` requests `zarr.json`, which does not
exist, and S3 answers 403. Two different causes, one status code, and neither says which. Going
through the client avoids both by not being the thing holding S3 credentials.

**The client renames the vertical axis and flips its sign.** The raw store publishes `elevation` in
*negative* metres (-0.5 to -5902); `copernicusmarine.open_dataset` hands back `depth` in *positive*
metres (0.5 to 5902). A level picker written against the store's convention minimises at the surface
for every survey when handed the client's -- and surface oxygen looks entirely plausible. Hence
:func:`nearest_depth` takes the positive convention, and a test pins both signs.

No index arithmetic here, deliberately. An earlier draft computed quarter-degree slices by hand and
carried a helper explaining how this grid's registration differs from OISST's; the client subsets by
coordinate *value*, so that whole class of off-by-one left with it. Grid points are assigned to the
lake's 1° cells by flooring, which is the rule `metrics.range.to_cells` uses to make them.
"""

import logging
from typing import TYPE_CHECKING, Any, Final

import numpy as np
import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.config import Settings
from migratlas.drivers.schema import DRIVER_SAMPLES, DriverKind
from migratlas.lake.writer import WriteResult, write_table

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

SOURCE_ID: Final = "cmems_bgc"
DATASET_ID: Final = "cmems_mod_glo_bgc_my_0.25deg_P1M-m"
OXYGEN: Final = "o2"
VARIABLE: Final = "cmems_o2_footprint_mean"
UNIT: Final = "mmol m-3"

CELL_DEG: Final = 1.0
"""The lake's cell size, matching `metrics.range.CELL_DEG`. Points are assigned to cells by
flooring, which is how `to_cells` builds them: centre = floor(coord) + 0.5."""

DEPTH_WINDOW_M: Final = 40.0
"""How much of the water column to request around a survey's median haul depth.

Wide enough that the nearest level is inside it for every survey in the panel -- the levels thin out
with depth, and GSL-N's 258 m sits where they are tens of metres apart -- and narrow enough that the
request is a slice rather than the whole column.
"""


def nearest_depth(depths: np.ndarray, target_m: float) -> int:
    """Index of the level closest to a depth in metres, in the client's positive convention.

    The raw store signs this axis negative and the client signs it positive, so a picker written for
    one silently reads the surface when handed the other. `abs(target_m)` makes either input work;
    the axis itself has to be the client's.
    """
    return int(np.argmin(np.abs(np.asarray(depths, dtype=float) - abs(target_m))))


def cell_of(coordinate: np.ndarray) -> np.ndarray:
    """The centre of the 1° cell each coordinate falls in. `to_cells`' rule, applied backwards."""
    return np.floor(np.asarray(coordinate, dtype=float) / CELL_DEG) * CELL_DEG + CELL_DEG / 2


def mean_over_footprint(
    oxygen: np.ndarray,
    latitudes: np.ndarray,
    longitudes: np.ndarray,
    footprint: set[tuple[float, float]],
) -> tuple[np.ndarray, int]:
    """Mean oxygen per timestep over the grid points inside the footprint's cells.

    Returns the series and the number of *cells* it drew on, so a footprint that turned out to be
    land is reported as coverage rather than published as a series of NaN.

    A point on land or below the sea floor is NaN in the product, and a cell can be part one and
    part the other, so the mean is over the finite points only -- see :func:`_mean_of_the_water` for
    why that is not `np.nanmean`.
    """
    grid_lat, grid_lon = np.meshgrid(cell_of(latitudes), cell_of(longitudes), indexing="ij")
    inside = np.zeros(grid_lat.shape, dtype=bool)
    used = 0
    for lat, lon in footprint:
        matches = (grid_lat == lat) & (grid_lon == lon)
        if matches.any():
            inside |= matches
            used += 1
    if not inside.any():
        return np.array([]), 0

    flat = oxygen.reshape(oxygen.shape[0], -1)[:, inside.reshape(-1)]
    return _mean_of_the_water(flat), used


def _mean_of_the_water(values: np.ndarray) -> np.ndarray:
    """Row means over the finite entries, NaN where a row has none.

    `np.nanmean` is the obvious call and it warns on an all-NaN row -- "Mean of empty slice" --
    which this suite turns into an error, and `np.errstate` does not cover it because it is a
    warning rather than a floating-point flag. Counting explicitly is also clearer about what the
    number is: the mean over the water, and nothing where there is none.
    """
    finite = np.isfinite(values)
    count = finite.sum(axis=1)
    total = np.where(finite, values, 0.0).sum(axis=1)
    return np.where(count > 0, total / np.maximum(count, 1), np.nan)


def open_box(bounds: tuple[float, float, float, float], depth_m: float) -> Any:
    """One authenticated, coordinate-subset read: the survey's box and a slice of water."""
    import copernicusmarine as cm  # noqa: PLC0415 -- geo extra, only this module

    south, north, west, east = bounds
    return cm.open_dataset(
        dataset_id=DATASET_ID,
        username=Settings.credential("cmems_username"),
        password=Settings.credential("cmems_password"),
        variables=[OXYGEN],
        minimum_latitude=south,
        maximum_latitude=north,
        minimum_longitude=west,
        maximum_longitude=east,
        minimum_depth=max(0.0, depth_m - DEPTH_WINDOW_M),
        maximum_depth=depth_m + DEPTH_WINDOW_M,
    )


def ingest(root: Path | None = None) -> WriteResult:
    """One footprint-mean oxygen series per survey unit, at its own depth, one write."""
    from migratlas.metrics import range as range_metrics  # noqa: PLC0415 -- report sibling
    from migratlas.reports import phase1b  # noqa: PLC0415 -- report sibling

    catalog.admit(SOURCE_ID)
    cells = range_metrics.to_cells(phase1b.survey_unit(phase1b.load()))

    frames = []
    for (unit,), survey in cells.group_by(["survey_unit"], maintain_order=True):
        restricted, footprint = range_metrics.consistent_footprint(survey)
        if footprint.cells < range_metrics.MIN_CELLS:
            continue

        depths = restricted["site_depth_m"].drop_nulls().to_numpy()
        if depths.size == 0:
            # Phase 3e's guard, inherited: a survey with no recorded depth has no depth to read
            # oxygen at, and substituting one would invent the driver.
            log.info("%s: no recorded haul depth; goes to coverage", unit)
            continue
        haul_depth = float(np.median(depths))

        wanted = {
            (float(row["cell_latitude"]), float(row["cell_longitude"]))
            for row in restricted.select("cell_latitude", "cell_longitude").unique().to_dicts()
        }
        lats = [lat for lat, _ in wanted]
        lons = [lon for _, lon in wanted]
        bounds = (min(lats) - 0.5, max(lats) + 0.5, min(lons) - 0.5, max(lons) + 0.5)

        data = open_box(bounds, haul_depth)
        depth_axis = data["depth"].to_numpy()
        level = nearest_depth(depth_axis, haul_depth)
        series, used = mean_over_footprint(
            data[OXYGEN].isel(depth=level).to_numpy(),
            data["latitude"].to_numpy(),
            data["longitude"].to_numpy(),
            wanted,
        )
        if used == 0:
            log.info("%s: footprint has no water at %.0f m; goes to coverage", unit, haul_depth)
            continue

        read_depth = float(depth_axis[level])
        months = pl.Series("period_start", data["time"].to_numpy()).cast(
            pl.Datetime("ms", time_zone="UTC")
        )
        keep = np.isfinite(series)
        rows = int(keep.sum())
        frames.append(
            pl.DataFrame(
                {
                    "source_id": [SOURCE_ID] * rows,
                    "site_id": [str(unit)] * rows,
                    "period_start": months.filter(pl.Series(keep)),
                    "longitude": [float("nan")] * rows,
                    "latitude": [float("nan")] * rows,
                    "depth_m": [read_depth] * rows,
                    "variable": [VARIABLE] * rows,
                    "value": series[keep],
                    "unit": [UNIT] * rows,
                    "kind": [DriverKind.GRIDDED.value] * rows,
                    "derived_from": [
                        f"CMEMS {DATASET_ID} monthly o2 at {read_depth:.1f} m "
                        f"(median haul depth {haul_depth:.0f} m), mean over {used} footprint cells"
                    ]
                    * rows,
                },
                schema_overrides={"depth_m": pl.Float64},
            )
        )
        log.info(
            "%s: %d months, %d cells, read at %.1f m for median haul depth %.0f m",
            unit,
            rows,
            used,
            read_depth,
            haul_depth,
        )

    table = pl.concat(frames)
    schema = DRIVER_SAMPLES.schema
    return write_table(
        table.select(schema.names).to_arrow().cast(schema),
        DRIVER_SAMPLES,
        source_id=SOURCE_ID,
        root=root,
    )
