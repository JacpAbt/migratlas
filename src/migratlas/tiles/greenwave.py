"""The green wave: a half-monthly NDVI climatology on the globe's own clock.

The idea note's headline (`docs/ideas/satellite-drivers-on-the-globe.md`): spring green-up is the
single most legible driver of northern-hemisphere migration timing, and seeing the wave move
north while the passage brightens is the Phase 2a story in one gesture. The clock's week picks
the half-month, the product's own step.

Three honesty notes, carried in the prose rather than discovered. This is a **climatology** --
the average wave of 1982-2022, against which any one spring runs early or late -- and the caption
says so, because animating an average against the passage's own averaged year is comparing two
climatologies and must not read as a particular spring. A 1° cell's value is the mean over its
**vegetated** twelfth-degree pixels only, and a cell publishes a half-month only when at least a
tenth of its pixels carried vegetation -- desert and open water are absences, not zeros. And the
values are quantised to hundredths, which already flatters a modelled consolidation.

The heavy lifting is cached: each source archive reduces once to a per-archive sum-and-count
checkpoint under the cache directory, so a rebuild reads four small arrays rather than 984
rasters, and an interrupted first build resumes at archive granularity. Delete the cache to
force recomputation.
"""

import json
import logging
import zipfile
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from migratlas.catalog import loader as catalog
from migratlas.config import get_settings
from migratlas.evidence import Realm, TaxonScope
from migratlas.ingest.http import Checksum, RemoteFile, fetch
from migratlas.redact import clear_for_publication

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

log = logging.getLogger(__name__)

SOURCE_ID: Final = "pku_gimms_ndvi"
LAYER_NAME: Final = "green-wave"

# The four consolidated archives, with the checksums Zenodo states.
ARCHIVES: Final[tuple[tuple[str, str], ...]] = (
    ("PKU_GIMMS_NDVI_AVHRR_MODIS_consolidated_1982_1990.zip", "a838b1be402938ad3a5ceac2c3707949"),
    ("PKU_GIMMS_NDVI_AVHRR_MODIS_consolidated_1991_2000.zip", "ad646d67a89a10d3838844437260916e"),
    ("PKU_GIMMS_NDVI_AVHRR_MODIS_consolidated_2001_2010.zip", "c8f95d9e7edba87cb4a3bdb59ba4a8be"),
    ("PKU_GIMMS_NDVI_AVHRR_MODIS_consolidated_2011_2022.zip", "225cf139bb1ed40c720c23c90dd659cc"),
)

MONTHS: Final = 12
HALF_MONTHS: Final = MONTHS * 2
FILL: Final = 65535
SCALE: Final = 0.001

# The product grid and the published one.
SOURCE_CELLS_PER_DEGREE: Final = 12
CELL_DEG: Final = 1.0

# A 1° cell speaks for a half-month only when at least this share of its 144 source pixels
# carried vegetation; below it the cell is an absence for that bin, not a confident green.
MIN_VALID_SHARE: Final = 0.1

TITLE: Final = "The green wave"
DESCRIPTION: Final = (
    "Vegetation greenness per one-degree cell, half-month by half-month: the average wave of "
    "1982-2022, moving north each spring as the passage brightens behind it. A climatology, "
    "not this year's spring -- any one year runs early or late against it, and that gap is a "
    "finding, not an error. A cell's value averages only its vegetated ground; deserts and "
    "open water are absences, not zeros."
)
POPUP_CAVEAT: Final = (
    "the average greenness of 1982-2022 for this half-month — a climatology's spring, which "
    "any particular year runs early or late against."
)


@dataclass(frozen=True, slots=True)
class WaveExport:
    path: str
    cells: int
    bins: int
    generalization: str

    @property
    def features(self) -> int:
        return self.cells


