"""JRC Global Surface Water, aggregated from 30 m pixels to the atlas grid.

Pre-registered in `docs/methods/phase1g-water.md`. Two layers land as driver samples: the net change
in water occurrence between the product's two epochs, and the long-run occurrence that says whether
a cell ever held water at all.

The tiles are 40,000 x 40,000 uint8 and there are five of them, which is eight billion pixels for
496 answers. Nothing is read whole: each footprint cell is one windowed read of its own thousand
pixels square, so the cost is 496 megabytes of IO rather than eight gigabytes of decode.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.drivers.schema import DRIVER_SAMPLES, DriverKind
from migratlas.lake.identifiers import cell_site_id

if TYPE_CHECKING:
    from pathlib import Path

    import pyarrow as pa

log = logging.getLogger(__name__)

SOURCE_ID: Final = "jrc_gsw"

# Read off `downloads_ancillary/change.qml`, the colour table shipped with the product, and not from
# memory. 0-200 is percentage-point change in occurrence with 100 as no change; the three values
# above it are not quantities and a mean that swallowed them would be meaningless.
NO_CHANGE: Final = 100
MAX_CHANGE: Final = 200
NOT_WATER: Final = 253
UNABLE: Final = 254
NO_DATA: Final = 255

# Occurrence is a straight percentage, with the same 255 for no data.
MAX_OCCURRENCE: Final = 100

# Below this share of usable pixels a cell is mostly cloud or canopy shadow. Reported, not
# dropped: which cells the sensor could not see is a property of the factor worth publishing.
MIN_USABLE_SHARE: Final = 0.5

TILE_DEG: Final = 10
PIXEL_DEG: Final = 0.00025

CHANGE_VARIABLE: Final = "surface_water_change_km2"
OCCURRENCE_VARIABLE: Final = "surface_water_extent_km2"

# The product's own epochs, from the INSPIRE metadata beside the tiles. Recorded in `derived_from`
# on every row so a reader cannot mistake them for the study's.
EPOCHS: Final = "1984-1999_vs_2000-2021"

# One epoch cannot be dated, so the timestamp is the midpoint of the product's whole span. The
# schema needs an instant; this one is honest about being a label rather than a measurement date.
PERIOD_START: Final = "2002-07-01"


@dataclass(frozen=True, slots=True)
class CellWater:
    """One quarter-degree cell's water, in area rather than in percentage points."""

    cell_lat: float
    cell_lon: float
    change_km2: float
    """Net change in water-equivalent area between the product's two epochs."""

    extent_km2: float
    """Mean water-equivalent area over 1984-2021. Zero means the cell never held water."""

    valid: float
    """Share of the cell's pixels the sensor could resolve at all.

    "Never water" counts as resolved, because it is an answer. Only "unable to compute" and "no
    data" are unobserved.
    """


def _tile_name(layer: str, longitude: float, latitude: float) -> str:
    """The tile filename covering a position, in the product's own naming.

    The tile is labelled by its *north-west* corner, which was confirmed against a file's own
    bounds rather than assumed: `20E_30S` reads 20 to 30 east and -40 to -30 north.
    """
    left = int(np.floor(longitude / TILE_DEG) * TILE_DEG)
    top = int(np.ceil(latitude / TILE_DEG) * TILE_DEG)
    return (
        f"{layer}_{abs(left)}{'E' if left >= 0 else 'W'}_"
        f"{abs(top)}{'S' if top <= 0 else 'N'}v1_4_2021.tif"
    )


def _cell_area_km2(latitude: float, size_deg: float) -> float:
    """Area of a square-degree cell at this latitude, on a spherical earth.

    Needed because a quarter-degree cell in the Karoo is smaller than one at the equator, and a
    water *area* summed in pixels would otherwise shrink with latitude for no physical reason.
    """
    earth_km = 6371.0088
    radians = np.deg2rad(size_deg)
    return float(earth_km**2 * radians * radians * np.cos(np.deg2rad(latitude)))


