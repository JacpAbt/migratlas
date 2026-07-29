"""Canonical Arrow schemas. Sources are adapted into these; nothing downstream sees
a source's native column names."""

from typing import TYPE_CHECKING, Final, NamedTuple

import pyarrow as pa

from migratlas.evidence.types import EvidenceType

if TYPE_CHECKING:
    from collections.abc import Mapping

# UTC-aware throughout. Phenology is a question about *when*, so a naive timestamp is
# a wrong answer waiting to happen at a DST boundary.
_TS = pa.timestamp("ms", tz="UTC")

# Computed at write time rather than stored, so it cannot drift from the time column.
DERIVED_PARTITION_COLUMNS: Final[frozenset[str]] = frozenset({"year"})

_CORE_FIELDS: Final[tuple[pa.Field, ...]] = (
    pa.field("source_id", pa.string(), nullable=False),
    pa.field("realm", pa.string(), nullable=False),
    pa.field("taxon_scope", pa.string(), nullable=False),
    # Nullable on purpose: radar biomass has no taxon. A schema requiring one here
    # would encode the assumption that every signal belongs to a known species.
    pa.field("taxon_key", pa.int64(), nullable=True),
    # Verbatim source label, kept for auditing the crosswalk.
    pa.field("taxon_label", pa.string(), nullable=True),
)


class EvidenceSpec(NamedTuple):
    """Schema, partitioning and time column for one evidence type."""

    evidence_type: EvidenceType
    schema: pa.Schema
    partition_by: tuple[str, ...]
    time_column: str | None
    """Column phenology metrics read. ``None`` for paired-event types."""

    value_column: str | None
    """Column holding the measurement. ``None`` for types that record a presence rather
    than a quantity, so a metric can refuse them instead of inventing a value of 1."""

    @property
    def name(self) -> str:
        """Directory name under the lake root, which satisfies ``lake.spec.TableSpec``."""
        return str(self.evidence_type)

    def validate(self, table: pa.Table) -> None:
        """Raise if ``table`` does not conform.

        Checks rather than casts, so an adapter emitting a plausible-looking string
        fails at ingest instead of silently coercing.
        """
        missing = set(self.schema.names) - set(table.schema.names)
        if missing:
            msg = f"{self.evidence_type} table is missing columns: {sorted(missing)}"
            raise ValueError(msg)

        for field in self.schema:
            actual = table.schema.field(field.name)
            if actual.type != field.type:
                msg = (
                    f"{self.evidence_type}.{field.name} has type {actual.type}, "
                    f"expected {field.type}"
                )
                raise ValueError(msg)
            if not field.nullable and table.num_rows and table.column(field.name).null_count:
                msg = f"{self.evidence_type}.{field.name} is non-nullable but contains nulls"
                raise ValueError(msg)


def _spec(
    evidence_type: EvidenceType,
    fields: tuple[pa.Field, ...],
    *,
    partition_by: tuple[str, ...],
    time_column: str | None,
    value_column: str | None = None,
) -> EvidenceSpec:
    return EvidenceSpec(
        evidence_type=evidence_type,
        schema=pa.schema([*_CORE_FIELDS, *fields]),
        partition_by=partition_by,
        time_column=time_column,
        value_column=value_column,
    )


TRACK = _spec(
    EvidenceType.TRACK,
    (
        pa.field("individual_id", pa.string(), nullable=False),
        pa.field("timestamp", _TS, nullable=False),
        pa.field("longitude", pa.float64(), nullable=False),
        pa.field("latitude", pa.float64(), nullable=False),
        pa.field("altitude_m", pa.float64(), nullable=True),
        # Argos classes and GPS fixes differ by orders of magnitude; a model ignoring
        # this reads a 10 km error as a real movement.
        pa.field("location_error_m", pa.float64(), nullable=True),
        pa.field("sensor_type", pa.string(), nullable=True),
    ),
    partition_by=("source_id", "year"),
    time_column="timestamp",
)

OCCURRENCE = _spec(
    EvidenceType.OCCURRENCE,
    (
        pa.field("occurrence_id", pa.string(), nullable=False),
        # Nullable: many museum and literature records carry a year and nothing finer.
        # Dropping them would bias the historical baseline change detection needs.
        pa.field("event_time", _TS, nullable=True),
        pa.field("longitude", pa.float64(), nullable=False),
        pa.field("latitude", pa.float64(), nullable=False),
        pa.field("coordinate_uncertainty_m", pa.float64(), nullable=True),
        pa.field("basis_of_record", pa.string(), nullable=True),
        # Generalisation the *publisher* already applied. Distinct from ours, and must
        # survive into published metadata.
        pa.field("source_generalizations", pa.string(), nullable=True),
    ),
    partition_by=("source_id", "year"),
    time_column="event_time",
)

ABUNDANCE_SURFACE = _spec(
    EvidenceType.ABUNDANCE_SURFACE,
    (
        # Cell centre. Always populated, whatever the grid system, so a consumer that only
        # wants a point does not need to understand H3 or geohash.
        pa.field("cell_longitude", pa.float64(), nullable=False),
        pa.field("cell_latitude", pa.float64(), nullable=False),
        # Nullable: only meaningful for a degree grid. H3 hexagons and geohashes have no
        # single degree size, and inventing one would misstate the geometry.
        pa.field("cell_size_deg", pa.float64(), nullable=True),
        # Native cell identifier and the system that issued it, e.g. "h3_7". Assuming every
        # gridded product is a degree grid would be the same kind of baked-in assumption
        # this core exists to avoid.
        pa.field("cell_id", pa.string(), nullable=True),
        pa.field("cell_system", pa.string(), nullable=True),
        pa.field("period_start", _TS, nullable=False),
        pa.field("period_end", _TS, nullable=False),
        pa.field("value", pa.float64(), nullable=False),
        # Relative abundance, individual counts and residency proportions are
        # different quantities and must never be summed together.
        pa.field("value_kind", pa.string(), nullable=False),
        pa.field("value_lower", pa.float64(), nullable=True),
        pa.field("value_upper", pa.float64(), nullable=True),
    ),
    partition_by=("source_id", "year"),
    time_column="period_start",
    value_column="value",
)