def build_greenwave(destination_root: Path) -> WaveExport:
    """Fetch, reduce and publish the climatology; every heavy step checkpointed."""
    source = catalog.get(SOURCE_ID)
    clearance = clear_for_publication(
        source_id=source.id,
        evidence_type=None,
        realm=Realm.TERRESTRIAL,
        sensitivity=source.default_sensitivity,
        taxon_scope=TaxonScope.UNATTRIBUTED,
        taxon_key=None,
        redistribution_allowed=source.redistribution.allowed,
    )

    cache = get_settings().cache_dir / SOURCE_ID
    cache.mkdir(parents=True, exist_ok=True)

    height = int(180 / CELL_DEG)
    width = int(360 / CELL_DEG)
    total = np.zeros((HALF_MONTHS, height, width), dtype=np.float64)
    count = np.zeros((HALF_MONTHS, height, width), dtype=np.int64)
    rasters = np.zeros(HALF_MONTHS, dtype=np.int64)

    for name, md5 in ARCHIVES:
        checkpoint = cache / f"{name}.climatology.npz"
        if not checkpoint.exists():
            archive = fetch(
                RemoteFile(
                    url=f"{source.download_uri}/{name}?download=1",
                    name=name,
                    checksum=Checksum("md5", md5),
                ),
                SOURCE_ID,
            )
            part_total, part_count, part_rasters = _reduce_archive(archive)
            np.savez_compressed(
                checkpoint, total=part_total, count=part_count, rasters=part_rasters
            )
            log.info("checkpointed %s", checkpoint.name)
        loaded = np.load(checkpoint)
        total += loaded["total"]
        count += loaded["count"]
        rasters += loaded["rasters"]

    pixels_per_cell = (CELL_DEG * SOURCE_CELLS_PER_DEGREE) ** 2
    with np.errstate(invalid="ignore"):
        mean = np.where(count > 0, total / np.maximum(count, 1), np.nan)
    # Count sums over years as well as pixels, so the share floor scales by the exact number of
    # rasters that fed each bin -- tallied during reduction, never inferred.
    floor = MIN_VALID_SHARE * pixels_per_cell * np.maximum(rasters, 1)[:, None, None]
    mean[count < floor] = np.nan

    cells_x: list[int] = []
    cells_y: list[int] = []
    values: list[list[int | None]] = []
    present = ~np.all(np.isnan(mean), axis=0)
    for y, x in np.argwhere(present):
        cells_x.append(int(x))
        # The rasters are north-up; the published grid follows the site's existing south-up
        # index convention, where cell centre latitude is (y + 0.5) * size - 90.
        cells_y.append(int(height - 1 - y))
        values.append(
            [
                None if np.isnan(mean[b, y, x]) else round(float(mean[b, y, x]) * 100)
                for b in range(HALF_MONTHS)
            ]
        )

    destination = destination_root / f"{LAYER_NAME}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(
            {
                "format": "seasonal-grid",
                "cell_size_deg": CELL_DEG,
                "bins": HALF_MONTHS,
                "value_kind": "ndvi_x100",
                "x": cells_x,
                "y": cells_y,
                "hm": values,
            },
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    statement = (
        f"{clearance.generalization.statement()}; reduced to a 1-degree half-monthly "
        f"climatology over 1982-2022, vegetated pixels only"
    )
    destination.with_suffix(".meta.json").write_text(
        json.dumps(
            {
                "source_id": clearance.source_id,
                "evidence_type": "driver",
                "realm": str(clearance.realm),
                "sensitivity": str(clearance.sensitivity),
                "dwc:dataGeneralizations": statement,
                "cleared_at": clearance.issued_at.isoformat(),
                "cells": len(values),
                "bins": HALF_MONTHS,
                "reduction": (
                    "Mean NDVI per one-degree cell per half-month of year, 1982-2022, over "
                    "vegetated pixels only; a cell-bin below a tenth of its pixels vegetated "
                    "is absent, not zero. A climatology: no value describes a particular year."
                ),
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    log.info("exported %d cells x %d bins to %s", len(values), HALF_MONTHS, destination)
    return WaveExport(
        path=str(destination),
        cells=len(values),
        bins=HALF_MONTHS,
        generalization=statement,
    )


def _reduce_archive(archive: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """One archive's rasters, block-reduced to 1° sums and vegetated-pixel counts per bin."""
    import rasterio  # noqa: PLC0415 -- geo extra, only this builder

    height = int(180 / CELL_DEG)
    width = int(360 / CELL_DEG)
    total = np.zeros((HALF_MONTHS, height, width), dtype=np.float64)
    count = np.zeros((HALF_MONTHS, height, width), dtype=np.int64)
    rasters = np.zeros(HALF_MONTHS, dtype=np.int64)

    with zipfile.ZipFile(archive) as bundle:
        members = sorted(m for m in bundle.namelist() if m.endswith(".tif"))
        for position, member in enumerate(members, start=1):
            bin_index = _bin_of(member)
            if bin_index is None:
                log.warning("unrecognised member name %s; skipped", member)
                continue
            with rasterio.open(f"zip://{archive}!{member}") as raster:
                ndvi = raster.read(1)
            valid = ndvi != FILL
            block_sum, block_count = _block_reduce(
                np.where(valid, ndvi.astype(np.float64) * SCALE, 0.0),
                valid,
            )
            total[bin_index] += block_sum
            count[bin_index] += block_count
            rasters[bin_index] += 1
            if position % 100 == 0:
                log.info("  %s: %d/%d rasters", archive.name, position, len(members))
    return total, count, rasters


def yearly_means(archive: Path) -> Iterator[tuple[int, np.ndarray]]:
    """Per year in one archive: 24 half-month cell means, NaN below the vegetated-share floor.

    The climatology above pools years before dividing; this keeps them apart, because the
    drivers work (Phase 3a) needs the years the tile deliberately averages away. Yields in year
    order — member names sort by their date stamp, so one year's rasters are consecutive and
    only one year's accumulator is alive at a time.
    """
    import rasterio  # noqa: PLC0415 -- geo extra, only this builder

    height = int(180 / CELL_DEG)
    width = int(360 / CELL_DEG)
    floor = MIN_VALID_SHARE * (CELL_DEG * SOURCE_CELLS_PER_DEGREE) ** 2

    def finish(total: np.ndarray, count: np.ndarray) -> np.ndarray:
        with np.errstate(invalid="ignore"):
            mean = np.where(count > 0, total / np.maximum(count, 1), np.nan)
        mean[count < floor] = np.nan
        return mean

    with zipfile.ZipFile(archive) as bundle:
        members = sorted(m for m in bundle.namelist() if m.endswith(".tif"))
        year: int | None = None
        total = np.zeros((HALF_MONTHS, height, width), dtype=np.float64)
        count = np.zeros((HALF_MONTHS, height, width), dtype=np.int64)
        for member in members:
            bin_index = _bin_of(member)
            stamp_year = _year_of(member)
            if bin_index is None or stamp_year is None:
                log.warning("unrecognised member name %s; skipped", member)
                continue
            if year is not None and stamp_year != year:
                yield year, finish(total, count)
                total[:] = 0.0
                count[:] = 0
            year = stamp_year
            with rasterio.open(f"zip://{archive}!{member}") as raster:
                ndvi = raster.read(1)
            valid = ndvi != FILL
            block_sum, block_count = _block_reduce(
                np.where(valid, ndvi.astype(np.float64) * SCALE, 0.0),
                valid,
            )
            total[bin_index] += block_sum
            count[bin_index] += block_count
        if year is not None:
            yield year, finish(total, count)


def _year_of(member: str) -> int | None:
    """The year from the product's date stamp, or None if the name is foreign."""
    stem = member.rsplit("/", maxsplit=1)[-1].removesuffix(".tif")
    digits = stem.rsplit("_", maxsplit=1)[-1]
    stamp_width = 8
    if len(digits) != stamp_width or not digits.isdigit():
        return None
    return int(digits[:4])


def _bin_of(member: str) -> int | None:
    """Half-month bin 0-23 from the product's own file naming, or None if the name is foreign."""
    stem = member.rsplit("/", maxsplit=1)[-1].removesuffix(".tif")
    digits = stem.rsplit("_", maxsplit=1)[-1]
    stamp_width = 8  # YYYYMMHH: year, month, and which half of the month
    if len(digits) != stamp_width or not digits.isdigit():
        return None
    month, half = int(digits[4:6]), int(digits[6:8])
    if not (1 <= month <= MONTHS and half in (1, 2)):
        return None
    return (month - 1) * 2 + (half - 1)


def _block_reduce(values: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Sum and count per 1° block, exact because 2160 and 4320 divide evenly by the block."""
    block = int(CELL_DEG * SOURCE_CELLS_PER_DEGREE)
    rows, cols = values.shape
    shaped = values.reshape(rows // block, block, cols // block, block)
    kept = valid.reshape(rows // block, block, cols // block, block)
    return shaped.sum(axis=(1, 3)), kept.sum(axis=(1, 3)).astype(np.int64)
