"""The green-up date: the timing metric Phase 3a registers for the yearly NDVI series.

The green-wave tile collapses 41 years to a 24-bin climatology; the models need the years back.
The metric is defined here, alone and tested, before the reduction that will apply it to the
PKU archives is built — the definition is what `phase3a-skill.md` binds to, and a metric that
lived inside a 2.4 GB batch job would be a metric nobody could test in milliseconds.

Midpoint-of-amplitude is the standard green-up definition precisely because it is relative: a
dark conifer cell and a bright tundra cell green up on their own scales, and an absolute
threshold would hand the date to the brightness rather than the timing.
"""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.config import get_settings
from migratlas.drivers.schema import DRIVER_SAMPLES, DriverKind
from migratlas.ingest.http import Checksum, RemoteFile, fetch
from migratlas.lake.writer import WriteResult, write_table
from migratlas.tiles import greenwave

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

SOURCE_ID: Final = greenwave.SOURCE_ID
VARIABLE: Final = "greenup_day_of_year"

# A cell whose seasonal swing is smaller than this has no green-up to date: deserts, ice and
# evergreen canopy produce crossings that are noise crossing noise. NDVI units, the product's
# 0-1 scale.
MIN_AMPLITUDE: Final = 0.1

# Every bin of the year must hold data before a crossing date is trusted: a year whose winter
# half-months are missing would place its "first crossing" wherever the gap ends.
BINS_PER_YEAR: Final = greenwave.HALF_MONTHS


def greenup_day(
    values: np.ndarray,
    *,
    bins: int = BINS_PER_YEAR,
    min_amplitude: float = MIN_AMPLITUDE,
) -> float | None:
    """Day of year when the series first crosses the midpoint of this year's amplitude, or None.

    ``values`` is one unit-year of within-year bins in order: 24 half-months for NDVI, 12
    months when Phase 3c applies the same metric to plankton abundance — one definition, two
    kingdoms, which is why the bin count is a parameter and not two functions that would drift.
    None when any bin is missing (a gap would masquerade as timing), when the amplitude is
    below ``min_amplitude`` (nothing to date; the caller's units decide the floor), or when the
    year opens already above its midpoint — a crossing that belongs to the previous year would
    fabricate a series with no variance. Linear interpolation inside the crossing bin, so the
    answer is a day rather than a bin: consumers difference these across years, and a
    bin-width quantum would swallow the signal it exists to carry.
    """
    if values.shape != (bins,) or np.isnan(values).any():
        return None
    low, high = float(values.min()), float(values.max())
    if high - low < min_amplitude:
        return None
    midpoint = low + (high - low) / 2.0
    above = values >= midpoint
    if above[0]:
        return None
    index = int(np.argmax(above))
    span = float(values[index] - values[index - 1])
    fraction = 0.5 if span == 0 else float(midpoint - values[index - 1]) / span
    return ((index - 1) + fraction + 0.5) * (365.0 / bins)


def build_greenup(root: Path | None = None) -> WriteResult:
    """Reduce every archive year to green-up days and land them as driver samples.

    Reads the same four checksummed zips the wave tile reads -- no new fetch, no new licence --
    and checkpoints per archive, because the wave's own build proved the archive boundary is
    the boundary an interrupted run wants back.
    """
    source = catalog.admit(SOURCE_ID)
    cache = get_settings().cache_dir / SOURCE_ID
    cache.mkdir(parents=True, exist_ok=True)

    frames = []
    for name, md5 in greenwave.ARCHIVES:
        checkpoint = cache / f"{name}.greenup.npz"
        if not checkpoint.exists():
            archive = fetch(
                RemoteFile(
                    url=f"{source.download_uri}/{name}?download=1",
                    name=name,
                    checksum=Checksum("md5", md5),
                ),
                SOURCE_ID,
            )
            years, lats, lons, days = _reduce(archive)
            np.savez_compressed(checkpoint, years=years, lats=lats, lons=lons, days=days)
            log.info("checkpointed %s", checkpoint.name)
        stored = np.load(checkpoint)
        frames.append(_to_frame(stored["years"], stored["lats"], stored["lons"], stored["days"]))

    rows = pl.concat(frames)
    log.info("green-up: %d cell-years across %d archives", rows.height, len(frames))
    schema = DRIVER_SAMPLES.schema
    return write_table(
        rows.select(schema.names).to_arrow().cast(schema),
        DRIVER_SAMPLES,
        source_id=SOURCE_ID,
        root=root,
    )


def _reduce(archive: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """One archive's cell-years: parallel arrays of year, cell-centre latitude/longitude, day."""
    years: list[int] = []
    lats: list[float] = []
    lons: list[float] = []
    days: list[float] = []
    for year, means in greenwave.yearly_means(archive):
        # Only a cell with all 24 bins can carry a date, and the metric refuses the rest, so
        # the candidate set is just the cells that are NaN nowhere.
        candidates = np.argwhere(~np.isnan(means).any(axis=0))
        dated = 0
        for y, x in candidates:
            day = greenup_day(means[:, y, x])
            if day is None:
                continue
            years.append(year)
            # Rasters arrive north-up: row 0 is the 90°N edge (the tile builder flips this for
            # its own south-up y; latitudes here need no flip, only the half-cell centre).
            lats.append(90.0 - (float(y) + 0.5) * greenwave.CELL_DEG)
            lons.append(-180.0 + (float(x) + 0.5) * greenwave.CELL_DEG)
            days.append(day)
            dated += 1
        log.info("  %d: %d cells dated of %d candidates", year, dated, len(candidates))
    return (
        np.array(years, dtype=np.int64),
        np.array(lats, dtype=np.float64),
        np.array(lons, dtype=np.float64),
        np.array(days, dtype=np.float64),
    )


def _to_frame(
    years: np.ndarray, lats: np.ndarray, lons: np.ndarray, days: np.ndarray
) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "source_id": [SOURCE_ID] * len(years),
            "site_id": [f"{lat:.1f},{lon:.1f}" for lat, lon in zip(lats, lons, strict=True)],
            "period_start": [datetime(int(year), 1, 1, tzinfo=UTC) for year in years],
            "longitude": lons,
            "latitude": lats,
            "depth_m": [None] * len(years),
            "variable": [VARIABLE] * len(years),
            "value": days,
            "unit": ["day_of_year"] * len(years),
            "kind": [DriverKind.GRIDDED.value] * len(years),
            "derived_from": ["PKU_GIMMS_NDVI4g:midpoint_amplitude"] * len(years),
        },
        schema_overrides={"depth_m": pl.Float64},
    )
