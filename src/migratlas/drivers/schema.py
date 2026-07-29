"""One table for every environmental driver, however it was obtained.

Long format -- one row per site-visit per variable -- rather than a column per variable, because
the set of drivers is open. Sea-surface temperature arrives measured alongside a trawl haul today;
850 hPa wind support will arrive sampled out of a reanalysis raster tomorrow, and chlorophyll after
that. A wide table would need a schema change per driver, and every schema change means
re-ingesting every source that predates it.

Deliberately not an evidence type. A sea-surface temperature is a fact about water, not about an
animal, and the seven evidence types are the shapes animal observations come in. Keeping drivers
out of that vocabulary is what lets the ethics gate stay a statement about animals.

``measured`` is the field that stops the two kinds being confused. An in-situ reading taken at the
haul is the ground truth a reanalysis is validated against; if a later analysis mixes them without
noticing, its residuals become a story about interpolation.
"""

from typing import Final, NamedTuple

import pyarrow as pa

_TS: Final = pa.timestamp("ms", tz="UTC")


class DriverSpec(NamedTuple):
    """Schema and partitioning for the driver table. Satisfies ``lake.spec.TableSpec``."""

    name: str
    schema: pa.Schema
    partition_by: tuple[str, ...]
    time_column: str | None

    def validate(self, table: pa.Table) -> None:
        """Raise if ``table`` does not conform.

        Checks rather than casts, exactly as the evidence specs do: an adapter emitting a
        plausible-looking string should fail here, not be silently coerced.
        """
        missing = set(self.schema.names) - set(table.schema.names)
        if missing:
            msg = f"{self.name} table is missing columns: {sorted(missing)}"
            raise ValueError(msg)
        for field in self.schema:
            actual = table.schema.field(field.name)
            if actual.type != field.type:
                msg = f"{self.name}.{field.name} has type {actual.type}, expected {field.type}"
                raise ValueError(msg)


DRIVER_SAMPLES: Final = DriverSpec(
    name="driver_samples",
    schema=pa.schema(
        (
            pa.field("source_id", pa.string(), nullable=False),
            # Which observation this driver belongs to, in the source's own site vocabulary, so a
            # join back to the evidence needs no coordinate matching and no tolerance.
            pa.field("site_id", pa.string(), nullable=False),
            pa.field("period_start", _TS, nullable=False),
            pa.field("longitude", pa.float64(), nullable=False),
            pa.field("latitude", pa.float64(), nullable=False),
            # Where in the water or air column. Null for a surface or column-integrated quantity.
            pa.field("depth_m", pa.float64(), nullable=True),
            pa.field("variable", pa.string(), nullable=False),
            pa.field("value", pa.float64(), nullable=False),
            pa.field("unit", pa.string(), nullable=False),
            # True for an instrument reading at the site, false for a value sampled out of a
            # gridded product. Never mix the two in one regression without saying so.
            pa.field("measured", pa.bool_(), nullable=False),
        )
    ),
    partition_by=("source_id", "year"),
    time_column="period_start",
)
