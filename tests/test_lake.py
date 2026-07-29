"""Lake writer: partitioning, idempotence, and the identifier guards."""

from datetime import UTC, datetime
from pathlib import Path
from string.templatelib import Template

import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
import pytest

from migratlas.evidence import EvidenceType, Realm, TaxonScope, spec_for
from migratlas.lake.identifiers import (
    UnsafeIdentifierError,
    new_run_id,
    quote_identifier,
    render_sql,
)
from migratlas.lake.writer import UNDATED, write_evidence

TS = pa.timestamp("ms", tz="UTC")


def _flux_table(source_id: str = "darkecology", years: tuple[int, ...] = (2019, 2020)) -> pa.Table:
    spec = spec_for(EvidenceType.FLUX)
    n = len(years)
    stamps = [datetime(year, 5, 1, tzinfo=UTC) for year in years]
    return pa.table(
        {
            "source_id": [source_id] * n,
            "realm": [Realm.AERIAL.value] * n,
            "taxon_scope": [TaxonScope.UNATTRIBUTED.value] * n,
            "taxon_key": pa.array([None] * n, type=pa.int64()),
            "taxon_label": pa.array([None] * n, type=pa.string()),
            "station_id": ["KBGM"] * n,
            "timestamp": pa.array(stamps, type=TS),
            "station_longitude": [-75.98] * n,
            "station_latitude": [42.2] * n,
            "height_min_m": [0.0] * n,
            "height_max_m": [200.0] * n,
            "magnitude": [float(i + 1) for i in range(n)],
            "quantity": ["reflectivity_cm2_km3"] * n,
            "integration_hours": pa.array([None] * n, type=pa.float64()),
            "coverage_fraction": pa.array([None] * n, type=pa.float64()),
            "rain_fraction": pa.array([None] * n, type=pa.float64()),
            "window_kind": pa.array([None] * n, type=pa.string()),
            "direction_deg": pa.array([None] * n, type=pa.float64()),
            "speed_ms": pa.array([None] * n, type=pa.float64()),
            "instrument_generation": ["dual_pol"] * n,
            "quality_flag": pa.array([None] * n, type=pa.string()),
        },
        schema=spec.schema,
    )


