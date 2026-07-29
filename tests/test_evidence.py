"""Invariants of the evidence core — the things that break quietly when someone adds
an eighth evidence type in a hurry."""

import pyarrow as pa
import pytest

from migratlas.evidence import (
    SPECS,
    EvidenceType,
    Granularity,
    Realm,
    TaxonScope,
    spec_for,
)
from migratlas.evidence.schema import DERIVED_PARTITION_COLUMNS


def test_every_evidence_type_has_a_spec() -> None:
    assert set(SPECS) == set(EvidenceType)


@pytest.mark.parametrize("evidence_type", list(EvidenceType))
def test_spec_carries_the_core_fields(evidence_type: EvidenceType) -> None:
    """Source and taxon identity must be present on every table, uniformly."""
    names = set(spec_for(evidence_type).schema.names)
    assert {"source_id", "realm", "taxon_scope", "taxon_key", "taxon_label"} <= names


@pytest.mark.parametrize("evidence_type", list(EvidenceType))
def test_partition_columns_are_resolvable(evidence_type: EvidenceType) -> None:
    """A partition column must either be in the schema or be a known derived one.

    Caught a real bug: every spec partitioned by ``year`` while no schema declared
    it, so the first write would have failed at runtime.
    """
    spec = spec_for(evidence_type)
    available = set(spec.schema.names) | DERIVED_PARTITION_COLUMNS
    assert set(spec.partition_by) <= available


@pytest.mark.parametrize("evidence_type", list(EvidenceType))
def test_year_partitioning_requires_a_time_column(evidence_type: EvidenceType) -> None:
    """``year`` is derived from the time column, so it cannot be derived without one."""
    spec = spec_for(evidence_type)
    if "year" in spec.partition_by:
        assert spec.time_column is not None


@pytest.mark.parametrize("evidence_type", list(EvidenceType))
def test_time_column_exists_in_schema(evidence_type: EvidenceType) -> None:
    spec = spec_for(evidence_type)
    if spec.time_column is not None:
        assert spec.time_column in spec.schema.names


@pytest.mark.parametrize("evidence_type", list(EvidenceType))
def test_timestamps_are_timezone_aware(evidence_type: EvidenceType) -> None:
    """Phenology is a question about *when*; a naive timestamp is a wrong answer."""
    for field in spec_for(evidence_type).schema:
        if pa.types.is_timestamp(field.type):
            assert field.type.tz == "UTC", f"{evidence_type}.{field.name} is naive"


@pytest.mark.parametrize("evidence_type", list(EvidenceType))
def test_taxon_key_is_nullable_everywhere(evidence_type: EvidenceType) -> None:
    """Radar biomass has no taxon. A schema demanding one would encode a bird bias."""
    assert spec_for(evidence_type).schema.field("taxon_key").nullable


def test_granularity_partitions_the_evidence_types() -> None:
    """Both granularities must be populated, or the policy tables are half dead."""
    by_granularity = {g: [t for t in EvidenceType if t.granularity is g] for g in Granularity}
    assert by_granularity[Granularity.AGGREGATE]
    assert by_granularity[Granularity.INDIVIDUAL]


def test_occurrence_counts_as_individual_granularity() -> None:
    """One observation pins one animal to one place -- which is what makes rare
    species occurrence records sensitive in the first place."""
    assert EvidenceType.OCCURRENCE.granularity is Granularity.INDIVIDUAL


def test_flux_counts_as_aggregate_granularity() -> None:
    assert EvidenceType.FLUX.granularity is Granularity.AGGREGATE


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------
def _minimal_flux_table() -> pa.Table:
    spec = spec_for(EvidenceType.FLUX)
    return pa.table(
        {
            "source_id": ["darkecology"],
            "realm": [Realm.AERIAL.value],
            "taxon_scope": [TaxonScope.UNATTRIBUTED.value],
            "taxon_key": pa.array([None], type=pa.int64()),
            "taxon_label": pa.array([None], type=pa.string()),
            "station_id": ["KBGM"],
            "timestamp": pa.array([1_700_000_000_000], type=pa.timestamp("ms", tz="UTC")),
            "station_longitude": [-75.98],
            "station_latitude": [42.2],
            "height_min_m": [0.0],
            "height_max_m": [200.0],
            "magnitude": [123.4],
            "quantity": ["reflectivity_cm2_km3"],
            "integration_hours": pa.array([None], type=pa.float64()),
            "coverage_fraction": pa.array([None], type=pa.float64()),
            "rain_fraction": pa.array([None], type=pa.float64()),
            "window_kind": pa.array([None], type=pa.string()),
            "direction_deg": pa.array([None], type=pa.float64()),
            "speed_ms": pa.array([None], type=pa.float64()),
            "instrument_generation": ["dual_pol"],
            "quality_flag": pa.array([None], type=pa.string()),
        },
        schema=spec.schema,
    )


def test_validate_accepts_a_conforming_table() -> None:
    spec = spec_for(EvidenceType.FLUX)
    spec.validate(_minimal_flux_table())


def test_validate_rejects_missing_columns() -> None:
    spec = spec_for(EvidenceType.FLUX)
    table = _minimal_flux_table().drop_columns(["magnitude"])
    with pytest.raises(ValueError, match="missing columns"):
        spec.validate(table)


def test_validate_rejects_wrong_types() -> None:
    """A source adapter emitting a plausible-looking string must fail loudly."""
    spec = spec_for(EvidenceType.FLUX)
    table = _minimal_flux_table()
    idx = table.schema.get_field_index("magnitude")
    broken = table.set_column(idx, "magnitude", pa.array(["123.4"], type=pa.string()))
    with pytest.raises(ValueError, match="has type string"):
        spec.validate(broken)