def read_cell(root: Path, cell_lat: float, cell_lon: float, size_deg: float) -> CellWater:
    """Aggregate one footprint cell from the 30 m tiles.

    Windowed: the read covers exactly this cell, so no tile is ever decoded whole.
    """
    import rasterio  # noqa: PLC0415 -- a heavy optional import, only for this adapter
    from rasterio.windows import from_bounds  # noqa: PLC0415

    half = size_deg / 2
    west, east = cell_lon - half, cell_lon + half
    south, north = cell_lat - half, cell_lat + half
    pixel_km2 = _cell_area_km2(cell_lat, PIXEL_DEG)

    def window(layer: str) -> np.ndarray:
        path = root / _tile_name(layer, west + PIXEL_DEG, north - PIXEL_DEG)
        with rasterio.open(path) as src:
            block: np.ndarray = src.read(
                1, window=from_bounds(west, south, east, north, src.transform)
            )
            return block

    change = window("change")
    # Two different questions, and conflating them cost a false alarm on 470 of 496 cells. Only
    # 0-200 carries a quantity to sum. But 253 -- "not water" -- is an *answer*: the sensor looked
    # and there was never water there, which over the Karoo is most of the ground. Unobserved is
    # 254 and 255 alone.
    usable = change <= MAX_CHANGE
    observed = usable | (change == NOT_WATER)
    # Percentage points of occurrence, converted to water-equivalent area. A pixel that went from
    # 40% to 90% of the time wet contributes half a pixel of new water, which is what the
    # occurrence scale means.
    change_km2 = float(((change[usable].astype(np.float64) - NO_CHANGE) / 100.0).sum() * pixel_km2)

    occurrence = window("occurrence")
    present = occurrence <= MAX_OCCURRENCE
    extent_km2 = float((occurrence[present].astype(np.float64) / 100.0).sum() * pixel_km2)

    return CellWater(
        cell_lat=cell_lat,
        cell_lon=cell_lon,
        change_km2=change_km2,
        extent_km2=extent_km2,
        valid=float(observed.mean()) if observed.size else 0.0,
    )


def to_samples(cells: list[CellWater]) -> pa.Table:
    """Driver rows, marked GRIDDED because a satellite composite is not a site measurement."""
    rows = pl.DataFrame(
        {
            "site_id": [cell_site_id(cell.cell_lat, cell.cell_lon) for cell in cells],
            "cell_lat": [cell.cell_lat for cell in cells],
            "cell_lon": [cell.cell_lon for cell in cells],
            "change": [cell.change_km2 for cell in cells],
            "extent": [cell.extent_km2 for cell in cells],
        }
    )
    long = rows.unpivot(
        on=["change", "extent"],
        index=["site_id", "cell_lat", "cell_lon"],
        variable_name="which",
        value_name="value",
    )
    out = long.select(
        source_id=pl.lit(SOURCE_ID),
        # The atlas cell, in the same vocabulary Phase 1e uses, so the join back to the evidence
        # needs no coordinate matching and no tolerance.
        site_id=pl.col("site_id"),
        period_start=pl.lit(PERIOD_START).str.to_datetime().dt.replace_time_zone("UTC"),
        longitude=pl.col("cell_lon").cast(pl.Float64),
        latitude=pl.col("cell_lat").cast(pl.Float64),
        depth_m=pl.lit(None, dtype=pl.Float64),
        variable=pl.when(pl.col("which") == "change")
        .then(pl.lit(CHANGE_VARIABLE))
        .otherwise(pl.lit(OCCURRENCE_VARIABLE)),
        value=pl.col("value").cast(pl.Float64),
        unit=pl.lit("km2"),
        kind=pl.lit(DriverKind.GRIDDED.value),
        derived_from=pl.lit(f"jrc_gsw:v1_4_2021:{EPOCHS}"),
    )
    schema = DRIVER_SAMPLES.schema
    return out.select(schema.names).to_arrow().cast(schema)


def ingest(root: Path, cells: pl.DataFrame, size_deg: float) -> pa.Table:
    """Aggregate every footprint cell and return the driver table.

    Goes through `catalog.admit` like every other adapter. The never-ingested floor is *not*
    called, matching the other drivers: it screens taxa, and there is no taxon in a water raster.
    Calling it with nothing would trip the guard added for unnamed animal rows, which exists to
    catch a taxon nobody recorded -- not to be answered "none, on purpose" by a satellite composite.
    """
    catalog.admit(SOURCE_ID)

    out: list[CellWater] = []
    for index, (lat, lon) in enumerate(cells.select("cell_lat", "cell_lon").iter_rows(), start=1):
        out.append(read_cell(root, float(lat), float(lon), size_deg))
        if index % 100 == 0:
            log.info("  aggregated %d/%d cells", index, cells.height)

    thin = [cell for cell in out if cell.valid < MIN_USABLE_SHARE]
    if thin:
        log.warning(
            "%d cells are under %.0f%% resolved -- cloud or canopy. Kept and reported rather than "
            "dropped: which cells the sensor could not see is a property of the factor.",
            len(thin),
            MIN_USABLE_SHARE * 100,
        )
    log.info("jrc_gsw: %d cells aggregated", len(out))
    return to_samples(out)