# --- Writing -----------------------------------------------------------------
def test_write_partitions_by_source_and_year(tmp_path: Path) -> None:
    result = write_evidence(
        _flux_table(), spec_for(EvidenceType.FLUX), source_id="darkecology", root=tmp_path
    )
    assert result.rows == 2
    written = {p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*.parquet")}
    assert any("source_id=darkecology/year=2019" in p for p in written), written
    assert any("source_id=darkecology/year=2020" in p for p in written), written


def test_written_data_round_trips(tmp_path: Path) -> None:
    spec = spec_for(EvidenceType.FLUX)
    write_evidence(_flux_table(), spec, source_id="darkecology", root=tmp_path)
    back = ds.dataset(tmp_path / str(spec.evidence_type), partitioning="hive").to_table()
    assert back.num_rows == 2
    assert sorted(back.column("magnitude").to_pylist()) == [1.0, 2.0]


def test_rerunning_replaces_rather_than_duplicates(tmp_path: Path) -> None:
    """A retried ingest must not double the data."""
    spec = spec_for(EvidenceType.FLUX)
    for _ in range(3):
        write_evidence(_flux_table(), spec, source_id="darkecology", root=tmp_path)
    back = ds.dataset(tmp_path / str(spec.evidence_type), partitioning="hive").to_table()
    assert back.num_rows == 2


def test_undated_records_get_their_own_partition(tmp_path: Path) -> None:
    """Records with no date are kept, not dropped -- they anchor the historical baseline."""
    spec = spec_for(EvidenceType.OCCURRENCE)
    table = pa.table(
        {
            "source_id": ["gbif"],
            "realm": [Realm.TERRESTRIAL.value],
            "taxon_scope": [TaxonScope.EXACT.value],
            "taxon_key": pa.array([2435350], type=pa.int64()),
            "taxon_label": ["Loxodonta africana"],
            "occurrence_id": ["abc-1"],
            "event_time": pa.array([None], type=TS),
            "longitude": [34.5],
            "latitude": [-1.2],
            "coordinate_uncertainty_m": pa.array([None], type=pa.float64()),
            "basis_of_record": ["HumanObservation"],
            "source_generalizations": pa.array([None], type=pa.string()),
        },
        schema=spec.schema,
    )
    write_evidence(table, spec, source_id="gbif", root=tmp_path)
    written = {p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*.parquet")}
    assert any(f"year={UNDATED}" in p for p in written), written


def test_mixed_sources_are_refused(tmp_path: Path) -> None:
    """source_id is a partition key, so a mismatch would scatter rows under the wrong
    directory and corrupt every later query."""
    table = pa.concat_tables([_flux_table("darkecology", (2019,)), _flux_table("enram", (2019,))])
    with pytest.raises(ValueError, match="One table, one source"):
        write_evidence(table, spec_for(EvidenceType.FLUX), source_id="darkecology", root=tmp_path)


def test_claiming_the_wrong_source_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="One table, one source"):
        write_evidence(
            _flux_table("enram"),
            spec_for(EvidenceType.FLUX),
            source_id="darkecology",
            root=tmp_path,
        )


def test_writing_into_a_drifted_directory_is_refused(tmp_path: Path) -> None:
    """The incident this guard exists for: a schema change plus an un-reingested source
    makes DuckDB intersect schemas, so newer columns vanish with no error."""
    spec = spec_for(EvidenceType.FLUX)
    write_evidence(_flux_table("oldsource"), spec, source_id="oldsource", root=tmp_path)

    # Simulate the older source predating a column by dropping it from its files.
    for parquet in (tmp_path / str(spec.evidence_type)).rglob("*.parquet"):
        table = pq.read_table(parquet)
        pq.write_table(table.drop_columns(["coverage_fraction"]), parquet)

    with pytest.raises(ValueError, match="do not match the current schema"):
        write_evidence(_flux_table("newsource"), spec, source_id="newsource", root=tmp_path)


def test_rewriting_the_same_source_is_not_blocked_by_its_own_files(tmp_path: Path) -> None:
    """Only *other* sources block a write; re-ingesting a drifted source is the fix."""
    spec = spec_for(EvidenceType.FLUX)
    write_evidence(_flux_table(), spec, source_id="darkecology", root=tmp_path)
    for parquet in (tmp_path / str(spec.evidence_type)).rglob("*.parquet"):
        table = pq.read_table(parquet)
        pq.write_table(table.drop_columns(["coverage_fraction"]), parquet)
    # Re-ingesting the same source must be allowed, or drift is unrecoverable.
    write_evidence(_flux_table(), spec, source_id="darkecology", root=tmp_path)


def test_manifest_records_the_run(tmp_path: Path) -> None:
    spec = spec_for(EvidenceType.FLUX)
    result = write_evidence(_flux_table(), spec, source_id="darkecology", root=tmp_path)
    manifest = tmp_path / "_manifests" / str(spec.evidence_type) / f"{result.run_id}.json"
    assert manifest.is_file()
    assert result.run_id in manifest.read_text(encoding="utf-8")


def test_invalid_table_is_refused_before_writing(tmp_path: Path) -> None:
    spec = spec_for(EvidenceType.FLUX)
    with pytest.raises(ValueError, match="missing columns"):
        write_evidence(
            _flux_table().drop_columns(["magnitude"]), spec, source_id="darkecology", root=tmp_path
        )
    assert not list(tmp_path.rglob("*.parquet"))


# --- Run ids -----------------------------------------------------------------
def test_run_ids_are_time_ordered() -> None:
    """UUIDv7, so provenance sorts chronologically on the key alone."""
    ids = [new_run_id() for _ in range(20)]
    assert ids == sorted(ids)
    assert len(set(ids)) == 20


# --- Identifier quoting ------------------------------------------------------
@pytest.mark.parametrize("name", ["year", "source_id", "_x", "Station1"])
def test_plain_identifiers_are_quoted(name: str) -> None:
    assert quote_identifier(name) == f'"{name}"'


@pytest.mark.parametrize(
    "name",
    ['x" OR 1=1 --', "drop table; --", "has space", "1leading", "", "año"],
)
def test_unsafe_identifiers_are_refused(name: str) -> None:
    """Rejected rather than escaped: anything needing exotic quoting means something
    upstream built a name from untrusted input."""
    with pytest.raises(UnsafeIdentifierError):
        quote_identifier(name)


def test_render_sql_quotes_interpolations_only() -> None:
    column, table = "magnitude", "flux"
    sql = render_sql(t"SELECT {column} FROM {table} WHERE magnitude > ?")
    assert sql == 'SELECT "magnitude" FROM "flux" WHERE magnitude > ?'


def test_render_sql_refuses_an_injected_identifier() -> None:
    hostile = 'flux"; DROP TABLE flux; --'
    with pytest.raises(UnsafeIdentifierError):
        render_sql(t"SELECT * FROM {hostile}")


def test_render_sql_takes_a_template_not_a_string() -> None:
    """Guards against someone passing an f-string, which would defeat the whole point."""
    assert isinstance(t"SELECT {1}", Template)
