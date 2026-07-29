"""Drivers that came measured alongside the animal observation.

FISHGLOB records sea-surface and bottom temperature at every haul, which is a better driver than
any reanalysis for the same purpose: it is the water the fish were actually in, at the hour they
were caught, with no interpolation between it and them. Phase 2a would otherwise sample a gridded
product at the haul position and inherit that product's biases in exactly the coastal shelf waters
where reanalysis is weakest.
"""

import logging
from typing import TYPE_CHECKING, Final

import polars as pl

from migratlas.drivers.schema import DRIVER_SAMPLES
from migratlas.lake.writer import WriteResult, write_table

if TYPE_CHECKING:
    import pyarrow as pa

log = logging.getLogger(__name__)

# Both are degrees Celsius in FISHGLOB, and both arrive as strings in some surveys.
VARIABLES: Final[dict[str, tuple[str, str]]] = {
    "sst": ("sea_surface_temperature", "degC"),
    "sbt": ("sea_bottom_temperature", "degC"),
}

# Physical plausibility. Sea temperature outside this is a parsing error or a sentinel value, not
# an ocean -- and a single -9999 would wreck any weighted mean it entered.
PLAUSIBLE: Final[tuple[float, float]] = (-3.0, 40.0)


def to_samples(hauls: pl.DataFrame, source_id: str) -> pa.Table:
    """Melt per-haul temperature columns into driver rows, one per variable.

    Expects one row per haul, not per haul-and-species: FISHGLOB repeats the haul's temperature
    on every species row, and writing all of them would multiply the table by the catch list.
    """
    present = [column for column in VARIABLES if column in hauls.columns]
    if not present:
        msg = f"{source_id}: none of {sorted(VARIABLES)} are present"
        raise ValueError(msg)

    frames = []
    for column in present:
        variable, unit = VARIABLES[column]
        frame = (
            hauls.select(
                source_id=pl.lit(source_id),
                site_id=pl.col("site_id"),
                period_start=pl.col("period_start"),
                longitude=pl.col("longitude").cast(pl.Float64),
                latitude=pl.col("latitude").cast(pl.Float64),
                # Surface readings sit at the surface; a bottom reading sits at the haul's depth.
                depth_m=(pl.col("depth").cast(pl.Float64) if column == "sbt" else pl.lit(0.0)).cast(
                    pl.Float64
                ),
                variable=pl.lit(variable),
                value=pl.col(column).cast(pl.String).cast(pl.Float64, strict=False),
                unit=pl.lit(unit),
                measured=pl.lit(value=True),
            )
            .drop_nulls("value")
            .filter(pl.col("value").is_between(*PLAUSIBLE))
        )
        log.info("  %s: %d usable readings", variable, frame.height)
        frames.append(frame)

    out = pl.concat(frames)
    schema = DRIVER_SAMPLES.schema
    return out.select(schema.names).to_arrow().cast(schema)


def write(hauls: pl.DataFrame, source_id: str) -> WriteResult:
    """Land one source's in-situ driver readings."""
    table = to_samples(hauls, source_id)
    log.info("%d driver samples from %d hauls", table.num_rows, hauls.height)
    return write_table(table, DRIVER_SAMPLES, source_id=source_id)
