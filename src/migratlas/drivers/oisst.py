"""OISST monthly means, reduced to one series per survey footprint.

`phase3e-marine-oisst.md` licenses exactly this: the footprint-mean sea surface temperature per
survey unit per month, from the verified PSL monthly file. The footprint is the survey's own —
the same consistent 1° cells `phase1b` analyses — so the water averaged here is the water the
trawls fished over, as a satellite estimated its surface.

The file serves 0-360 longitudes on a quarter-degree grid; the lake speaks -180..180 on 1°
cells. The index arithmetic lives in one testable helper rather than inline, because the
era5_land longitude trap cost a run and this module starts from that lesson.
"""

import logging
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.drivers.schema import DRIVER_SAMPLES, DriverKind
from migratlas.ingest.http import RemoteFile, fetch
from migratlas.lake.writer import WriteResult, write_table

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

SOURCE_ID: Final = "oisst"
FILE_NAME: Final = "sst.mon.mean.nc"
VARIABLE: Final = "oisst_sst_footprint_mean"

QUARTERS_PER_CELL: Final = 4
"""OISST's 0.25° grid packs a 4x4 block into each of the lake's 1° cells."""


def quarter_slice(centre: float, first: float) -> slice:
    """The four consecutive quarter-degree indices inside a 1° cell along one axis.

    ``first`` is the coordinate of index 0 (-89.875 for latitude, 0.125 for longitude), and
    ``centre`` must already be in the file's own convention. Exact because both grids are
    regular and 0.25 divides 1.0: the cell edge at centre-0.5 lands on index
    (centre - 0.5 - (first - 0.125)) / 0.25.
    """
    start = round((centre - 0.5 - (first - 0.125)) / 0.25)
    return slice(start, start + QUARTERS_PER_CELL)


def to_file_longitude(lon: float) -> float:
    """The lake's -180..180 into the file's 0-360."""
    return lon + 360.0 if lon < 0.0 else lon


def ingest(root: Path | None = None) -> WriteResult:
    """One footprint-mean series per survey unit, every month in the file, one write."""
    import xarray as xr  # noqa: PLC0415 -- gridded drivers only

    from migratlas.metrics import range as range_metrics  # noqa: PLC0415 -- report sibling
    from migratlas.reports import phase1b  # noqa: PLC0415 -- report sibling

    source = catalog.admit(SOURCE_ID)
    path = fetch(RemoteFile(url=source.download_uri, name=FILE_NAME), SOURCE_ID)
    dataset = xr.open_dataset(path)
    sst = dataset["sst"]
    lat_first = float(dataset["lat"][0])
    lon_first = float(dataset["lon"][0])
    months = pl.Series("period_start", dataset["time"].to_numpy()).cast(
        pl.Datetime("ms", time_zone="UTC")
    )

    cells = range_metrics.to_cells(phase1b.survey_unit(phase1b.load()))
    frames = []
    for (unit,), survey in cells.group_by(["survey_unit"], maintain_order=True):
        restricted, footprint = range_metrics.consistent_footprint(survey)
        if footprint.cells < range_metrics.MIN_CELLS:
            continue
        centres = restricted.select("cell_latitude", "cell_longitude").unique().to_dicts()
        per_cell = []
        for cell in centres:
            block = sst.isel(
                lat=quarter_slice(float(cell["cell_latitude"]), lat_first),
                lon=quarter_slice(to_file_longitude(float(cell["cell_longitude"])), lon_first),
            ).to_numpy()
            # A coastal cell is part land: the mean is over its ocean quarters only, and a
            # cell with no ocean at all contributes nothing rather than a NaN that would
            # poison the footprint.
            with np.errstate(invalid="ignore"):
                cell_mean = np.nanmean(block.reshape(block.shape[0], -1), axis=1)
            if np.isfinite(cell_mean).any():
                per_cell.append(cell_mean)
        if not per_cell:
            log.info("%s: footprint entirely landlocked in OISST; skipped", unit)
            continue
        series = np.nanmean(np.stack(per_cell), axis=0)
        keep = np.isfinite(series)
        frames.append(
            pl.DataFrame(
                {
                    "source_id": [SOURCE_ID] * int(keep.sum()),
                    "site_id": [str(unit)] * int(keep.sum()),
                    "period_start": months.filter(pl.Series(keep)),
                    "longitude": [float("nan")] * int(keep.sum()),
                    "latitude": [float("nan")] * int(keep.sum()),
                    "depth_m": [None] * int(keep.sum()),
                    "variable": [VARIABLE] * int(keep.sum()),
                    "value": series[keep],
                    "unit": ["degC"] * int(keep.sum()),
                    "kind": [DriverKind.GRIDDED.value] * int(keep.sum()),
                    "derived_from": [
                        f"OISST v2.1 monthly, mean over {len(per_cell)} footprint cells"
                    ]
                    * int(keep.sum()),
                },
                schema_overrides={"depth_m": pl.Float64},
            )
        )
        log.info("%s: %d months over %d ocean cells", unit, int(keep.sum()), len(per_cell))

    table = pl.concat(frames)
    schema = DRIVER_SAMPLES.schema
    return write_table(
        table.select(schema.names).to_arrow().cast(schema),
        DRIVER_SAMPLES,
        source_id=SOURCE_ID,
        root=root,
    )
