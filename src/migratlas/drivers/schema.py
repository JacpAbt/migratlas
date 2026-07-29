"""One table for every environmental driver, however it was obtained.

Long format -- one row per site-visit per variable -- rather than a column per variable, because
the set of drivers is open. Sea-surface temperature arrives measured alongside a trawl haul today;
850 hPa wind support will arrive sampled out of a reanalysis raster tomorrow, and chlorophyll after
that. A wide table would need a schema change per driver, and every schema change means
re-ingesting every source that predates it.

Deliberately not an evidence type. A sea-surface temperature is a fact about water, not about an
animal, and the seven evidence types are the shapes animal observations come in. Keeping drivers
out of that vocabulary is what lets the ethics gate stay a statement about animals.

``kind`` is the field that stops different things being confused. An in-situ reading at the haul is
the ground truth a reanalysis is validated against, and mixing them silently turns a model's
residuals into a story about interpolation. A *derived* driver is a third thing again: an index
computed from this lake's own evidence, which is how an indirect pathway gets represented at all.

That third kind is not a hypothetical. A seabird's migration can change because warmer water pushed
plankton deeper, so forage fish left, so there was nothing to eat -- the driver of the bird's
movement is a water temperature acting through two intermediate populations. Representing that
means being able to write "abundance of this fish, here, this year" as a driver of something else,
with the taxon it came from recorded. ``derived_from`` carries that so a driver can never be traced
to nowhere.
"""

from enum import StrEnum
from typing import Final, NamedTuple

import pyarrow as pa

_TS: Final = pa.timestamp("ms", tz="UTC")


class DriverKind(StrEnum):
    """Where a driver value came from. Never mix these in one regression silently."""

    MEASURED = "measured"
    """An instrument reading at the site itself."""

    GRIDDED = "gridded"
    """Sampled out of a reanalysis or satellite product at the site's position and time."""

    DERIVED = "derived"
    """An index computed from this lake's own evidence -- how an indirect pathway is expressed."""


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
            # "measured": an instrument reading at the site. "gridded": sampled out of a
            # reanalysis or satellite product at the site's position and time. "derived": an
            # index computed from this lake's own evidence, which is how a trophic pathway is
            # expressed -- one population's abundance as a driver of another's movement.
            pa.field("kind", pa.string(), nullable=False),
            # For a derived driver, what it was computed from: the source and taxon, so a
            # pathway can be traced back to the observations behind it rather than asserted.
            pa.field("derived_from", pa.string(), nullable=True),
        )
    ),
    partition_by=("source_id", "year"),
    time_column="period_start",
)