FLUX = _spec(
    EvidenceType.FLUX,
    (
        pa.field("station_id", pa.string(), nullable=False),
        pa.field("timestamp", _TS, nullable=False),
        pa.field("station_longitude", pa.float64(), nullable=False),
        pa.field("station_latitude", pa.float64(), nullable=False),
        pa.field("height_min_m", pa.float64(), nullable=True),
        pa.field("height_max_m", pa.float64(), nullable=True),
        pa.field("magnitude", pa.float64(), nullable=False),
        pa.field("quantity", pa.string(), nullable=False),
        # Null for an instantaneous measurement; set when `magnitude` is integrated over
        # a window. Night length varies with latitude and season, so a nightly total is
        # uninterpretable without it.
        pa.field("integration_hours", pa.float64(), nullable=True),
        # Which window: "night", "day", "utc_calendar_day". Orthogonal to `quantity`,
        # which names the physical measurement -- and the day window is a useful placebo,
        # since a trend in daytime passage points at the instrument, not migration.
        # Not called `window`: that is a reserved word in DuckDB and would need quoting
        # in every query, ad-hoc ones included.
        pa.field("window_kind", pa.string(), nullable=True),
        # How complete the measurement was, 0-1. Nights with sparse coverage have to be
        # excluded from phenology or they drag passage-date quantiles around.
        pa.field("coverage_fraction", pa.float64(), nullable=True),
        pa.field("direction_deg", pa.float64(), nullable=True),
        pa.field("speed_ms", pa.float64(), nullable=True),
        # Instrument upgrades masquerade as biological trends. Carrying a hardware
        # generation per record is what makes that break testable at all.
        pa.field("instrument_generation", pa.string(), nullable=True),
        pa.field("quality_flag", pa.string(), nullable=True),
    ),
    partition_by=("source_id", "year"),
    time_column="timestamp",
    value_column="magnitude",
)

DETECTION = _spec(
    EvidenceType.DETECTION,
    (
        pa.field("station_id", pa.string(), nullable=False),
        pa.field("timestamp", _TS, nullable=False),
        pa.field("station_longitude", pa.float64(), nullable=False),
        pa.field("station_latitude", pa.float64(), nullable=False),
        # Null for unmarked detections, e.g. an unidentified camera-trap animal.
        pa.field("individual_id", pa.string(), nullable=True),
        pa.field("detection_count", pa.int64(), nullable=True),
        pa.field("station_location_generalized", pa.bool_(), nullable=True),
    ),
    partition_by=("source_id", "year"),
    time_column="timestamp",
    value_column="detection_count",
)

MARK_RECAPTURE = _spec(
    EvidenceType.MARK_RECAPTURE,
    (
        pa.field("individual_id", pa.string(), nullable=False),
        pa.field("mark_time", _TS, nullable=True),
        pa.field("mark_longitude", pa.float64(), nullable=False),
        pa.field("mark_latitude", pa.float64(), nullable=False),
        pa.field("encounter_time", _TS, nullable=True),
        pa.field("encounter_longitude", pa.float64(), nullable=False),
        pa.field("encounter_latitude", pa.float64(), nullable=False),
        pa.field("encounter_condition", pa.string(), nullable=True),
    ),
    # Two timestamps and no single natural ordering, so metrics must be told which
    # end they mean rather than guessing.
    partition_by=("source_id",),
    time_column=None,
)

SURVEY_INDEX = _spec(
    EvidenceType.SURVEY_INDEX,
    (
        pa.field("site_id", pa.string(), nullable=False),
        pa.field("period_start", _TS, nullable=False),
        pa.field("period_end", _TS, nullable=False),
        pa.field("site_longitude", pa.float64(), nullable=False),
        pa.field("site_latitude", pa.float64(), nullable=False),
        # Depth of the site, where the scheme records it. Nullable because a terrestrial or
        # aerial survey has no such thing -- but for a marine survey it is not optional detail:
        # species answer warming by moving deeper about as often as by moving poleward, and a
        # schema without it would let a real depth response look like no response.
        pa.field("site_depth_m", pa.float64(), nullable=True),
        pa.field("count", pa.float64(), nullable=False),
        # A count without effort is uninterpretable, but many historical schemes did
        # not record it, so models must handle its absence.
        pa.field("effort", pa.float64(), nullable=True),
        pa.field("effort_unit", pa.string(), nullable=True),
        pa.field("protocol", pa.string(), nullable=True),
    ),
    partition_by=("source_id", "year"),
    time_column="period_start",
    value_column="count",
)


SPECS: Final[Mapping[EvidenceType, EvidenceSpec]] = {
    spec.evidence_type: spec
    for spec in (
        TRACK,
        OCCURRENCE,
        ABUNDANCE_SURFACE,
        FLUX,
        DETECTION,
        MARK_RECAPTURE,
        SURVEY_INDEX,
    )
}


def spec_for(evidence_type: EvidenceType) -> EvidenceSpec:
    """Return the canonical spec for ``evidence_type``."""
    return SPECS[evidence_type]
